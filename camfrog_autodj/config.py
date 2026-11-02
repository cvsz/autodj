from __future__ import annotations

import difflib
import re
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path


class ConfigError(Exception):
    """config.toml is unreadable or has a bad value. The message is written for the person editing the file."""


@dataclass
class Config:
    bot_nick: str = "AutoDJ"
    admins: list[str] = field(default_factory=list)
    prefix: str = "!"
    lang: str = "en"  # en | th (bot replies and GUI)
    chat_reader: str = "uia"
    chat_sender: str = "uia"
    window_title_re: str = ".*"  # room windows are titled "<room>: ห้องสนทนา": no "Camfrog" in it; process_re does the filtering
    process_re: str = "(?i)camfrog"  # window must belong to a process whose exe name matches ("" = any)
    window_exclude_re: str = ""  # drop matching titles when several windows match
    window_index: int = 0  # which match to use after filtering (0 = first)
    auto_discover: bool = True  # at startup (uia): find the room window + chat/input controls, save to config.toml
    view_kind: str = "auto"  # auto | web (Camfrog room: embedded web panes) | text (Document/Edit controls)
    web_view_title: str = "wb-log-room-data"  # substring of the chat-history pane title
    web_input_title: str = "wb-edit-data"  # substring of the message-box pane title
    send_mode: str = "auto"  # background (no focus steal) | foreground (focus + paste) | auto (background, verify, else foreground)
    send_verify: bool = True  # auto mode: confirm the line appeared in the room before accepting the background send
    web_strict_body: bool = True  # drop plain text that directly follows a message body (date headers / system lines)
    view_type: str = "Document"
    view_index: int = 0
    input_type: str = "Edit"
    input_index: int = -1
    log_path: str = ""
    log_encoding: str = "utf-8"
    line_regex: str = r"^(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*)?(?P<user>[^:\s][^:]{0,30}):\s(?P<text>.+)$"
    mpv_path: str = "mpv"
    audio_device: str = ""
    volume: int = 70
    music_dirs: list[str] = field(default_factory=list)
    autoplay_sources: list[str] = field(default_factory=list)
    shuffle: bool = True
    allowed_hosts: list[str] = field(
        default_factory=lambda: ["youtube.com", "youtu.be", "music.youtube.com"]
    )
    max_requests_per_user: int = 3
    max_queue: int = 50
    max_duration: int = 900
    voteskip_threshold: int = 3
    cooldown: float = 3.0
    send_interval: float = 1.5
    max_msg_len: int = 180
    announce_next: bool = True
    msg_now: str = ""  # empty = built-in text for `lang`
    msg_next: str = ""
    tts_voice: str = ""
    tts_rate: int = 170
    tts_duck: int = 25
    auto_launch: bool = False
    camfrog_exe: str = ""
    client_title_re: str = ".*"
    room: str = ""
    join_uri_template: str = (
        ""  # e.g. "<scheme>://...{room}": must match what your Camfrog build accepts
    )
    launch_timeout: int = 60
    blocked_users: list[str] = field(
        default_factory=list
    )  # nicks whose commands are ignored (admins cannot be blocked)
    ytdlp_path: str = ""  # "" = auto: yt-dlp(.exe) next to mpv or on PATH, else the bundled Python module
    poll_interval: float = (
        0.5  # seconds between chat reads (raise it if AutoDJ uses too much CPU)
    )
    log_file: str = ""  # also write the log to this file (rotating, 1 MB x 3)
    playlist_file: str = "playlist.json"  # user-requested tracks (!play / GUI request / !load) are appended here
    # (deduplicated) and join the autoplay pool (random); "" = disable persistence
    playlist_dir: str = ""  # directory of *.json playlist files auto-loaded at startup; "" = disabled
    search_limit: int = 1  # YouTube text-search results fetched per non-admin !play (1 = first match only)
    mpv_timeout: float = 30.0  # seconds to wait for one mpv track before treating it as hung (0 = no timeout)
    # Audio Engineering
    audio_fade: bool = True  # enable audio volume fade-in and fade-out
    audio_fade_in_sec: float = 1.2  # fade-in duration in seconds
    audio_fade_out_sec: float = 1.5  # fade-out duration on skip/stop in seconds
    audio_normalize: bool = False  # enable dynamic audio loudness normalization (dynaudnorm)
    # YouTube Authentication
    youtube_cookies_file: str = ""  # path to Netscape cookies.txt for yt-dlp
    youtube_cookies_browser: str = ""  # browser name for --cookies-from-browser (e.g. chrome, edge, firefox)
    # Dynamic Moderation
    voteskip_dynamic: bool = False  # dynamic voteskip threshold based on participant count
    voteskip_dynamic_pct: int = 30  # percentage of participants required to skip
    user_request_limit: int = 5  # max song requests allowed per user within rate_limit_window
    rate_limit_window: float = 300.0  # rolling time window for per-user request limit (seconds)

    @classmethod
    def load(cls, path: str | None) -> Config:
        p = Path(path) if path else None
        data: dict = {}
        if p and p.exists():
            try:
                text = p.read_text(
                    "utf-8-sig"
                )  # utf-8-sig: tolerate the BOM that Windows Notepad can add
            except UnicodeDecodeError as ex:
                raise ConfigError(
                    f"{p}: not valid UTF-8 ({ex.reason}). Save the file as UTF-8."
                ) from None
            try:
                data = tomllib.loads(text)
            except tomllib.TOMLDecodeError as ex:
                raise ConfigError(_syntax_message(p, text, ex)) from None
        names = {f.name for f in fields(cls)}
        bad = sorted(set(data) - names)
        if bad:
            lines = []
            for k in bad:
                near = difflib.get_close_matches(k, names, n=1)
                lines.append(
                    f"  {k}" + (f"   (did you mean '{near[0]}'?)" if near else "")
                )
            raise ConfigError(
                f"{p or 'config'}: unknown setting(s):\n" + "\n".join(lines)
            )
        cfg = cls(**data)
        _validate(cfg, data, str(p) if p else "config")
        return cfg


