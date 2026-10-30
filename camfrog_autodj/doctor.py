"""`AutoDJ.exe --check`: say in plain words what is and is not set up, before anything is started.
Pure checks over a Config (and the machine): each returns (level, text) with level OK | INFO | WARN | FAIL."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

from .library import MEDIA, find_ytdlp

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
        r = subprocess.run([exe, "--version"], **kw)
        return (
            (r.stdout or "").strip().splitlines()[0]
            if r.returncode == 0 and r.stdout.strip()
            else ""
        )
    except Exception:
        return ""


def run_checks(cfg, check_window: bool = True) -> list[Result]:
    out: list[Result] = []
    add = lambda level, text: out.append((level, text))

    # mpv: the player itself
    if shutil.which(cfg.mpv_path) or Path(cfg.mpv_path).is_file():
        add("OK", f"mpv: {cfg.mpv_path}")
    else:
        add(
            "FAIL",
            f"mpv not found at mpv_path = {cfg.mpv_path!r}. Install mpv and set the full path, "
            f'e.g. mpv_path = "C:/mpv/mpv.exe"; nothing can play without it.',
        )

    # yt-dlp: needed by mpv to play YouTube, and by AutoDJ to look up titles/durations
    exe = find_ytdlp(cfg.ytdlp_path, cfg.mpv_path)
    module = _have("yt_dlp")
    if exe:
        v = _ytdlp_version(exe)
        add("OK", f"yt-dlp: {exe}" + (f" (version {v})" if v else ""))
    else:
        add(
            "WARN",
            "no yt-dlp executable (next to mpv.exe, on PATH, or ytdlp_path): mpv cannot play YouTube links "
            "without it (local files still work). Download yt-dlp.exe into mpv's folder.",
        )
    if module:
        add(
            "OK" if not exe else "INFO",
            "yt_dlp Python module is available for title lookups",
        )
    elif not exe:
        add(
            "WARN",
            "no yt_dlp Python module either: YouTube links and song-name requests will be refused. "
            "Install yt-dlp.exe (above) or `pip install yt-dlp` and rebuild AutoDJ.exe.",
        )
    if (exe or module) and not any(shutil.which(r) for r in JS_RUNTIMES):
        add(
            "INFO",
            "no JavaScript runtime (deno/node/bun) on PATH. Recent yt-dlp versions may need one for YouTube; "
            "if lookups fail with a 'JavaScript runtime' message, install deno.",
        )

    # library
    for d in cfg.music_dirs:
        p = Path(d)
        if p.is_dir():
            n = sum(
                1 for f in p.rglob("*") if f.suffix.lower() in MEDIA and f.is_file()
            )
            add("OK", f"music_dirs: {d}: {n} media file(s)")
        else:
            add("WARN", f"music_dirs: folder not found: {d}")
    if not cfg.music_dirs and not cfg.autoplay_sources:
        add(
            "INFO",
            "music_dirs and autoplay_sources are empty: nothing plays until someone requests a song",
        )

    # who may command the bot
    if not cfg.admins:
        add(
            "WARN",
            'admins is empty: nobody can use admin commands from the room. Add admins = ["yournick"].',
        )
    else:
        add("OK", "admins: " + ", ".join(cfg.admins))
    if cfg.bot_nick == "AutoDJ":
        add(
            "INFO",
            "bot_nick is the default 'AutoDJ'. Lines the bot posts are recognised by their text anyway, "
            "but set bot_nick to the nickname it chats as so the GUI log labels them correctly.",
        )
    if not cfg.audio_device:
        add(
            "INFO",
            "audio_device is empty: music goes to the Windows default output. To feed the Camfrog mic, "
            "set it to your virtual cable (list with: mpv --audio-device=help).",
        )

    # optional Python pieces
    if not _have("mutagen"):
        add(
            "WARN",
            "mutagen is not installed: titles/durations of local files come from file names only",
        )
    if not _have("pyttsx3"):
        add("WARN", "pyttsx3 is not installed: the speak / TTS feature will not work")
    if os.name == "nt" and "uia" in (cfg.chat_reader, cfg.chat_sender):
        for mod in ("pywinauto", "pyperclip"):
            if not _have(mod):
                add(
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
                    add("OK", f"Camfrog room window found: {c.title!r}")
                else:
                    add(
                        "WARN",
                        f"no visible window matches window_title_re = {cfg.window_title_re!r} "
                        "(open the room window, or run AutoDJ.exe --windows to see what is open)",
                    )
            except Exception as ex:
                add("WARN", f"could not look for the Camfrog window: {ex}")
    return out
