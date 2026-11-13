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


class _DirBudget:
    """Thread-safe directory budget counter for parallel folder scanning.

    Ensures the global max_dirs limit is respected across all concurrent
    recursive scans by using an atomic counter with a lock.
    """

    __slots__ = ("_lock", "_remaining")

    def __init__(self, max_dirs: int):
        self._lock = threading.Lock()
        self._remaining = max_dirs if max_dirs > 0 else -1  # -1 = unlimited

    def consume(self, n: int = 1) -> bool:
        """Try to consume *n* directory slots. Returns True if granted."""
        with self._lock:
            if self._remaining < 0:
                return True  # unlimited
            if self._remaining >= n:
                self._remaining -= n
                return True
            return False

    @property
    def remaining(self) -> int:
        with self._lock:
            return self._remaining


log = logging.getLogger("autodj")

AUDIO = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".opus", ".aac"}
VIDEO = {".mp4", ".mkv", ".webm", ".avi", ".mov"}
MEDIA = AUDIO | VIDEO
SEARCH_PREFIX = re.compile(r"^ytsearch\d*:", re.IGNORECASE)

# Metadata cache version for forward compatibility
METADATA_CACHE_VERSION = 2  # Bumped for consolidated cache format
METADATA_CACHE_FILENAME = ".autodj_metadata_cache.json"
SCAN_STATE_FILENAME = ".autodj_scan_state.json"


class MetadataCache:
    """Thread-safe metadata cache with mtime-based invalidation.

    Stores mutagen-extracted metadata (title, artist, duration) keyed by file path.
    Invalidates entries when file mtime changes or cache version mismatches.
    Uses a single consolidated cache file for all music directories.
    """

    def __init__(self, music_dirs: list[str]):
        self._cache: dict[str, dict] = {}
        self._lock = threading.RLock()
        self._dirty = False
        # Single consolidated cache file in the first music directory, or temp
        base_dir = Path(music_dirs[0]).resolve() if music_dirs else Path.cwd()
        self._cache_path = base_dir / METADATA_CACHE_FILENAME
        self._load()

    def _load(self) -> None:
        """Load metadata cache from consolidated file."""
        try:
            if self._cache_path.is_file():
                with self._cache_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("version") == METADATA_CACHE_VERSION:
                    self._cache = data.get("entries", {})
                    log.debug(
                        "Loaded metadata cache from %s (%d entries)",
                        self._cache_path,
                        len(self._cache),
                    )
                else:
                    log.debug("Cache version mismatch, starting fresh")
        except (OSError, json.JSONDecodeError, KeyError) as ex:
            log.debug("Failed to load metadata cache from %s: %s", self._cache_path, ex)

    def save(self) -> None:
        """Save metadata cache to consolidated file (atomic write)."""
        if not self._dirty:
            return
        data = {"version": METADATA_CACHE_VERSION, "entries": self._cache}
        try:
            # Atomic write: temp file + replace
            temp_path = self._cache_path.with_suffix(".tmp")
            with temp_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, separators=(",", ":"))
            temp_path.replace(self._cache_path)
            self._dirty = False
            log.debug("Saved metadata cache (%d entries)", len(self._cache))
        except OSError as ex:
            log.debug("Failed to save metadata cache to %s: %s", self._cache_path, ex)

    def get(self, path: Path, mtime: float) -> dict | None:
        """Get cached metadata if mtime matches, else None."""
        key = str(path.resolve())
        with self._lock:
            entry = self._cache.get(key)
            if entry and entry.get("mtime") == mtime:
                return entry
        return None

    def set(
        self,
        path: Path,
        mtime: float,
        title: str,
        artist: str | None,
        duration: float | None,
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

    def get_all_mtimes(self) -> dict[str, float]:
        """Return a copy of all tracked file mtimes for incremental scan comparison."""
        with self._lock:
            return {k: v.get("mtime", 0.0) for k, v in self._cache.items()}


class ScanState:
    """Tracks file mtimes and directory structure for incremental scanning."""

    def __init__(self, music_dirs: list[str]):
        self._music_dirs = [Path(d).resolve() for d in music_dirs]
        base_dir = self._music_dirs[0] if self._music_dirs else Path.cwd()
        self._state_path = base_dir / SCAN_STATE_FILENAME
        self._file_mtimes: dict[str, float] = {}
        self._dir_mtimes: dict[str, float] = {}
        self._load()

    def _load(self) -> None:
        """Load scan state from file."""
        try:
            if self._state_path.is_file():
                with self._state_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("version") == 1:
                    self._file_mtimes = data.get("file_mtimes", {})
                    self._dir_mtimes = data.get("dir_mtimes", {})
                    log.debug(
                        "Loaded scan state from %s (%d files, %d dirs)",
                        self._state_path,
                        len(self._file_mtimes),
                        len(self._dir_mtimes),
                    )
        except (OSError, json.JSONDecodeError, KeyError) as ex:
            log.debug("Failed to load scan state from %s: %s", self._state_path, ex)

    def save(self) -> None:
        """Save scan state to file (atomic write)."""
        data = {
            "version": 1,
            "file_mtimes": self._file_mtimes,
            "dir_mtimes": self._dir_mtimes,
        }
        try:
            temp_path = self._state_path.with_suffix(".tmp")
            with temp_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, separators=(",", ":"))
            temp_path.replace(self._state_path)
            log.debug(
                "Saved scan state (%d files, %d dirs)",
                len(self._file_mtimes),
                len(self._dir_mtimes),
            )
        except OSError as ex:
            log.debug("Failed to save scan state to %s: %s", self._state_path, ex)

    def get_file_mtime(self, path: Path) -> float | None:
        """Get stored mtime for a file."""
        return self._file_mtimes.get(str(path.resolve()))

    def set_file_mtime(self, path: Path, mtime: float) -> None:
        """Update stored mtime for a file."""
        self._file_mtimes[str(path.resolve())] = mtime

    def remove_file(self, path: Path) -> None:
        """Remove a file from tracking."""
        self._file_mtimes.pop(str(path.resolve()), None)

    def get_dir_mtime(self, path: Path) -> float | None:
        """Get stored mtime for a directory."""
        return self._dir_mtimes.get(str(path.resolve()))

    def set_dir_mtime(self, path: Path, mtime: float) -> None:
        """Update stored mtime for a directory."""
        self._dir_mtimes[str(path.resolve())] = mtime

    def get_all_file_mtimes(self) -> dict[str, float]:
        """Return all tracked file mtimes."""
        return self._file_mtimes.copy()


