"""FastAPI webhook server for CamfrogAutoDJ.

This module provides a webhook API for controlling the AutoDJ engine remotely.
All FastAPI/uvicorn imports are lazy to avoid making them mandatory dependencies.
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    import uvicorn
    from fastapi import FastAPI

from camfrog_autodj.webhook.auth import (
    RateLimitMiddleware,
    RawBodyMiddleware,
    verify_signature_dep,
)
from camfrog_autodj.webhook.models import WebhookConfig

log = logging.getLogger("autodj.webhook")


# Request/Response models (defined at module level for FastAPI parameter detection)
class PlayRequest(BaseModel):
    query: str


class VolumeRequest(BaseModel):
    volume: int = Field(ge=0, le=100)


def _track_to_dict(track: Any) -> Optional[dict]:
    """Convert Track object or dict to dict."""
    if track is None:
        return None
    if isinstance(track, dict):
        return track
    # Assume it's a Track object with attributes
    return {
        "title": getattr(track, "title", str(track)),
        "dur": getattr(track, "dur", getattr(track, "duration", "?")),
        "requester": getattr(track, "requester", "Unknown"),
        "source": getattr(track, "source", ""),
    }


class WebhookAppState:
    """Holds the engine reference for the webhook app.

    This replaces the global variables with proper dependency injection
    via FastAPI's app.state mechanism.
    """

    def __init__(self, engine: Any, config: WebhookConfig):
        self.engine = engine
        self.config = config


def _create_base_app(config: WebhookConfig) -> "FastAPI":
    """Create the base FastAPI application with middleware.

    FastAPI is imported lazily here to avoid making it a mandatory dependency.
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    @asynccontextmanager
    async def lifespan(app: "FastAPI"):
        # Startup
        log.info("Webhook server starting on %s:%d", config.host, config.port)
        yield
        # Shutdown
        log.info("Webhook server shutting down")

    app = FastAPI(
        title="CamfrogAutoDJ Webhook API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/webhook/docs" if config.enabled else None,
        redoc_url=None,
    )

    # Store config and engine in app.state for dependency injection
    app.state.webhook_state = WebhookAppState(None, config)

    # Raw body capture middleware (MUST be first to capture body before parsing)
    app.add_middleware(RawBodyMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # Rate limiting middleware
    app.add_middleware(RateLimitMiddleware, config=config)

    return app


def _add_health_endpoint(app: "FastAPI"):
    """Add health check endpoint."""
    from fastapi import HTTPException

    @app.get("/webhook/health")
    async def health():
        state = app.state.webhook_state
        if not state.config.enabled:
            raise HTTPException(status_code=404, detail="Webhook disabled")
        return {
            "status": "healthy",
            "engine": state.engine is not None,
            "version": "1.0.0",
        }


def _add_metrics_endpoint(app: "FastAPI"):
    """Add Prometheus metrics endpoint."""
    from fastapi import HTTPException, Response

    @app.get("/webhook/metrics")
    async def metrics():
        state = app.state.webhook_state
        if not state.config.enabled:
            raise HTTPException(status_code=404, detail="Webhook disabled")

        if state.engine is None:
            return Response(content="# Engine not available\n", media_type="text/plain")

        try:
            health = state.engine.health_check()
            lines = [
                f"autodj_health_ok {1 if health['ok'] else 0}",
                f"autodj_mpv_available {1 if health['checks'].get('mpv', {}).get('ok', False) else 0}",
                f"autodj_circuit_breaker_open {1 if not health['checks'].get('circuit_breaker', {}).get('ok', True) else 0}",
                f"autodj_circuit_breaker_failures {health['checks'].get('circuit_breaker', {}).get('failures', 0)}",
                f"autodj_chat_send_suspended {1 if not health['checks'].get('chat_send', {}).get('ok', True) else 0}",
                f"autodj_queue_requests {health['checks'].get('queue', {}).get('requests', 0)}",
                f"autodj_queue_pool {health['checks'].get('queue', {}).get('pool', 0)}",
                f"autodj_im_entries {health['checks'].get('im_viewer', {}).get('entries', 0)}",
            ]
            return Response(content="\n".join(lines) + "\n", media_type="text/plain")
        except Exception as ex:
            log.exception("Failed to generate metrics")
            return Response(
                content=f"# Error generating metrics: {ex}\n",
                media_type="text/plain",
                status_code=500,
            )


def _add_playback_endpoints(app: "FastAPI"):
    """Add playback control endpoints."""
    _add_play_endpoint(app)
    _add_skip_endpoint(app)
    _add_volume_endpoint(app)


def _add_play_endpoint(app: "FastAPI"):
    """Add /webhook/play endpoint."""
    from fastapi import Depends, HTTPException

    auth_dep = Depends(verify_signature_dep)

    @app.post("/webhook/play")
    async def play_track(body: PlayRequest, _: bool = auth_dep):
        """Queue a track for playback. Body: {"query": "song name or URL"}"""
        state = app.state.webhook_state
        if not state.engine:
            raise HTTPException(status_code=503, detail="Engine not available")

        query = body.query.strip()
        if not query:
            raise HTTPException(status_code=400, detail="Missing query parameter")

        state.engine.request(query, user="webhook")
        return {"status": "queued", "query": query}


def _add_skip_endpoint(app: "FastAPI"):
    """Add /webhook/skip endpoint."""
    from fastapi import Depends, HTTPException

    auth_dep = Depends(verify_signature_dep)

    @app.post("/webhook/skip")
    async def skip_track(_: bool = auth_dep):
        """Skip the currently playing track."""
        state = app.state.webhook_state
        if not state.engine:
            raise HTTPException(status_code=503, detail="Engine not available")
        state.engine.skip()
        return {"status": "skipped"}


def _add_volume_endpoint(app: "FastAPI"):
    """Add /webhook/volume endpoint."""
    from fastapi import Depends, HTTPException

    auth_dep = Depends(verify_signature_dep)

    @app.post("/webhook/volume")
    async def set_volume(body: VolumeRequest, _: bool = auth_dep):
        """Set playback volume. Body: {"volume": 50}"""
        state = app.state.webhook_state
        if not state.engine:
            raise HTTPException(status_code=503, detail="Engine not available")

        vol = body.volume
        state.engine.set_volume(vol)
        return {"status": "ok", "volume": vol}


def _add_queue_endpoints(app: "FastAPI"):
    """Add queue and status endpoints."""
    from fastapi import Depends, HTTPException

    auth_dep = Depends(verify_signature_dep)

    @app.get("/webhook/status")
    async def get_status(_: bool = auth_dep):
        """Get current playback status."""
        state = app.state.webhook_state
        if not state.engine:
            raise HTTPException(status_code=503, detail="Engine not available")

        snap = state.engine.snapshot()
        current = _track_to_dict(snap.get("current"))
        next_track = _track_to_dict(snap.get("next"))

        return {
            "current": current.get("title") if current else None,
            "current_duration": current.get("dur") if current else None,
            "current_requester": current.get("requester") if current else None,
            "position": snap.get("position", 0),
            "paused": snap.get("paused", False),
            "volume": snap.get("volume", 0),
            "queue_length": len(snap.get("queue", [])),
            "next": {
                "title": next_track.get("title"),
                "duration": next_track.get("dur"),
                "requester": next_track.get("requester"),
            }
            if next_track
            else None,
            "shuffle": snap.get("shuffle", False),
            "repeat": snap.get("repeat", "off"),
        }

    @app.get("/webhook/queue")
    async def get_queue(_: bool = auth_dep):
        """Get the current queue."""
        state = app.state.webhook_state
        if not state.engine:
            raise HTTPException(status_code=503, detail="Engine not available")

        snap = state.engine.snapshot()
        queue = snap.get("queue", [])
        next_track = snap.get("next")

        return {
            "queue": [_track_to_dict(t) for t in queue],
            "next": _track_to_dict(next_track) if next_track else None,
        }

    @app.get("/webhook/history")
    async def get_history(_: bool = auth_dep):
        """Get playback history."""
        state = app.state.webhook_state
        if not state.engine:
            raise HTTPException(status_code=503, detail="Engine not available")

        snap = state.engine.snapshot()
        history = snap.get("history", [])

        return {"history": [_track_to_dict(t) for t in history]}


def _add_control_endpoints(app: "FastAPI"):
    """Add playback control endpoints (pause, resume, shuffle, repeat)."""
    _add_pause_endpoint(app)
    _add_resume_endpoint(app)
    _add_shuffle_endpoint(app)
    _add_repeat_endpoint(app)


def _add_pause_endpoint(app: "FastAPI"):
    """Add /webhook/pause endpoint."""
    from fastapi import Depends, HTTPException

    auth_dep = Depends(verify_signature_dep)

    @app.post("/webhook/pause")
    async def pause_playback(_: bool = auth_dep):
        """Pause playback."""
        state = app.state.webhook_state
        if not state.engine:
            raise HTTPException(status_code=503, detail="Engine not available")
        state.engine.pause()
        return {"status": "paused"}


def _add_resume_endpoint(app: "FastAPI"):
    """Add /webhook/resume endpoint."""
    from fastapi import Depends, HTTPException

    auth_dep = Depends(verify_signature_dep)

    @app.post("/webhook/resume")
    async def resume_playback(_: bool = auth_dep):
        """Resume playback."""
        state = app.state.webhook_state
        if not state.engine:
            raise HTTPException(status_code=503, detail="Engine not available")
        state.engine.resume()
        return {"status": "resumed"}


def _add_shuffle_endpoint(app: "FastAPI"):
    """Add /webhook/shuffle endpoint."""
    from fastapi import Depends, HTTPException, Request

    auth_dep = Depends(verify_signature_dep)

    @app.post("/webhook/shuffle")
    async def set_shuffle(request: Request, _: bool = auth_dep):
        """Toggle shuffle mode. Body: {"enabled": true}"""
        state = app.state.webhook_state
        if not state.engine:
            raise HTTPException(status_code=503, detail="Engine not available")

        try:
            data = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON") from None

        enabled = data.get("enabled", True)
        state.engine.queue.set_shuffle(enabled)
        return {"status": "ok", "shuffle": enabled}


def _add_repeat_endpoint(app: "FastAPI"):
    """Add /webhook/repeat endpoint."""
    from fastapi import Depends, HTTPException, Request

    auth_dep = Depends(verify_signature_dep)

    @app.post("/webhook/repeat")
    async def set_repeat(request: Request, _: bool = auth_dep):
        """Set repeat mode. Body: {"mode": "off" | "one"}"""
        state = app.state.webhook_state
        if not state.engine:
            raise HTTPException(status_code=503, detail="Engine not available")

        try:
            data = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON") from None

        mode = data.get("mode", "off")
        if mode not in ("off", "one"):
            raise HTTPException(status_code=400, detail="Mode must be 'off' or 'one'")

        state.engine.queue.repeat = mode
        return {"status": "ok", "repeat": mode}


def _add_chat_endpoints(app: "FastAPI"):
    """Add chat/say endpoints."""
    from fastapi import Depends, HTTPException, Request

    auth_dep = Depends(verify_signature_dep)

    @app.post("/webhook/say")
    async def say_message(request: Request, _: bool = auth_dep):
        """Send a message to the chat room. Body: {"text": "message to send"}"""
        state = app.state.webhook_state
        if not state.engine:
            raise HTTPException(status_code=503, detail="Engine not available")

        try:
            data = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON") from None

        text = data.get("text", "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="Missing text parameter")

        state.engine.say(text)
        return {"status": "sent"}


def _add_exception_handlers(app: "FastAPI"):
    """Add global exception handlers for clean error responses."""
    from fastapi import HTTPException, Request
    from fastapi.responses import JSONResponse

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        log.exception("Unhandled webhook error")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "status_code": 500},
        )


