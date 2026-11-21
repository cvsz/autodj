"""Stream-scoped authentication and authorization.

Ported from cvsz/streamdbc internal/auth/manager.go and authorize.go.

Provides JWT tokens (HS256) scoped to a stream with an action
(``publish`` or ``play``), plus API-key validation for management
operations.  Tokens may optionally bind to a client IP address.

AutoDJ uses this to control which platform bots can publish audio to a
stream and which clients can play/monitor it.
"""

from __future__ import annotations

import time
import uuid
from typing import Optional

try:
    import jwt  # PyJWT
except ImportError:  # pragma: no cover - jwt optional at import time
    jwt = None  # type: ignore[assignment]

from .stream_id import validate_stream_id


class AuthError(Exception):
    """Authentication or authorization error."""


class InvalidTokenError(AuthError):
    """The presented token is invalid."""


class ExpiredTokenError(AuthError):
    """The presented token has expired."""


class UnauthorizedError(AuthError):
    """The caller is not authorized for the requested action."""


# Minimum API key length (port from Go constant).
_MIN_API_KEY_LENGTH: int = 16
_MAX_TOKEN_LENGTH: int = 16 << 10  # 16 KiB


class Claims:
    """Stream-scoped JWT claims."""

    def __init__(
        self,
        stream_id: str,
        action: str,
        ip: str = "",
        api_key: str = "",
        issuer: str = "autodj",
    ) -> None:
        self.stream_id = stream_id
        self.action = action  # "publish" or "play"
        self.ip = ip
        self.api_key = api_key
        self.issuer = issuer
        self.issued_at: float = time.time()
        self.not_before: float = time.time() - 5.0  # clock skew tolerance
        self.expires_at: float = time.time() + 86400.0
        self.jti: str = str(uuid.uuid4())

    def to_dict(self) -> dict:
        return {
            "stream_id": self.stream_id,
            "action": self.action,
            "ip": self.ip,
            "api_key": self.api_key,
            "iss": self.issuer,
            "sub": self.stream_id,
            "iat": self.issued_at,
            "nbf": self.not_before,
            "exp": self.expires_at,
            "jti": self.jti,
        }


def _constant_time_compare(a: bytes, b: bytes) -> bool:
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b, strict=False):
        result |= x ^ y
    return result == 0


def _validate_api_key_format(key: str) -> None:
    if len(key) < _MIN_API_KEY_LENGTH:
        raise AuthError(f"API keys must be at least {_MIN_API_KEY_LENGTH} characters")
    if key != key.strip():
        raise AuthError("API keys must not contain surrounding whitespace")
    for ch in key:
        if ord(ch) < 32 or ord(ch) == 127 or ch.isspace():
            raise AuthError("API keys must not contain control characters or spaces")


def _parse_api_keys(api_keys: list[str]) -> list[bytes]:
    keys: list[bytes] = []
    seen: set[str] = set()
    for key in api_keys:
        _validate_api_key_format(key)
        if key in seen:
            raise AuthError("API keys must be unique")
        seen.add(key)
        keys.append(key.encode("utf-8"))
    if not keys:
        raise AuthError("at least one API key is required")
    return keys


