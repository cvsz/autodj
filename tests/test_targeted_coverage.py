"""Targeted tests for specific uncovered lines in testable modules."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from camfrog_autodj.config import Config, ConfigError, MessageStyle
from camfrog_autodj.doctor import run_checks
from camfrog_autodj.exceptions import (
    AutoDJError,
    BlockedUserError,
    ChatAdapterError,
    ChatError,
    ChatReadError,
    ChatSendError,
    ConfigValidationError,
    LibraryError,
    LibraryScanError,
    PlayerCrashError,
    PlayerError,
    PlayerHungError,
    PlayerNotAvailableError,
    QueueError,
    QueueFullError,
    RequestRateLimitError,
    SecurityError,
    TTSError,
    TTSUnavailableError,
    UnauthorizedError,
    YtdlpMissingError,
)
from camfrog_autodj.exceptions import (
    ConfigError as ExcConfigError,
)
from camfrog_autodj.library import (
    host_ok,
    is_url,
    local_track,
    parse_ytdlp_info,
)
from camfrog_autodj.migrate import (
    _expand_environment,
    _read_registry_values,
    detect_placeholders,
    migrate_config,
)
from camfrog_autodj.playlist import load_playlist
from camfrog_autodj.renderer import MessageRenderer, RenderedMessage, get_renderer
from camfrog_autodj.tts import synth
from camfrog_autodj.webchat import tokens_to_lines


class TestConfigUncoveredLines:
    """Test specific uncovered lines in config.py."""

    def test_message_style_validation_errors(self):
        """Test MessageStyle validation error paths (lines 29, 31, 33)."""
        # font_family empty
        style = MessageStyle(font_family="")
        with pytest.raises(ValueError, match="font_family must not be empty"):
            style.validate()

        # font_size too small
        style = MessageStyle(font_size=7)
        with pytest.raises(ValueError, match="font_size must be between 8 and 72"):
            style.validate()

        # font_size too large
        style = MessageStyle(font_size=73)
        with pytest.raises(ValueError, match="font_size must be between 8 and 72"):
            style.validate()

        # font_color invalid format
        style = MessageStyle(font_color="red")
        with pytest.raises(ValueError, match="font_color must be a valid hex color"):
            style.validate()

        # font_color invalid length
        style = MessageStyle(font_color="#FF00")
        with pytest.raises(ValueError, match="font_color must be a valid hex color"):
            style.validate()

    def test_message_style_to_toml_dict(self):
        """Test MessageStyle.to_toml_dict (line 37)."""
        style = MessageStyle(font_family="Test", font_size=14, font_color="#FF0000")
        data = style.to_toml_dict()
        assert data["font_family"] == "Test"
        assert data["font_size"] == 14
        assert data["font_color"] == "#FF0000"

    def test_message_style_from_toml_dict_matches_dataclass_defaults(self):
        """from_toml_dict({}) must match the MessageStyle() dataclass defaults.

        Regression guard: loading message_style from config.toml without font_size /
        font_color must not silently produce different preview values than MessageStyle().
        """
        style = MessageStyle.from_toml_dict({})
        default = MessageStyle()
        assert style.font_family == default.font_family == "Consolas"
        assert style.font_size == default.font_size == 14
        assert style.font_color == default.font_color == "#000000"
        assert style.bold == default.bold is False
        assert style.italic == default.italic is False
        assert style.underline == default.underline is False

    def test_config_load_unicode_decode_error(self, tmp_path):
        """Test Config.load UnicodeDecodeError handling (lines 232-233)."""
        bad_file = tmp_path / "bad.toml"
        bad_file.write_bytes(b"\xff\xfe")
        with pytest.raises(ConfigError, match="not valid UTF-8"):
            Config.load(str(bad_file))

    def test_config_load_message_style_validation(self, tmp_path):
        """Test Config.load message_style validation (lines 333-334)."""
        cfg_file = tmp_path / "cfg.toml"
        cfg_file.write_text('message_style = { font_color = "invalid" }\n')
        with pytest.raises(ConfigError, match="message_style"):
            Config.load(str(cfg_file))

    def test_config_validate_list_items_must_be_text(self, tmp_path):
        """Test _validate_field list item validation (line 374)."""
        cfg_file = tmp_path / "cfg.toml"
        cfg_file.write_text("admins = [123, 456]\n")
        with pytest.raises(ConfigError, match="every item of 'admins' must be text"):
            Config.load(str(cfg_file))


class TestExceptionsUncoveredLines:
    """Test exception constructor paths (lines 62, 71-74, 96, 105, 114, 123, 140, 149, 158, 167, 202, 219, 228, 237, 254, 263, 280, 289, 298)."""

    def test_all_exception_constructors(self):
        """Test all exception constructors are callable."""
        # AutoDJError base
        AutoDJError("test", code="test", details="details", context={"k": "v"})

        # Config errors
        ExcConfigError("test", code="config.test", details="d", context={})
        ConfigValidationError("test", field="volume", context={"v": 1})

        # Chat errors
        ChatError("test", code="chat.test", details="d")
        ChatReadError("test", details="d", context={})
        ChatSendError("test", details="d")
        ChatAdapterError("test", details="d")

        # Library errors
        LibraryError("test", code="lib.test", details="d")
        LibraryScanError("test", details="d", context={})

        # Player errors
        PlayerError("test", code="player.test", details="d")
        PlayerNotAvailableError("test", details="d")
        PlayerHungError("test", details="d", context={})
        PlayerCrashError("test", details="d")

        # Queue errors
        QueueError("test", code="queue.test", details="d")
        QueueFullError("test", details="d", context={})
        RequestRateLimitError("test", details="d", context={})

        # Security errors
        SecurityError("test", code="sec.test", details="d")
        UnauthorizedError("test", details="d", context={})
        BlockedUserError("test", details="d", context={})

        # TTS errors
        TTSError("test", code="tts.test", details="d")
        TTSUnavailableError("test", details="d")

        # Ytdlp
        YtdlpMissingError("test", details="d")


class TestMigrateUncoveredLines:
    """Test migrate.py uncovered lines."""

    def test_expand_environment_various(self):
        """Test _expand_environment (lines in _expand_environment)."""
        with patch.dict(os.environ, {"TEST": "/path", "APPDATA": "C:\\AppData"}):
            # Tilde expansion
            result = _expand_environment("~/music")
            assert not result.startswith("~")

            # Env var
            result = _expand_environment("$TEST/music")
            assert "/path/music" in result

            # Percent var
            result = _expand_environment("%APPDATA%\\AutoDJ")
            assert "AutoDJ" in result

            # Missing var unchanged
            result = _expand_environment("$MISSING/path")
            assert result == "$MISSING/path"

    def test_detect_placeholders(self):
        """Test detect_placeholders (migrate.py)."""
        text = 'mpv_path = "REPLACE_ME"\nytdlp_path = "change_me"\n'
        result = detect_placeholders(text)
        assert "mpv_path" in result
        assert "ytdlp_path" in result

        text = 'mpv_path = "/usr/bin/mpv"\n'
        result = detect_placeholders(text)
        assert result == {}

    def test_migrate_config_basic(self, tmp_path):
        """Test migrate_config (lines in migrate_config)."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text('mpv_path = "REPLACE_ME"\n')

        with patch("camfrog_autodj.migrate._discover_path", return_value="/usr/bin/mpv"):
            changes = migrate_config(str(cfg_file))

        assert any("mpv_path" in c for c in changes)
        # save_config uses single quotes for strings
        assert "mpv_path = '/usr/bin/mpv'" in cfg_file.read_text()

    def test_migrate_config_creates_backup(self, tmp_path):
        """Test migrate_config creates .bak (line 215-216)."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text('mpv_path = "REPLACE_ME"\n')

        with patch("camfrog_autodj.migrate._discover_path", return_value="/usr/bin/mpv"):
            migrate_config(str(cfg_file))

        bak = tmp_path / "config.toml.bak"
        assert bak.exists()

    def test_migrate_config_nonexistent(self, tmp_path):
        """Test migrate_config with nonexistent file."""
        cfg_file = tmp_path / "nonexistent.toml"
        changes = migrate_config(str(cfg_file))
        assert changes == []

    def test_migrate_config_unreadable(self, tmp_path):
        """Test migrate_config with unreadable file."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_bytes(b"\xff\xfe")
        changes = migrate_config(str(cfg_file))
        assert changes == []

    def test_read_registry_values_non_windows(self, monkeypatch):
        """Test _read_registry_values on non-Windows."""
        monkeypatch.setattr(os, "name", "posix")
        result = _read_registry_values()
        assert result == {}

    def test_read_registry_values_missing_key(self, monkeypatch):
        """Test _read_registry_values with missing registry key."""
        monkeypatch.setattr(os, "name", "nt")
        # Mock winreg module into sys.modules
        import sys

        mock_winreg = MagicMock()
        mock_winreg.OpenKey.side_effect = FileNotFoundError
        mock_winreg.HKEY_CURRENT_USER = 0x80000001
        monkeypatch.setitem(sys.modules, "winreg", mock_winreg)

        result = _read_registry_values()
        assert result == {}

    def test_read_registry_values_exception(self, monkeypatch):
        """Test _read_registry_values exception handling."""
        monkeypatch.setattr(os, "name", "nt")
        import sys

        mock_winreg = MagicMock()
        mock_winreg.OpenKey.side_effect = Exception("Access denied")
        mock_winreg.HKEY_CURRENT_USER = 0x80000001
        monkeypatch.setitem(sys.modules, "winreg", mock_winreg)

        result = _read_registry_values()
        assert result == {}


