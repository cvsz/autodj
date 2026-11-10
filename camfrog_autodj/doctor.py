"""`AutoDJ.exe --check`: say in plain words what is and is not set up, before anything is started.
Pure checks over a Config (and the machine): each returns (level, text) with level OK | INFO | WARN | FAIL."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

from .library import MEDIA, find_ytdlp
from .paths import resolve_executable

Result = tuple[str, str]
JS_RUNTIMES = ("deno", "node", "bun")


def _have(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def has_failures(results: list[Result]) -> bool:
    return any(level == "FAIL" for level, _ in results)


def format_report(results: list[Result]) -> str:
    return "\n".join(f"[{level:^4}] {text}" for level, text in results)


def _ytdlp_version(exe: str) -> str:
    try:
        kw: dict = {"capture_output": True, "text": True, "timeout": 15}
        if os.name == "nt":
            kw["creationflags"] = 0x08000000
        r = subprocess.run([exe, "--version"], check=False, **kw)
        return (
            (r.stdout or "").strip().splitlines()[0]
            if r.returncode == 0 and r.stdout.strip()
            else ""
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return ""


def run_checks(cfg, check_window: bool = True) -> list[Result]:
    out: list[Result] = []
    _check_mpv(cfg, out)
    _check_yt_dlp(cfg, out)
    _check_js_runtime(out)
    _check_music_dirs(cfg, out)
    _check_admin_bot_nick_audio(cfg, out)
    _check_optional_python(out)
    if os.name == "nt" and (cfg.chat_reader == "uia" or cfg.chat_sender == "uia"):
        _check_windows_uia(cfg, out, check_window)
    return out


def _add(out: list[Result], level: str, text: str) -> None:
    out.append((level, text))


def _check_mpv(cfg, out: list[Result]) -> None:
    mpv_executable = resolve_executable(cfg.mpv_path)
    if mpv_executable:
        _add(out, "OK", f"mpv: {mpv_executable}")
    else:
        _add(
            out,
            "FAIL",
            f"mpv not found at mpv_path = {cfg.mpv_path!r}. Install mpv and set the full path, "
            f'e.g. mpv_path = "C:/mpv/mpv.exe"; nothing can play without it.',
        )


def _check_yt_dlp(cfg, out: list[Result]) -> None:
    exe = find_ytdlp(cfg.ytdlp_path, cfg.mpv_path)
    module = _have("yt_dlp")
    if exe:
        v = _ytdlp_version(exe)
        _add(out, "OK", f"yt-dlp: {exe}" + (f" (version {v})" if v else ""))
    else:
        _add(
            out,
            "WARN",
            "no yt-dlp executable (next to mpv.exe, on PATH, or ytdlp_path): mpv cannot play YouTube links "
            "without it (local files still work). Download yt-dlp.exe into mpv's folder.",
        )
    if module:
        _add(
            out,
            "OK" if not exe else "INFO",
            "yt_dlp Python module is available for title lookups",
        )
    elif not exe:
        _add(
            out,
            "WARN",
            "no yt_dlp Python module either: YouTube links and song-name requests will be refused. "
            "Install yt-dlp.exe (above) or `pip install yt-dlp` and rebuild AutoDJ.exe.",
        )


def _check_js_runtime(out: list[Result]) -> None:
    if not any(shutil.which(r) for r in JS_RUNTIMES):
        _add(
            out,
            "INFO",
            "no JavaScript runtime (deno/node/bun) on PATH. Recent yt-dlp versions may need one for YouTube; "
            "if lookups fail with a 'JavaScript runtime' message, install deno.",
        )


def _count_media_files(folder: Path) -> int:
    """Count media files in *folder* without following symlinks (avoids cycles and reparse hangs)."""
    count = 0
    try:
        for entry in folder.iterdir():
            try:
                if entry.is_symlink():
                    continue  # never follow symlinks
                if entry.is_dir():
                    count += _count_media_files(entry)
                elif entry.is_file() and entry.suffix.lower() in MEDIA:
                    count += 1
            except (OSError, PermissionError):
                continue
    except (OSError, PermissionError):
        pass
    return count


def _check_music_dirs(cfg, out: list[Result]) -> None:
    for d in cfg.music_dirs:
        p = Path(d)
        if p.is_dir():
            n = _count_media_files(p)
            _add(out, "OK", f"music_dirs: {d}: {n} media file(s)")
        else:
            _add(out, "WARN", f"music_dirs: folder not found: {d}")
    if not cfg.music_dirs and not cfg.autoplay_sources:
        _add(
            out,
            "INFO",
            "music_dirs and autoplay_sources are empty: nothing plays until someone requests a song",
        )


def _check_admin_bot_nick_audio(cfg, out: list[Result]) -> None:
    if not cfg.admins:
        _add(
            out,
            "WARN",
            'admins is empty: nobody can use admin commands from the room. Add admins = ["yournick"].',
        )
    else:
        _add(out, "OK", "admins: " + ", ".join(cfg.admins))
    if cfg.bot_nick == "AutoDJ":
        _add(
            out,
            "INFO",
            "bot_nick is the default 'AutoDJ'. Lines the bot posts are recognised by their text anyway, "
            "but set bot_nick to the nickname it chats as so the GUI log labels them correctly.",
        )
    if not cfg.audio_device:
        _add(
            out,
            "INFO",
            "audio_device is empty: music goes to the Windows default output. To feed the Camfrog mic, "
            "set it to your virtual cable (list with: mpv --audio-device=help).",
        )


def _check_optional_python(out: list[Result]) -> None:
    if not _have("mutagen"):
        _add(
            out,
            "WARN",
            "mutagen is not installed: titles/durations of local files come from file names only",
        )
    if not _have("pyttsx3"):
        _add(out, "WARN", "pyttsx3 is not installed: the speak / TTS feature will not work")


def _check_windows_uia(cfg, out: list[Result], check_window: bool) -> None:
    for mod in ("pywinauto", "pyperclip"):
        if not _have(mod):
            _add(
                out,
                "FAIL",
                f"{mod} is not installed: chat_reader/chat_sender = 'uia' needs it",
            )
    if check_window:
        try:
            from .windows import resolve

            c = resolve(
                cfg.window_title_re,
                cfg.window_exclude_re,
                cfg.room,
                cfg.window_index,
                0,
                cfg.process_re,
            )
            if c:
                _add(out, "OK", f"Camfrog room window found: {c.title!r}")
            else:
                _add(
                    out,
                    "WARN",
                    f"no visible window matches window_title_re = {cfg.window_title_re!r} "
                    "(open the room window, or run AutoDJ.exe --windows to see what is open)",
                )
        except (OSError, RuntimeError) as ex:
            _add(out, "WARN", f"could not look for the Camfrog window: {ex}")
