"""Auto-update: a downloaded AutoDJ.exe must be signed by the pinned certificate.

The SHA-256 check alone only proves the file is what GitHub published; v0.3.10.1
shipped an unsigned AutoDJ.exe that the updater would have installed.
"""

from __future__ import annotations

import hashlib
import io
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from autodj import updater as upd
from autodj.updater import TRUSTED_SIGNER_THUMBPRINTS, Updater, verify_authenticode

PINNED = next(iter(TRUSTED_SIGNER_THUMBPRINTS))


class _Resp(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def _up():
    cfg = SimpleNamespace(
        auto_update_enabled=True, auto_update_repo="cvsz/autodj", auto_update_asset="AutoDJ.exe"
    )
    up = Updater(cfg)
    up._latest = {"assets": []}
    return up


def _asset(data: bytes) -> dict:
    return {
        "name": "AutoDJ.exe",
        "browser_download_url": "https://github.com/cvsz/autodj/x",
        "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
    }


def test_matching_digest_but_rejected_signature_is_discarded(tmp_path):
    data = b"MZ-unsigned"
    up = _up()
    up.verify_signature = lambda p: (False, "signature status is NotSigned")
    dest = tmp_path / "AutoDJ.next.exe"
    with patch("autodj.updater.urlopen", return_value=_Resp(data)):
        assert up.download_asset(_asset(data), dest) is False
    assert not dest.exists()
    assert not (tmp_path / "AutoDJ.next.exe.part").exists()


def test_signature_checked_on_the_final_exe_name(tmp_path):
    data = b"MZ-signed"
    seen: list[Path] = []
    up = _up()
    up.verify_signature = lambda p: (seen.append(p), (True, "ok"))[1]
    dest = tmp_path / "AutoDJ.next.exe"
    with patch("autodj.updater.urlopen", return_value=_Resp(data)):
        assert up.download_asset(_asset(data), dest) is True
    assert seen == [dest]


def test_non_exe_assets_skip_the_signature_check(tmp_path):
    data = b"checksums"
    up = _up()
    up.verify_signature = lambda p: pytest.fail("non-exe must not be Authenticode-checked")
    with patch("autodj.updater.urlopen", return_value=_Resp(data)):
        assert up.download_asset(_asset(data), tmp_path / "notes.txt") is True


def _fake_ps(stdout: str):
    return lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout=stdout, stderr="")


@pytest.mark.parametrize(
    ("stdout", "ok"),
    [
        (f"Valid|{PINNED}", True),
        (f"UnknownError|{PINNED.lower()}", True),  # self-signed root not trusted on this PC
        ("HashMismatch|" + PINNED, False),  # tampered after signing
        ("NotSigned|", False),
        ("Valid|" + "A" * 40, False),  # validly signed, but by someone else
        ("NotTrusted|" + PINNED, False),  # explicitly distrusted
        ("", False),
    ],
)
def test_verify_authenticode_decision(monkeypatch, stdout, ok):
    exe = Path("C:/x/AutoDJ.next.exe")  # before os.name is patched (no WindowsPath on Linux)
    monkeypatch.setattr(upd.os, "name", "nt")
    monkeypatch.setattr(upd.subprocess, "run", _fake_ps(stdout))
    assert verify_authenticode(exe)[0] is ok


def test_path_reaches_powershell_only_through_env(monkeypatch):
    captured = {}

    def run(argv, **kw):
        captured["argv"] = argv
        captured["env"] = kw["env"]
        return subprocess.CompletedProcess(argv, 0, stdout="NotSigned|", stderr="")

    evil = "C:/x/a'; Remove-Item C:/ -Recurse; '.exe"
    evil_path = Path(evil)  # before os.name is patched
    monkeypatch.setattr(upd.os, "name", "nt")
    monkeypatch.setattr(upd.subprocess, "run", run)
    verify_authenticode(evil_path)
    assert all(evil not in str(a) for a in captured["argv"])
    assert captured["env"]["AUTODJ_VERIFY_PATH"] == str(evil_path)


def test_powershell_failure_fails_closed(monkeypatch):
    def boom(*a, **k):
        raise subprocess.TimeoutExpired("powershell", 60)

    exe = Path("C:/x/AutoDJ.next.exe")  # before os.name is patched
    monkeypatch.setattr(upd.os, "name", "nt")
    monkeypatch.setattr(upd.subprocess, "run", boom)
    assert verify_authenticode(exe)[0] is False


def test_non_windows_fails_closed(monkeypatch):
    monkeypatch.setattr(upd.os, "name", "posix")
    assert verify_authenticode(Path("/tmp/AutoDJ.next.exe"))[0] is False


# ---- real PowerShell (Windows only) ---------------------------------------------------------

windows = pytest.mark.skipif(os.name != "nt", reason="Authenticode is Windows-only")


@windows
def test_real_unsigned_file_is_rejected(tmp_path):
    f = tmp_path / "AutoDJ.next.exe"
    f.write_bytes(b"MZ" + b"\0" * 512)
    ok, why = verify_authenticode(f)
    assert ok is False, why


@windows
def test_real_file_signed_by_someone_else_is_rejected():
    ps = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "notepad.exe"
    if not ps.is_file():
        pytest.skip("notepad.exe not present")
    ok, why = verify_authenticode(ps)
    assert ok is False, why


@windows
def test_real_release_exe_is_accepted():
    """Set AUTODJ_SIGNED_EXE to a signed AutoDJ.exe (e.g. the v0.3.10 asset) to run."""
    exe = os.environ.get("AUTODJ_SIGNED_EXE")
    if not exe:
        pytest.skip("AUTODJ_SIGNED_EXE not set")
    ok, why = verify_authenticode(Path(exe))
    assert ok is True, why
