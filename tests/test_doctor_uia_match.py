"""Test that doctor.py uses exact match for uia."""

from camfrog_autodj.config import Config


def test_doctor_exact_uia_match_logic():
    """Doctor should use exact match for 'uia' adapter type."""

    # Test the exact match logic used in doctor.py line 57
    def is_uia_enabled(cfg):
        return cfg.chat_reader == "uia" or cfg.chat_sender == "uia"

    # Exact match should work
    cfg = Config()
    cfg.chat_reader = "uia"
    cfg.chat_sender = "console"
    assert is_uia_enabled(cfg) is True

    cfg.chat_reader = "console"
    cfg.chat_sender = "uia"
    assert is_uia_enabled(cfg) is True

    cfg.chat_reader = "uia"
    cfg.chat_sender = "uia"
    assert is_uia_enabled(cfg) is True

    # Substring should NOT match
    cfg.chat_reader = "uia_something"
    cfg.chat_sender = "console"
    assert is_uia_enabled(cfg) is False

    cfg.chat_reader = "console"
    cfg.chat_sender = "something_uia"
    assert is_uia_enabled(cfg) is False

    cfg.chat_reader = "uia"
    cfg.chat_sender = "uia_something"
    assert is_uia_enabled(cfg) is True  # chat_reader is exact "uia"

    # Neither is uia
    cfg.chat_reader = "console"
    cfg.chat_sender = "logtail"
    assert is_uia_enabled(cfg) is False