def create_webhook_app(config: WebhookConfig, engine: Any = None) -> "FastAPI":
    """Create the FastAPI webhook application.

    Args:
        config: Webhook configuration
        engine: Engine instance for controlling playback (optional)

    Returns:
        Configured FastAPI app
    """
    app = _create_base_app(config)

    # Set engine in app.state
    app.state.webhook_state.engine = engine
    app.state.webhook_state.config = config

    # Add all endpoints
    _add_health_endpoint(app)
    _add_metrics_endpoint(app)
    _add_playback_endpoints(app)
    _add_queue_endpoints(app)
    _add_control_endpoints(app)
    _add_chat_endpoints(app)
    _add_exception_handlers(app)

    return app


class WebhookServer:
    """Async webhook server wrapper."""

    def __init__(self, config: WebhookConfig, engine: Any):
        self.config = config
        self.engine = engine
        self._app = create_webhook_app(config, engine)
        self._server: "uvicorn.Server | None" = None
        self._task: Any = None

    async def start(self):
        """Start the webhook server."""
        if not self.config.enabled:
            return

        import asyncio

        import uvicorn

        config = uvicorn.Config(
            self._app,
            host=self.config.host,
            port=self.config.port,
            log_level="info",
            access_log=False,
        )
        self._server = uvicorn.Server(config)
        self._task = asyncio.create_task(self._server.serve())

    async def stop(self):
        """Stop the webhook server."""
        if self._server:
            self._server.should_exit = True
        if self._task:
            await self._task
            self._task = None
        self._server = None

    @property
    def is_running(self) -> bool:
        return self._server is not None and not self._server.should_exit