# Global metadata cache instance (initialized by LocalIndex.scan)
_metadata_cache: MetadataCache | None = None
_metadata_cache_lock = threading.Lock()

# Global scan state instance
_scan_state: ScanState | None = None
_scan_state_lock = threading.Lock()


def _get_metadata_cache(music_dirs: list[str]) -> MetadataCache:
    global _metadata_cache
    with _metadata_cache_lock:
        if _metadata_cache is None:
            _metadata_cache = MetadataCache(music_dirs)
        return _metadata_cache


def _get_scan_state(music_dirs: list[str]) -> ScanState:
    global _scan_state
    with _scan_state_lock:
        if _scan_state is None:
            _scan_state = ScanState(music_dirs)
        return _scan_state


def shutdown_library_caches() -> None:
    """Shut down global library caches, saving state before exit."""
    global _metadata_cache, _scan_state
    with _metadata_cache_lock:
        if _metadata_cache is not None:
            _metadata_cache.save()
            _metadata_cache = None
    with _scan_state_lock:
        if _scan_state is not None:
            _scan_state.save()
            _scan_state = None


def is_url(s: str) -> bool:
    return s.lower().startswith(("http://", "https://"))


def host_ok(url: str, allowed: list[str]) -> bool:
    h = (urlparse(url).hostname or "").lower()
    return any(h == a or h.endswith("." + a) for a in allowed)


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
    folder,
    requester: str = "AutoDJ",
    limit: int = 0,
    max_dirs: int = 0,
    incremental: bool = True,
) -> list[Track]:
    """Recursively scan *folder* for media files, skipping unreadable directories.

    Symlinks are never followed (avoids symlink cycles and slow reparse-point
    hangs on Windows). *limit* caps the total tracks returned (0 = no cap).
    *max_dirs* caps the total number of sub-directories entered across the
    entire scan (0 = no cap) so a very deep/wide folder tree cannot scan forever.
    *incremental*: if True, only re-scan files whose mtime has changed.
    """
    budget = _DirBudget(max_dirs)
    return _scan_folder_recursive(folder, requester, limit, budget, incremental)


def _process_file_entry(
    entry: os.DirEntry,
    requester: str,
    media_extensions: set[str],
    scan_state: ScanState | None,
    incremental: bool,
) -> Track | None:
    """Process a single file entry, returning a Track or None."""
    entry_path = Path(entry.path)
    if entry_path.suffix.lower() not in media_extensions:
        return None
    # Check incremental scan state
    if incremental and scan_state:
        try:
            current_mtime = entry.stat().st_mtime
        except OSError:
            return None
        stored_mtime = scan_state.get_file_mtime(entry_path)
        if stored_mtime is not None and stored_mtime == current_mtime:
            # File unchanged, try to get from metadata cache
            cache = _get_metadata_cache([str(entry_path.parent)])
            cached = cache.get(entry_path, current_mtime)
            if cached:
                scan_state.set_file_mtime(entry_path, current_mtime)
                return Track(str(entry_path), cached["title"], cached["duration"], requester)
    # File changed or no cache: extract metadata
    track = local_track(entry_path, requester)
    if scan_state:
        try:
            scan_state.set_file_mtime(entry_path, entry.stat().st_mtime)
        except OSError:
            pass
    return track


