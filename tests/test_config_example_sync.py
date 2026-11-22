"""config.example.toml must stay in step with autodj.config.Config.

Every Config field is documented in the shipped example, the example has no
stale keys, and the file is plain UTF-8 (no BOM) so Thai text loads the same
everywhere.
"""

from __future__ import annotations

import dataclasses
import pathlib
import tomllib

from autodj.config import Config

EXAMPLE = pathlib.Path(__file__).resolve().parent.parent / "config.example.toml"


def _example() -> dict:
    with EXAMPLE.open("rb") as fh:
        return tomllib.load(fh)


def test_every_config_field_is_in_the_example():
    fields = {f.name for f in dataclasses.fields(Config)}
    missing = sorted(fields - set(_example()))
    assert not missing, f"add to config.example.toml: {missing}"


def test_example_has_no_stale_keys():
    fields = {f.name for f in dataclasses.fields(Config)}
    stale = sorted(set(_example()) - fields)
    assert not stale, f"not Config fields (remove or rename): {stale}"


def test_example_is_utf8_without_bom():
    raw = EXAMPLE.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "config.example.toml must not start with a BOM"
    text = raw.decode("utf-8")  # raises if not UTF-8
    assert "�" not in text
