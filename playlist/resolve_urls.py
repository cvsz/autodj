#!/usr/bin/env python3
"""Resolve search-backed playlist entries to verified YouTube watch URLs.

TLS verification is always enabled. POSIX (including WSL2) uses the system CA
store by default. Windows keeps yt-dlp's default CA behavior unless a custom
CA bundle or --system-ca is supplied.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SEARCH = re.compile(r"^ytsearch\d*:(?P<q>.+)$", re.I | re.S)
URL = re.compile(r"^https://www\.youtube\.com/watch\?v=[A-Za-z0-9_-]{11}$")
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
CANDIDATES = 3
DEFAULT_RETRIES = 2
DEFAULT_RETRY_DELAY = 1.0
MAX_RETRIES = 10
MAX_RETRY_DELAY = 60.0

TLS_FAILURE_MARKERS = (
    "certificate_verify_failed",
    "certificate verify failed",
    "self-signed certificate",
    "unable to get local issuer certificate",
    "unknown ca",
    "certificate has expired",
)
TRANSIENT_FAILURE_MARKERS = (
    "timed out",
    "timeout",
    "temporary failure",
    "name or service not known",
    "connection reset",
    "connection aborted",
    "connection refused",
    "network is unreachable",
    "remote end closed",
    "incomplete read",
    "unexpected eof",
    "temporarily unavailable",
    "too many requests",
    "service unavailable",
    "http error 408",
    "http error 425",
    "http error 429",
    "http error 500",
    "http error 502",
    "http error 503",
    "http error 504",
)


class ResolverError(RuntimeError):
    """A classified yt-dlp or playlist resolution failure."""

    def __init__(self, category: str, message: str):
        super().__init__(message)
        self.category = category


def find_ytdlp(explicit: str | None = None) -> list[str]:
    """Detect explicit executable, PATH executable, then current Python module."""
    if explicit:
        resolved = shutil.which(explicit)
        candidate = Path(explicit).expanduser()
        if resolved:
            return [resolved]
        if candidate.is_file():
            return [str(candidate.resolve())]
        raise ResolverError("ytdlp_not_found", f"Configured yt-dlp executable was not found: {explicit}")

    names = ("yt-dlp.exe", "yt-dlp") if os.name == "nt" else ("yt-dlp",)
    for name in names:
        resolved = shutil.which(name)
        if resolved:
            return [resolved]

    try:
        if importlib.util.find_spec("yt_dlp") is not None:
            return [sys.executable, "-m", "yt_dlp"]
    except (ImportError, ValueError):
        pass

    raise ResolverError(
        "ytdlp_not_found",
        "yt-dlp was not found. Install it with python -m pip install -U yt-dlp, "
        "add yt-dlp to PATH, or pass --ytdlp PATH.",
    )


def configure_ca(
    ca_bundle: str | None,
    system_ca: bool | None,
) -> tuple[dict[str, str], bool, str | None]:
    """Validate an optional PEM bundle and prepare a process-local CA environment."""
    configured = (
        ca_bundle
        or os.environ.get("AUTODJ_YTDLP_CA_BUNDLE")
        or os.environ.get("SSL_CERT_FILE")
    )
    env = os.environ.copy()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_file():
            raise ResolverError("invalid_ca_bundle", f"CA bundle does not exist or is not a file: {path}")
        try:
            ssl.create_default_context(cafile=str(path.resolve()))
        except (OSError, ssl.SSLError) as ex:
            raise ResolverError(
                "invalid_ca_bundle",
                f"CA bundle is not a valid readable PEM bundle: {path} ({ex})",
            ) from ex
        bundle = str(path.resolve())
        env["SSL_CERT_FILE"] = bundle
        env["REQUESTS_CA_BUNDLE"] = bundle
        env["CURL_CA_BUNDLE"] = bundle
        return env, True, bundle

    use_system_ca = (os.name != "nt") if system_ca is None else system_ca
    return env, use_system_ca, None


def classify_failure(message: str) -> str:
    lowered = message.lower()
    if any(marker in lowered for marker in TLS_FAILURE_MARKERS):
        return "tls_certificate"
    if any(marker in lowered for marker in TRANSIENT_FAILURE_MARKERS):
        return "transient_network"
    return "permanent"


def failure_guidance(category: str, message: str) -> str:
    if category == "tls_certificate":
        return (
            "TLS certificate verification failed; verification remains enabled. "
            "Check the HTTPS inspection/proxy CA trust chain. On WSL2/Linux, use "
            "--system-ca or --ca-bundle PATH; on Windows, export the trusted "
            "organization root CA as PEM and pass --ca-bundle PATH. "
            "Never disable certificate verification. Details: " + message
        )
    if category == "invalid_ca_bundle":
        return "Invalid CA bundle configuration. Supply a readable PEM CA bundle. Details: " + message
    if category == "ytdlp_not_found":
        return message
    if category == "transient_network":
        return "Temporary network failure after retry policy: " + message
    return message


def command_options(use_system_ca: bool) -> list[str]:
    options = [
        "--dump-single-json",
        "--flat-playlist",
        "--no-warnings",
        "--skip-download",
        "--retries",
        "0",
        "--extractor-retries",
        "0",
        "--socket-timeout",
        "30",
    ]
    if use_system_ca:
        options.extend(["--compat-options", "no-certifi"])
    return options


def search(
    query: str,
    command: list[str],
    env: dict[str, str],
    use_system_ca: bool,
    retries: int = DEFAULT_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
) -> list[dict]:
    target = f"ytsearch{CANDIDATES}:{query}"
    cmd = [*command, *command_options(use_system_ca), target]
    last_error = "unknown yt-dlp error"

    for attempt in range(retries + 1):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
                check=False,
                env=env,
            )
        except subprocess.TimeoutExpired:
            category = "transient_network"
            last_error = "yt-dlp process timed out after 120 seconds"
        except OSError as ex:
            raise ResolverError("ytdlp_execution", f"Could not execute yt-dlp: {ex}") from ex
        else:
            if result.returncode == 0:
                try:
                    info = json.loads(result.stdout)
                except (TypeError, ValueError) as ex:
                    raise ResolverError("invalid_response", f"yt-dlp returned invalid JSON: {ex}") from ex
                if not isinstance(info, dict):
                    raise ResolverError("invalid_response", "yt-dlp returned JSON that was not an object")
                return [entry for entry in (info.get("entries") or []) if isinstance(entry, dict)]

            last_error = (result.stderr or result.stdout or "").strip()
            if not last_error:
                last_error = f"yt-dlp exited with code {result.returncode}"
            category = classify_failure(last_error)

        if category != "transient_network" or attempt >= retries:
            raise ResolverError(category, last_error)
        time.sleep(min(retry_delay * (2**attempt), MAX_RETRY_DELAY))

    raise ResolverError("transient_network", last_error)


def pick(results: list[dict]) -> dict | None:
    """Select the first real video with a valid ID, title, and known duration."""
    for entry in results:
        video_id = str(entry.get("id") or "")
        if VIDEO_ID.fullmatch(video_id) and entry.get("duration") and entry.get("title"):
            return {
                "source": f"https://www.youtube.com/watch?v={video_id}",
                "title": entry["title"],
                "duration": float(entry["duration"]),
            }
    return None


def fix_entry(entry: dict, lookup) -> str:
    """Mutate one entry. Returns ok, skip, or fail:category:message."""
    source = str(entry.get("source") or "").strip()
    if URL.fullmatch(source):
        return "skip"
    match = SEARCH.match(source)
    if not match:
        return f"fail:invalid_source:unrecognised source {source!r}"
    query = match["q"].strip()
    try:
        hit = pick(lookup(query))
    except ResolverError as ex:
        return f"fail:{ex.category}:{failure_guidance(ex.category, str(ex))}"
    except Exception as ex:
        return f"fail:lookup_error:{ex}"
    if not hit:
        return "fail:no_result:no playable video result was returned"
    entry["query"] = query
    entry.update(hit)
    return "ok"


def process_file(
    path: Path,
    lookup,
    dry: bool,
    delay: float,
    failure_records: list[dict] | None = None,
) -> tuple[int, int, list[str]]:
    data = json.loads(path.read_text("utf-8-sig"))
    tracks = data["tracks"] if isinstance(data, dict) else data
    if not isinstance(tracks, list):
        raise ValueError("playlist must contain a tracks array or be a JSON array")

    ok = skip = 0
    fails: list[str] = []
    for entry in tracks:
        if not isinstance(entry, dict):
            message = "playlist entry must be a JSON object"
            fails.append(f"{path.name}: {message}")
            if failure_records is not None:
                failure_records.append({"file": path.name, "category": "invalid_playlist", "message": message})
            continue

        result = fix_entry(entry, lookup)
        if result == "ok":
            ok += 1
            print(f"  ok   {entry['source']}  {str(entry['title'])[:60]}")
            if not dry:
                save(path, data)
            if delay:
                time.sleep(delay)
        elif result == "skip":
            skip += 1
        else:
            detail = result[5:]
            category, separator, message = detail.partition(":")
            message = message if separator else detail
            failure = f"{path.name}: {entry.get('source')} ({category}: {message})"
            fails.append(failure)
            print(f"  FAIL {failure}")
            if failure_records is not None:
                failure_records.append(
                    {
                        "file": path.name,
                        "source": entry.get("source"),
                        "category": category,
                        "message": message,
                    }
                )

    seen: set[str] = set()
    unique = []
    for track in tracks:
        if not isinstance(track, dict):
            unique.append(track)
            continue
        source = str(track.get("source", ""))
        if URL.fullmatch(source):
            if source in seen:
                continue
            seen.add(source)
        unique.append(track)
    if len(unique) != len(tracks) and not dry:
        tracks[:] = unique
        save(path, data)
    return ok, skip, fails


def save(path: Path, data) -> None:
    backup = path.with_name(path.name + ".bak")
    if not backup.exists():
        shutil.copyfile(path, backup)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()


def write_report(path: Path, report: dict) -> None:
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", help="playlist files (default: every *.json next to this script)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ytdlp", help="explicit yt-dlp executable path or command")
    parser.add_argument("--ca-bundle", help="trusted PEM CA bundle; also accepts AUTODJ_YTDLP_CA_BUNDLE")
    parser.add_argument(
        "--system-ca",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="use the platform CA store (default: enabled on POSIX, disabled on Windows)",
    )
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES, help=f"retries for transient network failures (0-{MAX_RETRIES})")
    parser.add_argument("--retry-delay", type=float, default=DEFAULT_RETRY_DELAY, help="initial exponential retry delay in seconds")
    parser.add_argument("--delay", type=float, default=0.5, help="seconds between successful lookups (default 0.5)")
    parser.add_argument("--report-json", help="write a machine-readable summary and per-entry failure report")
    args = parser.parse_args(argv)

    if not 0 <= args.retries <= MAX_RETRIES:
        parser.error(f"--retries must be between 0 and {MAX_RETRIES}")
    if not 0 <= args.retry_delay <= MAX_RETRY_DELAY:
        parser.error(f"--retry-delay must be between 0 and {MAX_RETRY_DELAY}")
    if args.delay < 0:
        parser.error("--delay must not be negative")

    try:
        command = find_ytdlp(args.ytdlp)
        env, use_system_ca, ca_bundle = configure_ca(args.ca_bundle, args.system_ca)
    except ResolverError as ex:
        print(f"ERROR [{ex.category}]: {failure_guidance(ex.category, str(ex))}", file=sys.stderr)
        return 2

    print(f"yt-dlp command: {' '.join(command)}")
    print(f"TLS verification: enabled; CA mode: {'system' if use_system_ca else 'yt-dlp default'}")
    if ca_bundle:
        print(f"CA bundle: {ca_bundle}")

    here = Path(__file__).resolve().parent
    files = [Path(file) for file in args.files] or sorted(here.glob("*.json"))
    total_ok = total_skip = 0
    all_fails: list[str] = []
    failure_records: list[dict] = []
    file_reports: list[dict] = []

    for file_path in files:
        print(file_path.name)
        try:
            resolved, skipped, failures = process_file(
                file_path,
                lambda query: search(
                    query,
                    command,
                    env,
                    use_system_ca,
                    retries=args.retries,
                    retry_delay=args.retry_delay,
                ),
                args.dry_run,
                args.delay,
                failure_records,
            )
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, ValueError) as ex:
            message = f"{type(ex).__name__}: {ex}"
            all_fails.append(f"{file_path}: {message}")
            failure_records.append(
                {"file": str(file_path), "category": "playlist_file_error", "message": message}
            )
            file_reports.append({"file": str(file_path), "resolved": 0, "skipped": 0, "failed": 1})
            print(f"  FILE ERROR: {message}")
            continue

        total_ok += resolved
        total_skip += skipped
        all_fails.extend(failures)
        file_reports.append(
            {"file": str(file_path), "resolved": resolved, "skipped": skipped, "failed": len(failures)}
        )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": "playlist.resolve_urls",
        "yt_dlp_command": command,
        "tls_verification": "enabled",
        "ca_mode": "system" if use_system_ca else "yt-dlp-default",
        "ca_bundle": ca_bundle,
        "dry_run": args.dry_run,
        "summary": {"resolved": total_ok, "already_urls": total_skip, "failed": len(all_fails)},
        "files": file_reports,
        "failures": failure_records,
    }
    if args.report_json:
        try:
            write_report(Path(args.report_json), report)
            print(f"Failure report: {args.report_json}")
        except OSError as ex:
            print(f"ERROR: could not write JSON report: {ex}", file=sys.stderr)
            return 2

    print(
        f"\nresolved {total_ok}, already URLs {total_skip}, failed {len(all_fails)}"
        + (" (dry run: nothing written)" if args.dry_run else "")
    )
    for failure in all_fails:
        print(f"  could not resolve: {failure}", file=sys.stderr)
    return 1 if all_fails else 0


if __name__ == "__main__":
    sys.exit(main())
