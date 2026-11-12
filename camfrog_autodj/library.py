from __future__ import annotations

import json
import logging
import os
import re
import shutil  # noqa: F401  re-exported for test monkeypatching of library.shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

from .exceptions import YtdlpMissingError
from .models import Track
from .paths import resolve_executable

log = logging.getLogger("autodj")

AUDIO = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".opus", ".aac"}
VIDEO = {".mp4", ".mkv", ".webm", ".avi", ".mov"}
MEDIA = AUDIO | VIDEO
SEARCH_PREFIX = re.compile(r"^ytsearch\d*:", re.IGNORECASE)

# Metadata cache version for forward compatibility
METADATA_CACHE_VERSION = 1
METADATA_CACHE_FILENAME = ".autodj_metadata_cache.json"


def is_url(s: str) -> bool:
    return s.lower().startswith(("http://", "https://"))


def host_ok(url: str, allowed: list[str]) -> bool:
    h = (urlparse(url).hostname or "").lower()
    return any(h == a or h.endswith("." + a) for a in allowed)


class MetadataCache:
    """Thread-safe metadata cache with mtime-based invalidation.

    Stores mutagen-extracted metadata (title, artist, duration) keyed by file path.
    Invalidates entries when file mtime changes or cache version mismatches.
    """

    def __init__(self, music_dirs: list[str]):
        self._cache: dict[str, dict] = {}
        self._lock = threading.RLock()
        self._dirty = False
        self._cache_paths = [Path(d).resolve() / METADATA_CACHE_FILENAME for d in music_dirs]
        self._load()

    def _load(self) -> None:
        """Load metadata cache from all music directories."""
        for cache_path in self._cache_paths:
            try:
                if cache_path.is_file():
                    with cache_path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("version") == METADATA_CACHE_VERSION:
                        self._cache.update(data.get("entries", {}))
                        log.debug(
                            "Loaded metadata cache from %s (%d entries)",
                            cache_path,
                            len(data.get("entries", {})),
                        )
            except (OSError, json.JSONDecodeError, KeyError) as ex:
                log.debug("Failed to load metadata cache from %s: %s", cache_path, ex)

    def save(self) -> None:
        """Save metadata cache to all music directories (atomic writes)."""
        if not self._dirty:
            return
        data = {"version": METADATA_CACHE_VERSION, "entries": self._cache}
        for cache_path in self._cache_paths:
            try:
                # Atomic write: temp file + replace
                temp_path = cache_path.with_suffix(".tmp")
                with temp_path.open("w", encoding="utf-8") as f:
                    json.dump(data, f, separators=(",", ":"))
                temp_path.replace(cache_path)
            except OSError as ex:
                log.debug("Failed to save metadata cache to %s: %s", cache_path, ex)
        self._dirty = False

    def get(self, path: Path, mtime: float) -> dict | None:
        """Get cached metadata if mtime matches, else None."""
        key = str(path.resolve())
        with self._lock:
            entry = self._cache.get(key)
            if entry and entry.get("mtime") == mtime:
                return entry
        return None

    def set(
        self, path: Path, mtime: float, title: str, artist: str | None, duration: float | None
    ) -> None:
        """Store metadata for a file."""
        key = str(path.resolve())
        with self._lock:
            self._cache[key] = {
                "mtime": mtime,
                "title": title,
                "artist": artist,
                "duration": duration,
            }
            self._dirty = True

    def invalidate(self, path: Path) -> None:
        """Remove a specific path from cache."""
        key = str(path.resolve())
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._dirty = True


# Global metadata cache instance (initialized by LocalIndex.scan)
_metadata_cache: MetadataCache | None = None
_metadata_cache_lock = threading.Lock()


def _get_metadata_cache(music_dirs: list[str]) -> MetadataCache:
    global _metadata_cache
    with _metadata_cache_lock:
        if _metadata_cache is None:
            _metadata_cache = MetadataCache(music_dirs)
        return _metadata_cache


