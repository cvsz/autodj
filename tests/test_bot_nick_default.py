"""Default bot_nick is AutoDJBot; the setup check flags only that default."""

import re
import tomllib

from autodj import doctor
from autodj.config import DEFAULT_BOT_NICK, Config


def _infos(cfg):
    out = []
    doctor._check_admin_bot_nick_audio(cfg, out)
    return [r for r in out if "bot_nick" in str(r)]


def test_default_is_autodjbot_everywhere():
    assert DEFAULT_BOT_NICK == "AutoDJBot" == Config().bot_nick
    with open("config.example.toml", "rb") as fh:
        assert tomllib.load(fh)["bot_nick"] == DEFAULT_BOT_NICK


def test_doctor_flags_only_the_default_nick():
    assert _infos(Config(bot_nick=DEFAULT_BOT_NICK))  # default -> INFO
    assert not _infos(Config(bot_nick="AutoDJ"))  # a real nick (even the old default) -> quiet


def test_install_ps1_edits_match_the_example_config():
    """install.ps1 rewrites bot_nick/admins/music_dirs with regexes that must hit the example."""
    ps1 = open("install.ps1", encoding="utf-8-sig").read()
    example = open("config.example.toml", encoding="utf-8").read()
    for key, rx in (
        ("bot_nick", r'(?m)^bot_nick\s*=\s*"[^"]*"'),
        ("admins", r"(?m)^admins\s*=\s*\[[^\]]*\]"),
        ("music_dirs", r"(?m)^music_dirs\s*=\s*\[[^\]]*\]"),
    ):
        assert f"'{rx}'" in ps1, key  # the installer uses exactly this pattern
        assert re.search(rx, example), key  # and it matches the shipped example
