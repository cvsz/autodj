# Full Enterprise Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform CamfrogAutoDJ into a production-grade, enterprise-ready music bot with optimized performance, enhanced type safety, robust error handling, clean architecture, comprehensive observability, and complete documentation.

**Architecture:** Modular refactoring of the existing monolithic modules (engine.py 1700+ lines, gui.py 3000+ lines) into focused, single-responsibility components while preserving all existing functionality. Add circuit breaker patterns, structured logging, metrics collection, and improved concurrency controls.

**Tech Stack:** Python 3.11+, yt-dlp, mpv, pywinauto (Windows), tkinter (GUI), pytest, ruff, mypy, pyinstaller

**Spec:** AGENTS.md, README.md, ROADMAP.md, SECURITY.md, CONTRIBUTING.md

## Global Constraints

- Python 3.11+ only (modern typing, pattern matching, exception groups)
- No breaking changes to public CLI, config.toml schema, or plugin interfaces
- All existing tests must pass (450+ tests)
- Ruff, mypy, pytest must remain green
- Windows primary, Linux headless compatible
- No `shell=True`, no `pickle`/`yaml.load`, fail-closed config validation
- Atomic writes with .bak backup for all config/data files
- GPG-signed commits, PR review by independent account

## Review Focus

1. **Concurrency races**: Engine GUI callbacks (`tk.after`) vs. background threads — verify no Tkinter calls from non-main threads
2. **IPC resource leaks**: mpv named pipes/sockets — verify cleanup on crash, shutdown, skip, timeout
3. **Config migration edge cases**: Relocation to APPDATA, atomic writes, permission errors — verify no data loss
4. **Chat send storms**: Circuit breaker, rate limiting, backpressure — verify room not flooded
5. **Playlist corruption**: Concurrent writes, power loss mid-write — verify .bak recovery and atomic replace

---

### Task 1: Core Type System & Protocols

**Files:**
- Create: `camfrog_autodj/protocols.py`
- Modify: `camfrog_autodj/__init__.py:1-50`
- Test: `tests/test_protocols.py`

**Interfaces:**
- Consumes: None (foundation)
- Produces: Protocol interfaces for `ChatAdapter`, `Player`, `PlaylistStore`, `LocalIndex`, `Renderer`

- [ ] **Step 1: Write failing tests for protocol conformance**

```python
def test_chat_adapter_protocol():
    from camfrog_autodj.protocols import ChatAdapter
    # Verify base classes implement protocol
    from camfrog_autodj.adapters.uia import UiaAdapter
    from camfrog_autodj.adapters.console import ConsoleAdapter
    from camfrog_autodj.adapters.logtail import LogTailAdapter
    from camfrog_autodj.adapters import NullAdapter
    for cls in (UiaAdapter, ConsoleAdapter, LogTailAdapter, NullAdapter):
        assert issubclass(cls, ChatAdapter)

def test_player_protocol():
    from camfrog_autodj.protocols import Player
    from camfrog_autodj.player import MpvPlayer
    assert issubclass(MpvPlayer, Player)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_protocols.py -v`
Expected: FAIL - protocols.py doesn't exist

- [ ] **Step 3: Create `camfrog_autodj/protocols.py` with Protocol definitions**

```python
from __future__ import annotations
from abc import abstractmethod
from collections.abc import Iterator
from typing import Protocol
from .models import Track

class ChatAdapter(Protocol):
    @abstractmethod
    def messages(self) -> Iterator[ChatMessage]: ...
    @abstractmethod
    def send(self, text: str) -> None: ...
    def close(self) -> None: ...

class Player(Protocol):
    @abstractmethod
    def play(self, source: str, volume: int, duration: float | None) -> bool: ...
    @abstractmethod
    def stop(self) -> None: ...
    @abstractmethod
    def set_pause(self, v: bool) -> bool: ...
    @abstractmethod
    def set_volume(self, v: int) -> bool: ...
    @abstractmethod
    def seek(self, seconds: float) -> bool: ...
    @abstractmethod
    def get_time_pos(self) -> float | None: ...
    @abstractmethod
    def play_file(self, path: str) -> None: ...
    @property
    @abstractmethod
    def available(self) -> bool: ...

class PlaylistStore(Protocol):
    @abstractmethod
    def load(self) -> list[Track]: ...
    @abstractmethod
    def add(self, tracks: list[Track]) -> int: ...
    @abstractmethod
    def update_source(self, old_source: str, new_track: Track) -> bool: ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_protocols.py -v`
