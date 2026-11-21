"""Probe account management for social network connectors.

Handles secure storage, retrieval, and rotation of probe account credentials
used to connect to social platforms (YouTube, TikTok, Facebook, etc.).

Probe accounts are real user accounts that AutoDJ uses to:
- Read live chat/comments from social platforms
- Post responses back to the platform
- Monitor stream status and health

Credentials are stored encrypted and can be rotated without restarting.
"""

from __future__ import annotations

import base64
import json
import logging
import threading
import time
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

log = logging.getLogger("autodj.stream.probe_account")


@dataclass
class ProbeAccount:
    """A probe account for connecting to a social platform."""

    platform: str  # youtube | tiktok | facebook | camfrog
    username: str
    email: str = ""
    password: str = ""  # encrypted at rest
    access_token: str = ""  # OAuth2 access token
    refresh_token: str = ""  # OAuth2 refresh token
    token_expires_at: float = 0.0  # unix timestamp
    client_id: str = ""  # OAuth2 client ID
    client_secret: str = ""  # OAuth2 client secret
    api_key: str = ""  # Platform API key
    room_id: str = ""  # Platform-specific room/channel ID
    channel_id: str = ""  # YouTube channel ID
    page_id: str = ""  # Facebook page ID
    is_active: bool = True
    last_login: float = 0.0
    login_failure_count: int = 0
    max_login_failures: int = 5
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def is_token_expired(self) -> bool:
        """Check if the OAuth2 access token is expired."""
        if not self.access_token:
            return True
        if self.token_expires_at <= 0:
            return False
        return time.time() >= self.token_expires_at

    def is_locked(self) -> bool:
        """Check if the account is locked due to too many login failures."""
        return self.login_failure_count >= self.max_login_failures

    def record_login_success(self) -> None:
        """Record a successful login."""
        self.last_login = time.time()
        self.login_failure_count = 0
        self.updated_at = time.time()

    def record_login_failure(self) -> None:
        """Record a failed login attempt."""
        self.login_failure_count += 1
        self.updated_at = time.time()

    def to_dict(self) -> dict:
        """Serialize to dict for storage."""
        return {
            "platform": self.platform,
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_expires_at": self.token_expires_at,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "api_key": self.api_key,
            "room_id": self.room_id,
            "channel_id": self.channel_id,
            "page_id": self.page_id,
            "is_active": self.is_active,
            "last_login": self.last_login,
            "login_failure_count": self.login_failure_count,
            "max_login_failures": self.max_login_failures,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProbeAccount":
        """Deserialize from dict."""
        field_names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in field_names})


class ProbeAccountStore:
    """Encrypted storage for probe account credentials.

    Uses Fernet symmetric encryption to protect credentials at rest.
    The encryption key is derived from a passphrase or read from a key file.
    """

    def __init__(self, store_path: str | Path, passphrase: str | None = None) -> None:
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._fernet = self._init_fernet(passphrase)
        self._accounts: dict[str, ProbeAccount] = {}
        self._load()

    def _init_fernet(self, passphrase: str | None) -> Fernet:
        """Initialize Fernet encryption from passphrase or key file."""
        key_file = self.store_path.with_suffix(".key")
        if key_file.exists():
            key = key_file.read_bytes()
        elif passphrase:
            # Derive key from passphrase using PBKDF2
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

            salt = b"autodj-probe-account-salt"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
            key_file.write_bytes(key)
            key_file.chmod(0o600)
        else:
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            key_file.chmod(0o600)
        return Fernet(key)

    def _encrypt(self, value: str) -> str:
        if not value:
            return ""
        return self._fernet.encrypt(value.encode()).decode()

    def _decrypt(self, value: str) -> str:
        if not value:
            return ""
        return self._fernet.decrypt(value.encode()).decode()

    def _load(self) -> None:
        """Load accounts from disk."""
        if not self.store_path.exists():
            return
        try:
            data = json.loads(self.store_path.read_text(encoding="utf-8"))
            for key, acct_data in data.items():
                acct = ProbeAccount.from_dict(acct_data)
                # Decrypt sensitive fields
                acct.password = self._decrypt(acct.password)
                acct.access_token = self._decrypt(acct.access_token)
                acct.refresh_token = self._decrypt(acct.refresh_token)
                acct.client_secret = self._decrypt(acct.client_secret)
                acct.api_key = self._decrypt(acct.api_key)
                self._accounts[key] = acct
            log.info("Loaded %d probe accounts from %s", len(self._accounts), self.store_path)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to load probe accounts: %s", exc)

    def save(self) -> None:
        """Save accounts to disk (encrypted)."""
        with self._lock:
            data = {}
            for key, acct in self._accounts.items():
                d = acct.to_dict()
                # Encrypt sensitive fields before storage
                d["password"] = self._encrypt(acct.password)
                d["access_token"] = self._encrypt(acct.access_token)
                d["refresh_token"] = self._encrypt(acct.refresh_token)
                d["client_secret"] = self._encrypt(acct.client_secret)
                d["api_key"] = self._encrypt(acct.api_key)
                data[key] = d
            tmp = self.store_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(self.store_path)
            log.debug("Saved %d probe accounts to %s", len(self._accounts), self.store_path)

    def add(self, account: ProbeAccount) -> None:
        """Add or update a probe account."""
        with self._lock:
            key = f"{account.platform}:{account.username}"
            account.updated_at = time.time()
            self._accounts[key] = account
            self.save()

    def get(self, platform: str, username: str) -> Optional[ProbeAccount]:
        """Get a probe account by platform and username."""
        with self._lock:
            return self._accounts.get(f"{platform}:{username}")

    def get_by_platform(self, platform: str) -> list[ProbeAccount]:
        """Get all probe accounts for a platform."""
        with self._lock:
            return [
                acct
                for key, acct in self._accounts.items()
                if key.startswith(f"{platform}:") and acct.is_active
            ]

    def list_all(self) -> list[ProbeAccount]:
        """List all probe accounts."""
        with self._lock:
            return list(self._accounts.values())

    def remove(self, platform: str, username: str) -> bool:
        """Remove a probe account."""
        with self._lock:
            key = f"{platform}:{username}"
            if key in self._accounts:
                del self._accounts[key]
                self.save()
                return True
            return False

    def mark_login_success(self, platform: str, username: str) -> None:
        """Mark a successful login for an account."""
        with self._lock:
            acct = self._accounts.get(f"{platform}:{username}")
            if acct:
                acct.record_login_success()
                self.save()

    def mark_login_failure(self, platform: str, username: str) -> None:
        """Mark a failed login for an account."""
        with self._lock:
            acct = self._accounts.get(f"{platform}:{username}")
            if acct:
                acct.record_login_failure()
                self.save()

    def get_active_account(self, platform: str) -> Optional[ProbeAccount]:
        """Get the first active, non-locked account for a platform."""
        accounts = self.get_by_platform(platform)
        for acct in accounts:
            if acct.is_active and not acct.is_locked():
                return acct
        return None
