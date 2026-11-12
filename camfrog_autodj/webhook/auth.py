"""HMAC authentication for webhook endpoints."""

from __future__ import annotations

import hashlib
import hmac

from fastapi import Depends, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from camfrog_autodj.webhook.models import WebhookConfig


async def verify_webhook_signature(request: Request, config: WebhookConfig) -> bool:
    """Verify HMAC signature on webhook request.
    
    Args:
        request: FastAPI request object
        config: Webhook configuration with secret
        
    Returns:
        True if signature is valid
        
    Raises:
        HTTPException: If signature is missing or invalid
    """
    if not config.enabled:
        raise HTTPException(status_code=404, detail="Webhook disabled")
    
    signature = request.headers.get("X-Signature")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature")
    
    # Get body - try cached body first, then read from stream
    body = getattr(request, '_body', None)
    if body is None:
        body = await request.body()
    
    expected = hmac.new(
        config.secret.encode(), 
        body, 
        hashlib.sha256
    ).hexdigest()
    
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
            self._requests[client_ip] = [
                t for t in self._requests[client_ip] if t > cutoff
            ]
        else:
            self._requests[client_ip] = []
        
        # Check rate limit
        if len(self._requests[client_ip]) >= self.config.rate_limit_per_ip:
            raise HTTPException(
                status_code=429, 
                detail="Rate limit exceeded"
            )
        
        self._requests[client_ip].append(now)
        return await call_next(request)


def get_webhook_config() -> WebhookConfig:
    """Dependency to get webhook config. Override in tests."""
    # This will be overridden by the app
    return WebhookConfig()


async def verify_signature_dep(
    request: Request, 
    config: WebhookConfig = Depends(get_webhook_config)  # noqa: B008
) -> bool:
    """FastAPI dependency for signature verification."""
    return await verify_webhook_signature(request, config)