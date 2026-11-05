from __future__ import annotations

import json
import logging
import os
import re
import shutil  # noqa: F401  re-exported for test monkeypatching of library.shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from .models import Track, YtdlpMissing
from .paths import resolve_executable

log = logging.getLogger("autodj")

AUDIO = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".opus", ".aac"}
VIDEO = {".mp4", ".mkv", ".webm", ".avi", ".mov"}
MEDIA = AUDIO | VIDEO
SEARCH_PREFIX = re.compile(r"^ytsearch\d*:", re.IGNORECASE)


def is_url(s: str) -> bool:
    return s.lower().startswith(("http://", "https://"))


def host_ok(url: str, allowed: list[str]) -> bool:
    h = (urlparse(url).hostname or "").lower()
    return any(h == a or h.endswith("." + a) for a in allowed)


def local_track(path, requester: str = "AutoDJ") -> Track:
    p = Path(path)
    title, dur = p.stem, None
    try:
        import mutagen

        f = mutagen.File(p, easy=True)
        if f is not None:
            dur = getattr(f.info, "length", None)
            t = (f.get("title") or [None])[0]
            a = (f.get("artist") or [None])[0]
            if t:
                title = f"{a} - {t}" if a else t
    except ImportError:
        pass  # mutagen not installed; fall back to filename
    except (OSError, mutagen.MutagenError):
        pass  # metadata unavailable; fall back to filename
    return Track(str(p), title, dur, requester)


def scan_folder(folder, requester: str = "AutoDJ") -> list[Track]:
    """Recursively scan *folder* for media files, skipping unreadable directories."""
    files: list[Path] = []
    root = Path(folder)
    try:
        entries = list(root.iterdir())
    except (OSError, PermissionError):
        log.warning("cannot read folder %r: permission denied", folder)
        return []
    for entry in entries:
        try:
            if entry.is_dir():
                files.extend(scan_folder(str(entry), requester))
            elif entry.is_file() and entry.suffix.lower() in MEDIA:
                files.append(entry)
        except (OSError, PermissionError):
            continue
    files.sort()
    return [local_track(p, requester) for p in files]


def find_ytdlp(ytdlp_path: str = "", mpv_path: str = "") -> str:
    """Resolve yt-dlp consistently with mpv: configured path, beside mpv, then PATH.

    Explicit but invalid paths fail closed rather than silently selecting another binary.
    Relative configured paths are resolved from the application directory.
    """
    if ytdlp_path:
        return resolve_executable(ytdlp_path)

    mpv_executable = resolve_executable(mpv_path)
    names = ("yt-dlp.exe", "yt-dlp") if os.name == "nt" else ("yt-dlp",)
    if mpv_executable:
        mpv_candidate = Path(mpv_executable)
        for name in names:
            candidate = mpv_candidate.parent / name
            if candidate.is_file():
                return str(candidate.resolve())

    return resolve_executable("yt-dlp")


def parse_ytdlp_info(info: dict, requester: str = "AutoDJ") -> list[Track]:
    """yt-dlp's info dict (single video, playlist or search result) -> tracks.

    Only tracks with valid, non-empty URLs are returned. Tracks with missing or
    invalid URLs are skipped with a log warning.
    """
    out = []
    for e in info.get("entries") or [info]:
        if not e:
            continue
        url = e.get("webpage_url") or e.get("url") or ""
        if not is_url(url):
            if not e.get("id"):
                log.warning("yt-dlp entry missing URL and ID, skipping")
                continue
            url = f"https://www.youtube.com/watch?v={e['id']}"
        if not url or not is_url(url):
            log.warning(f"yt-dlp entry has invalid URL: {url!r}, skipping")
            continue
        out.append(Track(url, e.get("title") or url, e.get("duration"), requester))
    return out


def _extract_exe(
    exe: str,
    target: str,
    playlist: bool,
    limit: int,
    cookies_file: str = "",
    cookies_browser: str = "",
) -> dict:
    cmd = [
        exe,
        "--dump-single-json",
        "--flat-playlist",
        "--no-warnings",
        "--skip-download",
        "--yes-playlist" if playlist else "--no-playlist",
        "--playlist-end",
        str(limit),
    ]
    if cookies_file and Path(cookies_file).is_file():
        cmd.extend(["--cookies", str(Path(cookies_file).resolve())])
    elif cookies_browser:
        cmd.extend(["--cookies-from-browser", str(cookies_browser).strip()])
    cmd.append(target)
    kw: dict = {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": 90,
    }
    if os.name == "nt":
        kw["creationflags"] = (
            0x08000000  # CREATE_NO_WINDOW: no console flash from the GUI build
        )
    # yt-dlp.exe has no --certificate flag and does not honour REQUESTS_CA_BUNDLE.
    # Certificate verification is always preserved; we never disable it.
    # Custom CA bundle support is handled by the yt_dlp Python module path
    # (see _extract_module) which can patch certifi.where().
    try:
        r = subprocess.run(cmd, check=False, **kw)
    except subprocess.TimeoutExpired:
        raise RuntimeError("yt-dlp timed out") from None
    if r.returncode != 0:
        tail = (r.stderr or "").strip().splitlines()
        raise RuntimeError(
            "yt-dlp failed: " + (tail[-1] if tail else f"exit code {r.returncode}")
        )
    try:
        return json.loads(r.stdout)
    except ValueError:
        raise RuntimeError("yt-dlp returned no usable result") from None