Expected: PASS

- [ ] **Step 5: Update `__init__.py` to export protocols**

```python
from .protocols import ChatAdapter, Player, PlaylistStore, LocalIndex, Renderer
__all__ = [..., "ChatAdapter", "Player", "PlaylistStore", "LocalIndex", "Renderer"]
```

- [ ] **Step 6: Commit**

```bash
git add camfrog_autodj/protocols.py camfrog_autodj/__init__.py tests/test_protocols.py
git commit -m "feat: add Protocol interfaces for core abstractions"
```

---

### Task 2: Structured Exception Hierarchy Enhancement

**Files:**
- Modify: `camfrog_autodj/exceptions.py:1-333`
- Create: `camfrog_autodj/exceptions/context.py`
- Test: `tests/test_exceptions.py`

**Interfaces:**
- Consumes: Task 1 protocols
- Produces: Enhanced exception classes with structured context, error codes, recovery hints

- [ ] **Step 1: Write failing tests for exception enhancements**

```python
def test_exception_context_serialization():
    from camfrog_autodj.exceptions import PlayerHungError
    exc = PlayerHungError("track hung", details="mpv timeout", context={"source": "yt", "duration": 300})
    assert exc.code == "player.hung"
    assert exc.context["source"] == "yt"
    assert exc.to_dict() == {"code": "...", "message": "...", "details": "...", "context": {...}}

def test_exception_recovery_hints():
    from camfrog_autodj.exceptions import ConfigValidationError
    exc = ConfigValidationError("bad value", field="volume")
    assert exc.recovery_hint == "Set volume to 0-100 in config.toml"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_exceptions.py -v`
Expected: FAIL - new methods don't exist

- [ ] **Step 3: Enhance `exceptions.py` with `to_dict()`, `recovery_hint`, exception groups**

```python
class AutoDJError(Exception):
    ...
    def to_dict(self) -> dict:
        return {"code": self.code, "message": str(self), "details": self.details, "context": self.context}
    
    @property
    def recovery_hint(self) -> str | None:
        hints = {
            "config.validation": "Check config.toml syntax and value ranges",
            "player.hung": "Increase mpv_timeout or check mpv installation",
            "chat.send_failed": "Verify Camfrog window is open and bot has focus",
            "library.yt_dlp_missing": "Install yt-dlp next to mpv or set ytdlp_path",
        }
        return hints.get(self.code)
```

- [ ] **Step 4: Add exception grouping for batch operations**

```python
class BatchOperationError(AutoDJError):
    """Multiple errors during a batch operation (e.g., playlist load)."""
    def __init__(self, errors: list[AutoDJError], ...):
        self.errors = errors
        super().__init__(...)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_exceptions.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add camfrog_autodj/exceptions.py tests/test_exceptions.py
git commit -m "feat: enhance exception hierarchy with serialization and recovery hints"
```

---

### Task 3: Engine Modularization — Split into Focused Modules

**Files:**
- Create: `camfrog_autodj/engine/player_loop.py`
- Create: `camfrog_autodj/engine/chat_loop.py`
- Create: `camfrog_autodj/engine/queue_manager.py`
- Create: `camfrog_autodj/engine/autoplay_manager.py`
- Create: `camfrog_autodj/engine/health.py`
- Create: `camfrog_autodj/engine/__init__.py`
- Modify: `camfrog_autodj/engine.py` (refactor to delegate)
- Test: `tests/test_engine_modular.py`

**Interfaces:**
- Consumes: Tasks 1-2
- Produces: Modular engine components with clear boundaries

- [ ] **Step 1: Write failing tests for modular engine components**