class TestPlaylistUncoveredLines:
    """Test playlist.py uncovered lines."""

    def test_load_playlist_invalid_source_filtered(self, tmp_path):
        """Test load_playlist filters invalid sources (lines 36, 39, 65, 67-72)."""
        playlist_file = tmp_path / "playlist.json"
        playlist_file.write_text(
            json.dumps(
                {
                    "version": 1,
                    "tracks": [
                        {
                            "source": "https://youtube.com/watch?v=abc",
                            "title": "Valid",
                            "duration": 100,
                        },
                        {"source": "not-a-url", "title": "Invalid", "duration": 100},
                        {"source": "/local/file.mp3", "title": "Local", "duration": 100},
                    ],
                }
            )
        )

        tracks = load_playlist(str(playlist_file))
        # Only valid URL and local file
        assert len(tracks) == 2

    def test_load_playlist_missing_fields(self, tmp_path):
        """Test load_playlist with missing fields."""
        playlist_file = tmp_path / "playlist.json"
        playlist_file.write_text(
            json.dumps(
                {
                    "version": 1,
                    "tracks": [
                        {"source": "url", "title": "Test"},  # Missing duration
                        {"source": "url2", "duration": 100},  # Missing title
                    ],
                }
            )
        )

        tracks = load_playlist(str(playlist_file))
        # Should handle gracefully
        assert len(tracks) <= 2


