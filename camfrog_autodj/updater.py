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

import json
import logging
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .exceptions import AutoDJError

if TYPE_CHECKING:
    from .config import Config
    from .engine import Engine

log = logging.getLogger("autodj")

GITHUB_API = "https://api.github.com"
DEFAULT_REPO = "cvsz/autodj"
DEFAULT_CHECK_INTERVAL = 6 * 60 * 60  # 6 hours
UA = "CamfrogAutoDJ/0.3.0 (+https://github.com/cvsz/autodj)"


class UpdateError(AutoDJError):
    """Auto-update related failure."""


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
        self.repo: str = getattr(cfg, "auto_update_repo", DEFAULT_REPO)
        self.enabled: bool = getattr(cfg, "auto_update_enabled", False)
        self.check_interval: float = float(
            getattr(cfg, "auto_update_check_interval", DEFAULT_CHECK_INTERVAL)
        )
        self.asset_name: str = getattr(cfg, "auto_update_asset", "AutoDJ.exe")

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._latest: dict | None = None
        self._last_check: float = 0.0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        """Start the background auto-update check loop (daemon thread)."""
        if not self.enabled:
            log.debug("auto-update disabled; updater thread not started")
            return
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
            try:
                self.check_for_update()
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
        current = __import__("camfrog_autodj", fromlist=["__version__"]).__version__

        with self._lock:
            self._last_check = time.monotonic()
            if not latest or latest == current:
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
        for asset in release.get("assets", []) or []:
            if needle in (asset.get("name", "") or "").lower():
                return asset
        return None

    @staticmethod
    def _fail_closed_url(url: str) -> bool:
        """Return True only if *url* is on github.com (fail-closed)."""
        try:
            from urllib.parse import urlparse

            host = (urlparse(url).hostname or "").lower()
        except ValueError:
            return False
        return host == "github.com" or host.endswith(".github.com")

    def _fetch_json(self, url: str) -> dict:
        """Fetch and parse JSON from *url*.  Only github.com hosts allowed."""
        if not self._fail_closed_url(url):
            raise ValueError(f"non-GitHub URL rejected: {url}")
        req = Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})  # noqa: S310
        with urlopen(req, timeout=30) as resp:  # noqa: S310 - url is fail-closed to github.com above
            if resp.status != 200:
                raise HTTPError(url, resp.status, resp.reason, resp.headers, resp)
            return json.loads(resp.read().decode("utf-8"))

    def download_asset(self, asset: dict, dest: Path) -> bool:
        """Download *asset* to *dest*.  Returns True on success.

        Fail-closed: only github.com hosts are honoured.
        """
        url = asset.get("browser_download_url")
        if not url:
            log.error("auto-update: asset has no download URL")
            return False
        if not self._fail_closed_url(url):
            log.error("auto-update: refusing non-GitHub URL: %s", url)
            return False

        try:
            req = Request(url, headers={"User-Agent": UA, "Accept": "application/octet-stream"})  # noqa: S310
            with urlopen(req, timeout=60) as resp:  # noqa: S310 - url is fail-closed to github.com above
                if resp.status != 200:
                    log.error("auto-update: download HTTP %s", resp.status)
                    return False
                tmp = dest.with_suffix(dest.suffix + ".part")
                with open(tmp, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
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
            return False

    def apply_update(self, exe_path: str | Path | None = None) -> bool:
        """Download the latest AutoDJ.exe and stage it as ``AutoDJ.exe.next``.

        Also writes ``autodj_update.bat`` next to the exe which, when run,
        replaces the running executable with the staged one and relaunches.

        Returns True if the update was staged successfully.
        """
        if not self._latest:
            log.warning("auto-update: no release available to apply")
            return False
        asset = self.find_asset("AutoDJ.exe")
        if not asset:
            log.warning("auto-update: no AutoDJ.exe asset in latest release")
            return False

        exe = Path(exe_path) if exe_path else Path(__file__).resolve().parent.parent / "AutoDJ.exe"
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
        old = exe.with_name(exe.stem + ".old" + exe.suffix)
        script = exe.with_name("autodj_update.bat")
        lines = [
            "@echo off",
            "setlocal",
            "echo AutoDJ update: applying version %s..." % tag,
            'if not exist "%s" (echo ERROR: %s not found & goto end)' % (new_exe, new_exe),
            'taskkill /f /im "%s" >nul 2>&1' % exe.name,
            "timeout /t 2 /nobreak >nul",
            'if exist "%s" del "%s"' % (old, old),
            'ren "%s" "%s"' % (exe, old.name),
            'ren "%s" "%s"' % (new_exe, exe.name),
            'del "%s"' % old,
            'start "" "%s"' % exe,
            ":end",
            "endlocal",
        ]
        script.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
        log.debug("auto-update: restart script written to %s", script)

    @property
    def last_check(self) -> float:
        """Monotonic time of the last check, or 0 if never checked."""
        return self._last_check
