from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import certifi
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "playlist" / "resolve_urls.py"
SPEC = importlib.util.spec_from_file_location("playlist_resolver", SCRIPT)
assert SPEC and SPEC.loader
resolver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resolver)


def test_find_ytdlp_prefers_explicit_executable(monkeypatch, tmp_path):
    explicit = tmp_path / "custom-yt-dlp"
    explicit.write_text("binary", encoding="utf-8")
    monkeypatch.setattr(resolver.shutil, "which", lambda name: "/usr/bin/yt-dlp")
    assert resolver.find_ytdlp(str(explicit)) == [str(explicit.resolve())]


def test_find_ytdlp_uses_path_before_python_module(monkeypatch):
    monkeypatch.setattr(resolver.shutil, "which", lambda name: "/usr/bin/yt-dlp")
    monkeypatch.setattr(resolver.importlib.util, "find_spec", lambda name: object())
    assert resolver.find_ytdlp() == ["/usr/bin/yt-dlp"]


def test_find_ytdlp_falls_back_to_current_python_module(monkeypatch):
    monkeypatch.setattr(resolver.shutil, "which", lambda name: None)
    monkeypatch.setattr(resolver.importlib.util, "find_spec", lambda name: object())
    assert resolver.find_ytdlp() == [resolver.sys.executable, "-m", "yt_dlp"]


def test_find_ytdlp_reports_missing_installation(monkeypatch):
    monkeypatch.setattr(resolver.shutil, "which", lambda name: None)
    monkeypatch.setattr(resolver.importlib.util, "find_spec", lambda name: None)
    with pytest.raises(resolver.ResolverError, match="yt-dlp was not found"):
        resolver.find_ytdlp()


def test_configure_ca_uses_explicit_bundle_and_validates_it(monkeypatch, tmp_path):
    bundle = Path(certifi.where())
    env, use_system_ca, selected = resolver.configure_ca(str(bundle), None)
    assert use_system_ca is True
    assert selected == str(bundle.resolve())
    assert env["SSL_CERT_FILE"] == selected
    assert env["REQUESTS_CA_BUNDLE"] == selected
    assert env["CURL_CA_BUNDLE"] == selected

    with pytest.raises(resolver.ResolverError, match="does not exist"):
        resolver.configure_ca(str(tmp_path / "missing.pem"), None)


def test_configure_ca_uses_posix_system_store_by_default(monkeypatch):
    monkeypatch.setattr(resolver.os, "name", "posix")
    env, use_system_ca, selected = resolver.configure_ca(None, None)
    assert use_system_ca is True
    assert selected is None
    assert env == resolver.os.environ.copy()


def test_tls_failures_are_never_classified_as_transient():
    message = "CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain"
    assert resolver.classify_failure(message) == "tls_certificate"
    assert resolver.classify_failure("HTTP Error 503: Service Unavailable") == "transient_network"
    assert resolver.classify_failure("HTTP Error 403: Forbidden") == "permanent"


def test_search_retries_only_transient_network_failures(monkeypatch):
    calls = []
    payload = json.dumps({"entries": [{"id": "abcdefghijk", "title": "Track", "duration": 120}]})

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if len(calls) < 3:
            return subprocess.CompletedProcess(cmd, 1, "", "HTTP Error 503: Service Unavailable")
        return subprocess.CompletedProcess(cmd, 0, payload, "")

    monkeypatch.setattr(resolver.subprocess, "run", fake_run)
    monkeypatch.setattr(resolver.time, "sleep", lambda seconds: None)
    entries = resolver.search("EDM", ["yt-dlp"], {}, True, retries=2, retry_delay=0)
    assert entries[0]["id"] == "abcdefghijk"
    assert len(calls) == 3
    assert "--compat-options" in calls[0]
    assert "no-certifi" in calls[0]


def test_search_does_not_retry_tls_verification_failure(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(
            cmd,
            1,
            "",
            "CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain",
        )

    monkeypatch.setattr(resolver.subprocess, "run", fake_run)
    monkeypatch.setattr(resolver.time, "sleep", lambda seconds: pytest.fail("TLS errors must not be retried"))
    with pytest.raises(resolver.ResolverError) as error:
        resolver.search("EDM", ["yt-dlp"], {}, True, retries=3, retry_delay=0)
    assert error.value.category == "tls_certificate"
    assert len(calls) == 1


def test_search_does_not_retry_permanent_http_errors(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 1, "", "HTTP Error 403: Forbidden")

    monkeypatch.setattr(resolver.subprocess, "run", fake_run)
    with pytest.raises(resolver.ResolverError) as error:
        resolver.search("EDM", ["yt-dlp"], {}, True, retries=3, retry_delay=0)
    assert error.value.category == "permanent"
    assert len(calls) == 1


def test_tls_failure_is_reported_in_json_and_exit_status(monkeypatch, tmp_path):
    playlist = tmp_path / "edm_house.json"
    playlist.write_text(
        json.dumps({"tracks": [{"source": "ytsearch1:EDM festival hits official music video"}]}),
        encoding="utf-8",
    )
    report_path = tmp_path / "reports" / "playlist-report.json"

    monkeypatch.setattr(resolver, "find_ytdlp", lambda explicit=None: ["yt-dlp"])
    monkeypatch.setattr(resolver, "configure_ca", lambda ca, system: ({}, True, None))

    def fail_search(*args, **kwargs):
        raise resolver.ResolverError(
            "tls_certificate",
            "CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain",
        )

    monkeypatch.setattr(resolver, "search", fail_search)
    exit_code = resolver.main(
        [str(playlist), "--delay", "0", "--report-json", str(report_path)]
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert report["tls_verification"] == "enabled"
    assert report["summary"]["failed"] == 1
    assert report["failures"][0]["category"] == "tls_certificate"
    assert "Never disable certificate verification" in report["failures"][0]["message"]
    assert playlist.read_text(encoding="utf-8") == json.dumps(
        {"tracks": [{"source": "ytsearch1:EDM festival hits official music video"}]}
    )