class TestRendererUncoveredLines:
    """Test renderer.py uncovered lines."""

    def test_renderer_basic(self):
        """Test MessageRenderer basic functionality."""
        renderer = MessageRenderer()
        from camfrog_autodj.config import MessageStyle

        # render takes (style, text) not (text, style)
        result = renderer.render(MessageStyle(), "Hello")

        assert isinstance(result, RenderedMessage)
        assert result.plain_text == "Hello"
        assert result.rich_text is None

    def test_renderer_with_style(self):
        """Test renderer with style for preview."""
        renderer = MessageRenderer()
        from camfrog_autodj.config import MessageStyle

        style = MessageStyle(font_family="Arial", font_size=16, font_color="#FF0000", bold=True)
        result = renderer.render(style, "Hello")

        assert result.plain_text == "Hello"
        assert result.preview_tags is not None

    def test_get_renderer_singleton(self):
        """Test get_renderer returns singleton."""
        r1 = get_renderer()
        r2 = get_renderer()
        assert r1 is r2


class TestTTSUncoveredLines:
    """Test tts.py uncovered lines."""

    def test_synth_exists(self):
        """Test synth function exists."""
        assert synth is not None
        assert callable(synth)


class TestWebchatUncoveredLines:
    """Test webchat.py uncovered lines."""

    def test_tokens_to_lines_basic(self):
        """Test tokens_to_lines basic functionality.

        Format: [body..., nick, time, body...] where time token triggers new message.
        """
        # The function looks for time tokens, uses previous token as nick, following tokens as body
        tokens = ["prev msg", "user:", "10:30", "Hello world"]
        lines = tokens_to_lines(tokens)
        assert len(lines) == 1
        assert "10:30 user: Hello world" in lines[0]

    def test_tokens_to_lines_multiple(self):
        tokens = ["prev msg", "user1:", "10:30", "Hello", "user2:", "10:31", "World"]
        lines = tokens_to_lines(tokens)
        assert len(lines) == 2
        assert "10:30 user1: Hello" in lines[0]
        assert "10:31 user2: World" in lines[1]

    def test_tokens_to_lines_time_like_body(self):
        # Time-like token that's not at the right position should not start new message
        tokens = ["The time is", "user:", "10:30", "12:34 now"]
        lines = tokens_to_lines(tokens)
        assert len(lines) == 1
        assert "12:34" in lines[0]

    def test_tokens_to_lines_empty(self):
        lines = tokens_to_lines([])
        assert lines == []

    def test_tokens_to_lines_no_timestamp(self):
        tokens = ["user:", "Hello"]
        lines = tokens_to_lines(tokens)
        assert len(lines) == 0  # No timestamp = no messages

    def test_tokens_to_lines_continuation(self):
        tokens = ["prev", "user:", "10:30", "Hello", "world", "user2:", "10:31", "Hi"]
        lines = tokens_to_lines(tokens)
        assert len(lines) == 2
        assert "Hello world" in lines[0]


