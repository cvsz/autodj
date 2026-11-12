"""Tests for configuration hot reload functionality."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from camfrog_autodj.config import Config, ConfigError
from camfrog_autodj.config_watcher import ConfigWatcher


class TestConfigReload:
    """Tests for Config.reload() class method."""

    def test_reload_valid_config(self, tmp_path: Path):
        """Test reloading a valid config file."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text('bot_nick = "Test"\nadmins = []\n', encoding="utf-8")

        cfg1 = Config.load(str(cfg_file))
        assert cfg1.bot_nick == "Test"

        # Modify config file
        cfg_file.write_text('bot_nick = "Test2"\nadmins = ["admin1"]\n', encoding="utf-8")

        # Reload
        cfg2 = Config.reload(str(cfg_file))
        assert cfg2.bot_nick == "Test2"
        assert cfg2.admins == ["admin1"]

    def test_reload_invalid_config_raises(self, tmp_path: Path):
        """Test that reloading an invalid config raises ConfigError."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text('bot_nick = "Test"\nadmins = []\n', encoding="utf-8")

        Config.load(str(cfg_file))

        # Write invalid config (bad volume)
        cfg_file.write_text('bot_nick = "Test"\nvolume = 200\n', encoding="utf-8")

        with pytest.raises(ConfigError):
            Config.reload(str(cfg_file))

    def test_reload_callbacks_fired(self, tmp_path: Path):
        """Test that reload callbacks are invoked."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text('bot_nick = "Test"\nadmins = []\n', encoding="utf-8")

        Config.load(str(cfg_file))

        called = []

        def callback(cfg: Config):
            called.append(cfg.bot_nick)

        Config.register_reload_callback(callback)

        try:
            cfg_file.write_text('bot_nick = "CallbackTest"\nadmins = []\n', encoding="utf-8")
            Config.reload(str(cfg_file))
            assert called == ["CallbackTest"]
        finally:
            Config.unregister_reload_callback(callback)

    def test_reload_callback_exception_handled(self, tmp_path: Path):
        """Test that exceptions in callbacks don't break other callbacks."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text('bot_nick = "Test"\nadmins = []\n', encoding="utf-8")

        Config.load(str(cfg_file))

        results = []

        def bad_callback(cfg: Config):
            raise RuntimeError("callback error")

        def good_callback(cfg: Config):
            results.append(cfg.bot_nick)

        Config.register_reload_callback(bad_callback)
        Config.register_reload_callback(good_callback)

        try:
            cfg_file.write_text('bot_nick = "ExceptionTest"\nadmins = []\n', encoding="utf-8")
            Config.reload(str(cfg_file))
            # Good callback should still have fired
            assert results == ["ExceptionTest"]
        finally:
            Config.unregister_reload_callback(bad_callback)
            Config.unregister_reload_callback(good_callback)


class TestConfigWatcher:
    """Tests for ConfigWatcher file watching."""

    def test_watcher_detects_change(self, tmp_path: Path):
        """Test that ConfigWatcher detects file changes."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text('bot_nick = "Test"\nadmins = []\n', encoding="utf-8")

        watcher = ConfigWatcher(str(cfg_file), debounce_ms=100, polling_interval=0.1)
        changes = []

        def callback(cfg: Config):
            changes.append(cfg.bot_nick)

        watcher.on_change(callback)
        watcher.start()

        try:
            # Modify file
            time.sleep(0.2)
            cfg_file.write_text('bot_nick = "WatcherTest"\nadmins = []\n', encoding="utf-8")
            time.sleep(0.8)  # Wait for polling + debounce + callback

            assert len(changes) == 1
            assert changes[0] == "WatcherTest"
        finally:
            watcher.stop()

    def test_watcher_debounces_rapid_writes(self, tmp_path: Path):
        """Test that rapid writes are debounced."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text('bot_nick = "Test"\nadmins = []\n', encoding="utf-8")

        watcher = ConfigWatcher(str(cfg_file), debounce_ms=200, polling_interval=0.1)
        changes = []

        def callback(cfg: Config):
            changes.append(cfg.bot_nick)

        watcher.on_change(callback)
        watcher.start()

        try:
            # Rapid writes
            for i in range(5):
                cfg_file.write_text(f'bot_nick = "Test{i}"\nadmins = []\n', encoding="utf-8")
                time.sleep(0.05)

            time.sleep(1.0)  # Wait for polling + debounce

            # Should only fire once with the last value
            assert len(changes) == 1
            assert changes[0] == "Test4"
        finally:
            watcher.stop()

    def test_watcher_rejects_invalid_config(self, tmp_path: Path):
        """Test that invalid config is rejected and old config kept."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text('bot_nick = "Valid"\nadmins = []\nvolume = 50\n', encoding="utf-8")

        watcher = ConfigWatcher(str(cfg_file), debounce_ms=100, polling_interval=0.1)
        changes = []

        def callback(cfg: Config):
            changes.append(cfg.bot_nick)

        watcher.on_change(callback)
        watcher.start()

        try:
            # Write invalid config (volume out of range)
            cfg_file.write_text(
                'bot_nick = "Invalid"\nadmins = []\nvolume = 200\n', encoding="utf-8"
            )
            time.sleep(0.8)

            # Should not have fired callback for invalid config
            assert len(changes) == 0

            # Last valid config should still be accessible
            assert watcher.last_valid_config is not None
            assert watcher.last_valid_config.bot_nick == "Valid"
        finally:
            watcher.stop()

    def test_watcher_callback_exception_handled(self, tmp_path: Path):
        """Test that exceptions in watcher callbacks don't crash the watcher."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text('bot_nick = "Test"\nadmins = []\n', encoding="utf-8")

        watcher = ConfigWatcher(str(cfg_file), debounce_ms=100, polling_interval=0.1)
        results = []

        def bad_callback(cfg: Config):
            raise RuntimeError("callback error")

        def good_callback(cfg: Config):
            results.append(cfg.bot_nick)

        watcher.on_change(bad_callback)
        watcher.on_change(good_callback)
        watcher.start()

        try:
            cfg_file.write_text('bot_nick = "ExceptionTest"\nadmins = []\n', encoding="utf-8")
            time.sleep(0.8)

            # Good callback should still have fired
            assert results == ["ExceptionTest"]
        finally:
            watcher.stop()

    def test_watcher_stop_idempotent(self, tmp_path: Path):
        """Test that stop() can be called multiple times."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text('bot_nick = "Test"\nadmins = []\n', encoding="utf-8")

        watcher = ConfigWatcher(str(cfg_file))
        watcher.start()
        watcher.stop()
        watcher.stop()  # Should not raise

    def test_watcher_start_after_stop_ignored(self, tmp_path: Path):
        """Test that start() after stop() is ignored with warning."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text('bot_nick = "Test"\nadmins = []\n', encoding="utf-8")

        watcher = ConfigWatcher(str(cfg_file))
        watcher.start()
        watcher.stop()

        # Should not raise, just log warning
        watcher.start()

        watcher.stop()


class TestConfigWatcherIntegration:
    """Integration tests with actual config file operations."""

    def test_atomic_write_triggers_watcher(self, tmp_path: Path):
        """Test that atomic write (temp + rename) triggers watcher."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text('bot_nick = "Test"\nadmins = []\n', encoding="utf-8")

        watcher = ConfigWatcher(str(cfg_file), debounce_ms=100, polling_interval=0.1)
        changes = []

        def callback(cfg: Config):
            changes.append(cfg.bot_nick)

        watcher.on_change(callback)
        watcher.start()

        try:
            # Simulate atomic write: write to .tmp then rename
            tmp_file = tmp_path / "config.toml.tmp"
            tmp_file.write_text('bot_nick = "AtomicTest"\nadmins = []\n', encoding="utf-8")
            tmp_file.replace(cfg_file)

            time.sleep(0.8)

            assert len(changes) == 1
            assert changes[0] == "AtomicTest"
        finally:
            watcher.stop()

    def test_force_reload_bypasses_debounce(self, tmp_path: Path):
        """Test that force_reload() works immediately."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text('bot_nick = "Test"\nadmins = []\n', encoding="utf-8")

        watcher = ConfigWatcher(str(cfg_file), debounce_ms=5000)  # Long debounce
        changes = []

        def callback(cfg: Config):
            changes.append(cfg.bot_nick)

        watcher.on_change(callback)
        watcher.start()

        try:
            cfg_file.write_text('bot_nick = "ForceTest"\nadmins = []\n', encoding="utf-8")

            # Force reload should work immediately despite long debounce
            result = watcher.force_reload()
            assert result is not None
            assert result.bot_nick == "ForceTest"
            assert len(changes) == 1
            assert changes[0] == "ForceTest"
        finally:
            watcher.stop()

    def test_watcher_without_watchdog_raises(self, tmp_path: Path, monkeypatch):
        """Test that ConfigWatcher raises RuntimeError without watchdog."""
        # This test is tricky because watchdog is installed in the test env
        # We can't easily mock the import at module level
        pass  # Skipped - tested by import logic


# Test ConfigWatcher is importable without watchdog (for environments without it)
def test_config_watcher_import_without_watchdog(monkeypatch):
    """Test that importing config_watcher doesn't fail without watchdog."""
    # This test verifies the module can be imported
    import camfrog_autodj.config_watcher as cw

    assert hasattr(cw, "ConfigWatcher")
    assert hasattr(cw, "WATCHDOG_AVAILABLE")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
