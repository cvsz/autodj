"""FastAPI webhook server for CamfrogAutoDJ."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from camfrog_autodj.webhook.auth import (
    RateLimitMiddleware,
    get_webhook_config,
    verify_signature_dep,
)
from camfrog_autodj.webhook.models import WebhookConfig

if TYPE_CHECKING:
    import asyncio
    from typing import Any

    import uvicorn

# Global references for the running server
_engine = None
_config: Optional[WebhookConfig] = None


def _track_to_dict(track) -> Optional[dict]:
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


def _create_base_app(config: WebhookConfig) -> FastAPI:
    """Create the base FastAPI application with middleware."""
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
    
    app = FastAPI(
        title="CamfrogAutoDJ Webhook API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/webhook/docs" if config.enabled else None,
        redoc_url=None,
    )
    
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
    
    # Override config dependency
    def _get_config() -> WebhookConfig:
        return config
    
    app.dependency_overrides[get_webhook_config] = _get_config
    
    return app


def _add_health_endpoint(app: FastAPI):
    """Add health check endpoint."""
    @app.get("/webhook/health")
    async def health():
        if _config is None or not _config.enabled:
            raise HTTPException(status_code=404, detail="Webhook disabled")
        return {
            "status": "healthy",
            "engine": _engine is not None,
            "version": "1.0.0",
        }


def _add_playback_endpoints(app: FastAPI):
    """Add playback control endpoints."""
    _add_play_endpoint(app)
    _add_skip_endpoint(app)
    _add_volume_endpoint(app)


def _add_play_endpoint(app: FastAPI):
    """Add /webhook/play endpoint."""
    auth_dep = Depends(verify_signature_dep)
    
    @app.post("/webhook/play")
    async def play_track(request: Request, _: bool = auth_dep):
        """Queue a track for playback. Body: {"query": "song name or URL"}"""
        if not _engine:
            raise HTTPException(status_code=503, detail="Engine not available")
        
        try:
            data = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON") from None
        
        query = data.get("query", "").strip()
        if not query:
            raise HTTPException(status_code=400, detail="Missing query parameter")
        
        _engine.request(query, user="webhook")
        return {"status": "queued", "query": query}


def _add_skip_endpoint(app: FastAPI):
    """Add /webhook/skip endpoint."""
    auth_dep = Depends(verify_signature_dep)
    
    @app.post("/webhook/skip")
    async def skip_track(_: bool = auth_dep):
        """Skip the currently playing track."""
        if not _engine:
            raise HTTPException(status_code=503, detail="Engine not available")
        _engine.skip()
        return {"status": "skipped"}


def _add_volume_endpoint(app: FastAPI):
    """Add /webhook/volume endpoint."""
    auth_dep = Depends(verify_signature_dep)
    
    @app.post("/webhook/volume")
    async def set_volume(request: Request, _: bool = auth_dep):
        """Set playback volume. Body: {"volume": 50}"""
        if not _engine:
            raise HTTPException(status_code=503, detail="Engine not available")
        
        try:
            data = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON") from None
        
        vol = data.get("volume")
        if vol is None:
            raise HTTPException(status_code=400, detail="Missing volume parameter")
        
        try:
            vol = int(vol)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Volume must be an integer") from None
        
        vol = max(0, min(100, vol))
        _engine.set_volume(vol)
        return {"status": "ok", "volume": vol}


def _add_queue_endpoints(app: FastAPI):
    """Add queue and status endpoints."""
    auth_dep = Depends(verify_signature_dep)
    
    @app.get("/webhook/status")
    async def get_status(_: bool = auth_dep):
        """Get current playback status."""
        if not _engine:
            raise HTTPException(status_code=503, detail="Engine not available")
        
        snap = _engine.snapshot()
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
            } if next_track else None,
            "shuffle": snap.get("shuffle", False),
            "repeat": snap.get("repeat", "off"),
        }
    
    @app.get("/webhook/queue")
    async def get_queue(_: bool = auth_dep):
        """Get the current queue."""
        if not _engine:
            raise HTTPException(status_code=503, detail="Engine not available")
        
        snap = _engine.snapshot()
        queue = snap.get("queue", [])
        next_track = snap.get("next")
        
        return {
            "queue": [_track_to_dict(t) for t in queue],
            "next": _track_to_dict(next_track) if next_track else None,
        }
    
    @app.get("/webhook/history")
    async def get_history(_: bool = auth_dep):
        """Get playback history."""
        if not _engine:
            raise HTTPException(status_code=503, detail="Engine not available")
        
        snap = _engine.snapshot()
        history = snap.get("history", [])
        
        return {"history": [_track_to_dict(t) for t in history]}


def _add_control_endpoints(app: FastAPI):
    """Add playback control endpoints (pause, resume, shuffle, repeat)."""
    _add_pause_endpoint(app)
    _add_resume_endpoint(app)
    _add_shuffle_endpoint(app)
    _add_repeat_endpoint(app)


def _add_pause_endpoint(app: FastAPI):
    """Add /webhook/pause endpoint."""
    auth_dep = Depends(verify_signature_dep)
    
    @app.post("/webhook/pause")
    async def pause_playback(_: bool = auth_dep):
        """Pause playback."""
        if not _engine:
            raise HTTPException(status_code=503, detail="Engine not available")
        _engine.pause()
        return {"status": "paused"}


def _add_resume_endpoint(app: FastAPI):
    """Add /webhook/resume endpoint."""
    auth_dep = Depends(verify_signature_dep)
    
    @app.post("/webhook/resume")
    async def resume_playback(_: bool = auth_dep):
        """Resume playback."""
        if not _engine:
            raise HTTPException(status_code=503, detail="Engine not available")
        _engine.resume()
        return {"status": "resumed"}


def _add_shuffle_endpoint(app: FastAPI):
    """Add /webhook/shuffle endpoint."""
    auth_dep = Depends(verify_signature_dep)
    
    @app.post("/webhook/shuffle")
    async def set_shuffle(request: Request, _: bool = auth_dep):
        """Toggle shuffle mode. Body: {"enabled": true}"""
        if not _engine:
            raise HTTPException(status_code=503, detail="Engine not available")
        
        try:
            data = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON") from None
        
        enabled = data.get("enabled", True)
        _engine.queue.set_shuffle(enabled)
        return {"status": "ok", "shuffle": enabled}


def _add_repeat_endpoint(app: FastAPI):
    """Add /webhook/repeat endpoint."""
    auth_dep = Depends(verify_signature_dep)
    
    @app.post("/webhook/repeat")
    async def set_repeat(request: Request, _: bool = auth_dep):
        """Set repeat mode. Body: {"mode": "off" | "one"}"""
        if not _engine:
            raise HTTPException(status_code=503, detail="Engine not available")
        
        try:
            data = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON") from None
        
        mode = data.get("mode", "off")
        if mode not in ("off", "one"):
            raise HTTPException(status_code=400, detail="Mode must be 'off' or 'one'")
        
        _engine.queue.repeat = mode
        return {"status": "ok", "repeat": mode}


def _add_chat_endpoints(app: FastAPI):
    """Add chat/say endpoints."""
    auth_dep = Depends(verify_signature_dep)
    
    @app.post("/webhook/say")
    async def say_message(request: Request, _: bool = auth_dep):
        """Send a message to the chat room. Body: {"text": "message to send"}"""
        if not _engine:
            raise HTTPException(status_code=503, detail="Engine not available")
        
        try:
            data = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON") from None
        
        text = data.get("text", "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="Missing text parameter")
        
        _engine.say(text)
        return {"status": "sent"}


def _add_exception_handlers(app: FastAPI):
    """Add global exception handlers for clean error responses."""
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code},
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logging.getLogger("autodj.webhook").exception("Unhandled webhook error")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "status_code": 500},
        )


def create_webhook_app(config: WebhookConfig, engine=None) -> FastAPI:
    """Create the FastAPI webhook application.
    
    Args:
        config: Webhook configuration
        engine: Engine instance for controlling playback (optional)
        
    Returns:
        Configured FastAPI app
    """
    global _engine, _config
    _engine = engine
    _config = config
    
    app = _create_base_app(config)
    
    # Add all endpoints
    _add_health_endpoint(app)
    _add_playback_endpoints(app)
    _add_queue_endpoints(app)
    _add_control_endpoints(app)
    _add_chat_endpoints(app)
    _add_exception_handlers(app)
    
    return app


class WebhookServer:
    """Async webhook server wrapper."""
    
    def __init__(self, config: WebhookConfig, engine):
        self.config = config
        self.engine = engine
        self._app = create_webhook_app(config, engine)
        self._server: "uvicorn.Server | None" = None
        self._task: "asyncio.Task[Any] | None" = None
    
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