```python
def test_player_loop_isolated():
    from camfrog_autodj.engine.player_loop import PlayerLoop
    loop = PlayerLoop(...)
    # Test single track playback logic in isolation

def test_chat_loop_isolated():
    from camfrog_autodj.engine.chat_loop import ChatLoop
    loop = ChatLoop(...)
    # Test message handling in isolation
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_engine_modular.py -v`
Expected: FAIL - modules don't exist

- [ ] **Step 3: Create `engine/player_loop.py` with `PlayerLoop` class**

Extract playback logic from `Engine._player_loop`, `_play_one_track`, `_track_failed`, `_try_play`, `_announce_playback_failure`, `_check_autoplay_mode`, `_pop_next_track`

- [ ] **Step 4: Create `engine/chat_loop.py` with `ChatLoop` class**

Extract chat handling from `Engine._chat_loop`, `_handle_room_message`, `_handle_im`, `_handle_re_events`, `_should_ignore_message`, `_log_im_message`, `_handle_admin_greeting`, `_handle_welcome_message`

- [ ] **Step 5: Create `engine/queue_manager.py` with `QueueManager` class**

Extract queue operations: `_load_all`, `_load_library`, `_load_autoplay_sources`, `_load_playlist`, `_load_playlist_dir`, `load_source`, `load_async`, `request`, `resolve`

- [ ] **Step 6: Create `engine/autoplay_manager.py` with `AutoplayManager` class**

Extract autoplay logic: `_autoplay_mode`, `_last_user_request_time`, `autoplay_idle_timeout`, autoplay source management

- [ ] **Step 7: Create `engine/health.py` with `HealthChecker` class**

Extract `health_check` method and circuit breaker logic

- [ ] **Step 8: Refactor `engine.py` to compose modular components**

```python
class Engine:
    def __init__(self, ...):
        self.player_loop = PlayerLoop(self)
        self.chat_loop = ChatLoop(self)
        self.queue_manager = QueueManager(self)
        self.autoplay_manager = AutoplayManager(self)
        self.health_checker = HealthChecker(self)
    def start(self):
        self.player_loop.start()
        self.chat_loop.start()
        ...
```

- [ ] **Step 9: Run all tests to verify they pass**

Run: `pytest tests/test_engine_modular.py tests/test_core.py -v`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add camfrog_autodj/engine/ camfrog_autodj/engine.py tests/test_engine_modular.py
git commit -m "refactor: split Engine into modular components (player_loop, chat_loop, queue_manager, autoplay_manager, health)"
```

---

### Task 4: GUI Modularization — Split into Focused Modules

**Files:**
- Create: `camfrog_autodj/gui/now_playing.py`
- Create: `camfrog_autodj/gui/queue_panel.py`
- Create: `camfrog_autodj/gui/history_panel.py`
- Create: `camfrog_autodj/gui/chat_panel.py`
- Create: `camfrog_autodj/gui/im_panel.py`
- Create: `camfrog_autodj/gui/settings_dialog.py`
- Create: `camfrog_autodj/gui/animations.py`
- Create: `camfrog_autodj/gui/__init__.py`
- Modify: `camfrog_autodj/gui.py` (refactor to delegate)
- Test: `tests/test_gui_modular.py`

**Interfaces:**
- Consumes: Task 3
- Produces: Modular GUI components with clear boundaries

- [ ] **Step 1: Write failing tests for modular GUI components**

```python
def test_now_playing_widget():
    from camfrog_autodj.gui.now_playing import NowPlayingWidget
    widget = NowPlayingWidget(...)
    widget.update(track, position, paused)
    # Verify rendering
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_gui_modular.py -v`
Expected: FAIL - modules don't exist

- [ ] **Step 3: Create `gui/animations.py` with animation logic**

Extract: `_animate_aurora`, `_animate_particles`, `_update_border_glow_and_level`, `_animate_bars`, `_animate_record`, `_update_playback_indicators`, `_frame`, `_tick`, `_layout_line`, `_layout_stage`, `_launch_confetti`, `_run_confetti`

- [ ] **Step 4: Create `gui/now_playing.py` with `NowPlayingWidget`**

Extract: Stage canvas, title/sub labels, progress bar, time label, control buttons (pause, skip, voteskip, discover, check), volume slider

- [ ] **Step 5: Create `gui/queue_panel.py` with `QueuePanel`**

Extract: Queue listbox, remove/clear buttons, double-click handler, shuffle/repeat chips

- [ ] **Step 6: Create `gui/history_panel.py` with `HistoryPanel`**

Extract: History listbox rendering

- [ ] **Step 7: Create `gui/chat_panel.py` with `ChatPanel`**

Extract: Chat text widget, send/speak entries, message rendering with tags

- [ ] **Step 8: Create `gui/im_panel.py` with `IMPanel`**

Extract: IM text widget, private message rendering

- [ ] **Step 9: Create `gui/settings_dialog.py` with `SettingsDialog`**

Extract: Entire `open_settings`, `save_settings`, all setting rows, validation, TOML writing

- [ ] **Step 10: Refactor `gui.py` to compose modular widgets**

```python
class App(tk.Tk):
    def __init__(self, engine):
        self.now_playing = NowPlayingWidget(self, engine)
        self.queue_panel = QueuePanel(self, engine)
        self.history_panel = HistoryPanel(self, engine)
        self.chat_panel = ChatPanel(self, engine)
        self.im_panel = IMPanel(self, engine)
        self.settings = SettingsDialog(self, engine)
        self.animations = AnimationController(self, engine)
