"""Auto-update client for CamfrogAutoDJ.

Checks GitHub releases for a newer AutoDJ.exe and downloads it from
``https://github.com/cvsz/autodj/releases/latest`` only (fail-closed:
never downloads from any host other than github.com).

On Windows, ``apply_update()`` stages the new executable as
``AutoDJ.exe.next`` in the same directory as the running exe and writes
``autodj_update.bat`` which, when run, replaces the running exe with the
new one and relaunches AutoDJ.  This avoids file-lock issues with the
running PyInstaller exe.

Config keys (``config.toml``):

    auto_update_enabled = true          # enable background checks
    auto_update_repo = "cvsz/autodj"    # GitHub repo (owner/name)
    auto_update_check_interval = 21600.0 # seconds between checks (default 6h)
    auto_update_asset = "AutoDJ.exe"    # release asset filename to download
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re

# security review: subprocess only with fixed argv lists, never shell=True
import subprocess  # nosec B404
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import __version__
from .exceptions import AutoDJError

if TYPE_CHECKING:
    from .config import Config
    from .engine import Engine

log = logging.getLogger("autodj")

GITHUB_API = "https://api.github.com"
DEFAULT_REPO = "cvsz/autodj"
DEFAULT_CHECK_INTERVAL = 6 * 60 * 60  # 6 hours
UA = f"CamfrogAutoDJ/{__version__} (+https://github.com/cvsz/autodj)"


class UpdateError(AutoDJError):
    """Auto-update related failure."""


_VERSION_RE = re.compile(r"^v?(\d+(?:\.\d+)*)")


def parse_version(text: str) -> tuple[int, ...] | None:
    """Parse ``"v1.2.3"`` / ``"1.2.3-rc1"`` into ``(1, 2, 3)``; None if unparsable."""
    m = _VERSION_RE.match((text or "").strip())
    if not m:
        return None
    return tuple(int(p) for p in m.group(1).split("."))


def is_newer(latest: str, current: str) -> bool:
    """True only when *latest* is strictly newer than *current*.

    Unparsable versions are never treated as newer (fail-closed: a malformed
    or older tag must not trigger an update prompt / download).
    """
    lv, cv = parse_version(latest), parse_version(current)
    if lv is None or cv is None:
        return False
    width = max(len(lv), len(cv))
    return lv + (0,) * (width - len(lv)) > cv + (0,) * (width - len(cv))


def _bat(value: object) -> str:
    """Escape ``%`` for a .bat file: cmd expands ``%NAME%`` even inside quotes."""
    return str(value).replace("%", "%%")


def default_exe_path() -> Path:
    """Path of the running AutoDJ executable.

    In a PyInstaller build ``__file__`` points into the temporary extraction
    dir (``_MEIPASS``), so the real exe location is ``sys.executable``.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return Path(__file__).resolve().parent.parent / "AutoDJ.exe"