def local_track(path, requester: str = "AutoDJ") -> Track:
    p = Path(path)
    title, dur = p.stem, None
    artist = None

    # Try metadata cache first
    try:
        mtime = p.stat().st_mtime
        cache = _get_metadata_cache([str(p.parent)])  # Use parent dir as cache root
        cached = cache.get(p, mtime)
        if cached:
            title = cached["title"]
            artist = cached["artist"]
            dur = cached["duration"]
            return Track(str(p), title, dur, requester)
    except OSError:
        pass

    # Fallback to mutagen extraction
    try:
        import mutagen

        f = mutagen.File(p, easy=True)
        if f is not None:
            dur = getattr(f.info, "length", None)
            t = (f.get("title") or [None])[0]
            a = (f.get("artist") or [None])[0]
            if t:
                title = f"{a} - {t}" if a else t
                artist = a
    except ImportError:
        pass  # mutagen not installed; fall back to filename
    except Exception:  # nosec B110  # any metadata error: fall back to filename, never crash the folder scan  # noqa: S110, BLE001
        pass

    # Cache the result (even if fallback to filename)
    try:
        mtime = p.stat().st_mtime
        cache = _get_metadata_cache([str(p.parent)])
        cache.set(p, mtime, title, artist, dur)
    except OSError:
        pass

    return Track(str(p), title, dur, requester)


def scan_folder(
    folder, requester: str = "AutoDJ", limit: int = 0, max_dirs: int = 0
) -> list[Track]:
    """Recursively scan *folder* for media files, skipping unreadable directories.

    Symlinks are never followed (avoids symlink cycles and slow reparse-point
    hangs on Windows). *limit* caps the total tracks returned (0 = no cap).
    *max_dirs* caps the total number of sub-directories entered across the
    entire scan (0 = no cap) so a very deep/wide folder tree cannot scan forever.
    """
    return _scan_folder_recursive(folder, requester, limit, max_dirs)


def _scan_dir_entries(
    entries: list[os.DirEntry],
    requester: str,
    limit: int,
    remaining_dirs: int,
    media_extensions: set[str],
) -> tuple[list[Track], int]:
    """Scan a list of directory entries (for parallel processing).

    Returns (tracks, dirs_consumed).
    """
    tracks: list[Track] = []
    dirs_consumed = 0

    for entry in entries:
        if limit and len(tracks) >= limit:
            break
        try:
            if entry.is_symlink():
                continue  # never follow symlinks: avoids cycles and slow reparse points
            if entry.is_dir():
                if remaining_dirs - dirs_consumed <= 0:
                    continue  # global directory budget exhausted
                dirs_consumed += 1
            elif entry.is_file():
                entry_path = Path(entry.path)
                if entry_path.suffix.lower() in media_extensions:
                    tracks.append(local_track(entry_path, requester))
        except (OSError, PermissionError):
            continue

    return tracks, dirs_consumed


def _scan_folder_recursive(  # noqa: C901
    folder: str, requester: str, limit: int, remaining_dirs: int
) -> list[Track]:
    """Internal recursive implementation with global directory budget.

    Uses ThreadPoolExecutor for parallel subdirectory scanning when
    there are multiple subdirectories to process. The budget is consumed
    sequentially to match the original semantics: each subdirectory entered
    decrements the budget, and recursive calls receive the updated budget.
    """
    root = Path(folder)
    try:
        # Use os.scandir for better performance: DirEntry has cached stat info
        entries = list(os.scandir(root))
    except (OSError, PermissionError):
        log.warning("cannot read folder %r: permission denied", folder)
        return []

    tracks: list[Track] = []
    subdirs: list[str] = []

    # First pass: collect files and subdirectories (consume budget sequentially)
    for entry in entries:
        if limit and len(tracks) >= limit:
            break
        try:
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if remaining_dirs <= 0:
                    continue  # global directory budget exhausted
                remaining_dirs -= 1
                subdirs.append(entry.path)
            elif entry.is_file():
                entry_path = Path(entry.path)
                if entry_path.suffix.lower() in MEDIA:
                    tracks.append(local_track(entry_path, requester))
        except (OSError, PermissionError):
            continue

    # Parallel scan subdirectories if there are multiple and we have budget
    # Pass the SAME remaining_dirs to all - they will consume sequentially within their own scope
    if subdirs and remaining_dirs >= 0:
        # Limit parallelism to avoid overwhelming the filesystem
        max_workers = min(4, len(subdirs))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for subdir in subdirs:
                if limit and len(tracks) >= limit:
                    break
                # Each subdir gets the current remaining_dirs (sequential budget semantics)
                futures[
                    executor.submit(
                        _scan_folder_recursive, subdir, requester, limit, remaining_dirs
                    )
                ] = subdir

            for future in as_completed(futures):
                if limit and len(tracks) >= limit:
                    break
                try:
                    sub_tracks = future.result()
                    need = limit - len(tracks) if limit else 0
                    tracks.extend(sub_tracks[:need] if need else sub_tracks)
                except Exception as ex:
                    log.debug("subdirectory scan failed: %s", ex)

    tracks.sort(key=lambda t: t.source)
    return tracks


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


