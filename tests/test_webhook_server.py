"""Tests for webhook server."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from camfrog_autodj.webhook.models import WebhookConfig
from camfrog_autodj.webhook.server import WebhookServer, create_webhook_app


def _signed(
    method: str, path: str, body: bytes = b"", secret: bytes = b"test-secret-key-12345"
) -> dict:
    """Headers for the timestamped HMAC scheme (see webhook.auth.signing_payload)."""
    ts = str(int(time.time()))
    msg = f"{ts}.{method}.{path}.".encode() + body
    return {"X-Timestamp": ts, "X-Signature": hmac.new(secret, msg, hashlib.sha256).hexdigest()}


class TestWebhookConfig:
    """Tests for WebhookConfig model."""

    def test_default_config(self):
        config = WebhookConfig()
        assert config.enabled is False
        assert config.port == 8080
        assert config.secret == ""
        assert config.host == "127.0.0.1"
        assert config.rate_limit_per_ip == 60
        assert config.cors_origins == ["*"]

    def test_custom_config(self):
        config = WebhookConfig(
            enabled=True,
            port=9000,
            secret="test-secret-key-12345",  # noqa: S106
            host="0.0.0.0",  # noqa: S104
            rate_limit_per_ip=100,
            cors_origins=["https://example.com"],
        )
        assert config.enabled is True
        assert config.port == 9000
        assert config.secret == "test-secret-key-12345"  # noqa: S105
        assert config.host == "0.0.0.0"  # noqa: S104
        assert config.rate_limit_per_ip == 100
        assert config.cors_origins == ["https://example.com"]


class TestWebhookServer:
    """Tests for webhook server endpoints."""

    def _make_client(self, config: WebhookConfig, engine=None):
        app = create_webhook_app(config, engine)
        return TestClient(app)

    def test_health_endpoint(self):
        config = WebhookConfig(enabled=True, secret="test-secret-key-12345")  # noqa: S106
        client = self._make_client(config)
        # Compute HMAC signature for GET request (empty body)
        hdr = _signed("GET", "/webhook/health", b"")
        response = client.get("/webhook/health", headers=hdr)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "engine" in data

    def test_play_endpoint_requires_auth(self):
        config = WebhookConfig(enabled=True, secret="test-secret-key-12345")  # noqa: S106
        client = self._make_client(config)
        response = client.post("/webhook/play", json={"query": "test song"})
        assert response.status_code == 401

    def test_play_endpoint_with_valid_hmac(self):
        config = WebhookConfig(enabled=True, secret="test-secret-key-12345")  # noqa: S106
        engine = Mock()
        client = self._make_client(config, engine)

        # TestClient sends JSON but FastAPI re-serializes to compact form (separators=(',', ':'))
        # Compute signature on the compact form that FastAPI actually receives
        payload = json.dumps({"query": "test song"}, separators=(",", ":")).encode()
        hdr = _signed("POST", "/webhook/play", payload)

        response = client.post("/webhook/play", json={"query": "test song"}, headers=hdr)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["query"] == "test song"
        engine.request.assert_called_once_with("test song", user="webhook")

    def test_play_endpoint_invalid_hmac(self):
        config = WebhookConfig(enabled=True, secret="test-secret-key-12345")  # noqa: S106
        client = self._make_client(config)

        response = client.post(
            "/webhook/play",
            json={"query": "test song"},
            headers={"X-Signature": "invalid-signature"},
        )
        assert response.status_code == 401

    def test_play_endpoint_missing_query(self):
        config = WebhookConfig(enabled=True, secret="test-secret-key-12345")  # noqa: S106
        engine = Mock()
        client = self._make_client(config, engine)

        payload = json.dumps({}, separators=(",", ":")).encode()
        hdr = _signed("POST", "/webhook/play", payload)

        response = client.post("/webhook/play", json={}, headers=hdr)
        # FastAPI returns 422 for validation errors (missing required field)
        assert response.status_code == 422
        data = response.json()
        assert data["detail"][0]["loc"] == ["body", "query"]

    def test_skip_endpoint(self):
        config = WebhookConfig(enabled=True, secret="test-secret-key-12345")  # noqa: S106
        engine = Mock()
        client = self._make_client(config, engine)

        payload = json.dumps({}, separators=(",", ":")).encode()
        hdr = _signed("POST", "/webhook/skip", payload)

        response = client.post("/webhook/skip", json={}, headers=hdr)
        assert response.status_code == 200
        engine.skip.assert_called_once()

    def test_volume_endpoint(self):
        config = WebhookConfig(enabled=True, secret="test-secret-key-12345")  # noqa: S106
        engine = Mock()
        client = self._make_client(config, engine)

        payload = json.dumps({"volume": 75}, separators=(",", ":")).encode()
        hdr = _signed("POST", "/webhook/volume", payload)

        response = client.post("/webhook/volume", json={"volume": 75}, headers=hdr)
        assert response.status_code == 200
        engine.set_volume.assert_called_once_with(75)

    def test_status_endpoint(self):
        config = WebhookConfig(enabled=True, secret="test-secret-key-12345")  # noqa: S106
        engine = Mock()
        engine.snapshot.return_value = {
            "current": {"title": "Test Song", "dur": "3:00", "requester": "user1"},
            "position": 45.0,
            "paused": False,
            "volume": 70,
            "queue": [],
            "next": None,
            "shuffle": False,
            "repeat": "off",
        }
        client = self._make_client(config, engine)

        # GET request with empty body
        payload = b""
        hdr = _signed("GET", "/webhook/status", payload)

        response = client.get("/webhook/status", headers=hdr)
        assert response.status_code == 200
        data = response.json()
        assert data["current"] == "Test Song"
        assert data["position"] == 45.0
        assert data["paused"] is False
        assert data["volume"] == 70

    def test_queue_endpoint(self):
        config = WebhookConfig(enabled=True, secret="test-secret-key-12345")  # noqa: S106
        engine = Mock()
        engine.snapshot.return_value = {
            "queue": [
                {
                    "title": "Song 1",
                    "dur": "3:00",
                    "requester": "user1",
                    "source": "url1",
                },
                {
                    "title": "Song 2",
                    "dur": "4:00",
                    "requester": "user2",
                    "source": "url2",
                },
            ],
            "next": {"title": "Next Song", "dur": "3:30", "requester": "user3"},
        }
        client = self._make_client(config, engine)

        # GET request with empty body
        payload = b""
        hdr = _signed("GET", "/webhook/queue", payload)

        response = client.get("/webhook/queue", headers=hdr)
        assert response.status_code == 200
        data = response.json()
        assert len(data["queue"]) == 2
        assert data["queue"][0]["title"] == "Song 1"
        assert data["next"]["title"] == "Next Song"

    def test_disabled_webhook_returns_404(self):
        config = WebhookConfig(enabled=False, secret="test-secret-key-12345")  # noqa: S106
        client = self._make_client(config)

        response = client.get("/webhook/health")
        assert response.status_code == 404

    def test_webhook_server_start_stop(self):
        config = WebhookConfig(enabled=True, secret="test-secret-key-12345", port=0)  # noqa: S106
        engine = Mock()
        server = WebhookServer(config, engine)

        # Server should be created
        assert server.config == config
        assert server.engine == engine
        assert server._app is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestWebhookSignatureHardening:
    """Replay / cross-endpoint / weak-secret protections."""

    SECRET = "test-secret-key-12345"  # noqa: S105

    def _client(self, engine=None, **kw):
        cfg = WebhookConfig(enabled=True, secret=kw.pop("secret", self.SECRET), **kw)
        return TestClient(create_webhook_app(cfg, engine))

    def test_replayed_signature_rejected(self):
        client = self._client(Mock())
        hdr = _signed("POST", "/webhook/skip", b"")
        assert client.post("/webhook/skip", headers=hdr).status_code == 200
        assert client.post("/webhook/skip", headers=hdr).status_code == 401

    def test_signature_not_valid_for_other_endpoint(self):
        client = self._client(Mock())
        hdr = _signed("GET", "/webhook/health", b"")
        assert client.post("/webhook/skip", headers=hdr).status_code == 401

    def test_stale_timestamp_rejected(self):
        client = self._client(Mock())
        ts = str(int(time.time()) - 3600)
        msg = f"{ts}.GET./webhook/health.".encode()
        sig = hmac.new(self.SECRET.encode(), msg, hashlib.sha256).hexdigest()
        r = client.get("/webhook/health", headers={"X-Timestamp": ts, "X-Signature": sig})
        assert r.status_code == 401

    def test_empty_secret_fails_closed(self):
        client = self._client(Mock(), secret="")
        hdr = _signed("GET", "/webhook/health", b"", secret=b"")
        assert client.get("/webhook/health", headers=hdr).status_code == 503

    def test_rate_limit_returns_429_not_500(self):
        client = self._client(Mock(), rate_limit_per_ip=2)
        codes = [client.get("/webhook/health").status_code for _ in range(3)]
        assert codes[-1] == 429
