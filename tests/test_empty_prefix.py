"""Test that empty prefix is rejected."""

import os
import tempfile

from camfrog_autodj.config import Config
from camfrog_autodj.exceptions import ConfigError


def test_empty_prefix_rejected_at_config():
    """Config validation should reject empty prefix."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('prefix = ""\n')
        f.write('admins = ["admin"]\n')
        fname = f.name

    try:
        Config.load(fname)
        raise AssertionError("Should have raised ConfigError")
    except ConfigError as e:
        assert "prefix" in str(e)
        assert "empty" in str(e).lower() or "must not be empty" in str(e)
    finally:
        os.unlink(fname)


def test_whitespace_prefix_rejected_at_config():
    """Config validation should reject whitespace-only prefix."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('prefix = "   "\n')
        f.write('admins = ["admin"]\n')
        fname = f.name

    try:
        Config.load(fname)
        raise AssertionError("Should have raised ConfigError")
    except ConfigError as e:
        assert "prefix" in str(e)
    finally:
        os.unlink(fname)


def test_valid_prefix_accepted():
    """Valid prefix should be accepted."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('prefix = "!"\n')
        f.write('admins = ["admin"]\n')
        fname = f.name

    try:
        cfg = Config.load(fname)
        assert cfg.prefix == "!"
    finally:
        os.unlink(fname)