# ---- validation -------------------------------------------------------------------------------

_CHOICES = {
    "lang": ("en", "th"),
    "chat_reader": ("uia", "logtail", "console"),
    "chat_sender": ("uia", "logtail", "console"),
    "view_kind": ("auto", "web", "text"),
    "send_mode": ("auto", "background", "foreground"),
}
_REGEXES = (
    "window_title_re",
    "process_re",
    "window_exclude_re",
    "line_regex",
    "client_title_re",
)
_RANGES = {
    "volume": (0, 100),
    "max_requests_per_user": (1, 1000),
    "max_queue": (1, 100000),
    "max_duration": (1, 86400 * 7),
    "voteskip_threshold": (1, 1000),
    "cooldown": (0, 3600),
    "send_interval": (0, 3600),
    "max_msg_len": (20, 2000),
    "poll_interval": (0.05, 60),
    "tts_duck": (0, 100),
    "search_limit": (1, 50),
    "mpv_timeout": (0, 3600),
    "audio_fade_in_sec": (0.1, 10.0),
    "audio_fade_out_sec": (0.1, 10.0),
    "voteskip_dynamic_pct": (1, 100),
    "user_request_limit": (1, 1000),
    "rate_limit_window": (10.0, 86400.0),
}


def _syntax_message(p: Path, text: str, ex: Exception) -> str:
    m = re.search(r"line (\d+), column (\d+)", str(ex))
    msg = re.sub(r"\s*\(at line.*\)$", "", str(ex))
    out = [f"{p}: TOML syntax error: {msg}"]
    if m:
        ln, col = int(m[1]), int(m[2])
        lines = text.splitlines()
        if 1 <= ln <= len(lines):
            out += [
                f"  line {ln}: {lines[ln - 1]}",
                "  " + " " * (len(f"line {ln}: ") + max(col - 1, 0)) + "^",
            ]
            if "=" not in lines[ln - 1]:
                out.append(
                    "  This line has no '='. If it is a note or something pasted by accident, "
                    "delete it or put '#' in front of it."
                )
    out.append(
        "Fix that line, or copy config.example.toml over config.toml to start again."
    )
    return "\n".join(out)


def _type_name(v) -> str:
    return {
        str: "text",
        int: "a whole number",
        float: "a number",
        bool: "true/false",
        list: "a list",
    }.get(type(v), type(v).__name__)


def _validate(cfg: Config, data: dict, where: str) -> None:
    defaults = Config()
    for f in fields(Config):
        if f.name not in data:
            continue
        v, want = data[f.name], type(getattr(defaults, f.name))
        ok = (
            isinstance(v, bool)
            if want is bool
            else isinstance(v, (int, float)) and not isinstance(v, bool)
            if want is float
            else isinstance(v, int) and not isinstance(v, bool)
            if want is int
            else isinstance(v, want)
        )
        if not ok:
            hint = ' (a list looks like ["nick1", "nick2"])' if want is list else ""
            raise ConfigError(
                f"{where}: '{f.name}' must be {_type_name(getattr(defaults, f.name))}, "
                f"got {v!r}{hint}"
            )
        if want is list and not all(isinstance(x, str) for x in v):
            raise ConfigError(
                f"{where}: every item of '{f.name}' must be text, got {v!r}"
            )
    for k, allowed in _CHOICES.items():
        if getattr(cfg, k) not in allowed:
            raise ConfigError(
                f"{where}: '{k}' must be one of {', '.join(allowed)}; got {getattr(cfg, k)!r}"
            )
    for k, (lo, hi) in _RANGES.items():
        v = getattr(cfg, k)
        if not lo <= v <= hi:
            raise ConfigError(f"{where}: '{k}' must be between {lo} and {hi}; got {v}")
    for k in _REGEXES:
        try:
            re.compile(getattr(cfg, k))
        except re.error as ex:
            raise ConfigError(
                f"{where}: '{k}' is not a valid regular expression ({ex}). "
                "Tip: write regexes in 'single quotes' so backslashes stay as they are."
            ) from None
    if not cfg.prefix.strip():
        raise ConfigError(f"{where}: 'prefix' must not be empty (e.g. prefix = \"!\")")
    cfg.prefix = cfg.prefix.strip()
    cfg.admins = [a.strip() for a in cfg.admins if a.strip()]
    cfg.blocked_users = [a.strip() for a in cfg.blocked_users if a.strip()]