# yt-dlp process pool for connection pooling
_ytdlp_pool: ThreadPoolExecutor | None = None
_ytdlp_pool_lock = threading.Lock()
_YTDLP_POOL_SIZE = 2  # Conservative: yt-dlp is CPU/memory intensive


def _get_ytdlp_pool() -> ThreadPoolExecutor:
    global _ytdlp_pool
    with _ytdlp_pool_lock:
        if _ytdlp_pool is None:
            _ytdlp_pool = ThreadPoolExecutor(
                max_workers=_YTDLP_POOL_SIZE, thread_name_prefix="ytdlp"
            )
        return _ytdlp_pool


def _shutdown_ytdlp_pool() -> None:
    global _ytdlp_pool
    with _ytdlp_pool_lock:
        if _ytdlp_pool is not None:
            _ytdlp_pool.shutdown(wait=True, cancel_futures=True)
            _ytdlp_pool = None


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
        kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW: no console flash from the GUI build
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
        raise RuntimeError("yt-dlp failed: " + (tail[-1] if tail else f"exit code {r.returncode}"))
    try:
        return json.loads(r.stdout)
    except ValueError:
        raise RuntimeError("yt-dlp returned no usable result") from None


def _extract_module(target: str, playlist: bool, limit: int, ca_bundle: str = "") -> dict:
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
                raise YtdlpMissingError(
                    "yt-dlp not found: the yt-dlp executable failed "
                    f"({exe_error}) and this build has no yt_dlp Python module. "
                    "Put yt-dlp.exe next to mpv.exe (or set ytdlp_path in config.toml), "
                    "or `pip install yt-dlp` and rebuild AutoDJ.exe."
                ) from None
            raise YtdlpMissingError(
                "yt-dlp not found: there is no yt-dlp executable (next to mpv.exe or on PATH) and this build has no "
                "yt_dlp Python module. Put yt-dlp.exe next to mpv.exe (or set ytdlp_path in config.toml), "
                "or `pip install yt-dlp` and rebuild AutoDJ.exe."
            ) from None
    return parse_ytdlp_info(info, requester)


class LocalIndex:
    def __init__(self, dirs):
        self.dirs = [Path(d).resolve() for d in dirs]
        self.tracks: list[Track] = []
        self._hay: list[str] = []  # precomputed lowercase search strings, parallel to self.tracks

    def scan(self):
        # Initialize metadata cache for these directories
        _get_metadata_cache([str(d) for d in self.dirs])
        self.tracks = [t for d in self.dirs if d.is_dir() for t in scan_folder(d)]
        self._hay = [f"{t.title} {Path(t.source).name}".lower() for t in self.tracks]
        # Save metadata cache after scan
        global _metadata_cache
        if _metadata_cache:
            _metadata_cache.save()

    def find(self, query: str, requester: str) -> Track | None:
        words = query.lower().split()
        if not words:
            return None
        hay = self._hay
        for i, t in enumerate(self.tracks):
            h = hay[i] if i < len(hay) else f"{t.title} {Path(t.source).name}".lower()
            if all(w in h for w in words):
                return Track(t.source, t.title, t.duration, requester)
        return None

    def contains(self, path) -> bool:
        p = Path(path).resolve()
        return any(p.is_relative_to(d) for d in self.dirs)