```

- [ ] **Step 11: Run all tests to verify they pass**

Run: `pytest tests/test_gui_modular.py tests/test_gui_logic.py tests/test_gui_i18n.py -v`
Expected: PASS

- [ ] **Step 12: Commit**

```bash
git add camfrog_autodj/gui/ camfrog_autodj/gui.py tests/test_gui_modular.py
git commit -m "refactor: split GUI into modular widgets (now_playing, queue_panel, history_panel, chat_panel, im_panel, settings_dialog, animations)"
```

---

### Task 5: Enhanced Observability — Structured Logging & Metrics

**Files:**
- Create: `camfrog_autodj/observability.py`
- Create: `camfrog_autodj/metrics.py`
- Modify: `camfrog_autodj/engine.py` (integrate metrics)
- Test: `tests/test_observability.py`

**Interfaces:**
- Consumes: Tasks 1-4
- Produces: Structured JSON logging, Prometheus-compatible metrics, health endpoints

- [ ] **Step 1: Write failing tests for observability**

```python
def test_structured_logging():
    from camfrog_autodj.observability import StructuredLogger
    logger = StructuredLogger("test")
    logger.info("track_played", track_id="123", duration=180.5, source="youtube")
    # Verify JSON output

def test_metrics_collection():
    from camfrog_autodj.metrics import MetricsCollector
    m = MetricsCollector()
    m.increment("tracks_played")
    m.histogram("track_duration", 180.5)
    assert m.get("tracks_played") == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_observability.py -v`
Expected: FAIL - modules don't exist

- [ ] **Step 3: Create `observability.py` with `StructuredLogger`**

```python
class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._extra = {}
    
    def bind(self, **kwargs) -> StructuredLogger:
        new = StructuredLogger(self.logger.name)
        new._extra = {**self._extra, **kwargs}
        return new
    
    def _log(self, level, msg, **kwargs):
        extra = {**self._extra, **kwargs}
        self.logger.log(level, msg, extra={"structured": extra})
    
    def info(self, msg, **kwargs): self._log(logging.INFO, msg, **kwargs)
    def warning(self, msg, **kwargs): self._log(logging.WARNING, msg, **kwargs)
    def error(self, msg, **kwargs): self._log(logging.ERROR, msg, **kwargs)
```

- [ ] **Step 4: Create `metrics.py` with `MetricsCollector`**

```python
class MetricsCollector:
    def __init__(self):
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.RLock()
    
    def increment(self, name: str, value: int = 1, labels: dict | None = None):
        with self._lock:
            key = self._make_key(name, labels)
            self._counters[key] += value
    
    def histogram(self, name: str, value: float, labels: dict | None = None):
        with self._lock:
            key = self._make_key(name, labels)
            self._histograms[key].append(value)
    
    def gauge(self, name: str, value: float, labels: dict | None = None):
        with self._lock:
            key = self._make_key(name, labels)
            self._gauges[key] = value
    
    def get_metrics(self) -> dict:
        # Prometheus text format export
        ...