def _extract_module(
    target: str, playlist: bool, limit: int, ca_bundle: str = ""
) -> dict:
    import yt_dlp

    # yt_dlp uses certifi.where() for its CA bundle (see networking/_helper.py).
    # Temporarily patch certifi.where() to return a custom bundle when configured.
    # Certificate verification is always preserved; we never disable it.
    _certifi_where = None
    if ca_bundle and Path(ca_bundle).is_file():
        import certifi

        _certifi_where = certifi.where
        certifi.where = lambda *a, **k: str(Path(ca_bundle).resolve())

    try:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": "in_playlist",
            "noplaylist": not playlist,
            "playlistend": limit,
        }
        with yt_dlp.YoutubeDL(opts) as y:
            return y.extract_info(target, download=False) or {}
    finally:
        if _certifi_where is not None:
            certifi.where = _certifi_where


def remote_tracks(
    query: str,
    requester: str = "AutoDJ",
    playlist: bool = False,
    limit: int = 200,
    ytdlp_path: str = "",
    mpv_path: str = "",
    search_limit: int = 1,
    raw_target: bool = False,
    cookies_file: str = "",
    cookies_browser: str = "",
    ca_bundle: str = "",
) -> list[Track]:
    """YouTube URL, playlist URL, or plain text search -> tracks (metadata only).
    Uses the yt-dlp executable when there is one (see find_ytdlp), else the yt_dlp Python module.

    *search_limit*: for plain-text queries, how many YouTube results to fetch (default 1 keeps
    backward-compatible behaviour for non-admin !play).  Admins can pass a higher value to get a
    playlist of search results.

    *ca_bundle*: path to a custom PEM CA bundle for certificate verification.
    yt-dlp.exe has no --certificate flag and does not honour REQUESTS_CA_BUNDLE, so when the
    executable fails with a certificate error and a ca_bundle is configured, we fall back to
    the yt_dlp Python module where certifi.where() can be patched.  Certificate verification
    is always preserved; it is never disabled.
    """
    n = max(1, int(search_limit))
    # raw_target: operator-supplied yt-dlp search such as "ytsearch20:mandopop" (autoplay_sources) is used as is
    if is_url(query) or (raw_target and SEARCH_PREFIX.match(query)):
        target = query
    else:
        target = f"ytsearch{n}:{query}"
    exe = find_ytdlp(ytdlp_path, mpv_path)
    info = None
    exe_error = None
    if exe:
        try:
            info = _extract_exe(
                exe,
                target,
                playlist,
                limit,
                cookies_file=cookies_file,
                cookies_browser=cookies_browser,
            )
        except OSError as ex:  # cannot even start it: try the module instead
            log.warning("cannot run %s (%s): trying the yt_dlp module", exe, ex)
        except RuntimeError as ex:
            exe_error = ex
            msg = str(ex)
            # If the executable failed with a certificate error and a custom CA
            # bundle is configured, fall back to the Python module where we can
            # patch certifi.where() to use the bundle.  Verification stays on.
            if (
                ca_bundle
                and Path(ca_bundle).is_file()
                and ("SSL" in msg or "CERTIFICATE" in msg or "certificate" in msg)
            ):
                log.warning(
                    "yt-dlp.exe certificate failure; falling back to yt_dlp module with custom CA bundle"
                )
            else:
                # Non-SSL failure, or SSL without a CA bundle: report the error
                raise
    if info is None:
        try:
            info = _extract_module(target, playlist, limit, ca_bundle=ca_bundle)
        except ImportError:
            if exe_error is not None:
                raise YtdlpMissing(
                    "yt-dlp not found: the yt-dlp executable failed "
                    f"({exe_error}) and this build has no yt_dlp Python module. "
                    "Put yt-dlp.exe next to mpv.exe (or set ytdlp_path in config.toml), "
                    "or `pip install yt-dlp` and rebuild AutoDJ.exe."
                ) from None
            raise YtdlpMissing(
                "yt-dlp not found: there is no yt-dlp executable (next to mpv.exe or on PATH) and this build has no "
                "yt_dlp Python module. Put yt-dlp.exe next to mpv.exe (or set ytdlp_path in config.toml), "
                "or `pip install yt-dlp` and rebuild AutoDJ.exe."
            ) from None
    return parse_ytdlp_info(info, requester)


class LocalIndex:
    def __init__(self, dirs):
        self.dirs = [Path(d).resolve() for d in dirs]
        self.tracks: list[Track] = []

    def scan(self):
        self.tracks = [t for d in self.dirs if d.is_dir() for t in scan_folder(d)]

    def find(self, query: str, requester: str) -> Track | None:
        words = query.lower().split()
        for t in self.tracks:
            hay = f"{t.title} {Path(t.source).name}".lower()
            if words and all(w in hay for w in words):
                return Track(t.source, t.title, t.duration, requester)
        return None

    def contains(self, path) -> bool:
        p = Path(path).resolve()
        return any(p.is_relative_to(d) for d in self.dirs)