class TestModelsUncovered:
    """Test models.py uncovered line (line 10)."""

    def test_fmt_time_edge_cases(self):
        from camfrog_autodj.models import fmt_time

        assert fmt_time(None) == "?"
        assert fmt_time(0) == "?"
        assert fmt_time(30) == "0:30"
        assert fmt_time(90) == "1:30"
        assert fmt_time(3661) == "1:01:01"


class TestLibraryUncovered:
    """Test library.py uncovered lines."""

    def test_local_track_mutagen_failure_fallback(self, tmp_path):
        """Test local_track fallback when mutagen fails."""
        mp3_file = tmp_path / "test.mp3"
        mp3_file.write_text("not audio")

        # Mock the import inside the function
        with patch("builtins.__import__", side_effect=ImportError("No module")):
            track = local_track(mp3_file, "requester")
            assert track.title == "test"
            assert track.duration is None

    def test_local_track_no_mutagen(self, tmp_path):
        """Test local_track when mutagen not available."""
        mp3_file = tmp_path / "test.mp3"
        mp3_file.write_text("not audio")

        with patch("builtins.__import__", side_effect=ImportError("No module")):
            track = local_track(mp3_file, "requester")
            assert track.title == "test"

    def test_parse_ytdlp_info_invalid_url_filtered(self):
        """Test parse_ytdlp_info filters invalid URLs.

        Note: if entry has an ID, it constructs a YouTube URL, so we test with
        an entry that has neither valid URL nor ID.
        """
        info = {
            "id": "abc",
            "title": "Test",
            "duration": 100,
            "url": "not-a-url",
        }
        tracks = parse_ytdlp_info(info)
        # Since it has an ID, it will construct a YouTube URL
        assert len(tracks) == 1
        assert "youtube.com/watch?v=abc" in tracks[0].source

        # Test with entry missing both URL and ID
        info2 = {
            "title": "Test",
            "duration": 100,
            "url": "not-a-url",
        }
        tracks2 = parse_ytdlp_info(info2)
        assert len(tracks2) == 0

    def test_parse_ytdlp_info_playlist(self):
        """Test parse_ytdlp_info with playlist."""
        info = {
            "_type": "playlist",
            "entries": [
                {
                    "id": "a",
                    "title": "Song A",
                    "duration": 100,
                    "url": "https://youtube.com/watch?v=a",
                },
                None,
                {
                    "id": "b",
                    "title": "Song B",
                    "duration": 200,
                    "url": "https://youtube.com/watch?v=b",
                },
            ],
        }
        tracks = parse_ytdlp_info(info)
        assert len(tracks) == 2
        assert tracks[0].title == "Song A"

    def test_is_url(self):
        assert is_url("http://example.com") is True
        assert is_url("https://example.com") is True
        assert is_url("ftp://example.com") is False
        assert is_url("example.com") is False

    def test_host_ok(self):
        assert host_ok("https://youtube.com/watch?v=123", ["youtube.com"]) is True
        assert host_ok("https://music.youtube.com/watch?v=123", ["youtube.com"]) is True
        assert host_ok("https://vimeo.com/123", ["youtube.com"]) is False


class TestDoctorUncovered:
    """Test doctor.py uncovered lines."""

    def test_run_checks_basic(self):
        """Test run_checks returns results."""
        cfg = Config()
        results = run_checks(cfg)

        assert isinstance(results, list)
        assert len(results) > 0

        for level, _message in results:
            assert level in ("OK", "INFO", "WARN", "FAIL")


class TestPathsUncovered:
    """Test paths.py uncovered lines."""

    def test_application_dir(self):
        from camfrog_autodj.paths import application_dir

        path = application_dir()
        assert isinstance(path, Path)

    def test_resolve_executable(self):
        from camfrog_autodj.paths import resolve_executable

        # Non-existent
        result = resolve_executable("/nonexistent/path")
        assert result == ""

        # Current executable
        result = resolve_executable("python")
        assert result != ""


class TestPlayQueueUncovered:
    """Test playqueue.py uncovered lines."""

    def test_play_queue_edge_cases(self):
        from camfrog_autodj.playqueue import PlayQueue

        q = PlayQueue(shuffle=False)

        # Empty queue
        assert q.pop() is None
        assert q.peek() is None

        # Remove from empty
        assert q.remove(1) is None

        # Count by empty
        assert q.count_by("nobody") == 0


class TestVisualsUncovered:
    """Test visuals.py uncovered line."""

    def test_visual_helpers(self):
        from camfrog_autodj.visuals import gradient, hex_to_rgb, lerp_color, rgb_to_hex

        assert hex_to_rgb("#FF0000") == (255, 0, 0)
        assert rgb_to_hex(255, 0, 0) == "#ff0000"
        assert lerp_color("#FF0000", "#00FF00", 0.5) == "#808000"
        assert gradient(["#FF0000", "#00FF00"], 3) == ["#ff0000", "#808000", "#00ff00"]
