"""Probe account login manager for social network platforms.

Handles OAuth2 login flows, token refresh, and credential rotation for
YouTube, TikTok, and Facebook probe accounts.

Ported patterns from cvsz/streamdbc auth/manager.go - stream-scoped auth
with JWT tokens and API keys - adapted to Python for probe account login.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import requests

from .probe_account import ProbeAccount, ProbeAccountStore

log = logging.getLogger("autodj.stream.probe_login")


class ProbeLoginError(Exception):
    """Probe account login error."""


class ProbeLoginManager:
    """Manages probe account login and token refresh for social platforms.

    Supports:
    - OAuth2 authorization code flow (YouTube, Facebook)
    - Password-based login (TikTok via unofficial client)
    - Token refresh when access tokens expire
    - Account rotation when locked
    """

    def __init__(self, store: ProbeAccountStore) -> None:
        self.store = store
        self._sessions: dict[str, requests.Session] = {}

    # ------------------------------------------------------------------
    # YouTube OAuth2 login
    # ------------------------------------------------------------------
    def login_youtube(
        self,
        username: str,
        client_id: str,
        client_secret: str,
        refresh_token: str | None = None,
    ) -> ProbeAccount:
        """Login to YouTube via OAuth2.

        If refresh_token is provided, refresh the access token.
        Otherwise, return instructions for the user to complete the
        authorization code flow manually.
        """
        acct = self.store.get("youtube", username)
        if not acct:
            acct = ProbeAccount(
                platform="youtube",
                username=username,
                client_id=client_id,
                client_secret=client_secret,
            )

        if refresh_token:
            acct.refresh_token = refresh_token
            self._refresh_youtube_token(acct)
        elif acct.refresh_token and acct.is_token_expired():
            self._refresh_youtube_token(acct)

        acct.record_login_success()
        self.store.add(acct)
        log.info("YouTube probe account logged in: %s", username)
        return acct

    def _refresh_youtube_token(self, acct: ProbeAccount) -> None:
        """Refresh YouTube OAuth2 access token."""
        # OAuth2 token endpoint URL, not a secret
        token_url = "https://oauth2.googleapis.com/token"  # noqa: S105  # nosec B105
        data = {
            "client_id": acct.client_id,
            "client_secret": acct.client_secret,
            "refresh_token": acct.refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            resp = requests.post(token_url, data=data, timeout=15)
            resp.raise_for_status()
            token_data = resp.json()
            acct.access_token = token_data["access_token"]
            acct.token_expires_at = time.time() + token_data.get("expires_in", 3600)
            log.info("YouTube token refreshed for %s", acct.username)
        except Exception as exc:  # noqa: BLE001
            acct.record_login_failure()
            raise ProbeLoginError(f"YouTube token refresh failed: {exc}") from exc

    def get_youtube_access_token(self, username: str) -> str:
        """Get a valid YouTube access token for a probe account, refreshing if needed."""
        acct = self.store.get("youtube", username)
        if not acct:
            raise ProbeLoginError(f"YouTube probe account not found: {username}")
        if acct.is_locked():
            raise ProbeLoginError(f"YouTube probe account locked: {username}")
        if acct.is_token_expired():
            self._refresh_youtube_token(acct)
            self.store.add(acct)
        return acct.access_token

    # ------------------------------------------------------------------
    # Facebook OAuth2 login
    # ------------------------------------------------------------------
    def login_facebook(
        self,
        username: str,
        client_id: str,
        client_secret: str,
        access_token: str | None = None,
        refresh_token: str | None = None,
    ) -> ProbeAccount:
        """Login to Facebook via OAuth2 access token."""
        acct = self.store.get("facebook", username)
        if not acct:
            acct = ProbeAccount(
                platform="facebook",
                username=username,
                client_id=client_id,
                client_secret=client_secret,
            )

        if access_token:
            acct.access_token = access_token
            acct.token_expires_at = time.time() + 3600  # Default 1 hour
        if refresh_token:
            acct.refresh_token = refresh_token

        # Validate the token by querying the Graph API
        self._validate_facebook_token(acct)

        acct.record_login_success()
        self.store.add(acct)
        log.info("Facebook probe account logged in: %s", username)
        return acct

    def _validate_facebook_token(self, acct: ProbeAccount) -> None:
        """Validate a Facebook access token by querying /me."""
        if not acct.access_token:
            raise ProbeLoginError("Facebook access token is empty")
        try:
            resp = requests.get(
                "https://graph.facebook.com/me",
                params={"access_token": acct.access_token, "fields": "id,name"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise ProbeLoginError(f"Facebook token invalid: {data['error']}")
            log.info("Facebook token validated for %s (%s)", acct.username, data.get("name"))
        except ProbeLoginError:
            raise
        except Exception as exc:  # noqa: BLE001
            acct.record_login_failure()
            raise ProbeLoginError(f"Facebook token validation failed: {exc}") from exc

    def get_facebook_access_token(self, username: str) -> str:
        """Get a valid Facebook access token."""
        acct = self.store.get("facebook", username)
        if not acct:
            raise ProbeLoginError(f"Facebook probe account not found: {username}")
        if acct.is_locked():
            raise ProbeLoginError(f"Facebook probe account locked: {username}")
        return acct.access_token

    # ------------------------------------------------------------------
    # TikTok login (via unofficial client session)
    # ------------------------------------------------------------------
    def login_tiktok(
        self,
        username: str,
        password: str,
        room_id: str | None = None,
    ) -> ProbeAccount:
        """Login to TikTok via probe account credentials.

        TikTok doesn't have a public OAuth2 API for chat, so this stores
        credentials for use with the TikTokLive unofficial client.
        The actual login happens client-side when TikTokLiveClient connects.
        """
        acct = self.store.get("tiktok", username)
        if not acct:
            acct = ProbeAccount(
                platform="tiktok",
                username=username,
                room_id=room_id or "",
            )

        acct.password = password
        if room_id:
            acct.room_id = room_id

        # Mark as attempted - actual login verified on connect
        acct.record_login_success()
        self.store.add(acct)
        log.info("TikTok probe account credentials stored: %s", username)
        return acct

    def get_tiktok_credentials(self, username: str) -> tuple[str, str]:
        """Get TikTok probe account credentials (username, password)."""
        acct = self.store.get("tiktok", username)
        if not acct:
            raise ProbeLoginError(f"TikTok probe account not found: {username}")
        if acct.is_locked():
            raise ProbeLoginError(f"TikTok probe account locked: {username}")
        return acct.username, acct.password

    # ------------------------------------------------------------------
    # Account rotation
    # ------------------------------------------------------------------
    def rotate_account(self, platform: str) -> Optional[ProbeAccount]:
        """Rotate to the next available active account for a platform."""
        accounts = self.store.get_by_platform(platform)
        if not accounts:
            return None
        # Return the first non-locked account with the fewest failures
        available = [a for a in accounts if not a.is_locked()]
        if not available:
            log.warning("All probe accounts locked for %s", platform)
            return None
        available.sort(key=lambda a: a.login_failure_count)
        return available[0]

    def get_session(self, platform: str, username: str) -> requests.Session:
        """Get or create an HTTP session for a probe account."""
        key = f"{platform}:{username}"
        if key not in self._sessions:
            session = requests.Session()
            session.headers.update({"User-Agent": "AutoDJ/0.4.0 (probe-account)"})
            self._sessions[key] = session
        return self._sessions[key]


class ProbeAccountLoginUI:
    """Helper to generate login URLs and instructions for users."""

    @staticmethod
    def youtube_auth_url(client_id: str, redirect_uri: str) -> str:
        """Generate YouTube OAuth2 authorization URL."""
        from urllib.parse import urlencode

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "https://www.googleapis.com/auth/youtube.force-ssl",
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
        }
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)

    @staticmethod
    def facebook_auth_url(client_id: str, redirect_uri: str) -> str:
        """Generate Facebook OAuth2 authorization URL."""
        from urllib.parse import urlencode

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "public_profile,pages_show_list,pages_read_engagement",
            "response_type": "code",
        }
        return "https://www.facebook.com/v18.0/dialog/oauth?" + urlencode(params)

    @staticmethod
    def print_login_instructions(platform: str, client_id: str, redirect_uri: str) -> None:
        """Print login instructions for a platform."""
        if platform == "youtube":
            url = ProbeAccountLoginUI.youtube_auth_url(client_id, redirect_uri)
            print("\n" + "=" * 60)
            print("YouTube Probe Account Login")
            print("=" * 60)
            print("1. Open this URL in a browser:")
            print(f"   {url}")
            print("2. Sign in with the probe account and authorize AutoDJ")
            print("3. Copy the authorization code from the redirect URL")
            print("4. Exchange the code for tokens using the token endpoint")
            print("=" * 60 + "\n")
        elif platform == "facebook":
            url = ProbeAccountLoginUI.facebook_auth_url(client_id, redirect_uri)
            print("\n" + "=" * 60)
            print("Facebook Probe Account Login")
            print("=" * 60)
            print("1. Open this URL in a browser:")
            print(f"   {url}")
            print("2. Sign in with the probe account and authorize AutoDJ")
            print("3. Copy the authorization code from the redirect URL")
            print("4. Exchange the code for a page access token")
            print("=" * 60 + "\n")