```

- [ ] **Step 5: Integrate metrics into Engine**

Track: tracks_played, tracks_failed, chat_messages_sent, chat_messages_received, queue_length, autoplay_activations, circuit_breaker_trips, tts_synthesis_count, command_executions

- [ ] **Step 6: Add health endpoint data structure**

```python
def health_check(self) -> HealthStatus:
    return HealthStatus(
        ok=...,
        checks={...},
        metrics=self.metrics.get_summary(),
        timestamp=time.time()
    )
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/test_observability.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add camfrog_autodj/observability.py camfrog_autodj/metrics.py camfrog_autodj/engine.py tests/test_observability.py
git commit -m "feat: add structured logging and metrics collection"
```

---

### Task 6: Performance Optimization — IPC Connection Pool & Caching

**Files:**
- Modify: `camfrog_autodj/player.py:1-497`
- Modify: `camfrog_autodj/engine.py` (position caching)
- Test: `tests/test_performance.py`

**Interfaces:**
- Consumes: Tasks 1-5
- Produces: Optimized IPC reuse, reduced syscall overhead, faster GUI polling

- [ ] **Step 1: Write failing performance tests**

```python
def test_ipc_connection_reuse():
    from camfrog_autodj.player import MpvPlayer
    # Verify connections are pooled and reused
    # Measure syscall reduction

def test_position_cache_hit_rate():
    from camfrog_autodj.engine import Engine
    # Verify cache hits reduce IPC calls by >80%
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_performance.py -v`
Expected: FAIL - benchmarks not implemented

- [ ] **Step 3: Optimize `player.py` IPC connection pool**

- Add connection warm-up on player start
- Implement connection health checks before reuse
- Add metrics for pool hit/miss rates
- Optimize Windows named pipe vs Unix socket handling

```python
class IpcConnectionPool:
    def __init__(self):
        self._pool: dict[str, IpcConnection] = {}
        self._lock = threading.RLock()
        self._stats = {"hits": 0, "misses": 0, "errors": 0}
    
    def get(self, ipc_path: str) -> IpcConnection | None:
        with self._lock:
            conn = self._pool.get(ipc_path)
            if conn and conn.is_healthy():
                self._stats["hits"] += 1
                return conn
            self._stats["misses"] += 1
            # Create new...
```

- [ ] **Step 4: Add adaptive polling in Engine**

```python
def _refresh(self):
    # Only call IPC for position when actually playing
    # Use cached position when paused/idle
    # Batch GUI updates
```

- [ ] **Step 5: Add lazy loading for heavy imports**

```python
# In modules that import mutagen, yt_dlp, pyttsx3, pywinauto
# Use importlib.import_module() on first use
```

- [ ] **Step 6: Run tests and benchmarks**

Run: `pytest tests/test_performance.py tests/test_player_cache.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add camfrog_autodj/player.py camfrog_autodj/engine.py tests/test_performance.py
git commit -m "perf: optimize IPC connection pooling and position caching"
```

---

### Task 7: Configuration System Hardening

**Files:**
- Modify: `camfrog_autodj/config.py:1-394`
- Create: `camfrog_autodj/config/schema.py`
- Test: `tests/test_config_hardening.py`

**Interfaces:**
- Consumes: Tasks 1-2
- Produces: Schema-driven validation, config versioning, migration framework

- [ ] **Step 1: Write failing tests for config hardening**

```python
def test_schema_validation():
    from camfrog_autodj.config.schema import ConfigSchema
    schema = ConfigSchema()
    # Valid config passes
    # Invalid config raises ConfigValidationError with field path

