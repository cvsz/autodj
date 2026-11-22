"""Regression tests for auto-update integrity and AI endpoint validation."""

from __future__ import annotations

import hashlib
import io
from types import SimpleNamespace
from unittest.mock import patch

from autodj.ai import AIClient
from autodj.config import Config
from autodj.updater import Updater, is_newer


def _cfg(**kw):
    base = {
        "auto_update_enabled": True,
        "auto_update_repo": "cvsz/autodj",
        "auto_update_asset": "AutoDJ.exe",
    }
    base.update(kw)
    return SimpleNamespace(**base)


class _Resp(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def test_startup_apply_setting_and_missing_script(tmp_path):
    assert Config().auto_update_apply_on_start is True
    updater = Updater(_cfg())
    assert updater.launch_update_script(tmp_path / "AutoDJ.exe") is False


def test_version_compare_only_strictly_newer():
    assert is_newer("v0.3.1", "0.3.0")
    assert is_newer("1.0", "0.9.9")
    assert not is_newer("v0.2.9", "0.3.0")  # older tag must not prompt
    assert not is_newer("0.3.0", "0.3.0")
    assert not is_newer("nightly", "0.3.0")


def test_check_for_update_ignores_older_release():
    up = Updater(_cfg())
    with patch.object(up, "_fetch_json", return_value={"tag_name": "v0.0.1", "assets": []}):
        assert up.check_for_update() is None


def test_repo_setting_cannot_inject_path():
    assert Updater(_cfg(auto_update_repo="evil/x/../../y?a=1")).repo == "cvsz/autodj"


def test_find_asset_prefers_exact_name():
    up = Updater(_cfg())
    up._latest = {"assets": [{"name": "AutoDJ.exe.sha256"}, {"name": "AutoDJ.exe"}]}
    assert up.find_asset()["name"] == "AutoDJ.exe"


def test_download_refused_without_digest(tmp_path):
    up = Updater(_cfg())
    up._latest = {"assets": []}
    asset = {"name": "AutoDJ.exe", "browser_download_url": "https://github.com/cvsz/autodj/x"}
    with patch("autodj.updater.urlopen") as uo:
        assert up.download_asset(asset, tmp_path / "AutoDJ.next.exe") is False
        uo.assert_not_called()


def test_download_rejects_digest_mismatch(tmp_path):
    up = Updater(_cfg())
    up._latest = {"assets": []}
    asset = {
        "name": "AutoDJ.exe",
        "browser_download_url": "https://github.com/cvsz/autodj/x",
        "digest": "sha256:" + "0" * 64,
    }
    dest = tmp_path / "AutoDJ.next.exe"
    with patch("autodj.updater.urlopen", return_value=_Resp(b"tampered")):
        assert up.download_asset(asset, dest) is False
    assert not dest.exists()
    assert not (tmp_path / "AutoDJ.next.exe.part").exists()


def test_download_accepts_matching_digest(tmp_path):
    data = b"MZ-real-binary"
    up = Updater(_cfg())
    up._latest = {"assets": []}
    asset = {
        "name": "AutoDJ.exe",
        "browser_download_url": "https://github.com/cvsz/autodj/x",
        "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
    }
    dest = tmp_path / "AutoDJ.next.exe"
    with patch("autodj.updater.urlopen", return_value=_Resp(data)):
        assert up.download_asset(asset, dest) is True
    assert dest.read_bytes() == data


def test_updater_disabled_reads_live_config():
    cfg = _cfg(auto_update_enabled=False)
    up = Updater(cfg)
    assert up.enabled is False
    cfg.auto_update_enabled = True
    assert up.enabled is True


def test_ai_url_policy():
    ok = AIClient._allowed_url
    assert ok("https://api.openai.com/v1/chat/completions")
    assert ok("https://openrouter.ai/api/v1/chat/completions")
    assert ok("http://127.0.0.1:8080/v1/chat/completions")
    assert not ok("http://api.openai.com/v1/chat/completions")  # key over cleartext
    assert not ok("https://user:pw@example.com/v1")
    assert not ok("file:///etc/passwd")


def test_ai_post_reaches_configured_provider():
    cfg = SimpleNamespace(ai_enabled=True, ai_api_key="k", ai_base_url="https://api.openai.com/v1")
    client = AIClient(cfg)
    body = b'{"choices":[{"message":{"content":"hi"}}]}'
    with patch("autodj.ai.urlopen", return_value=_Resp(body)) as uo:
        assert client.chat("hello") == "hi"
    assert uo.call_args[0][0].full_url == "https://api.openai.com/v1/chat/completions"


def test_ai_never_answers_private_messages_in_public_room():
    from unittest.mock import Mock

    from autodj.engine import Engine

    fake = Mock()
    fake.ai.is_enabled.return_value = True
    Engine._ai_handle_im(fake, SimpleNamespace(user="bob", text="my secret", is_im=True))
    fake.ai.chat.assert_not_called()
    fake.say.assert_not_called()


def _fake_ai_engine():
    import threading
    from unittest.mock import Mock

    fake = Mock()
    fake.cfg.prefix = "!"
    fake.blocked = set()
    fake._ai_inflight = 0
    fake._ai_inflight_lock = threading.Lock()
    fake.ai.is_enabled.return_value = True
    fake.ai.can_reply.return_value = True
    fake.t.side_effect = lambda key, **kw: key
    return fake


def test_ai_ask_is_async_and_cooldown_gated():
    from autodj.engine import Engine

    fake = _fake_ai_engine()
    Engine.ai_ask(fake, "bob", "hello")
    fake.ai.chat.assert_not_called()  # not on the chat thread
    # dedicated AI pool, never the command executor
    fake._ai_exec.submit.assert_called_once_with(fake._ai_reply, "bob", "hello")
    fake.exec.submit.assert_not_called()

    fake._ai_exec.reset_mock()
    fake.ai.can_reply.return_value = False
    Engine.ai_ask(fake, "amy", "again")
    fake._ai_exec.submit.assert_not_called()
    fake.say.assert_called_with("amy: ai_wait")


def test_ai_ask_caps_inflight_calls():
    from autodj.engine import AI_MAX_INFLIGHT, Engine

    fake = _fake_ai_engine()
    for n in range(AI_MAX_INFLIGHT + 3):
        Engine.ai_ask(fake, f"u{n}", "hi")
    assert fake._ai_exec.submit.call_count == AI_MAX_INFLIGHT  # slow provider: refuse the rest
    fake.say.assert_called_with(f"u{AI_MAX_INFLIGHT + 2}: ai_busy")

    fake.ai.chat.return_value = "ok"
    Engine._ai_reply(fake, "u0", "hi")  # a finished call frees its slot
    assert fake._ai_inflight == AI_MAX_INFLIGHT - 1
    fake.say.assert_called_with("u0: ok")


def test_ai_numeric_settings_are_range_checked(tmp_path):
    import pytest

    from autodj.config import Config, ConfigError

    for line in ("ai_user_cooldown = -5", "ai_max_chars = 0"):
        p = tmp_path / "config.toml"
        p.write_text(line + "\n", encoding="utf-8")
        with pytest.raises(ConfigError):
            Config.load(str(p))
