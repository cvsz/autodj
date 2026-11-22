"""Configuration loading, validation, and defaults for AutoDJ.

The :class:`Config` dataclass holds all runtime settings.  :meth:`Config.load`
parses ``config.toml`` with ``tomllib`` and validates values with exact line
and column markers so operators can fix problems by hand.
"""

from __future__ import annotations

import difflib
import logging
import re
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import ClassVar

from .exceptions import ConfigError
from .theme import THEMES

log = logging.getLogger("autodj")


@dataclass
class MessageStyle:
    """Style for message display (GUI preview only; Camfrog sends plain text)."""

    font_family: str = "Consolas"
    font_size: int = 14
    font_color: str = "#000000"
    bold: bool = False
    italic: bool = False
    underline: bool = False

    _HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

    def validate(self) -> None:
        """Validate all fields; raises ValueError on any invalid field."""
        if not self.font_family or not self.font_family.strip():
            raise ValueError("font_family must not be empty")
        if not (8 <= self.font_size <= 72):
            raise ValueError("font_size must be between 8 and 72")
        if not self._HEX_RE.match(self.font_color or ""):
            raise ValueError("font_color must be a valid hex color")

    def to_toml_dict(self) -> dict:
        """Return a plain dict suitable for writing back to a TOML file."""
        return {
            "font_family": self.font_family,
            "font_size": self.font_size,
            "font_color": self.font_color,
            "bold": self.bold,
            "italic": self.italic,
            "underline": self.underline,
        }

    @classmethod
    def from_toml_dict(cls, data: dict) -> "MessageStyle":
        """Build a MessageStyle from a TOML table dict; missing keys keep defaults."""
        return cls(
            font_family=data.get("font_family", cls.font_family),
            font_size=data.get("font_size", cls.font_size),
            font_color=data.get("font_color", cls.font_color),
            bold=data.get("bold", cls.bold),
            italic=data.get("italic", cls.italic),
            underline=data.get("underline", cls.underline),
        )


# ConfigError is re-exported from exceptions so that config.py and
# tests using `from autodj.exceptions import ConfigError` refer
# to the same class.


# Shipped default nick: the setup check (doctor) asks to replace it with the
# nickname the bot really chats as.
DEFAULT_BOT_NICK = "AutoDJ"


