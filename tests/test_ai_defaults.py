"""The AI defaults live in two places: keep them equal and pointing at a real NVIDIA model."""

import tomllib

from autodj import ai
from autodj.config import Config


def test_config_and_client_defaults_agree():
    c = Config()
    assert c.ai_base_url == ai.DEFAULT_BASE_URL
    assert c.ai_model == ai.DEFAULT_MODEL
    assert c.ai_system_prompt == ai.DEFAULT_SYSTEM_PROMPT


def test_example_config_matches_code_defaults():
    with open("config.example.toml", "rb") as fh:
        ex = tomllib.load(fh)
    c = Config()
    for key in ("ai_enabled", "ai_api_key", "ai_base_url", "ai_model", "ai_system_prompt"):
        assert ex[key] == getattr(c, key), key
    assert ex["ai_api_key"] == "" and ex["ai_enabled"] is True  # template ships AI on


def test_ai_off_without_key():
    client = ai.AIClient(Config(ai_enabled=True, ai_api_key=""))
    assert not client.is_enabled() and not client.can_reply("amy")
