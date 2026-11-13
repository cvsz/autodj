"""Configuration file watcher for hot reload support.

Uses watchdog to monitor config.toml for changes and triggers
validated reload callbacks. Designed for production use with
debouncing, validation, and thread-safe callbacks.

Uses PollingObserver for cross-platform reliability (works in containers
and network filesystems where inotify may not be available).
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Callable, Optional

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers.polling import PollingObserver as Observer

    WATCHDOG_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    WATCHDOG_AVAILABLE = False
    Observer = object  # type: ignore
    FileSystemEventHandler = object  # type: ignore
    FileSystemEvent = object  # type: ignore

from .config import Config, ConfigError

log = logging.getLogger("autodj")


class ConfigWatcher:
    """Watch a config file for changes and invoke callbacks with validated config.

    Features:
    - Debounces rapid file writes (default 500ms)
    - Validates new config before invoking callbacks
    - Thread-safe callback invocation
    - Automatic fallback to previous valid config on validation failure
    """

    def __init__(
        self,
        config_path: str,
        *,
        debounce_ms: int = 500,
        polling_interval: float = 0.5,
        validate: bool = True,
    ):
        """
        Args:
            config_path: Path to config.toml to watch
            debounce_ms: Milliseconds to wait after last write before processing
            polling_interval: Seconds between filesystem polls (PollingObserver timeout)
            validate: Whether to validate config before callback (should always be True)
        """
        if not WATCHDOG_AVAILABLE:
            raise RuntimeError(
                "watchdog is not installed. Install with: pip install 'camfrog-autodj[hotreload]'"
            )

        self.config_path = Path(config_path).resolve()
        self.debounce_ms = debounce_ms
        self.polling_interval = polling_interval
        self.validate = validate

        self._observer: Optional[Observer] = None
        self._callbacks: list[Callable[[Config], None]] = []
        self._callbacks_lock = threading.Lock()
        self._last_valid_config: Optional[Config] = None
        self._config_lock = threading.Lock()
        self._debounce_timer: Optional[threading.Timer] = None
        self._debounce_lock = threading.Lock()
        self._pending_reload = False
        self._stopped = False

    def on_change(self, callback: Callable[[Config], None]) -> None:
        """Register a callback to be invoked when config changes and validates.

        The callback receives the new Config instance. Callbacks are invoked
        in registration order. Exceptions in callbacks are logged but do not
        stop other callbacks.
        """
        with self._callbacks_lock:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[Config], None]) -> bool:
        """Remove a previously registered callback. Returns True if found."""
        with self._callbacks_lock:
            try:
                self._callbacks.remove(callback)
                return True
            except ValueError:
                return False

    def start(self, initial_config: Optional[Config] = None) -> None:
        """Start watching the config file.

        Args:
            initial_config: Optional initial config to use as the last known valid.
                           If not provided, loads from config_path.
        """
        if self._stopped:
            log.warning("ConfigWatcher.start() called after stop(); ignoring")
            return

        if initial_config is not None:
            with self._config_lock:
                self._last_valid_config = initial_config
        else:
            try:
                with self._config_lock:
                    self._last_valid_config = Config.load(str(self.config_path))
            except ConfigError as ex:
                log.error("ConfigWatcher: initial config load failed: %s", ex)
                # Will try again on first file change

        # Set up watchdog observer
        event_handler = _ConfigFileHandler(self)
        self._observer = Observer(timeout=self.polling_interval)
        self._observer.schedule(
            event_handler,
            str(self.config_path.parent),
            recursive=False,
        )
        self._observer.start()
        log.info(
            "ConfigWatcher started for %s (polling interval: %.1fs)",
            self.config_path,
            self.polling_interval,
        )

    def stop(self) -> None:
        """Stop watching and clean up resources."""
        self._stopped = True
        # Cancel any pending debounce timer
        with self._debounce_lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
                self._debounce_timer = None
        # Stop observer
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=2.0)
            self._observer = None
        log.info("ConfigWatcher stopped")

    def _trigger_reload(self) -> None:
        """Trigger a config reload (called by file handler after debounce)."""
        if self._stopped:
            return

        try:
            new_config = Config.load(str(self.config_path))
        except ConfigError as ex:
            log.error(
                "ConfigWatcher: config validation failed, keeping previous config: %s",
                ex,
            )
            # Notify callbacks of validation failure with old config (if any)
            self._notify_callbacks_failed(str(ex))
            return

        with self._config_lock:
            self._last_valid_config = new_config

        log.info("ConfigWatcher: config reloaded successfully from %s", self.config_path)
        self._notify_callbacks(new_config)

    def _notify_callbacks(self, config: Config) -> None:
        """Invoke all registered callbacks with the new config."""
        with self._callbacks_lock:
            callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                cb(config)
            except Exception:
                log.exception("ConfigWatcher callback failed")

    def _notify_callbacks_failed(self, error: str) -> None:
        """Notify callbacks of validation failure (pass error info)."""
        # For now, just log. Could extend to pass error to callbacks.
        log.warning("ConfigWatcher: validation failed: %s", error)

    @property
    def last_valid_config(self) -> Optional[Config]:
        """Get the last successfully validated config."""
        with self._config_lock:
            return self._last_valid_config

    def force_reload(self) -> Optional[Config]:
        """Force an immediate reload (bypasses debounce). Returns new config or None on failure."""
        if self._stopped:
            return None
        try:
            new_config = Config.load(str(self.config_path))
        except ConfigError as ex:
            log.error("ConfigWatcher: force_reload validation failed: %s", ex)
            return None
        with self._config_lock:
            self._last_valid_config = new_config
        self._notify_callbacks(new_config)
        return new_config


class _ConfigFileHandler(FileSystemEventHandler):
    """Watchdog event handler for config file changes.

    Uses FileSystemEventHandler instead of PatternMatchingEventHandler
    for compatibility with PollingObserver.
    """

    def __init__(self, watcher: ConfigWatcher):
        super().__init__()
        self._watcher = watcher
        self._target_name = watcher.config_path.name
        self._last_event_time = 0.0

    def _should_handle(self, path: str | bytes) -> bool:
        """Check if the event is for our target config file."""
        if isinstance(path, bytes):
            path = path.decode("utf-8", errors="replace")
        return Path(path).name == self._target_name

    def _schedule_reload(self) -> None:
        """Schedule a reload after the debounce period.

        Cancels any existing timer and starts a new one.
        """
        with self._watcher._debounce_lock:
            if self._watcher._debounce_timer is not None:
                self._watcher._debounce_timer.cancel()
            self._watcher._debounce_timer = threading.Timer(
                self._watcher.debounce_ms / 1000.0,
                self._watcher._trigger_reload,
            )
            self._watcher._debounce_timer.daemon = True
            self._watcher._debounce_timer.start()

    def _handle_event(self, event: FileSystemEvent) -> None:
        """Common handler for all relevant event types."""
        if event.is_directory:
            return
        if not self._should_handle(event.src_path):
            return
        # Always schedule a reload (debounced)
        self._schedule_reload()
        self._last_event_time = time.monotonic() * 1000

    def on_modified(self, event: FileSystemEvent) -> None:
        self._handle_event(event)

    def on_created(self, event: FileSystemEvent) -> None:
        # Handle atomic writes (rename creates new file)
        self._handle_event(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        # Handle atomic writes (rename deletes old file)
        # Schedule reload for the subsequent create event
        if self._should_handle(event.src_path):
            self._last_event_time = time.monotonic() * 1000

    def on_moved(self, event: FileSystemEvent) -> None:
        # Handle atomic writes (write to .tmp then rename)
        if event.is_directory:
            return
        if hasattr(event, "dest_path") and self._should_handle(event.dest_path):
            self._handle_event(event)