def _process_dir_entry(
    entry: os.DirEntry,
    remaining_dirs: int,
    dirs_consumed: int,
) -> tuple[int, bool]:
    """Process a single directory entry, returning (new_dirs_consumed, should_continue)."""
    if remaining_dirs - dirs_consumed <= 0:
        return dirs_consumed, False  # global directory budget exhausted
    return dirs_consumed + 1, True


def _scan_dir_entries(
    entries: list[os.DirEntry],
    requester: str,
    limit: int,
    remaining_dirs: int,
    media_extensions: set[str],
    scan_state: ScanState | None,
    incremental: bool,
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
                dirs_consumed, should_continue = _process_dir_entry(
                    entry, remaining_dirs, dirs_consumed
                )
                if not should_continue:
                    continue
            elif entry.is_file():
                track = _process_file_entry(
                    entry, requester, media_extensions, scan_state, incremental
                )
                if track:
                    tracks.append(track)
        except (OSError, PermissionError):
            continue

    return tracks, dirs_consumed


def _scan_folder_recursive(  # noqa: C901
    folder: str,
    requester: str,
    limit: int,
    budget: _DirBudget,
    incremental: bool = True,
) -> list[Track]:
    """Internal recursive implementation with global directory budget.

    Uses ThreadPoolExecutor for parallel subdirectory scanning when
    there are multiple subdirectories to process. The budget is consumed
    atomically across all concurrent scans via _DirBudget.
    """
    root = Path(folder)
    scan_state = _get_scan_state([str(root)]) if incremental else None

    try:
        # Use os.scandir for better performance: DirEntry has cached stat info
        entries = list(os.scandir(root))
    except (OSError, PermissionError):
        log.warning("cannot read folder %r: permission denied", folder)
        return []

    tracks: list[Track] = []
    subdirs: list[str] = []

    # Update directory mtime
    if scan_state:
        try:
            scan_state.set_dir_mtime(root, root.stat().st_mtime)
        except OSError:
            pass

    # First pass: collect files and subdirectories (consume budget atomically)
    for entry in entries:
        if limit and len(tracks) >= limit:
            break
        try:
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if not budget.consume(1):
                    continue  # global directory budget exhausted
                subdirs.append(entry.path)
            elif entry.is_file():
                entry_path = Path(entry.path)
                if entry_path.suffix.lower() in MEDIA:
                    # Check incremental scan state
                    if incremental and scan_state:
                        current_mtime = entry.stat().st_mtime
                        stored_mtime = scan_state.get_file_mtime(entry_path)
                        if stored_mtime is not None and stored_mtime == current_mtime:
                            # File unchanged, try to get from metadata cache
                            cache = _get_metadata_cache([str(entry_path.parent)])
                            cached = cache.get(entry_path, current_mtime)
                            if cached:
                                tracks.append(
                                    Track(
                                        str(entry_path),
                                        cached["title"],
                                        cached["duration"],
                                        requester,
                                    )
                                )
                                scan_state.set_file_mtime(entry_path, current_mtime)
                                continue
                    # File changed or no cache: extract metadata
                    tracks.append(local_track(entry_path, requester))
                    if scan_state:
                        scan_state.set_file_mtime(entry_path, entry.stat().st_mtime)
        except (OSError, PermissionError):
            continue

    # Parallel scan subdirectories if there are multiple and we have budget
    # All recursive calls share the same budget object for atomic consumption.
    # We scan all collected subdirs because we already consumed budget for them.
    if subdirs:
        # Limit parallelism to avoid overwhelming the filesystem
        max_workers = min(4, len(subdirs))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for subdir in subdirs:
                if limit and len(tracks) >= limit:
                    break
                # Pass the SAME budget object to all - atomic consumption ensures global limit
                futures[
                    executor.submit(
                        _scan_folder_recursive,
                        subdir,
                        requester,
                        limit,
                        budget,
                        incremental,
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

    def scan(self, incremental: bool = True):
        # Initialize metadata cache for these directories
        _get_metadata_cache([str(d) for d in self.dirs])
        _get_scan_state([str(d) for d in self.dirs])
        self.tracks = [
            t for d in self.dirs if d.is_dir() for t in scan_folder(d, incremental=incremental)
        ]
        self._hay = [f"{t.title} {Path(t.source).name}".lower() for t in self.tracks]
        # Save metadata cache and scan state after scan
        global _metadata_cache, _scan_state
        if _metadata_cache:
            _metadata_cache.save()
        if _scan_state:
            _scan_state.save()

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
