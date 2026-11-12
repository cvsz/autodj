"""Webhook configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class WebhookConfig:
    """Configuration for the webhook server."""

    enabled: bool = False
    port: int = 8080
    secret: str = ""  # HMAC secret for signature verification
    host: str = "127.0.0.1"
    rate_limit_per_ip: int = 60  # requests per minute
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