@dataclass
class Config:
    bot_nick: str = DEFAULT_BOT_NICK
    admins: list[str] = field(default_factory=list)
    prefix: str = "!"
    lang: str = "en"  # en | th (bot replies and GUI)
    chat_reader: str = "uia"
    chat_sender: str = "uia"
    window_title_re: str = ".*"  # room windows are titled "<room>: ห้องสนทนา": no "Camfrog" in it; process_re does the filtering
    process_re: str = (
        "(?i)camfrog"  # window must belong to a process whose exe name matches ("" = any)
    )
    window_exclude_re: str = ""  # drop matching titles when several windows match
    window_index: int = 0  # which match to use after filtering (0 = first)
    auto_discover: bool = (
        True  # at startup (uia): find the room window + chat/input controls, save to config.toml
    )
    view_kind: str = (
        "auto"  # auto | web (Camfrog room: embedded web panes) | text (Document/Edit controls)
    )
    web_view_title: str = "wb-log-room-data"  # substring of the chat-history pane title
    web_input_title: str = "wb-edit-data"  # substring of the message-box pane title
    send_mode: str = "auto"  # background | foreground | auto (background, verify, fallback)
    send_verify: bool = (
        True  # auto mode: confirm line appeared in room before accepting background send
    )
    web_strict_body: bool = (
        True  # drop plain text that directly follows a message body (date headers / system lines)
    )
    view_type: str = "Document"
    view_index: int = 0
    input_type: str = "Edit"
    input_index: int = -1
    log_path: str = ""  # Also write chat log to this file (rotating, 1 MB x 3)
    log_encoding: str = "utf-8"  # Log file encoding
    line_regex: str = (
        r"^(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*)?(?P<user>[^:\s][^:]{0,30}):\s(?P<text>.+)$"
    )
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
    # Answer "what song is this?" lines in the room (no command needed)
    np_question_reply: bool = True
    np_question_keywords: list[str] = field(
        default_factory=lambda: [
            "เพลงอะไร",
            "เพลงไร",
            "เพลงชื่อ",
            "ชื่อเพลง",
            "เพลงนี้ชื่อ",
            "what song",
            "whats playing",
            "what's playing",
            "song name",
        ]
    )
    np_question_cooldown: float = 20.0  # seconds; room-wide, prevents flooding
    msg_now: str = ""  # empty = built-in text for `lang`
    msg_next: str = ""
    ui_theme: str = "zplayer-dark"  # GUI theme: zplayer-dark | zplayer-neon | zplayer-light
    tts_voice: str = ""
    tts_rate: int = 170
    tts_duck: int = 25
    auto_launch: bool = False
    camfrog_exe: str = ""
    client_title_re: str = ".*"
    room: str = ""
    join_uri_template: str = ""  # e.g. "<scheme>://...{room}"
    launch_timeout: int = 60
    blocked_users: list[str] = field(
        default_factory=list
    )  # nicks whose commands are ignored (admins cannot be blocked)
    ytdlp_path: str = (
        ""  # "" = auto: yt-dlp(.exe) next to mpv or on PATH, else the bundled Python module
    )
    poll_interval: float = 0.5  # seconds between chat reads (raise it if AutoDJ uses too much CPU)
    log_file: str = ""  # also write the log to this file (rotating, 1 MB x 3)
    playlist_file: str = (
        "playlist.json"  # user-requested tracks (!play / GUI request / !load) are appended here
    )
    # (deduplicated) and join the autoplay pool (random); "" = disable persistence
    playlist_dir: str = (
        ""  # directory of *.json playlist files auto-loaded at startup; "" = disabled
    )
    # Even when playlist_dir is set, do not auto-load its files unless explicitly
    # enabled: demo/test playlists must not fill the live request queue.
    playlist_dir_autoload: bool = False
    search_limit: int = (
        1  # YouTube text-search results fetched per non-admin !play (1 = first match only)
    )
    mpv_timeout: float = (
        0.0  # seconds to wait for one mpv track before treating it as hung (0 = no timeout)
    )
    # Audio Engineering
    audio_fade: bool = True  # enable audio volume fade-in and fade-out
    audio_fade_in_sec: float = 1.2  # fade-in duration in seconds
    audio_fade_out_sec: float = 1.5  # fade-out duration on skip/stop in seconds
    audio_normalize: bool = False  # enable dynamic audio loudness normalization (dynaudnorm)
    # YouTube Authentication
    youtube_cookies_file: str = ""  # path to Netscape cookies.txt for yt-dlp
    youtube_cookies_browser: str = (
        ""  # browser name for --cookies-from-browser (e.g. chrome, edge, firefox)
    )
    youtube_ca_bundle: str = (
        ""  # path to custom CA bundle PEM file for yt-dlp certificate verification
    )
    # Dynamic Moderation
    voteskip_dynamic: bool = False  # dynamic voteskip threshold based on participant count
    voteskip_dynamic_pct: int = 30  # percentage of participants required to skip
    user_request_limit: int = 5  # max song requests allowed per user within rate_limit_window
    rate_limit_window: float = 300.0  # rolling time window for per-user request limit (seconds)
    voteskip_cooldown: float = 10.0  # seconds between voteskips from same user
    admin_block_user: bool = False  # Enable !block user command (admin can block a user)
    admin_unblock_user: bool = False  # Enable !unblock user command (admin can unblock a user)
    admin_block_bot: bool = True  # Enable !block-bot command
    admin_unblock_bot: bool = True  # Enable !unblock-bot command
    admin_kick_user: bool = True  # Enable !kick command
    admin_ban_user: bool = True  # Enable !ban command
    admin_unban_user: bool = True  # Enable !unban command
    admin_punish_user: bool = True  # Enable !punish command
    admin_punish_bot: bool = True  # Enable !punish-bot command
    admin_delete_message_enabled: bool = True  # Enable !delete <msg id> command
    # Auto-reply: scheduled messages sent to the room from ads-list.json
    auto_reply_enabled: bool = False  # enable scheduled auto-reply messages
    auto_reply_interval: float = 300.0  # seconds between auto-reply messages (5 minutes)
    auto_reply_file: str = "ads-list.json"  # JSON file with messages to rotate through

    # IM Auto-reply: automatic reply to private/instant messages
    im_auto_reply_enabled: bool = True  # enable auto-reply to private/instant messages
    im_auto_reply_message: str = (
        "Thanks for your message! I'm a bot and will respond when I can. Use !help for commands."
    )
    im_auto_reply_cooldown: float = 60.0  # seconds between auto-replies to the same user
    # Private reply to an IM sender who is not in the room (im_require_room_presence).
    # {room} = room name; Camfrog shows camfrog:join:<room> as a Join link. "" = no reply.
    im_join_room_message: str = "กรุณาเข้าห้อง camfrog:join:{room} ก่อนขอเพลงครับ"

    # IM Security: require user to be in room to use IM commands
    im_require_room_presence: bool = True  # only users seen in room chat can DM the bot
    # Song requests in room chat too (IM always works for users in the room;
    # see im_require_room_presence / im_join_room_message). False = IM only.
    allow_play_in_room: bool = True

    # Autoplay: switch to autoplay pool after idle timeout
    # Default song: plays at startup and whenever the request queue is empty and
    # nobody requested for autoplay_idle_timeout seconds; a request cuts it.
    default_track: str = ""
    autoplay_idle_timeout: float = 30.0  # seconds before autoplay starts when no user requests

    # Admin Greeting
    admin_greeting_enabled: bool = True  # greet admins (instead of the welcome) when they arrive
    admin_greeting_message: str = "สวัสดีครับแอดมิน {admin} ยินดีต้อนรับกลับมา!"
    admin_greeting_cooldown: float = 3600.0  # seconds between greetings for same admin (1 hour)

    # IM Viewer
    im_viewer_enabled: bool = True  # show the IM / private message viewer tab in the GUI

    # Font/Style Customization (GUI Preview Only)
    message_style: MessageStyle = field(default_factory=MessageStyle)

    # Admin Mic Mute/Unmute
    admin_mute_mic: bool = True  # enable !mute command
    admin_unmute_mic: bool = True  # enable !unmute command
    mute_enabled: bool = False  # mic muted state (persisted)

    # Welcome Message
    welcome_message_enabled: bool = True  # greet every (non-admin) user who enters the room
    welcome_message_message: str = (
        "ยินดีต้อนรับ {user} เข้าสู่ {room} สถานีเพลง อัตโนมัติ 24/7 ชั่วโมง"  # {user} {room}
    )
    welcome_message_delay: float = 0.0  # seconds to wait before sending the welcome (0 = instant)
    # Room notice for someone entering, with a (?P<user>...) group; "" disables join detection
    # (users are then greeted on their first message). Check the exact wording your Camfrog
    # client shows and adjust if needed.
    join_line_regex: str = (
        r"^(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*)?\W{0,4}\s*"
        r"(?:(?P<user>[^\s:]+)\s+(?:has\s+)?(?:joined|entered)\b"
        r"|(?P<user_th>[^\s:]+)\s+(?:ได้)?เข้า(?:สู่|มาใน)?ห้อง)"
    )
    welcome_message_cooldown: float = 3600.0  # seconds between welcome messages (1 hour)

    # Mic/DJ greeting: announce when a user gets the room mic (becomes the DJ)
    mic_greeting_enabled: bool = True  # greet users who receive the room mic
    mic_greeting_message: str = ""  # {user} = nick; "" = localized default (messages.py)
    mic_greeting_cooldown: float = 300.0  # seconds between mic greetings for same user
    # Room bots trusted to announce that *another* nick took the mic, e.g. ["ZeazBot"]
    # for "Seaza กำลังรับไมค์".  Other users can only announce themselves.
    mic_notice_senders: list[str] = field(default_factory=list)
    # Nicks never greeted on the mic (e.g. the account AutoDJ streams the music from).
    mic_greeting_ignore: list[str] = field(default_factory=list)

    # Camfrog RE Integrations (Gift / Avatar / Status / Status Alert)
    gift_announce_enabled: bool = True  # announce virtual-gift messages sent to the room
    avatar_change_enabled: bool = True  # announce avatar change messages sent to the room
    status_indicator_enabled: bool = True  # announce user status changes in room chat
    status_alert_enabled: bool = True  # alert when Camfrog shows upgrade/payment-required status

    # Webhook / API Integration
    webhook_enabled: bool = False  # enable HTTP webhook server for external control
    webhook_host: str = "127.0.0.1"  # host to bind webhook server
    webhook_port: int = 8080  # port for webhook server
    webhook_secret: str = ""  # HMAC secret for webhook signature verification
    webhook_rate_limit_per_ip: int = 60  # max requests per IP per minute
    webhook_cors_origins: list[str] = field(default_factory=lambda: ["*"])  # CORS allowed origins

    # Config Hot Reload
    config_hot_reload: bool = False  # enable hot reload of config.toml

    # Plugin System
    plugins: list[str] = field(
        default_factory=lambda: ["builtin.stats", "builtin.help"]
    )  # plugin modules to load

    # JSON structured logging
    log_json: bool = False  # enable JSON structured logging output
    log_json_fields: list[str] = field(
        default_factory=lambda: [
            "request_id",
            "delivery_id",
            "user",
            "track_id",
            "generation",
            "attempt_id",
            "category",
            "stage",
            "state",
        ]
    )  # extra fields to include in JSON logs

    # Auto-update: check GitHub releases for newer AutoDJ.exe
    auto_update_enabled: bool = False  # enable automatic update checks
    auto_update_repo: str = "cvsz/autodj"  # GitHub repo (owner/name) for release checks
    auto_update_check_interval: float = 21600.0  # seconds between checks (default 6h)
    auto_update_asset: str = "AutoDJ.exe"  # release asset filename to download
    # When auto_update_enabled, download the latest AutoDJ.exe on startup and
    # replace this installation (via autodj_update.bat) before starting the bot.
    auto_update_apply_on_start: bool = True

    # AI: optional chat-completion integration (enabled by default)
    ai_enabled: bool = True  # allow `!ai ask` answers (needs ai_api_key)
    ai_api_key: str = ""  # API key for the AI provider
    ai_base_url: str = "https://integrate.api.nvidia.com/v1"  # NVIDIA Inference API endpoint
    ai_model: str = "nvidia/llama-3.3-nemotron-super-49b-v1.5"  # NVIDIA API catalog model id
    ai_system_prompt: str = (
        "You are AutoDJ, a music bot in a Camfrog room powered by NVIDIA AI. Keep replies short, "
        "friendly, and on-topic. Do not claim to play music unless asked."
    )
    ai_max_chars: int = 200  # max characters in AI reply
    ai_user_cooldown: float = 30.0  # seconds between AI replies to same user

    # Multi-platform streaming (ported from cvsz/streamdbc architecture)
    # Stream/room registry tracks active broadcasts across platforms
    # (Camfrog, YouTube Live, TikTok Live, Facebook Live). Each platform has
    # its own adapter; the registry assigns a safe stream_id per room and
    # manages lifecycle (IDLE / LIVE / RECORDING / ERROR).
    streams: dict = field(default_factory=dict)

    # Reload callbacks (class-level, shared across all instances)
    _reload_callbacks: ClassVar[list] = []

    @classmethod
    def register_reload_callback(cls, callback) -> None:
        """Register a callback to be invoked on Config.reload()."""
        Config._reload_callbacks.append(callback)

    @classmethod
    def unregister_reload_callback(cls, callback) -> None:
        """Remove a previously registered reload callback."""
        try:
            cls._reload_callbacks.remove(callback)
        except ValueError:
            pass

    @classmethod
    def _fire_reload_callbacks(cls, cfg: "Config") -> None:
        for cb in list(cls._reload_callbacks):
            try:
                cb(cfg)
            except Exception:  # a reload callback must never break reload
                log.exception("config reload callback %r failed", cb)

    @classmethod
    def reload(cls, path: str | None) -> "Config":
        """Reload config from *path*, re-validating and firing callbacks."""
        cfg = cls.load(path)
        cls._fire_reload_callbacks(cfg)
        return cfg

    @classmethod
    def load(cls, path: str | None) -> "Config":
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
        # Convert an inline TOML table for message_style into a MessageStyle instance
        # so the dataclass field receives the right type (tomllib yields plain dicts).
        if "message_style" in data and isinstance(data["message_style"], dict):
            try:
                style = MessageStyle(**data["message_style"])
                style.validate()  # reject invalid font values early
            except (TypeError, ValueError) as ex:
                raise ConfigError(f"{p or 'config'}: invalid message_style table: {ex}") from None
            data["message_style"] = style
        names = {f.name for f in fields(cls)}
        bad = sorted(set(data) - names)
        if bad:
            lines = []
            for k in bad:
                near = difflib.get_close_matches(k, names, n=1)
                lines.append(f"  {k}" + (f"   (did you mean '{near[0]}'?)" if near else ""))
            raise ConfigError(f"{p or 'config'}: unknown setting(s):\n" + "\n".join(lines))
        cfg = cls(**data)
        _validate(cfg, data, str(p) if p else "config")
        return cfg

    @classmethod
    def validate_values(cls, data: dict, where: str = "settings") -> "Config":
        """Validate already-parsed settings without touching disk.

        Used by the GUI before saving so an invalid value can never be written
        to config.toml and make the next startup fail closed.  Raises
        ConfigError with the offending field and location.
        """
        names = {f.name for f in fields(cls)}
        bad = sorted(set(data) - names)
        if bad:
            raise ConfigError(f"{where}: unknown setting(s): {', '.join(bad)}")
        if "message_style" in data and isinstance(data["message_style"], dict):
            data = dict(data)
            try:
                data["message_style"] = MessageStyle(**data["message_style"])
            except (TypeError, ValueError) as ex:
                raise ConfigError(f"{where}: invalid message_style table: {ex}") from None
        cfg = cls(**data)
        _validate(cfg, data, where)
        return cfg