class Updater:
    """Background + on-demand update checker/downloader for AutoDJ.exe.

    Only GitHub releases are consulted and only github.com URLs are ever
    downloaded (fail-closed).  The new executable is staged as
    ``<exe_dir>/AutoDJ.exe.next``; applying it requires a restart (see
    :meth:`apply_update` and the generated ``autodj_update.bat``).
    """

    def __init__(self, cfg: "Config", engine: "Engine | None" = None):
        self.cfg = cfg
        self.engine = engine

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._latest: dict | None = None
        self._last_check: float = 0.0
        self._lock = threading.Lock()
        self._announced_tag: str | None = None
        # Called (from the updater thread) once per newly seen release tag.
        self.on_available: Callable[[dict], None] | None = None

    # Settings are read live from ``self.cfg`` so a config reload takes effect.
    @property
    def repo(self) -> str:
        repo = str(getattr(self.cfg, "auto_update_repo", DEFAULT_REPO) or DEFAULT_REPO)
        # owner/name only — never let config smuggle a path/query into the API URL
        return repo if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) else DEFAULT_REPO

    @property
    def enabled(self) -> bool:
        return bool(getattr(self.cfg, "auto_update_enabled", False))

    @property
    def check_interval(self) -> float:
        val = float(getattr(self.cfg, "auto_update_check_interval", DEFAULT_CHECK_INTERVAL))
        return max(300.0, val)  # never hammer the GitHub API

    @property
    def asset_name(self) -> str:
        return str(getattr(self.cfg, "auto_update_asset", "AutoDJ.exe") or "AutoDJ.exe")

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        """Start the background auto-update check loop (daemon thread)."""
        if not self.enabled:
            log.debug("auto-update disabled; updater thread not started")
            return
        if self._thread is not None and self._thread.is_alive():
            return  # already running (e.g. re-enabled by a config reload)
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="autodj-updater")
        self._thread.start()
        log.info(
            "auto-update enabled (repo=%s, interval=%.0fs)",
            self.repo,
            self.check_interval,
        )

    def stop(self) -> None:
        """Stop the background updater thread."""
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

    def _loop(self) -> None:
        while not self._stop.is_set():
            if not self.enabled:
                # Disabled by a config reload: no GitHub traffic until re-enabled.
                time.sleep(1.0)
                continue
            try:
                release = self.check_for_update()
                if release and release.get("tag") != self._announced_tag:
                    self._announced_tag = release.get("tag")
                    if self.on_available is not None:
                        self.on_available(release)
            except Exception:  # pragma: no cover - updater thread must never die
                log.exception("auto-update check loop failed")
            # Sleep in 1s increments so stop() is responsive.
            for _ in range(int(self.check_interval)):
                if self._stop.is_set():
                    break
                time.sleep(1.0)

    # ------------------------------------------------------------------ public API
    def check_for_update(self) -> dict | None:
        """Query GitHub for the latest release.

        Returns the release dict if a newer version is available, else None.
        Never raises: network/API failures are logged and return None.
        """
        url = f"{GITHUB_API}/repos/{self.repo}/releases/latest"
        try:
            data = self._fetch_json(url)
        except Exception as ex:  # noqa: BLE001 - updater must never crash
            log.warning("auto-update: cannot reach GitHub API: %s", ex)
            return None

        tag_name = data.get("tag_name", "") or ""
        latest = tag_name.lstrip("v")
        current = __import__("autodj", fromlist=["__version__"]).__version__

        with self._lock:
            self._last_check = time.monotonic()
            if not latest or not is_newer(latest, current):
                log.info(
                    "auto-update: up to date (current=%s, latest=%s)",
                    current,
                    latest,
                )
                self._latest = None
                return None

            log.info(
                "auto-update: new version available (current=%s, latest=%s)",
                current,
                latest,
            )
            self._latest = {
                "tag": latest,
                "tag_name": tag_name,
                "name": data.get("name", ""),
                "body": data.get("body", ""),
                "published_at": data.get("published_at", ""),
                "html_url": data.get("html_url", ""),
                "assets": data.get("assets", []),
            }
            return self._latest

    def latest(self) -> dict | None:
        """Return the most recently checked release info, or None."""
        with self._lock:
            return self._latest

    def find_asset(self, name_substring: str | None = None) -> dict | None:
        """Find a release asset matching *name_substring* (default: auto_update_asset)."""
        with self._lock:
            release = self._latest
        if not release:
            return None
        needle = (name_substring or self.asset_name).lower()
        assets = release.get("assets", []) or []
        # Exact name first, so "AutoDJ.exe" never resolves to "AutoDJ.exe.sha256".
        for asset in assets:
            if (asset.get("name", "") or "").lower() == needle:
                return asset
        for asset in assets:
            name = (asset.get("name", "") or "").lower()
            if needle in name and not name.endswith((".sha256", ".sig", ".asc", ".txt")):
                return asset
        return None

    @staticmethod
    def _fail_closed_url(url: str) -> bool:
        """Return True only if *url* is on github.com (fail-closed)."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            if parsed.scheme != "https":  # assets must never be fetched over plain HTTP
                return False
            host = (parsed.hostname or "").lower()
        except ValueError:
            return False
        return host == "github.com" or host.endswith(".github.com")

    def _fetch_json(self, url: str) -> dict:
        """Fetch and parse JSON from *url*.  Only github.com hosts allowed."""
        if not self._fail_closed_url(url):
            raise ValueError(f"non-GitHub URL rejected: {url}")
        req = Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})  # noqa: S310
        # security review: URL scheme/host validated just above (https/github.com only)
        with urlopen(req, timeout=30) as resp:  # noqa: S310 - url is fail-closed to github.com above  # nosec B310
            if resp.status != 200:
                raise HTTPError(url, resp.status, resp.reason, resp.headers, resp)
            return json.loads(resp.read().decode("utf-8"))

    def expected_sha256(self, asset: dict) -> str | None:
        """Return the expected SHA-256 hex digest for *asset*, or None.

        Sources, in order: the ``digest`` field GitHub's releases API returns
        for each asset (``"sha256:<hex>"``), then a sibling release asset named
        ``<asset>.sha256`` / ``SHA256SUMS`` containing the hash.
        """
        digest = (asset.get("digest") or "").strip().lower()
        if digest.startswith("sha256:") and re.fullmatch(r"[0-9a-f]{64}", digest[7:]):
            return digest[7:]
        name = asset.get("name", "") or ""
        with self._lock:
            assets = list((self._latest or {}).get("assets", []) or [])
        for cand in assets:
            cname = (cand.get("name", "") or "").lower()
            if cname not in (f"{name.lower()}.sha256", "sha256sums", "sha256sums.txt"):
                continue
            url = cand.get("browser_download_url") or ""
            if not self._fail_closed_url(url):
                continue
            try:
                req = Request(url, headers={"User-Agent": UA})  # noqa: S310
                # security review: URL scheme/host validated just above (https/github.com only)
                with urlopen(req, timeout=30) as resp:  # noqa: S310 - github.com only  # nosec B310
                    text = resp.read(1 << 16).decode("utf-8", "replace")
            except (URLError, HTTPError, OSError) as ex:
                log.warning("auto-update: cannot fetch checksum file: %s", ex)
                continue
            for line in text.splitlines():
                parts = line.strip().split()
                if not parts or not re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
                    continue
                if len(parts) == 1 or parts[-1].lstrip("*").lower() == name.lower():
                    return parts[0].lower()
        return None

    def download_asset(self, asset: dict, dest: Path) -> bool:
        """Download *asset* to *dest*.  Returns True on success.

        Fail-closed: only github.com hosts are honoured, and the file is only
        kept when its SHA-256 matches the digest published with the release.
        """
        url = asset.get("browser_download_url")
        if not url:
            log.error("auto-update: asset has no download URL")
            return False
        if not self._fail_closed_url(url):
            log.error("auto-update: refusing non-GitHub URL: %s", url)
            return False

        expected = self.expected_sha256(asset)
        if not expected:
            log.error(
                "auto-update: no SHA-256 digest published for %s; refusing unverified download",
                asset.get("name"),
            )
            return False

        tmp = dest.with_suffix(dest.suffix + ".part")
        try:
            req = Request(url, headers={"User-Agent": UA, "Accept": "application/octet-stream"})  # noqa: S310
            # security review: URL scheme/host validated just above (https/github.com only)
            with urlopen(req, timeout=60) as resp:  # noqa: S310 - url is fail-closed to github.com above  # nosec B310
                if resp.status != 200:
                    log.error("auto-update: download HTTP %s", resp.status)
                    return False
                h = hashlib.sha256()
                with open(tmp, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        h.update(chunk)
                        f.write(chunk)
            if h.hexdigest() != expected:
                log.error(
                    "auto-update: SHA-256 mismatch for %s (expected %s, got %s); discarded",
                    url,
                    expected,
                    h.hexdigest(),
                )
                tmp.unlink(missing_ok=True)
                return False
            tmp.replace(dest)
            log.info(
                "auto-update: downloaded %s -> %s (%d bytes)",
                url,
                dest,
                dest.stat().st_size,
            )
            return True
        except (URLError, HTTPError, OSError) as ex:
            log.exception("auto-update: download failed: %s", ex)
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            return False

    def launch_update_script(self, exe_path: str | Path | None = None) -> bool:
        """Run the staged ``autodj_update.bat`` to replace the installed exe.

        Uses an argv list (never ``shell=True``) and an absolute cmd.exe path.
        Returns False on a non-Windows host or when no script was staged.
        """
        if os.name != "nt":
            log.info("auto-update: swapping the exe is Windows-only")
            return False
        exe = Path(exe_path) if exe_path else default_exe_path()
        script = exe.with_name("autodj_update.bat")
        if not script.is_file():
            log.warning("auto-update: no staged update script at %s", script)
            return False
        cmd = os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe")
        try:
            # security review: fixed argv list, absolute cmd.exe path from COMSPEC
            subprocess.Popen(  # nosec B603
                [cmd, "/c", str(script)],
                cwd=str(exe.parent),
                close_fds=True,
            )
        except OSError:
            log.exception("auto-update: cannot launch %s", script)
            return False
        log.info("auto-update: launched %s", script)
        return True

    def apply_update(self, exe_path: str | Path | None = None) -> bool:
        """Download the latest AutoDJ.exe and stage it as ``AutoDJ.exe.next``.

        Also writes ``autodj_update.bat`` next to the exe which, when run,
        replaces the running executable with the staged one and relaunches.

        Returns True if the update was staged successfully.
        """
        if not self._latest:
            log.warning("auto-update: no release available to apply")
            return False
        asset = self.find_asset(self.asset_name)
        if not asset:
            log.warning("auto-update: no AutoDJ.exe asset in latest release")
            return False

        exe = Path(exe_path) if exe_path else default_exe_path()
        if not exe.is_absolute():
            exe = Path.cwd() / exe
        dest = exe.with_name(exe.stem + ".next" + exe.suffix)

        if not self.download_asset(asset, dest):
            return False

        self._write_update_script(exe, dest, self._latest.get("tag", ""))
        log.info(
            "auto-update: staged %s -> %s; run autodj_update.bat to apply and restart",
            asset.get("browser_download_url"),
            dest,
        )
        if self.engine:
            self.engine.say(
                "AutoDJ version %s downloaded. Run autodj_update.bat or restart to apply."
                % self._latest.get("tag", "")
            )
        return True

    # ------------------------------------------------------------------ helpers
    def _write_update_script(self, exe: Path, new_exe: Path, tag: str) -> None:
        """Write a batch file that swaps the running exe with the new one."""
        # The tag comes from a GitHub release name: whitelist it before it is
        # interpolated into a .bat file so `&` / `|` cannot chain commands.
        safe_tag = re.sub(r"[^A-Za-z0-9._-]", "", tag)[:64]
        old = exe.with_name(exe.stem + ".old" + exe.suffix)
        script = exe.with_name("autodj_update.bat")
        # chcp 65001: the script is written as UTF-8, and a non-ASCII install
        # path (e.g. a Thai user profile) was mangled under the OEM codepage.
        # Paths inside ( ... ) blocks are always quoted: an unquoted ")" such
        # as "Program Files (x86)" closed the block early and broke the script.
        lines = [
            "@echo off",
            "chcp 65001 >nul",
            "setlocal",
            "echo AutoDJ update: applying version %s..." % safe_tag,
            'if not exist "%s" (echo ERROR: "%s" not found & goto end)'
            % (_bat(new_exe), _bat(new_exe)),
            'taskkill /f /im "%s" >nul 2>&1' % _bat(exe.name),
            "timeout /t 2 /nobreak >nul",
            'if exist "%s" del "%s"' % (_bat(old), _bat(old)),
            'ren "%s" "%s" || (echo ERROR: cannot rename running exe & goto end)'
            % (_bat(exe), _bat(old.name)),
            'ren "%s" "%s" || (ren "%s" "%s" & echo ERROR: update failed, rolled back & goto end)'
            % (_bat(new_exe), _bat(exe.name), _bat(old), _bat(exe.name)),
            'del "%s"' % _bat(old),
            'start "" "%s"' % _bat(exe),
            ":end",
            "endlocal",
        ]
        script.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
        log.debug("auto-update: restart script written to %s", script)

    @property
    def last_check(self) -> float:
        """Monotonic time of the last check, or 0 if never checked."""
        return self._last_check

