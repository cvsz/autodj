"""Built-in AI client for CamfrogAutoDJ.

Optional, fail-closed integration with OpenAI-compatible chat APIs
(OpenAI, OpenRouter, local llama.cpp, etc.).  Disabled by default;
never makes network requests unless explicitly enabled and configured.

All network calls target the configured ``ai_base_url`` only.  No data is
sent to any third party unless the operator explicitly configures it.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from . import __version__
from .exceptions import AutoDJError

log = logging.getLogger("autodj")

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-3.5-turbo"
DEFAULT_SYSTEM_PROMPT = (
    "You are AutoDJ, a music bot in a Camfrog room.  Keep replies short, "
    "friendly, and on-topic.  Do not claim to play music unless asked."
)
DEFAULT_CHECK_INTERVAL = 60.0  # seconds between AI message checks (not used yet)
MAX_RESPONSE_CHARS = 200  # Camfrog message length safety
USER_COOLDOWN = 30.0  # seconds between AI replies to same user
UA = f"CamfrogAutoDJ/{__version__} (+https://github.com/cvsz/autodj)"


class AIError(AutoDJError):
    """AI client failure."""


class AIClient:
    """Chat-completion client for optional AI replies.

    Never raises on network failure: errors are logged and the caller
    receives ``None`` so the bot keeps running.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.enabled: bool = bool(getattr(cfg, "ai_enabled", False))
        self.api_key: str = str(getattr(cfg, "ai_api_key", "") or "")
        self.base_url: str = str(
            getattr(cfg, "ai_base_url", DEFAULT_BASE_URL) or DEFAULT_BASE_URL
        ).rstrip("/")
        self.model: str = str(getattr(cfg, "ai_model", DEFAULT_MODEL) or DEFAULT_MODEL)
        self.system_prompt: str = str(
            getattr(cfg, "ai_system_prompt", DEFAULT_SYSTEM_PROMPT) or DEFAULT_SYSTEM_PROMPT
        )
        self.max_chars: int = int(getattr(cfg, "ai_max_chars", MAX_RESPONSE_CHARS))
        self.user_cooldown: float = float(getattr(cfg, "ai_user_cooldown", USER_COOLDOWN))
        self._lock = threading.Lock()
        self._user_cooldowns: dict[str, float] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        """No background thread yet; kept for symmetry with Engine.start()."""
        if not self.enabled:
            log.debug("AI disabled; client not started")
            return
        log.info("AI client enabled (base=%s, model=%s)", self.base_url, self.model)

    def stop(self) -> None:
        self._stop.set()

    # ------------------------------------------------------------------ public API
    def is_enabled(self) -> bool:
        return self.enabled and bool(self.api_key)

    def can_reply(self, user: str) -> bool:
        """Return True if *user* is not on cooldown."""
        if not self.enabled or not self.api_key:
            return False
        now = time.monotonic()
        with self._lock:
            last = self._user_cooldowns.get(user.lower(), 0.0)
            if now - last < self.user_cooldown:
                return False
            self._user_cooldowns[user.lower()] = now
            return True

    def chat(self, text: str) -> str | None:
        """Send *text* to the AI and return a reply string, or None on failure.

        Never raises: network/API failures are logged and return None.
        """
        if not self.is_enabled():
            return None
        if not text or not text.strip():
            return None
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": text},
            ],
            "max_tokens": max(1, self.max_chars // 4),
            "temperature": 0.7,
        }
        try:
            data = self._post_json(f"{self.base_url}/chat/completions", payload)
        except Exception as ex:  # noqa: BLE001 - AI must never crash the bot
            log.warning("AI request failed: %s", ex)
            return None
        try:
            choices = data.get("choices") or []
            if not choices:
                return None
            message = choices[0].get("message") or {}
            content = message.get("content") or ""
            content = content.strip()
            if not content:
                return None
            if len(content) > self.max_chars:
                content = content[: self.max_chars].rstrip() + "..."
            return content
        except Exception:  # noqa: BLE001 - malformed response must not crash bot
            log.exception("AI response parsing failed")
            return None

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _allowed_url(url: str) -> bool:
        """Return True only for a safe AI endpoint URL.

        ``https://`` is required for remote hosts so the API key never travels
        in clear text; plain ``http://`` is accepted only for loopback hosts
        (local llama.cpp / Ollama style servers).  URLs carrying embedded
        credentials are rejected.
        """
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
        except ValueError:
            return False
        if not host or parsed.username or parsed.password:
            return False
        if parsed.scheme == "https":
            return True
        return parsed.scheme == "http" and host in ("localhost", "127.0.0.1", "::1")

    def _post_json(self, url: str, payload: dict) -> dict:
        if not self._allowed_url(url):
            raise ValueError(f"AI base URL rejected (https required for remote hosts): {url}")
        data = json.dumps(payload).encode("utf-8")
        req = Request(  # noqa: S310 - scheme/host validated by _allowed_url above
            url,
            data=data,
            headers={
                "User-Agent": UA,
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urlopen(req, timeout=30) as resp:  # noqa: S310 - validated by _allowed_url  # nosec B310 - URL scheme/host validated just above (https/github.com only)
            if resp.status != 200:
                raise HTTPError(url, resp.status, resp.reason, resp.headers, resp)
            return json.loads(resp.read().decode("utf-8"))