def test_config_migration():
    from camfrog_autodj.config import migrate_config
    # Old config v1 -> v2 migration works
    # Invalid migrations are rejected
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config_hardening.py -v`
Expected: FAIL - schema module doesn't exist

- [ ] **Step 3: Create `config/schema.py` with declarative schema**

```python
from dataclasses import dataclass
from typing import Annotated
from annotated_types import Ge, Le, Gt, Lt

@dataclass
class ConfigSchema:
    bot_nick: Annotated[str, MinLen(1), MaxLen(50)]
    admins: Annotated[list[str], MinLen(0)]
    volume: Annotated[int, Ge(0), Le(100)]
    # ... all fields with validation metadata
```

- [ ] **Step 4: Refactor `config.py` to use schema for validation**

- Generate `_RANGES`, `_CHOICES`, `_REGEXES` from schema
- Add config version field
- Implement migration functions with version tracking

- [ ] **Step 5: Add config diff/preview in settings dialog**

```python
def preview_changes(self) -> dict[str, tuple[old, new]]:
    # Show what will change before save
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_config_hardening.py tests/test_core.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add camfrog_autodj/config.py camfrog_autodj/config/schema.py tests/test_config_hardening.py
git commit -m "feat: add schema-driven config validation and migration framework"
```

---

### Task 8: Security Hardening — Input Validation & Rate Limiting

**Files:**
- Modify: `camfrog_autodj/commands.py:1-658`
- Modify: `camfrog_autodj/engine.py` (rate limiting)
- Create: `camfrog_autodj/security.py`
- Test: `tests/test_security.py`

**Interfaces:**
- Consumes: Tasks 1-2
- Produces: Hardened input validation, enhanced rate limiting, audit logging

- [ ] **Step 1: Write failing tests for security hardening**

```python
def test_command_injection_prevention():
    from camfrog_autodj.commands import Router
    # Verify no shell injection via track titles, user input

def test_rate_limiting_enforcement():
    from camfrog_autodj.security import RateLimiter
    # Verify per-user, per-command, global limits
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_security.py -v`
Expected: FAIL - security module doesn't exist

- [ ] **Step 3: Create `security.py` with centralized security utilities**

```python
class InputSanitizer:
    @staticmethod
    def sanitize_track_title(title: str) -> str:
        # Remove control chars, limit length, escape for safe display
    
    @staticmethod
    def sanitize_chat_message(msg: str) -> str:
        # Prevent command injection, limit length

class RateLimiter:
    def __init__(self, max_per_window: int, window_sec: float):
        ...
    
    def check_limit(self, key: str) -> bool:
        # Sliding window with burst allowance
```

- [ ] **Step 4: Enhance command authorization**

- Add audit log for all admin commands
- Implement command cooldowns per-user per-command
- Add IP-based rate limiting for web chat (if applicable)

- [ ] **Step 5: Harden playlist/file path validation**

```python
def validate_safe_path(path: Path, allowed_roots: list[Path]) -> bool:
    # Resolve symlinks, check traversal, verify within allowed roots
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_security.py tests/test_commands.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add camfrog_autodj/security.py camfrog_autodj/commands.py camfrog_autodj/engine.py tests/test_security.py
git commit -m "feat: security hardening - input validation, rate limiting, audit logging"
```

---

### Task 9: Comprehensive Test Coverage Enhancement

**Files:**
- Create: `tests/test_integration_full_flow.py`
- Create: `tests/test_edge_cases.py`
- Create: `tests/test_concurrency_stress.py`
- Modify: `tests/conftest.py` (add fixtures)
- Test: All new test files

**Interfaces:**
- Consumes: Tasks 1-8
- Produces: 90%+ coverage, integration tests, stress tests

- [ ] **Step 1: Write integration test for full play flow**

```python
def test_full_play_flow_youtube():
    # Engine -> resolve -> queue -> play -> complete -> next
    # Mock mpv, yt-dlp, adapter

def test_full_play_flow_local():
    # Local file -> metadata -> play -> complete
```

- [ ] **Step 2: Write edge case tests**

```python
def test_mpv_crash_recovery():
    # mpv exits with code != 0 -> circuit breaker -> recovery

