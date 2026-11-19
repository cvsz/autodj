"""HMAC authentication for webhook endpoints."""

from __future__ import annotations

import hashlib
import hmac
import threading
import time
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

if TYPE_CHECKING:
    from autodj.webhook.models import WebhookConfig

# Key for storing raw body in request.state
_RAW_BODY_KEY = "_webhook_raw_body"

# Largest accepted request body. Every endpoint takes a tiny JSON document.
MAX_BODY_BYTES = 64 * 1024


class RawBodyMiddleware(BaseHTTPMiddleware):
    """Middleware to capture the raw request body before any parsing.

    This must be added as the FIRST middleware to ensure it captures the
    body before FastAPI's request parsing middleware consumes it.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Check if body is already cached (e.g., by TestClient)
        if hasattr(request, "_body") and request._body is not None:
            if len(request._body) > MAX_BODY_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"error": "Request body too large", "status_code": 413},
                )
            request.state.__dict__[_RAW_BODY_KEY] = request._body
            return await call_next(request)

        # Consume the receive stream to get the raw body. Bounded: an unbounded
        # read let any client hold arbitrary amounts of memory before auth ran.
        body_chunks: list[bytes] = []
        size = 0
        while True:
            message = await request._receive()
            if message["type"] != "http.request":
                # http.disconnect: the old loop kept polling forever here
                # (more_body never became False), pinning a CPU core.
                return Response(status_code=400)
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > MAX_BODY_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"error": "Request body too large", "status_code": 413},
                )
            body_chunks.append(chunk)
            if not message.get("more_body", False):
                break

        # Store the complete raw body
        raw_body = b"".join(body_chunks)
        request.state.__dict__[_RAW_BODY_KEY] = raw_body

        # Replace the receive function with one that returns the stored body
        # This allows downstream middleware/handlers to read the body again
        async def new_receive():
            return {
                "type": "http.request",
                "body": raw_body,
                "more_body": False,
            }

        request._receive = new_receive

        return await call_next(request)


# Signed requests older/newer than this many seconds are rejected.
SIGNATURE_TOLERANCE_S = 300


def signing_payload(timestamp: str, method: str, path: str, body: bytes) -> bytes:
    """Canonical bytes covered by ``X-Signature``.

    Binding the timestamp, HTTP method and path into the MAC means a captured
    signature cannot be replayed later or against another endpoint (with the
    old body-only scheme every empty-body request — health, skip, pause,
    resume — shared one identical, never-expiring signature).
    """
    return f"{timestamp}.{method.upper()}.{path}.".encode() + body


def _check_fresh(timestamp: str, now: float) -> None:
    """Reject non-numeric or out-of-window ``X-Timestamp`` values."""
    try:
        ts = int(timestamp)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid timestamp") from None
    if abs(now - ts) > SIGNATURE_TOLERANCE_S:
        raise HTTPException(status_code=401, detail="Stale signature")


_REPLAY_LOCK = threading.Lock()


def _remember_once(state: object, signature: str, now: float) -> None:
    """Replay cache: accept each valid signature only once within the window.

    The check-and-insert must be atomic: concurrent requests carrying the same
    valid signature may reach this helper from different uvicorn worker threads.
    """
    with _REPLAY_LOCK:
        seen: dict[str, float] = state.__dict__.setdefault("_seen_signatures", {})
        for sig, exp in list(seen.items()):
            if exp < now:
                seen.pop(sig, None)
        if signature in seen:
            raise HTTPException(status_code=401, detail="Replayed signature")
        seen[signature] = now + 2 * SIGNATURE_TOLERANCE_S


async def verify_webhook_signature(request: Request) -> bool:
    """Verify HMAC signature on webhook request.

    Clients send ``X-Timestamp`` (unix seconds) and
    ``X-Signature = hex(HMAC-SHA256(secret, signing_payload(...)))``.

    Raises:
        HTTPException: If the webhook is unconfigured, or the signature is
            missing, stale, replayed or invalid.
    """
    state = getattr(request.app.state, "webhook_state", None)
    if state is None:
        raise HTTPException(status_code=503, detail="Webhook not configured")

    config = state.config
    if not config.enabled:
        raise HTTPException(status_code=404, detail="Webhook disabled")
    if not config.secret or len(config.secret) < 16:
        # An empty/short key makes HMAC trivially forgeable — fail closed.
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    signature = request.headers.get("X-Signature")
    timestamp = request.headers.get("X-Timestamp")
    if not signature or not timestamp:
        raise HTTPException(status_code=401, detail="Missing signature")
    now = time.time()
    _check_fresh(timestamp, now)

    # Get raw body captured by RawBodyMiddleware
    body = getattr(request.state, _RAW_BODY_KEY, None)
    if body is None:
        body = getattr(request, "_body", None)
    if body is None:
        body = await request.body()

    payload = signing_payload(timestamp, request.method, request.url.path, body)
    expected = hmac.new(config.secret.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature.lower(), expected):
        raise HTTPException(status_code=401, detail="Invalid signature")

    _remember_once(state, expected, now)

    return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting per IP."""

    def __init__(self, app, config: WebhookConfig):
        super().__init__(app)
        self.config = config
        self._requests: dict[str, list[float]] = {}
        self._cleanup_interval = 60.0  # seconds
        self._last_cleanup = 0.0

    async def dispatch(self, request: Request, call_next):
        if not self.config.enabled:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        cutoff = now - 60.0  # 1 minute window

        # Periodically drop idle IPs so the table cannot grow without bound.
        if now - self._last_cleanup > self._cleanup_interval:
            self._requests = {
                ip: [t for t in ts if t > cutoff]
                for ip, ts in self._requests.items()
                if ts and ts[-1] > cutoff
            }
            self._last_cleanup = now

        hits = [t for t in self._requests.get(client_ip, []) if t > cutoff]
        if len(hits) >= self.config.rate_limit_per_ip:
            self._requests[client_ip] = hits
            # HTTPException raised inside BaseHTTPMiddleware bypasses FastAPI's
            # exception handlers (it surfaces as a 500); return the 429 directly.
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "status_code": 429},
            )
        hits.append(now)
        self._requests[client_ip] = hits
        return await call_next(request)


async def verify_signature_dep(req: Request) -> bool:
    """FastAPI dependency for signature verification."""
    return await verify_webhook_signature(req)
