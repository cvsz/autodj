# CamfrogAutoDJ Enhancement Plan - Phase 1/2/7

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Configuration Hot Reload, Structured JSON Logging, and Graceful Degradation fallbacks to enhance production operability.

**Architecture:** Build on existing Config/Engine/Adapter patterns. Hot reload uses watchdog for file watching with atomic reload. JSON logging adds a formatter with structured fields. Graceful degradation adds fallback chat adapters and automatic failover.

**Tech Stack:** Python 3.11+, watchdog (file watching), stdlib logging (formatters), existing adapter pattern.

**Spec:** `IMPLEMENTATION_PLAN_V2.md` (Phases 1, 2, 7)

## Global Constraints

- Python 3.11+ (per pyproject.toml)
- All changes must pass: `ruff check`, `ruff format --check`, `mypy`, `pytest -q`
- No new dependencies without justification (watchdog is acceptable for hot reload)
- Windows primary, Linux headless compatible
- Fail-closed validation on all config changes
- Atomic writes for config (temp file + os.replace + .bak)
- Thread-safe: all shared state guarded by locks
- No audio I/O on GUI thread

## Review Focus

1. **Config reload during playback** - Must not interrupt current track; queue/volume changes apply atomically
2. **Log format change mid-run** - Handlers must be swapped atomically; no log loss
3. **Chat adapter failover** - Must preserve message ordering; no duplicate sends
4. **Hot reload with invalid config** - Must reject and keep previous valid config; alert admin
5. **Concurrent config changes** - File watcher + GUI save must not race; last-write-wins with validation

---

### Task 1: Add watchdog dependency and Config hot reload infrastructure

**Files:**
- Modify: `pyproject.toml` (add watchdog to optional deps)
- Create: `camfrog_autodj/config_watcher.py`
- Modify: `camfrog_autodj/config.py` (add reload callback support)
- Test: `tests/test_config_hot_reload.py`

**Interfaces:**
- Consumes: `Config.load()`, `Config._validate()`
- Produces: `ConfigWatcher` class with `start()`, `stop()`, `on_change(callback)`

- [ ] **Step 1: Write failing test for ConfigWatcher**

```python
def test_config_watcher_detects_change(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text('bot_nick = "Test"\nadmins = []\n')
    watcher = ConfigWatcher(str(cfg_file))
    changes = []
    watcher.on_change(lambda path: changes.append(path))
    watcher.start()
    # Modify file
    cfg_file.write_text('bot_nick = "Test2"\nadmins = []\n')
    time.sleep(0.5)
    watcher.stop()
    assert len(changes) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config_hot_reload.py::test_config_watcher_detects_change -v`
Expected: FAIL - ConfigWatcher not defined

- [ ] **Step 3: Implement ConfigWatcher in camfrog_autodj/config_watcher.py**

- Use watchdog.Observer with PatternMatchingEventHandler
- Debounce rapid writes (500ms)
- Validate new config before callback
- Thread-safe callback invocation

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config_hot_reload.py::test_config_watcher_detects_change -v`
Expected: PASS

- [ ] **Step 5: Add Config.reload() method and callback registry**

Modify: `camfrog_autodj/config.py`
- Add `Config.reload() -> Config` class method
- Add `Config.register_reload_callback(callback)` / `unregister_reload_callback()`
- Callbacks receive new Config instance after validation

- [ ] **Step 6: Test Config.reload() with valid and invalid configs**

```python
def test_config_reload_valid(tmp_path):
    # ... test valid reload updates values
    
def test_config_reload_invalid_keeps_old(tmp_path):
    # ... test invalid reload raises and old config preserved
```

- [ ] **Step 7: Run tests and commit**

---

### Task 2: Integrate ConfigWatcher into Engine and GUI

**Files:**
- Modify: `camfrog_autodj/engine.py` (add config watcher, handle reload)
- Modify: `camfrog_autodj/gui.py` (trigger reload on settings save)
- Modify: `camfrog_autodj/__main__.py` (start watcher in GUI mode)
- Test: `tests/test_engine_config_reload.py`

**Interfaces:**
- Consumes: `ConfigWatcher`, `Config.register_reload_callback`
- Produces: `Engine._on_config_reload(new_cfg)` method

- [ ] **Step 1: Write failing test for Engine config reload**

```python
def test_engine_reload_updates_volume(engine, tmp_path):
    # ... test volume change via config reload applies to player
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Add ConfigWatcher to Engine.__init__ (GUI mode only)**

- Start watcher when GUI mode detected
- Register callback: `self._on_config_reload`
- Stop watcher on shutdown()

- [ ] **Step 4: Implement Engine._on_config_reload(new_cfg)**

- Apply dynamic settings: volume, shuffle, repeat, lang, cooldown, send_interval, poll_interval
- Defer adapter changes: log warning, require restart
- Update GUI via generation bump
- Log reload event with changed keys

- [ ] **Step 5: Modify GUI save_settings to trigger reload**

- After atomic write, ConfigWatcher will detect change
- No additional action needed (watcher handles it)

- [ ] **Step 6: Run tests and commit**

---

### Task 3: JSON Structured Logging Formatter

**Files:**
- Create: `camfrog_autodj/logging_json.py`
- Modify: `camfrog_autodj/__main__.py` (add --log-json flag, configure formatter)
- Modify: `camfrog_autodj/config.py` (add log_json, log_json_fields settings)
- Test: `tests/test_json_logging.py`