def test_network_timeout_during_resolve():
    # yt-dlp timeout -> UserError -> queue continues

def test_config_corruption_recovery():
    # Corrupt config.toml -> .bak restore -> defaults
```

- [ ] **Step 3: Write concurrency stress tests**

```python
def test_concurrent_requests():
    # 50 simultaneous !play commands -> all handled correctly

def test_concurrent_gui_updates():
    # Rapid queue changes + GUI polling -> no crashes
```

- [ ] **Step 4: Run tests and measure coverage**

Run: `pytest tests/ -v --cov=camfrog_autodj --cov-report=term-missing`
Expected: >90% coverage

- [ ] **Step 5: Commit**

```bash
git add tests/test_integration_full_flow.py tests/test_edge_cases.py tests/test_concurrency_stress.py tests/conftest.py
git commit -m "test: add integration, edge case, and concurrency stress tests"
```

---

### Task 10: Documentation Overhaul & Final Report

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/user-manual.en.md`
- Modify: `docs/user-manual.th.md`
- Create: `docs/architecture.md`
- Create: `docs/api-reference.md`
- Create: `Final-Report.md`
- Test: `docs/` (markdown lint)

**Interfaces:**
- Consumes: Tasks 1-9
- Produces: Complete documentation matching implementation

- [ ] **Step 1: Update README.md with new architecture**

- Module diagram
- Configuration reference
- CLI reference
- Troubleshooting guide

- [ ] **Step 2: Update CHANGELOG.md with all changes**

Follow Keep a Changelog format

- [ ] **Step 3: Create `docs/architecture.md`**

- Component diagram
- Data flow
- Concurrency model
- Security model

- [ ] **Step 4: Create `docs/api-reference.md`**

- Protocol interfaces
- Exception hierarchy
- Config schema
- Metrics format

- [ ] **Step 5: Update user manuals (EN/TH)**

- New features
- Updated settings
- New commands

- [ ] **Step 6: Create `Final-Report.md`**

- Executive summary
- Technical achievements
- Performance benchmarks
- Test results
- Migration guide
- Known limitations

- [ ] **Step 7: Run markdown lint**

Run: `markdownlint docs/*.md README.md CHANGELOG.md`
Expected: PASS

- [ ] **Step 8: Final verification - all checks**

```bash
python -m pytest -q -p no:faulthandler -p no:cacheprovider
ruff check camfrog_autodj tests tools
ruff format --check camfrog_autodj tests tools
mypy camfrog_autodj
shellcheck scripts/*.sh tools/*.sh
```

- [ ] **Step 9: Commit**

```bash
git add README.md CHANGELOG.md docs/ Final-Report.md
git commit -m "docs: complete documentation overhaul and final report"
```

---

### Task 11: Release Preparation & GitHub Workflow

**Files:**
- Modify: `.github/workflows/*.yml`
- Create: `.github/workflows/release.yml`
- Test: CI pipeline

**Interfaces:**
- Consumes: Tasks 1-10
- Produces: Automated release pipeline with GPG signing

- [ ] **Step 1: Update CI workflow with new checks**

- Add performance benchmarks
- Add security scan (bandit)
- Add dependency audit

- [ ] **Step 2: Create release workflow**

- Version bump
- Changelog generation
- GPG-signed tag
- PyInstaller build
- Asset upload

- [ ] **Step 3: Verify GitHub CLI workflow (cvsz ↔ policedbc)**

```bash
gh auth switch -u cvsz
# Create PR
gh auth switch -u policedbc
# Review & approve
gh auth switch -u cvsz
# Merge with --match-head-commit
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/
git commit -m "ci: update release pipeline and GitHub workflow"
```

---

## Execution Approach

**Recommendation: Subagent-driven development**

**Reason:** This plan has 11 major tasks with complex interdependencies (modularization must complete before observability integration, security hardening before stress tests). Subagent-driven ensures each task gets independent review before the next begins, critical for a production-grade refactor of this scope. The modular architecture means tasks 3-4 can run in parallel after tasks 1-2.

**Next Step:** Please review this plan. Does it capture what you want? If yes, which execution approach do you prefer?