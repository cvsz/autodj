"""ProbeAccountStore: credentials encrypted at rest, passphrase never persisted,
wrong passphrase fails closed instead of wiping the store."""

# The passphrases and passwords below are throwaway test fixtures, not secrets.
# ruff: noqa: S105, S106

from __future__ import annotations

import json

import pytest

from autodj.stream.probe_account import ProbeAccount, ProbeAccountStore


@pytest.fixture(autouse=True)
def _fast_kdf(monkeypatch):
    # 600k PBKDF2 rounds are right for production, slow for a unit test.
    monkeypatch.setattr(ProbeAccountStore, "PBKDF2_ITERATIONS", 1_000, raising=False)


def _acct(**kw):
    base = {"platform": "youtube", "username": "probe1", "password": "s3cret-pass"}
    base.update(kw)
    return ProbeAccount(**base)


def test_passphrase_key_is_never_written_to_disk(tmp_path):
    store = ProbeAccountStore(tmp_path / "accounts.json", passphrase="correct horse")
    store.add(_acct())
    assert not (tmp_path / "accounts.key").exists()
    salt = (tmp_path / "accounts.salt").read_bytes()
    assert len(salt) == 16


def test_secrets_are_encrypted_at_rest(tmp_path):
    path = tmp_path / "accounts.json"
    ProbeAccountStore(path, passphrase="correct horse").add(_acct(api_key="AK-123"))
    raw = path.read_text(encoding="utf-8")
    assert "s3cret-pass" not in raw and "AK-123" not in raw
    stored = json.loads(raw)["youtube:probe1"]
    assert stored["username"] == "probe1"


def test_same_passphrase_reopens_store(tmp_path):
    path = tmp_path / "accounts.json"
    ProbeAccountStore(path, passphrase="correct horse").add(_acct())
    again = ProbeAccountStore(path, passphrase="correct horse")
    got = again.get("youtube", "probe1")
    assert got is not None and got.password == "s3cret-pass"


def test_wrong_passphrase_fails_closed_and_keeps_data(tmp_path):
    path = tmp_path / "accounts.json"
    ProbeAccountStore(path, passphrase="correct horse").add(_acct())
    before = path.read_bytes()
    with pytest.raises(ValueError, match="wrong passphrase"):
        ProbeAccountStore(path, passphrase="wrong")
    assert path.read_bytes() == before  # nothing overwritten


def test_salt_differs_per_store(tmp_path):
    ProbeAccountStore(tmp_path / "a.json", passphrase="p").add(_acct())
    ProbeAccountStore(tmp_path / "b.json", passphrase="p").add(_acct())
    assert (tmp_path / "a.salt").read_bytes() != (tmp_path / "b.salt").read_bytes()


def test_legacy_key_file_still_opens(tmp_path):
    path = tmp_path / "accounts.json"
    ProbeAccountStore(path).add(_acct())  # no passphrase: random key in accounts.key
    assert (tmp_path / "accounts.key").exists()
    got = ProbeAccountStore(path, passphrase="ignored when a key file exists").get(
        "youtube", "probe1"
    )
    assert got is not None and got.password == "s3cret-pass"