**Interfaces:**
- Consumes: stdlib logging, Engine request/delivery tracking
- Produces: `JsonFormatter` class, `configure_json_logging()` function

- [ ] **Step 1: Write failing test for JsonFormatter**

```python
def test_json_formatter_includes_structured_fields():
    record = logging.LogRecord(...)
    record.request_id = "req-123"
    record.user = "testuser"
    formatted = JsonFormatter().format(record)
    data = json.loads(formatted)
    assert data["request_id"] == "req-123"
    assert data["user"] == "testuser"
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Implement JsonFormatter in camfrog_autodj/logging_json.py**

- Extend logging.Formatter
- Include: timestamp, level, logger, message, request_id, delivery_id, user, track_id, generation
- Handle extra fields from LogRecord.__dict__
- Ensure JSON serializable (handle exceptions, datetime)

- [ ] **Step 4: Add config options and CLI flag**

Config: `log_json = false`, `log_json_fields = ["request_id", "user", "track_id"]`
CLI: `--log-json` enables JSON output to stdout/file

- [ ] **Step 5: Test JSON logging output**

```python
def test_json_logging_to_file(tmp_path):
    # ... test file handler with JsonFormatter writes valid JSON lines
```

- [ ] **Step 6: Run tests and commit**

---

### Task 4: Graceful Degradation - Fallback Chat Adapters

**Files:**
- Modify: `camfrog_autodj/adapters/__init__.py` (add fallback chain logic)
- Modify: `camfrog_autodj/adapters/uia.py` (improve error handling)
- Create: `camfrog_autodj/adapters/logtail.py` (enhance for fallback)
- Modify: `camfrog_autodj/__main__.py` (auto-fallback logic)
- Test: `tests/test_adapter_fallback.py`

**Interfaces:**
- Consumes: `build_adapter()`, `NullAdapter`, `Composite`
- Produces: `build_adapter_with_fallback(cfg)` function

- [ ] **Step 1: Write failing test for adapter fallback**

```python
def test_uia_failure_falls_back_to_logtail(monkeypatch):
    # ... mock UIA failure, verify logtail adapter created
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Implement fallback chain in adapters/__init__.py**

- `build_adapter_with_fallback(cfg)` tries: uia -> logtail -> console -> null
- Each failure logs warning and tries next
- Track which adapter is active for health check

- [ ] **Step 4: Enhance LogTailAdapter for production use**

- Poll log file at poll_interval
- Parse with line_regex
- Handle rotation/truncation

- [ ] **Step 5: Add adapter status to Engine.health_check()**

- Include: active_adapter, fallback_count, last_fallback_time

- [ ] **Step 6: Run tests and commit**

---

### Task 5: Engine Health Check Enhancements

**Files:**
- Modify: `camfrog_autodj/engine.py` (enhance health_check())
- Test: `tests/test_health_check.py`

**Interfaces:**
- Consumes: existing health_check(), circuit breaker state, adapter status
- Produces: enhanced health dict with new fields

- [ ] **Step 1: Write failing test for enhanced health check**

```python
def test_health_check_includes_adapter_and_circuit_state(engine):
    health = engine.health_check()
    assert "active_adapter" in health
    assert "circuit_breaker" in health
    assert "chat_rate_limit" in health
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Enhance Engine.health_check()**

Add:
- `active_adapter`: str (uia/logtail/console/null)
- `fallback_count`: int
- `circuit_breaker`: {playback: state, chat_send: state}
- `chat_rate_limit`: {tracked_users: int, total_dropped: int}
- `queue_depth`: int
- `autoplay_mode`: bool
- `uptime_seconds`: float
- `memory_mb`: float (optional, if psutil available)

- [ ] **Step 4: Add health check to GUI (optional status indicator)**

- [ ] **Step 5: Run tests and commit**

---

### Task 6: Integration Tests & Final Validation

**Files:**
- Create: `tests/test_integration_hot_reload.py`
- Create: `tests/test_integration_fallback.py`
- Modify: `Makefile` (add hot-reload, json-logging, fallback test targets)

- [ ] **Step 1: Write integration test for full hot reload cycle**

```python
def test_full_hot_reload_cycle(tmp_path):
    # Start engine with config
    # Modify config.toml
    # Verify engine picks up changes
    # Verify GUI updates
```

- [ ] **Step 2: Write integration test for adapter fallback**

```python
def test_adapter_fallback_preserves_messages():
    # Start with UIA
    # Simulate UIA failure
    # Verify messages sent via logtail
    # Verify no message loss/duplication
```

- [ ] **Step 3: Run full test suite**

Run: `make all`
Expected: All 450+ new tests pass, zero lint/typecheck warnings

- [ ] **Step 4: Update documentation**

- README.md: document --log-json, hot reload, fallback behavior
- CHANGELOG.md: add entries for v0.3.1
- config.example.toml: add new settings with comments

- [ ] **Step 5: Commit and create PR**

---

## Execution Notes

**Dependencies between tasks:**
- Task 1 (ConfigWatcher) → Task 2 (Engine/GUI integration)
- Task 3 (JSON logging) independent
- Task 4 (Fallback adapters) → Task 5 (Health check)
- Task 6 depends on all

**Recommended execution order:** 1 → 2 → 3 → 4 → 5 → 6

**Estimated effort:** ~200-300 lines of new code across 8 files + tests