# ---- validation -------------------------------------------------------------------------------

_CHOICES = {
    "lang": ("en", "th"),
    "chat_reader": ("uia", "logtail", "console"),
    "chat_sender": ("uia", "logtail", "console"),
    "view_kind": ("auto", "web", "text"),
    "send_mode": ("auto", "background", "foreground"),
    "ui_theme": tuple(THEMES.keys()),
}
_REGEXES = (
    "window_title_re",
    "process_re",
    "window_exclude_re",
    "line_regex",
    "client_title_re",
    "join_line_regex",
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
    "auto_reply_interval": (60.0, 86400.0),
    "np_question_cooldown": (0.0, 3600.0),
    "autoplay_idle_timeout": (0.0, 86400.0),
    "ai_user_cooldown": (0.0, 86400.0),
    "ai_max_chars": (1, 2000),
    "welcome_message_delay": (0.0, 3600.0),
    "mic_greeting_cooldown": (0.0, 86400.0),
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
    out.append("Fix that line, or copy config.example.toml over config.toml to start again.")
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
        _validate_field(cfg, data, f, defaults, where)
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
        _validate_regex(cfg, k, where)
    if not cfg.prefix.strip():
        raise ConfigError(f"{where}: 'prefix' must not be empty (e.g. prefix = \"!\")")
    cfg.prefix = cfg.prefix.strip()
    cfg.admins = [a.strip() for a in cfg.admins if a.strip()]
    cfg.blocked_users = [a.strip() for a in cfg.blocked_users if a.strip()]

    # Validate multi-platform streaming config
    streams_cfg = data.get("streams", {})
    if isinstance(streams_cfg, dict):
        _validate_streams(streams_cfg, where)


def _validate_field(cfg: Config, data: dict, f, defaults: Config, where: str) -> None:
    v = data[f.name]
    want = type(getattr(defaults, f.name))
    if not _is_type(v, want):
        hint = ' (a list looks like ["nick1", "nick2"])' if want is list else ""
        raise ConfigError(
            f"{where}: '{f.name}' must be {_type_name(getattr(defaults, f.name))}, got {v!r}{hint}"
        )
    if want is list and not all(isinstance(x, str) for x in v):
        raise ConfigError(f"{where}: every item of '{f.name}' must be text, got {v!r}")


def _is_type(v, want) -> bool:
    if want is bool:
        return isinstance(v, bool)
    if want is float:
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if want is int:
        return isinstance(v, int) and not isinstance(v, bool)
    return isinstance(v, want)


def _validate_regex(cfg: Config, k: str, where: str) -> None:
    try:
        re.compile(getattr(cfg, k))
    except re.error as ex:
        raise ConfigError(
            f"{where}: '{k}' is not a valid regular expression ({ex}). "
            "Tip: write regexes in 'single quotes' so backslashes stay as they are."
        ) from None


def _validate_streams(streams_cfg: dict, where: str) -> None:
    """Validate the [streams] TOML table (multi-platform streaming config)."""
    enabled = streams_cfg.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ConfigError(f"{where}: 'streams.enabled' must be true/false")

    if not enabled:
        return  # nothing more to validate when disabled

    max_concurrent = streams_cfg.get("max_concurrent_streams", 16)
    if not isinstance(max_concurrent, int) or not 1 <= max_concurrent <= 256:
        raise ConfigError(f"{where}: 'streams.max_concurrent_streams' must be 1-256")

    registry_ttl = streams_cfg.get("registry_ttl_seconds", 86400.0)
    if not isinstance(registry_ttl, (int, float)) or registry_ttl <= 0:
        raise ConfigError(f"{where}: 'streams.registry_ttl_seconds' must be > 0")

    _validate_streams_auth(streams_cfg.get("auth", {}), where)
    _validate_streams_platforms(streams_cfg.get("platforms", {}), where)
    _validate_streams_recorder(streams_cfg.get("recorder", {}), where)
    _validate_streams_transcoder(streams_cfg.get("transcoder", {}), where)


def _validate_streams_auth(auth_cfg: dict, where: str) -> None:
    if not isinstance(auth_cfg, dict):
        return
    jwt_secret = auth_cfg.get("jwt_secret", "")
    if jwt_secret and len(jwt_secret) < 32:
        raise ConfigError(f"{where}: 'streams.auth.jwt_secret' must be at least 32 characters")
    api_keys = auth_cfg.get("api_keys", [])
    if not isinstance(api_keys, list):
        raise ConfigError(f"{where}: 'streams.auth.api_keys' must be a list")
    for key in api_keys:
        if not isinstance(key, str) or len(key) < 16:
            raise ConfigError(f"{where}: each 'streams.auth.api_keys' entry must be >= 16 chars")


def _validate_streams_platforms(platforms_cfg: dict, where: str) -> None:
    if not isinstance(platforms_cfg, dict):
        raise ConfigError(f"{where}: 'streams.platforms' must be a table")
    allowed_platforms = {"camfrog", "youtube", "tiktok", "facebook"}
    for platform_name, platform_cfg in platforms_cfg.items():
        if platform_name not in allowed_platforms:
            raise ConfigError(
                f"{where}: unknown platform '{platform_name}' in streams.platforms "
                f"(allowed: {', '.join(sorted(allowed_platforms))})"
            )
        if not isinstance(platform_cfg, dict):
            raise ConfigError(f"{where}: 'streams.platforms.{platform_name}' must be a table")
        if "enable" in platform_cfg and not isinstance(platform_cfg["enable"], bool):
            raise ConfigError(
                f"{where}: 'streams.platforms.{platform_name}.enable' must be true/false"
            )


def _validate_streams_recorder(recorder_cfg: dict, where: str) -> None:
    if not isinstance(recorder_cfg, dict):
        return
    max_active = recorder_cfg.get("max_active", 64)
    if not isinstance(max_active, int) or not 1 <= max_active <= 256:
        raise ConfigError(f"{where}: 'streams.recorder.max_active' must be 1-256")


def _validate_streams_transcoder(transcoder_cfg: dict, where: str) -> None:
    if not isinstance(transcoder_cfg, dict):
        return
    worker_count = transcoder_cfg.get("worker_count", 2)
    if not isinstance(worker_count, int) or not 1 <= worker_count <= 16:
        raise ConfigError(f"{where}: 'streams.transcoder.worker_count' must be 1-16")