class AuthManager:
    """Issues and validates JWT tokens and API keys."""

    def __init__(
        self,
        jwt_secret: str,
        jwt_expiry: str,
        api_keys: list[str],
        allow_anonymous: bool = False,
    ) -> None:
        if jwt is None:
            raise AuthError("PyJWT is not installed; run: pip install pyjwt")
        secret = jwt_secret or ""
        if secret != secret.strip() or len(secret) < 32:
            raise AuthError("JWT secret must be at least 32 characters")
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in secret):
            raise AuthError("JWT secret must not contain control characters")

        try:
            expiry_duration = _parse_duration(jwt_expiry)
        except ValueError as exc:
            raise AuthError(f"invalid JWT expiry {jwt_expiry!r}") from exc
        if expiry_duration <= 0:
            raise AuthError("JWT expiry must be positive")

        key_bytes = _parse_api_keys(api_keys)
        self._jwt_secret = secret.encode("utf-8")
        self._jwt_expiry = expiry_duration
        self._api_keys = key_bytes
        self._allow_anonymous = allow_anonymous

    # ------------------------------------------------------------------
    # Token issuance
    # ------------------------------------------------------------------
    def generate_publish_token(self, stream_id: str, api_key: str, ip: str = "") -> str:
        """Issue a publish token for *stream_id* after validating *api_key*."""
        validate_stream_id(stream_id)
        _validate_ip(ip)
        if not self.validate_api_key(api_key):
            raise UnauthorizedError("invalid API key for publish token")
        return self._generate_token(stream_id, "publish", api_key, ip)

    def generate_play_token(self, stream_id: str, ip: str = "") -> str:
        """Issue a play token for *stream_id* (no API key required)."""
        validate_stream_id(stream_id)
        _validate_ip(ip)
        return self._generate_token(stream_id, "play", "", ip)

    def _generate_token(self, stream_id: str, action: str, api_key: str, ip: str) -> str:
        if action not in ("publish", "play"):
            raise AuthError(f"unsupported token action {action!r}")
        if action == "publish" and not self.validate_api_key(api_key):
            raise UnauthorizedError("invalid API key")

        now = time.time()
        claims = Claims(stream_id, action, ip, api_key)
        claims.issued_at = now
        claims.not_before = now - 5.0
        claims.expires_at = now + self._jwt_expiry

        encoded = jwt.encode(claims.to_dict(), self._jwt_secret, algorithm="HS256")
        return encoded if isinstance(encoded, str) else encoded.decode("utf-8")

    # ------------------------------------------------------------------
    # Token validation
    # ------------------------------------------------------------------
    def validate_token(self, token_string: str) -> Claims:
        if not token_string or len(token_string) > _MAX_TOKEN_LENGTH:
            raise InvalidTokenError("invalid token length")
        try:
            payload = jwt.decode(
                token_string,
                self._jwt_secret,
                algorithms=["HS256"],
                issuer="autodj",
            )
        except jwt.ExpiredSignatureError as exc:
            raise ExpiredTokenError("token expired") from exc
        except jwt.InvalidTokenError as exc:
            raise InvalidTokenError(str(exc)) from exc

        stream_id = payload.get("sub", "")
        action = payload.get("action", "")
        ip = payload.get("ip", "")
        api_key = payload.get("api_key", "")
        jti = payload.get("jti", "")

        if (
            not stream_id
            or action not in ("publish", "play")
            or api_key != ""
            or not jti
            or "\x00" in ip
            or "\r" in ip
            or "\n" in ip
            or "\t" in ip
        ):
            raise InvalidTokenError("invalid token claims")
        try:
            validate_stream_id(stream_id)
        except AuthError as exc:
            raise InvalidTokenError(str(exc)) from exc

        claims = Claims(stream_id, action, ip, api_key)
        claims.issued_at = float(payload.get("iat", 0))
        claims.not_before = float(payload.get("nbf", 0))
        claims.expires_at = float(payload.get("exp", 0))
        claims.jti = jti
        return claims

    def validate_api_key(self, key: str) -> bool:
        if (
            len(key) < _MIN_API_KEY_LENGTH
            or key != key.strip()
            or any(ord(ch) < 32 or ord(ch) == 127 or ch.isspace() for ch in key)
        ):
            return False
        key_bytes = key.encode("utf-8")
        for configured in self._api_keys:
            if _constant_time_compare(configured, key_bytes):
                return True
        return False

    def allow_anonymous(self) -> bool:
        return self._allow_anonymous

    def can_publish(self, claims: Claims, stream_id: str) -> bool:
        return claims is not None and claims.action == "publish" and claims.stream_id == stream_id

    def can_play(self, claims: Claims, stream_id: str) -> bool:
        return claims is not None and claims.action == "play" and claims.stream_id == stream_id

    def can_publish_from_ip(self, claims: Claims, stream_id: str, ip: str) -> bool:
        return self.can_publish(claims, stream_id) and self._ip_matches(claims, ip)

    def can_play_from_ip(self, claims: Claims, stream_id: str, ip: str) -> bool:
        return self.can_play(claims, stream_id) and self._ip_matches(claims, ip)

    def _ip_matches(self, claims: Claims, ip: str) -> bool:
        return claims is not None and (claims.ip == "" or claims.ip == ip)


def authorize(
    manager: Optional[AuthManager],
    token: str,
    action: str,
    stream_id: str,
    ip: str,
) -> bool:
    """Authorize a publish/play action for *stream_id* from *ip*.

    A nil manager permits all requests.  Play with no token allows anonymous
    access only when the manager permits it.
    """
    if manager is None:
        return True
    if not token and action == "play" and manager.allow_anonymous():
        return True
    try:
        claims = manager.validate_token(token)
    except AuthError:
        return False
    if action == "publish":
        return manager.can_publish_from_ip(claims, stream_id, ip)
    if action == "play":
        return manager.can_play_from_ip(claims, stream_id, ip)
    return False


def _validate_ip(ip: str) -> None:
    if "\x00" in ip or "\r" in ip or "\n" in ip or "\t" in ip or ip != ip.strip():
        raise AuthError("invalid client IP")


def _parse_duration(value: str) -> float:
    """Parse a Go-style duration string (e.g. ``24h``, ``30m``, ``15s``)."""
    value = value.strip()
    if not value:
        raise ValueError("empty duration")
    unit = value[-1:]
    number = value[:-1]
    try:
        num = float(number)
    except ValueError as exc:
        raise ValueError(f"invalid duration {value!r}") from exc
    multipliers = {"s": 1.0, "m": 60.0, "h": 3600.0, "d": 86400.0}
    if unit not in multipliers:
        raise ValueError(f"unknown duration unit {unit!r}")
    return num * multipliers[unit]


class APIKeyValidator:
    """Key-only checker for management operations when JWT auth is disabled."""

    def __init__(self, api_keys: list[str]) -> None:
        self._api_keys = _parse_api_keys(api_keys)

    def validate(self, key: str) -> bool:
        if (
            len(key) < _MIN_API_KEY_LENGTH
            or key != key.strip()
            or any(ord(ch) < 32 or ord(ch) == 127 or ch.isspace() for ch in key)
        ):
            return False
        key_bytes = key.encode("utf-8")
        for configured in self._api_keys:
            if _constant_time_compare(configured, key_bytes):
                return True
        return False
