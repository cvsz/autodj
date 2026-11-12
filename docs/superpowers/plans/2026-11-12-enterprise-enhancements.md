# Enterprise Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete all missing enterprise-grade features for CamfrogAutoDJ: Webhook/API integration, Plugin System, Performance Optimizations (persistent IPC, lock separation, batch cleanup), Enhanced Audit Logging, Dead Letter Queue, and documentation updates.

**Architecture:** Modular, clean architecture with clear separation of concerns. New components follow existing patterns (async-friendly, thread-safe, observable). All changes maintain backward compatibility and zero-downtime reload capability.

**Tech Stack:** Python 3.11+, FastAPI/Starlette (optional webhook), watchdog (hot reload), yt-dlp, mpv, pywinauto, tkinter (GUI)

**Spec:** 
- IMPLEMENTATION_PLAN_V2.md (Phases 3-10)
- PERFORMANCE_OPTIMIZATION_PLAN.md (Phases 1-4)
- AGENTS.md (project contract)

## Global Constraints

- Python >= 3.11 (required)
- All dependencies must have available type stubs or be ignored in mypy config
- No `shell=True` in subprocess (security)
- All file writes atomic (temp + replace + .bak)
- Config validation fail-closed with exact line + ^ marker
- Cross-platform: Windows primary, Linux headless supported
- No secrets committed (.env gitignored, .env.example only)
- GPG-signed commits required
- All tests must pass (pytest, ruff, mypy, shellcheck, compileall)
- Code coverage > 90% for new code

## Review Focus

1. **Webhook authentication bypass** - HMAC verification must be enforced on all webhook endpoints; test with invalid/empty signatures
2. **Plugin sandbox escape** - Plugins must not access engine internals beyond defined interface; test with malicious plugin
3. **IPC connection leak** - Persistent mpv IPC must be closed on track end, error, and shutdown; test with rapid track changes
4. **Audit log tampering** - Hash-chained audit log must detect modifications; test with corrupted log file
5. **Dead letter queue memory growth** - DLQ must have size limit and TTL; test with continuous failures

---

### Task 1: Webhook/API Integration - Core Server

**Files:**
- Create: `camfrog_autodj/webhook/server.py`
- Create: `camfrog_autodj/webhook/__init__.py`
- Create: `camfrog_autodj/webhook/models.py`
- Create: `camfrog_autodj/webhook/auth.py`
- Modify: `camfrog_autodj/config.py` (add webhook config fields)
- Test: `tests/test_webhook_server.py`

**Interfaces:**
- Consumes: `Engine` (for queue/playback control), `Config` (for webhook settings)
- Produces: `WebhookServer` class with `start()`, `stop()`, `health_check()` methods

- [ ] **Step 1: Write failing tests for webhook server**

```python
# tests/test_webhook_server.py
import pytest
from fastapi.testclient import TestClient
from camfrog_autodj.webhook.server import create_webhook_app
from camfrog_autodj.webhook.models import WebhookConfig

def test_webhook_health_endpoint():
    config = WebhookConfig(enabled=True, port=0, secret="test-secret")
    app = create_webhook_app(config, engine=None)
    client = TestClient(app)
    response = client.get("/webhook/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_webhook_play_endpoint_requires_auth():
    config = WebhookConfig(enabled=True, port=0, secret="test-secret")
    app = create_webhook_app(config, engine=None)
    client = TestClient(app)
    response = client.post("/webhook/play", json={"query": "test song"})
    assert response.status_code == 401  # Missing HMAC

def test_webhook_play_endpoint_with_valid_hmac():
    config = WebhookConfig(enabled=True, port=0, secret="test-secret")
    app = create_webhook_app(config, engine=None)
    client = TestClient(app)
    import hmac, hashlib
    payload = b'{"query": "test song"}'
    sig = hmac.new(b"test-secret", payload, hashlib.sha256).hexdigest()
    response = client.post("/webhook/play", json={"query": "test song"}, headers={"X-Signature": sig})
    assert response.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_webhook_server.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement webhook models and config**

Create `camfrog_autodj/webhook/models.py`:
```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class WebhookConfig:
    enabled: bool = False
    port: int = 8080
    secret: str = ""  # HMAC secret for signature verification
    host: str = "127.0.0.1"
    rate_limit_per_ip: int = 60  # requests per minute
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
```

Add to `camfrog_autodj/config.py`:
```python
# In Config dataclass, add:
webhook_enabled: bool = False
webhook_port: int = 8080
webhook_secret: str = ""
webhook_host: str = "127.0.0.1"
webhook_rate_limit_per_ip: int = 60
```

- [ ] **Step 4: Implement HMAC authentication**

Create `camfrog_autodj/webhook/auth.py`:
```python
import hmac
import hashlib
from fastapi import Request, HTTPException, Depends
from camfrog_autodj.webhook.models import WebhookConfig

