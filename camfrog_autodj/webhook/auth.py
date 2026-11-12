"""HMAC authentication for webhook endpoints."""

from __future__ import annotations

import hashlib
import hmac
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

if TYPE_CHECKING:
    from camfrog_autodj.webhook.models import WebhookConfig

# Key for storing raw body in request.state
_RAW_BODY_KEY = "_webhook_raw_body"


class RawBodyMiddleware(BaseHTTPMiddleware):
    """Middleware to capture the raw request body before any parsing.

    This must be added as the FIRST middleware to ensure it captures the
    body before FastAPI's request parsing middleware consumes it.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Check if body is already cached (e.g., by TestClient)
        if hasattr(request, "_body") and request._body is not None:
            request.state.__dict__[_RAW_BODY_KEY] = request._body
            return await call_next(request)

        # Consume the receive stream to get the raw body
        body_chunks = []
        more_body = True

        async def receive():
            nonlocal more_body
            message = await request._receive()
            if message["type"] == "http.request":
                body_chunks.append(message.get("body", b""))
                more_body = message.get("more_body", False)
            return message

        # Read all body chunks
        while more_body:
            await receive()

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


async def verify_webhook_signature(request: Request) -> bool:
    """Verify HMAC signature on webhook request.

    Gets config from request.app.state.webhook_state.

    Args:
        request: FastAPI request object

    Returns:
        True if signature is valid

    Raises:
        HTTPException: If signature is missing or invalid
    """
    state = getattr(request.app.state, "webhook_state", None)
    if state is None:
        raise HTTPException(status_code=503, detail="Webhook not configured")

    config = state.config
    if not config.enabled:
        raise HTTPException(status_code=404, detail="Webhook disabled")

    signature = request.headers.get("X-Signature")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature")

    # Get raw body captured by RawBodyMiddleware
    body = getattr(request.state, _RAW_BODY_KEY, None)
    if body is None:
        # Fallback: try cached body (may be re-serialized by FastAPI)
        body = getattr(request, "_body", None)
    if body is None:
        body = await request.body()

    expected = hmac.new(config.secret.encode(), body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid signature")

    return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting per IP."""

    def __init__(self, app, config: WebhookConfig):
        super().__init__(app)
        self.config = config
        self._requests: dict[str, list[float]] = {}
        self._cleanup_interval = 60.0  # seconds

    async def dispatch(self, request: Request, call_next):
        if not self.config.enabled:
            return await call_next(request)

        import time

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Clean old entries
        cutoff = now - 60.0  # 1 minute window
        if client_ip in self._requests:
            self._requests[client_ip] = [t for t in self._requests[client_ip] if t > cutoff]
        else:
            self._requests[client_ip] = []

        # Check rate limit
        if len(self._requests[client_ip]) >= self.config.rate_limit_per_ip:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        self._requests[client_ip].append(now)
        return await call_next(request)


async def verify_signature_dep(req: Request) -> bool:
    """FastAPI dependency for signature verification."""
    return await verify_webhook_signature(req)