async def verify_webhook_signature(request: Request, config: WebhookConfig):
    if not config.enabled:
        raise HTTPException(404, "Webhook disabled")
    signature = request.headers.get("X-Signature")
    if not signature:
        raise HTTPException(401, "Missing signature")
    body = await request.body()
    expected = hmac.new(config.secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(401, "Invalid signature")
    return True
```

- [ ] **Step 5: Implement FastAPI webhook server**

Create `camfrog_autodj/webhook/server.py`:
```python
from fastapi import FastAPI, Depends, HTTPException, Request
from contextlib import asynccontextmanager
from camfrog_autodj.webhook.models import WebhookConfig
from camfrog_autodj.webhook.auth import verify_webhook_signature
from camfrog_autodj.engine import Engine

_engine: Engine | None = None
_config: WebhookConfig | None = None

def create_webhook_app(config: WebhookConfig, engine: Engine | None = None) -> FastAPI:
    global _engine, _config
    _engine = engine
    _config = config
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
    
    app = FastAPI(title="CamfrogAutoDJ Webhook", lifespan=lifespan)
    
    @app.get("/webhook/health")
    async def health():
        return {"status": "healthy", "engine": _engine is not None}
    
    @app.post("/webhook/play")
    async def play_track(request: Request, _: bool = Depends(verify_webhook_signature)):
        if not _engine:
            raise HTTPException(503, "Engine not available")
        data = await request.json()
        query = data.get("query", "")
        if not query:
            raise HTTPException(400, "Missing query")
        # Queue track via engine (non-blocking)
        _engine.request(query, user="webhook")
        return {"status": "queued", "query": query}
    
    @app.post("/webhook/skip")
    async def skip_track(_: bool = Depends(verify_webhook_signature)):
        if not _engine:
            raise HTTPException(503, "Engine not available")
        _engine.skip()
        return {"status": "skipped"}
    
    @app.post("/webhook/volume")
    async def set_volume(request: Request, _: bool = Depends(verify_webhook_signature)):
        if not _engine:
            raise HTTPException(503, "Engine not available")
        data = await request.json()
        vol = int(data.get("volume", 50))
        _engine.set_volume(vol)
        return {"status": "ok", "volume": vol}
    
    @app.get("/webhook/status")
    async def get_status(_: bool = Depends(verify_webhook_signature)):
        if not _engine:
            raise HTTPException(503, "Engine not available")
        snap = _engine.snapshot()
        return {
            "current": snap["current"].title if snap["current"] else None,
            "position": snap["position"],
            "paused": snap["paused"],
            "volume": snap["volume"],
            "queue_length": len(snap["queue"]),
        }
    
    @app.get("/webhook/queue")
    async def get_queue(_: bool = Depends(verify_webhook_signature)):
        if not _engine:
            raise HTTPException(503, "Engine not available")
        snap = _engine.snapshot()
        return {
            "queue": [{"title": t.title, "duration": t.dur, "requester": t.requester} for t in snap["queue"]],
            "next": {"title": snap["next"].title, "duration": snap["next"].dur} if snap["next"] else None
        }
    
    return app

class WebhookServer:
    def __init__(self, config: WebhookConfig, engine: Engine):
        self.config = config
        self.engine = engine
        self._app = create_webhook_app(config, engine)
        self._server = None
    
    async def start(self):
        import uvicorn
        self._server = uvicorn.Server(uvicorn.Config(
            self._app, host=self.config.host, port=self.config.port, log_level="info"
        ))
        await self._server.serve()
    
    async def stop(self):
        if self._server:
            self._server.should_exit = True
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_webhook_server.py -v`
Expected: PASS

- [ ] **Step 7: Add webhook integration to Engine**

Modify `camfrog_autodj/engine.py`:
- Add `webhook_server` attribute
- Add `start_webhook()` and `stop_webhook()` methods
- Start webhook server in `start()` if config.webhook_enabled

- [ ] **Step 8: Run full test suite**

Run: `pytest -q -p no:faulthandler -p no:cacheprovider`
Expected: 472+ tests pass

- [ ] **Step 9: Commit**

```bash
git add camfrog_autodj/webhook/ camfrog_autodj/config.py camfrog_autodj/engine.py tests/test_webhook_server.py
git commit -m "feat: add webhook/API integration (Phase 3)"
```

---

### Task 2: Plugin System Architecture

**Files:**
- Create: `camfrog_autodj/plugins/__init__.py`
- Create: `camfrog_autodj/plugins/base.py`
- Create: `camfrog_autodj/plugins/manager.py`
- Create: `camfrog_autodj/plugins/builtin/stats.py`
- Create: `camfrog_autodj/plugins/builtin/__init__.py`
- Modify: `camfrog_autodj/config.py` (add plugins config)
- Modify: `camfrog_autodj/engine.py` (integrate plugin manager)
- Test: `tests/test_plugin_system.py`

**Interfaces:**
- Consumes: `Engine` (read-only access via defined interface), `Config`
- Produces: `PluginManager` with `load_plugins()`, `unload_plugins()`, `emit(event, data)`

- [ ] **Step 1: Write failing tests for plugin system**

```python
# tests/test_plugin_system.py
import pytest
from camfrog_autodj.plugins.manager import PluginManager
from camfrog_autodj.plugins.base import Plugin, PluginInterface

class TestPlugin(Plugin):
    name = "test_plugin"
    def on_load(self, engine): self.loaded = True
    def on_unload(self): self.unloaded = True
    def on_track_start(self, track): self.track = track

def test_plugin_manager_loads_plugin():
    class MockEngine: pass
    mgr = PluginManager(MockEngine(), [])
    mgr.load_plugin(TestPlugin)
    assert mgr.get_plugin("test_plugin").loaded is True

def test_plugin_manager_emits_events():
    class MockEngine: pass
    mgr = PluginManager(MockEngine(), [])
    plugin = TestPlugin()
    mgr.load_plugin_instance(plugin)
    mgr.emit("track_start", {"title": "Test Song"})
    assert plugin.track["title"] == "Test Song"

def test_plugin_sandbox_no_engine_internals():
    """Plugins cannot access private engine attributes."""
    class MaliciousPlugin(Plugin):
        name = "malicious"
        def on_load(self, engine):
            # This should fail or be prevented
            self.bad_access = engine._active_requests
    # Test that plugin only gets safe interface
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_plugin_system.py -v`
Expected: FAIL

- [ ] **Step 3: Implement plugin base interface**

Create `camfrog_autodj/plugins/base.py`:
```python
from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass

@dataclass
class PluginInterface:
    """Safe interface exposed to plugins - no engine internals."""
    def queue_track(self, query: str, user: str = "plugin"): ...
    def skip_track(self): ...
    def set_volume(self, volume: int): ...
    def get_status(self) -> dict: ...
    def say(self, text: str): ...
    def get_config(self) -> Any: ...  # read-only config view

class Plugin(ABC):
    name: str = ""
    version: str = "1.0.0"
    config: dict = {}
    
    def __init__(self):
        self._interface: PluginInterface | None = None
    
    @abstractmethod
    def on_load(self, interface: PluginInterface) -> None:
        """Called when plugin is loaded."""
        pass
    
    def on_unload(self) -> None:
        """Called when plugin is unloaded."""
        pass
    
    def on_track_start(self, track: dict) -> None:
        pass
    
    def on_track_end(self, track: dict) -> None:
        pass
    
    def on_command(self, command: str, user: str, args: str) -> bool:
        """Return True if command was handled."""
        return False
    
    def on_chat(self, user: str, text: str, is_im: bool) -> None:
        pass
```

- [ ] **Step 4: Implement plugin manager**

Create `camfrog_autodj/plugins/manager.py`:
```python
import importlib
import logging
from typing import Any
from camfrog_autodj.plugins.base import Plugin, PluginInterface
from camfrog_autodj.engine import Engine

log = logging.getLogger("autodj.plugins")

class SafeEngineInterface(PluginInterface):
    """Safe wrapper around Engine for plugins."""
    def __init__(self, engine: Engine):
        self._engine = engine
    
    def queue_track(self, query: str, user: str = "plugin"):
        self._engine.request(query, user)
    
    def skip_track(self):
        self._engine.skip()
    
    def set_volume(self, volume: int):
        self._engine.set_volume(volume)
    
    def get_status(self) -> dict:
        return self._engine.snapshot()
    
    def say(self, text: str):
        self._engine.say(text)
    
    def get_config(self):
        # Return read-only view of safe config
        from types import MappingProxyType
        safe_keys = {"volume", "max_queue", "max_duration", "shuffle", "repeat", "lang"}
        return MappingProxyType({k: getattr(self._engine.cfg, k) for k in safe_keys})

class PluginManager:
    def __init__(self, engine: Engine, plugin_names: list[str]):
        self.engine = engine
        self.plugin_names = plugin_names
        self.plugins: dict[str, Plugin] = {}
        self._interface = SafeEngineInterface(engine)
    
    def load_plugins(self):
        for name in self.plugin_names:
            self.load_plugin(name)
    
    def load_plugin(self, name: str):
        if name in self.plugins:
            log.warning("Plugin %s already loaded", name)
            return
        try:
            if name.startswith("builtin."):
                mod = importlib.import_module(f"camfrog_autodj.plugins.builtin.{name[8:]}")
            else:
                mod = importlib.import_module(name)
            # Find Plugin subclass
            for attr in dir(mod):
                obj = getattr(mod, attr)
                if isinstance(obj, type) and issubclass(obj, Plugin) and obj is not Plugin:
                    plugin = obj()
                    plugin.on_load(self._interface)
                    self.plugins[plugin.name or name] = plugin
                    log.info("Loaded plugin: %s", plugin.name or name)
                    return
            log.error("No Plugin class found in %s", name)
        except Exception:
            log.exception("Failed to load plugin %s", name)
    
    def load_plugin_instance(self, plugin: Plugin):
        plugin.on_load(self._interface)
        self.plugins[plugin.name] = plugin
    
    def unload_plugins(self):
        for name, plugin in self.plugins.items():
            try:
                plugin.on_unload()
            except Exception:
                log.exception("Error unloading plugin %s", name)
        self.plugins.clear()
    
    def get_plugin(self, name: str) -> Plugin | None:
        return self.plugins.get(name)
    
    def emit(self, event: str, data: Any):
        for plugin in self.plugins.values():
            try:
                method = getattr(plugin, f"on_{event}", None)
                if method:
                    method(data)
            except Exception:
                log.exception("Plugin %s error in %s", plugin.name, event)
```

- [ ] **Step 5: Implement built-in stats plugin**

Create `camfrog_autodj/plugins/builtin/stats.py`:
```python
import json
import logging
from pathlib import Path
from collections import Counter
from camfrog_autodj.plugins.base import Plugin
from camfrog_autodj.models import Track

log = logging.getLogger("autodj.plugins.stats")

class StatsPlugin(Plugin):
    name = "stats"
    version = "1.0.0"
    
    def __init__(self):
        super().__init__()
        self.stats_file = Path("plugin_stats.json")
        self.track_counts: Counter[str] = Counter()
        self.user_counts: Counter[str] = Counter()
        self.total_plays = 0
        self._load()
    
    def _load(self):
        if self.stats_file.exists():
            try:
                data = json.loads(self.stats_file.read_text())
                self.track_counts = Counter(data.get("tracks", {}))
                self.user_counts = Counter(data.get("users", {}))
                self.total_plays = data.get("total_plays", 0)
            except Exception:
                log.exception("Failed to load stats")
    
    def _save(self):
        try:
            data = {
                "tracks": dict(self.track_counts),
                "users": dict(self.user_counts),
                "total_plays": self.total_plays,
            }
            self.stats_file.write_text(json.dumps(data))
        except Exception:
            log.exception("Failed to save stats")
    
    def on_load(self, interface):
        log.info("Stats plugin loaded")
    
    def on_unload(self):
        self._save()
        log.info("Stats plugin unloaded")
    
    def on_track_start(self, track: dict):
        title = track.get("title", "Unknown")
        requester = track.get("requester", "Unknown")
        self.track_counts[title] += 1
        self.user_counts[requester] += 1
        self.total_plays += 1
        self._save()
    
    def on_command(self, command: str, user: str, args: str) -> bool:
        if command in ("stats", "statistics", "สถิติ"):
            top_tracks = self.track_counts.most_common(5)
            top_users = self.user_counts.most_common(5)
            msg = f"📊 Top tracks: {', '.join(f'{t} ({c})' for t, c in top_tracks)} | Top users: {', '.join(f'{u} ({c})' for u, c in top_users)} | Total: {self.total_plays}"
            self._interface.say(msg)
            return True
        return False
```

- [ ] **Step 6: Add plugin config to Config class**

Modify `camfrog_autodj/config.py`:
```python
# In Config dataclass, add:
plugins: list[str] = field(default_factory=lambda: ["builtin.stats"])
```

- [ ] **Step 7: Integrate plugin manager into Engine**

Modify `camfrog_autodj/engine.py`:
- Import `PluginManager`
- In `__init__`: `self.plugin_manager = PluginManager(self, cfg.plugins)`
- In `start()`: `self.plugin_manager.load_plugins()`
- In `shutdown()`: `self.plugin_manager.unload_plugins()`
- Emit events in `_play_one_track` (track_start, track_end), `_handle_room_message` (chat), `_dispatch_command` (command)

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest tests/test_plugin_system.py -v`
Expected: PASS

- [ ] **Step 9: Run full test suite**

Run: `pytest -q -p no:faulthandler -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 10: Commit**

```bash
git add camfrog_autodj/plugins/ camfrog_autodj/config.py camfrog_autodj/engine.py tests/test_plugin_system.py
git commit -m "feat: add plugin system architecture (Phase 4)"
```

---

### Task 3: Performance Optimizations - Persistent IPC Connection

**Files:**
- Modify: `camfrog_autodj/player.py` (persistent IPC)
- Modify: `camfrog_autodj/engine.py` (separate locks, batch rate limit cleanup)
- Test: `tests/test_player_ipc_performance.py`, `tests/test_lock_contention.py`

**Interfaces:**
- Consumes: Existing `MpvPlayer` interface
- Produces: `MpvPlayer` with persistent IPC connection during track playback

- [ ] **Step 1: Write failing tests for persistent IPC**

```python
# tests/test_player_ipc_performance.py
import time
import pytest
from unittest.mock import Mock, patch, MagicMock
from camfrog_autodj.player import MpvPlayer
from camfrog_autodj.config import Config

def test_ipc_connection_reused_for_multiple_commands():
    """Verify IPC connection is reused, not recreated for each command."""
    cfg = Config(mpv_path="mpv/mpv.exe", mpv_timeout=30)
    player = MpvPlayer(cfg)
    
    with patch.object(player, '_cmd_get') as mock_get, \
         patch.object(player, '_cmd') as mock_cmd:
        
        # Simulate track playing with IPC connection
        player._ipc = r"\\.\pipe\test-123"
        player.proc = Mock(poll=lambda: None)
        
        # Multiple calls should reuse connection
        player.get_time_pos()
        player.set_volume(50)
        player.set_pause(True)
        player.seek(30.0)
        
        # All should use the same IPC path
        assert mock_get.call_count + mock_cmd.call_count == 4

def test_ipc_closed_on_track_end():
    """Verify IPC connection is cleaned up when track ends."""
    cfg = Config(mpv_path="mpv/mpv.exe")
    player = MpvPlayer(cfg)
    player._ipc = r"\\.\pipe\test-123"
    player.proc = Mock(poll=lambda: 0, wait=Mock(return_value=0))
    
    # Play a track (mocked)
    with patch('subprocess.Popen') as mock_popen:
        mock_proc = Mock()
        mock_proc.poll.return_value = 0
        mock_proc.wait.return_value = 0
        mock_popen.return_value = mock_proc
        
        player.play("test.mp3", 50, 10.0)
        
        # IPC should be cleaned up
        assert player._ipc is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_player_ipc_performance.py -v`
Expected: FAIL

- [ ] **Step 3: Implement persistent IPC in MpvPlayer**

Modify `camfrog_autodj/player.py`:
- Keep IPC connection open during track playback
- Store IPC handle/connection in `_ipc_handle` 
- Reuse for `get_time_pos`, `seek`, `set_pause`, `set_volume`
- Close only in `stop()` and when track ends in `play()`
- Add `_ensure_ipc_connected()` helper

Key changes:
```python
def play(self, source: str, volume: int, duration: float | None = None) -> bool:
    # ... existing setup ...
    # Create IPC connection ONCE
    if _is_windows():
        self._ipc_handle = open(ipc, "r+b", buffering=0)
    else:
        import socket
        self._ipc_handle = socket.socket(socket.AF_UNIX)
        self._ipc_handle.connect(ipc)
    
    # ... rest of play ...
    # At end (success or failure):
    self._close_ipc()
    return ok

def _close_ipc(self):
    if self._ipc_handle:
        try:
            self._ipc_handle.close()
        except Exception:
            pass
        self._ipc_handle = None
    self._ipc = None

def _cmd(self, *cmd) -> bool:
    if not self._ipc_handle:
        return False
    data = (json.dumps({"command": list(cmd)}) + "\n").encode()
    try:
        if _is_windows():
            self._ipc_handle.write(data)
        else:
            self._ipc_handle.sendall(data)
        return True
    except OSError:
        self._close_ipc()
        return False

def _cmd_get(self, *cmd) -> float | None:
    if not self._ipc_handle:
        return None
    # Similar but with response reading
```

- [ ] **Step 4: Implement separate locks in Engine**

Modify `camfrog_autodj/engine.py`:
- Split `_send_failure_lock` into:
  - `_circuit_breaker_lock` for circuit breaker state
  - `_send_failure_lock` for send failures only
- Update `_record_circuit_failure`, `_record_circuit_success`, `_is_circuit_open`
- Update `health_check()` to use `_circuit_breaker_lock`
- Add `_rate_limit_cleanup_lock` for rate limit cleanup (if not using `_chat_lock`)

- [ ] **Step 5: Implement batch rate limit cleanup**

Modify `camfrog_autodj/engine.py`:
- Add `_rate_limit_cleanup_task()` method that runs every 60s
- Move cleanup logic from `_within_limits` to this periodic task
- Use `ThreadPoolExecutor` to submit cleanup task in `start()`
- Cleanup: prune `_chat_rate_window`, `_im_reply_cooldowns`, `_admin_greeting_cooldowns`, `_welcome_cooldowns`

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_player_ipc_performance.py tests/test_lock_contention.py -v`
Expected: PASS

- [ ] **Step 7: Run full test suite**

Run: `pytest -q -p no:faulthandler -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
git add camfrog_autodj/player.py camfrog_autodj/engine.py tests/test_player_ipc_performance.py tests/test_lock_contention.py
git commit -m "perf: persistent IPC connection, separate locks, batch rate limit cleanup"
```

---

### Task 4: Enhanced Audit Logging

**Files:**
- Create: `camfrog_autodj/audit.py`
- Modify: `camfrog_autodj/config.py` (add audit config)
- Modify: `camfrog_autodj/engine.py` (emit audit events)
- Modify: `camfrog_autodj/commands.py` (audit admin commands)
- Test: `tests/test_audit_logging.py`

**Interfaces:**
- Consumes: `Config` (audit settings), `Engine` (for context)
- Produces: `AuditLogger` with `log_event(event_type, actor, target, result, details)`

- [ ] **Step 1: Write failing tests for audit logging**

```python
# tests/test_audit_logging.py
import json
import tempfile
from pathlib import Path
from camfrog_autodj.audit import AuditLogger, AuditEvent

def test_audit_log_writes_structured_events():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "audit.log"
        logger = AuditLogger(str(log_path), max_size=1_000_000, backup_count=3)
        
        logger.log_event(
            event_type="admin_command",
            actor="admin1",
            target="user2",
            result="success",
            details={"command": "ban", "reason": "spam"}
        )
        logger.flush()
        
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        event = json.loads(lines[0])
        assert event["event_type"] == "admin_command"
        assert event["actor"] == "admin1"
        assert event["target"] == "user2"
        assert event["result"] == "success"
        assert "timestamp" in event
        assert "hash" in event  # Hash-chained

def test_audit_log_hash_chain_detects_tampering():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "audit.log"
        logger = AuditLogger(str(log_path))
        
        logger.log_event("test", "a", "b", "success", {})
        logger.log_event("test", "c", "d", "success", {})
        logger.flush()
        
        # Tamper with first line
        lines = log_path.read_text().splitlines()
        lines[0] = lines[0].replace('"actor": "a"', '"actor": "hacked"')
        log_path.write_text("\n".join(lines))
        
        # Verify chain broken
        assert not logger.verify_chain()

def test_audit_log_rotation():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "audit.log"
        logger = AuditLogger(str(log_path), max_size=100, backup_count=2)  # Tiny for test
        
        for i in range(50):
            logger.log_event("test", f"user{i}", "target", "success", {"data": "x" * 50})
        logger.flush()
        
        # Should have rotated
        assert log_path.exists()
        # Backup files should exist
        backups = list(Path(tmpdir).glob("audit.log.*"))
        assert len(backups) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_audit_logging.py -v`
Expected: FAIL

- [ ] **Step 3: Implement AuditLogger**

Create `camfrog_autodj/audit.py`:
```python
import hashlib
import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

log = logging.getLogger("autodj.audit")

class AuditLogger:
    """Tamper-evident audit log with hash chaining."""
    
    def __init__(self, path: str, max_size: int = 1_000_000, backup_count: int = 3):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size
        self.backup_count = backup_count
        self._lock = threading.Lock()
        self._last_hash = self._compute_last_hash()
        self._handler = RotatingFileHandler(
            self.path, maxBytes=max_size, backupCount=backup_count, encoding="utf-8"
        )
    
    def _compute_last_hash(self) -> str:
        """Compute hash of last line in current log file."""
        if not self.path.exists():
            return "0" * 64  # Genesis hash
        try:
            with open(self.path, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                # Read last ~2KB to find last line
                f.seek(max(0, size - 2048))
                data = f.read().decode("utf-8", errors="replace")
                lines = data.strip().splitlines()
                if lines:
                    last = json.loads(lines[-1])
                    return last.get("hash", "0" * 64)
        except Exception:
            pass
        return "0" * 64
    
    def log_event(self, event_type: str, actor: str, target: str, result: str, details: dict):
        """Log an audit event with hash chaining."""
        timestamp = datetime.now().isoformat()
        event = {
            "timestamp": timestamp,
            "event_type": event_type,
            "actor": actor,
            "target": target,
            "result": result,
            "details": details,
            "prev_hash": self._last_hash,
        }
        # Compute hash of this event (excluding hash field itself)
        event_json = json.dumps(event, sort_keys=True, separators=(",", ":"))
        event_hash = hashlib.sha256(event_json.encode()).hexdigest()
        event["hash"] = event_hash
        
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        
        with self._lock:
            self._handler.stream.write(line + "\n")
            self._handler.stream.flush()
            self._last_hash = event_hash
    
    def flush(self):
        with self._lock:
            self._handler.flush()
    
    def verify_chain(self) -> bool:
        """Verify hash chain integrity. Returns True if valid."""
        if not self.path.exists():
            return True
        try:
            prev_hash = "0" * 64
            with open(self.path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    event = json.loads(line)
                    if event.get("prev_hash") != prev_hash:
                        log.error("Audit chain broken at line %d", line_num)
                        return False
                    # Recompute hash
                    event_copy = {k: v for k, v in event.items() if k != "hash"}
                    event_json = json.dumps(event_copy, sort_keys=True, separators=(",", ":"))
                    computed = hashlib.sha256(event_json.encode()).hexdigest()
                    if computed != event.get("hash"):
                        log.error("Audit hash mismatch at line %d", line_num)
                        return False
                    prev_hash = event["hash"]
            return True
        except Exception:
            log.exception("Audit chain verification failed")
            return False
    
    def close(self):
        with self._lock:
            self._handler.close()
```

- [ ] **Step 4: Add audit config to Config**

Modify `camfrog_autodj/config.py`:
```python
# In Config dataclass, add:
audit_log_enabled: bool = True
audit_log_path: str = "audit.log"
audit_log_max_size: int = 1_000_000
audit_log_backup_count: int = 3
```

- [ ] **Step 5: Integrate audit logging into Engine**

Modify `camfrog_autodj/engine.py`:
- Import `AuditLogger`
- In `__init__`: `self.audit = AuditLogger(cfg.audit_log_path, cfg.audit_log_max_size, cfg.audit_log_backup_count) if cfg.audit_log_enabled else None`
- Add `audit_event()` helper method
- Call `audit_event()` for: admin commands, block/unblock, config changes, user ban/kick/punish

- [ ] **Step 6: Integrate audit logging into commands**

Modify `camfrog_autodj/commands.py`:
- In `_dispatch_command`, after successful admin command, emit audit event
- Event types: `admin_command`, `user_blocked`, `user_unblocked`, `user_banned`, `user_unbanned`, `user_kicked`, `user_punished`, `bot_blocked`, `bot_unblocked`, `message_deleted`

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/test_audit_logging.py -v`
Expected: PASS

- [ ] **Step 8: Run full test suite**

Run: `pytest -q -p no:faulthandler -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 9: Commit**

```bash
git add camfrog_autodj/audit.py camfrog_autodj/config.py camfrog_autodj/engine.py camfrog_autodj/commands.py tests/test_audit_logging.py
git commit -m "feat: add tamper-evident audit logging (Phase 5)"
```

---

### Task 5: Dead Letter Queue (DLQ)

**Files:**
- Create: `camfrog_autodj/dlq.py`
- Modify: `camfrog_autodj/engine.py` (integrate DLQ)
- Modify: `camfrog_autodj/config.py` (DLQ config)
- Test: `tests/test_dlq.py`

**Interfaces:**
- Consumes: Failed track info (track, error, failure count)
- Produces: `DeadLetterQueue` with `add()`, `retry()`, `list()`, `clear()`

- [ ] **Step 1: Write failing tests for DLQ**

```python
# tests/test_dlq.py
import tempfile
from pathlib import Path
from camfrog_autodj.dlq import DeadLetterQueue
from camfrog_autodj.models import Track

def test_dlq_adds_failed_tracks():
    with tempfile.TemporaryDirectory() as tmpdir:
        dlq = DeadLetterQueue(Path(tmpdir) / "dlq.json", max_size=100, ttl_hours=24)
        
        track = Track("https://youtube.com/watch?v=abc", "Test Song", 180.0, "user1")
        dlq.add(track, "Connection timeout", failure_count=3)
        
        items = dlq.list()
        assert len(items) == 1
        assert items[0]["track"]["title"] == "Test Song"
        assert items[0]["error"] == "Connection timeout"
        assert items[0]["failure_count"] == 3

def test_dlq_retry_moves_track_back_to_queue():
    with tempfile.TemporaryDirectory() as tmpdir:
        dlq = DeadLetterQueue(Path(tmpdir) / "dlq.json")
        track = Track("https://youtube.com/watch?v=abc", "Test Song", 180.0, "user1")
        dlq.add(track, "Timeout", 3)
        
        # Mock engine to verify retry
        retry_track = dlq.retry(0)
        assert retry_track is not None
        assert retry_track.title == "Test Song"
        
        # Item should be removed from DLQ
        assert len(dlq.list()) == 0

def test_dlq_respects_max_size():
    with tempfile.TemporaryDirectory() as tmpdir:
        dlq = DeadLetterQueue(Path(tmpdir) / "dlq.json", max_size=2)
        for i in range(5):
            track = Track(f"url{i}", f"Song {i}", 180.0, "user1")
            dlq.add(track, f"Error {i}", 1)
        
        # Should only keep max_size items (newest)
        assert len(dlq.list()) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_dlq.py -v`
Expected: FAIL

- [ ] **Step 3: Implement DeadLetterQueue**

Create `camfrog_autodj/dlq.py`:
```python
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .models import Track

log = logging.getLogger("autodj.dlq")

class DeadLetterQueue:
    """Dead letter queue for failed tracks with retry capability."""
    
    def __init__(self, path: Path, max_size: int = 1000, ttl_hours: int = 24):
        self.path = Path(path)
        self.max_size = max_size
        self.ttl_seconds = ttl_hours * 3600
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
    
    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text("utf-8"))
        except Exception:
            return []
    
    def _save(self, items: list[dict]):
        # Atomic write
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(items, ensure_ascii=False, indent=1), "utf-8")
        tmp.replace(self.path)
    
    def _cleanup_expired(self, items: list[dict]) -> list[dict]:
        now = time.time()
        return [item for item in items if now - item.get("timestamp", 0) < self.ttl_seconds]
    
    def add(self, track: Track, error: str, failure_count: int = 1):
        """Add a failed track to the DLQ."""
        with self._lock:
            items = self._cleanup_expired(self._load())
            item = {
                "track": {
                    "source": track.source,
                    "title": track.title,
                    "duration": track.duration,
                    "requester": track.requester,
                },
                "error": error,
                "failure_count": failure_count,
                "timestamp": time.time(),
                "added_at": datetime.now().isoformat(),
            }
            items.append(item)
            # Keep only max_size newest items
            if len(items) > self.max_size:
                items = items[-self.max_size:]
            self._save(items)
            log.info("DLQ: added %s (%s)", track.title, error)
    
    def list(self) -> list[dict]:
        """List all DLQ entries (newest first)."""
        with self._lock:
            items = self._cleanup_expired(self._load())
            return list(reversed(items))
    
    def retry(self, index: int) -> Track | None:
        """Remove item from DLQ and return Track for re-queueing."""
        with self._lock:
            items = self._cleanup_expired(self._load())
            if not 0 <= index < len(items):
                return None
            item = items.pop(index)
            self._save(items)
            t = item["track"]
            return Track(t["source"], t["title"], t.get("duration"), t.get("requester", "DLQ"))
    
    def clear(self) -> int:
        """Clear all DLQ entries."""
        with self._lock:
            items = self._load()
            count = len(items)
            self._save([])
            return count
    
    def get_stats(self) -> dict:
        """Get DLQ statistics."""
        with self._lock:
            items = self._cleanup_expired(self._load())
            return {
                "count": len(items),
                "oldest": items[0]["added_at"] if items else None,
                "newest": items[-1]["added_at"] if items else None,
            }
```

- [ ] **Step 4: Add DLQ config**

Modify `camfrog_autodj/config.py`:
```python
# In Config dataclass, add:
dlq_enabled: bool = True
dlq_path: str = "dlq.json"
dlq_max_size: int = 1000
dlq_ttl_hours: int = 24
```

- [ ] **Step 5: Integrate DLQ into Engine**

Modify `camfrog_autodj/engine.py`:
- In `__init__`: `self.dlq = DeadLetterQueue(Path(cfg.dlq_path), cfg.dlq_max_size, cfg.dlq_ttl_hours) if cfg.dlq_enabled else None`
- In `_track_failed`: `self.dlq.add(t, error, fails)` when max retries exceeded
- Add admin command `!dlq` to list/retry/clear DLQ (in commands.py)

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_dlq.py -v`
Expected: PASS

- [ ] **Step 7: Run full test suite**

Run: `pytest -q -p no:faulthandler -p no:cacheprovider`
Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
git add camfrog_autodj/dlq.py camfrog_autodj/config.py camfrog_autodj/engine.py camfrog_autodj/commands.py tests/test_dlq.py
git commit -m "feat: add dead letter queue for failed tracks (Phase 7)"
```

---

### Task 6: Enhanced Circuit Breakers

**Files:**
- Modify: `camfrog_autodj/engine.py` (separate breakers per failure type)
- Modify: `camfrog_autodj/config.py` (circuit breaker config)
- Test: `tests/test_circuit_breaker_enhanced.py`

**Interfaces:**
- Consumes: Failure events (resolve, playback, chat)
- Produces: Separate circuit breakers with configurable thresholds

- [ ] **Step 1: Write failing tests**

```python
# tests/test_circuit_breaker_enhanced.py
from camfrog_autodj.engine import Engine

def test_separate_circuit_breakers():
    """Test that resolve, playback, and chat have separate breakers."""
    # Mock config with low thresholds
    # Trigger resolve failures - should open resolve breaker only
    # Playback and chat should still work
    pass

def test_circuit_breaker_configurable_thresholds():
    """Test that thresholds are configurable per breaker."""
    pass

def test_admin_circuit_breaker_reset():
    """Test admin command to manually reset breaker."""
    pass
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement separate circuit breakers**

Modify `camfrog_autodj/engine.py`:
- Replace single `_circuit_breaker_failures` with dict: `{"resolve": 0, "playback": 0, "chat": 0}`
- Replace single `_circuit_breaker_open_until` with dict per failure type
- Add config fields: `cb_resolve_threshold`, `cb_playback_threshold`, `cb_chat_threshold`, `cb_reset_timeout`
- Add `_record_failure(failure_type)`, `_record_success(failure_type)`, `_is_circuit_open(failure_type)`
- Add `reset_circuit_breaker(failure_type)` method for admin command
- Update `health_check()` to return per-breaker status

- [ ] **Step 4: Add admin command for circuit breaker reset**

Modify `camfrog_autodj/commands.py`:
- Add `!circuitbreaker reset <type>` command (admin only)
- Types: resolve, playback, chat, all

- [ ] **Step 5: Run tests to verify they pass**

- [ ] **Step 6: Run full test suite**

- [ ] **Step 7: Commit**

```bash
git add camfrog_autodj/engine.py camfrog_autodj/config.py camfrog_autodj/commands.py tests/test_circuit_breaker_enhanced.py
git commit -m "feat: enhanced circuit breakers per failure type (Phase 7)"
```

---

### Task 7: Documentation Updates

**Files:**
- Modify: `README.md` (add webhook, plugin, DLQ, audit docs)
- Modify: `CHANGELOG.md` (add unreleased section)
- Modify: `config.example.toml` (add new config options)
- Create: `docs/webhook.md`
- Create: `docs/plugins.md`
- Create: `docs/audit-logging.md`
- Create: `docs/dead-letter-queue.md`
- Create: `docs/adr/0002-webhook-api-integration.md`
- Create: `docs/adr/0003-plugin-system.md`
- Create: `docs/adr/0004-audit-logging.md`

- [ ] **Step 1: Update config.example.toml with all new options**

Add webhook, plugin, audit, DLQ, enhanced circuit breaker configs

- [ ] **Step 2: Update README.md**

Add sections for:
- Webhook API (endpoints, auth, examples)
- Plugin System (builtin plugins, custom plugins)
- Audit Logging (format, verification)
- Dead Letter Queue (usage, admin commands)
- Enhanced Circuit Breakers

- [ ] **Step 3: Create detailed documentation files**

Create `docs/webhook.md`, `docs/plugins.md`, etc.

- [ ] **Step 4: Create ADRs**

Document architectural decisions for each major feature

- [ ] **Step 5: Update CHANGELOG.md**

Add "Unreleased" section with all new features

- [ ] **Step 6: Verify documentation consistency**

Run: `python -m pytest tests/test_version_and_release.py -v` (if exists)

- [ ] **Step 7: Commit**

```bash
git add README.md CHANGELOG.md config.example.toml docs/
git commit -m "docs: update documentation for v0.4.0 enterprise features"
```

---

### Task 8: Final Validation & Release Preparation

**Files:**
- All modified files

- [ ] **Step 1: Run full validation suite**

```bash
# All verification checks
python -m compileall -q camfrog_autodj tests tools
ruff check camfrog_autodj tests tools
ruff format --check camfrog_autodj tests tools
mypy camfrog_autodj
shellcheck scripts/*.sh tools/*.sh
python -m pytest -q -p no:faulthandler -p no:cacheprovider
```

Expected: All pass with 0 errors

- [ ] **Step 2: Run security checks**

```bash
make security-check
make security-audit
```

Expected: 0 secrets, 0 vulnerabilities in declared deps

- [ ] **Step 3: Bump version**

Update `pyproject.toml`, `camfrog_autodj/__init__.py`, `version_info.txt`, `installer.nsi`, `install.ps1`, `install.bat` to 0.4.0

- [ ] **Step 4: Build and test**

```bash
make build
make test
```

- [ ] **Step 5: Create PR and follow GitHub workflow**

Per AGENTS.md: Phase A (cvsz), Phase B (policedbc), Phase C (cvsz)

- [ ] **Step 6: Final commit**

```bash
git commit -m "chore: release v0.4.0"
git tag -s v0.4.0 -m "Release v0.4.0"
```

---

## Execution Order

1. Task 1: Webhook/API Integration (foundation for external integration)
2. Task 2: Plugin System (extensibility)
3. Task 3: Performance Optimizations (core engine improvements)
4. Task 4: Enhanced Audit Logging (security/compliance)
5. Task 5: Dead Letter Queue (resilience)
6. Task 6: Enhanced Circuit Breakers (resilience)
7. Task 7: Documentation Updates
8. Task 8: Final Validation & Release

## Dependencies

- Task 1, 2, 4, 5, 6 all depend on config.py changes (can be done in parallel)
- Task 3 depends on engine.py and player.py (independent of others)
- Task 7 depends on all features being complete
- Task 8 depends on everything

## Risk Mitigation

- Each task has comprehensive tests written first (TDD)
- All changes are backward compatible
- Config defaults keep new features disabled by default
- Feature flags allow gradual rollout
- Existing 472 tests must continue to pass