# CamfrogAutoDJ - Comprehensive Enhancement Plan v2

**Current State**: 450 tests passing, all lint/typecheck/format clean, production-ready v0.3.0
**Goal**: Full enterprise production-grade enhancements with zero regressions

---

## Phase 1: Configuration Hot Reload & Dynamic Settings

### 1.1 Config Hot Reload
- Add `Config.watch()` method with file watcher (watchdog)
- Implement `Config.reload()` with atomic validation
- Engine subscribes to config changes via callback
- GUI settings dialog triggers reload on save
- Preserve runtime state (queue, history, current track)

### 1.2 Dynamic Settings Apply
- Volume, shuffle, repeat apply immediately
- Chat reader/sender changes require adapter rebuild (deferred)
- Language changes update GUI immediately
- TTS voice/rate/duck apply on next synthesis

---

## Phase 2: Structured Logging & Observability

### 2.1 JSON Structured Logging
- Add `log_json` config option
- Implement `JsonFormatter` with structured fields
- Include: timestamp, level, logger, message, trace_id, request_id, user, track_id
- Support for Loki/Grafana/Elasticsearch ingestion

### 2.2 Metrics / Prometheus Export
- Add `/metrics` HTTP endpoint (optional, configurable port)
- Export: queue_depth, current_track_duration, playback_failures_total, chat_messages_sent, chat_messages_failed, circuit_breaker_state, rate_limit_hits, active_users, uptime_seconds
- Health check endpoint already exists - enhance with metrics

### 2.3 Structured Audit Logging
- Security events: admin commands, block/unblock, config changes, login attempts
- Separate audit log file with tamper-evident format
- Include: actor, action, target, result, timestamp, correlation_id

---

## Phase 3: Webhook / API Integration

### 3.1 HTTP Webhook Server (Optional)
- Add `webhook_enabled`, `webhook_port`, `webhook_secret` config
- FastAPI/Starlette based (minimal deps)
- Endpoints:
  - `POST /webhook/play` - queue a track
  - `POST /webhook/skip` - skip current
  - `POST /webhook/volume` - set volume
  - `GET /webhook/status` - current state
  - `GET /webhook/queue` - queue snapshot
  - `GET /webhook/health` - health check
- HMAC signature verification
- Rate limiting per IP

### 3.2 Event Webhooks (Outbound)
- Configurable webhook URLs for events:
  - `track_started`, `track_completed`, `track_failed`
  - `user_requested`, `user_skipped`, `user_voted`
  - `admin_action`, `user_blocked`, `user_banned`
  - `circuit_breaker_opened`, `circuit_breaker_closed`
- Retry with exponential backoff
- Signature verification for receiver

---

## Phase 4: Plugin System

### 4.1 Plugin Architecture
- `plugins/` directory with entry points
- Plugin interface: `on_load(engine)`, `on_unload()`, `on_track_start(track)`, `on_track_end(track)`, `on_command(cmd, msg)`, `on_chat(msg)`
- Config: `plugins = ["plugin_name"]` with per-plugin settings
- Hot reload support (unload/reload)

### 4.2 Built-in Plugins
- `stats` - track play statistics, top users, top tracks
- `lyrics` - fetch and display lyrics (optional)
- `lastfm` - scrobble to Last.fm
- `discord` - Discord webhook notifications
- `spotify` - Spotify link resolution

---

## Phase 5: Enhanced Security & Validation

### 5.1 Input Sanitization Hardening
- All user inputs validated at boundaries
- Command arguments: length, charset, injection prevention
- Config values: strict type/range/regex validation (already done)
- File paths: path traversal prevention (already done)

### 5.2 Audit Logging Enhancement
- Structured audit events for all security-relevant actions
- Tamper-evident log format (append-only, hash-chained)
- Config: `audit_log_enabled`, `audit_log_path`, `audit_log_max_size`

### 5.3 Dependency Scanning Integration
- `make security-audit` already exists
- Add SBOM generation to CI (already in release.yml)
- Add vulnerability scanning to PR checks

---

## Phase 6: Performance Optimizations

### 6.1 Async/Await Migration (Selective)
- Convert blocking I/O to async where beneficial:
  - yt-dlp metadata extraction
  - HTTP requests for webhooks
  - File I/O for playlist/logs
- Keep mpv subprocess sync (IPC requires it)

### 6.2 Caching Enhancements
- LRU cache for yt-dlp search results (TTL configurable)
- LocalIndex: persistent index file (avoid re-scan on restart)
- Playlist: in-memory cache with dirty flag

### 6.3 Memory Profiling
- Add `tracemalloc` integration for memory leak detection
- Periodic memory stats in health check
- GC tuning for long-running process

---

## Phase 7: Graceful Degradation & Resilience

### 7.1 Fallback Modes
- `chat_reader=logtail` - read from log file when UIA fails
- `chat_sender=webhook` - send via HTTP when UIA fails
- `player=mock` - test mode without mpv
- Automatic fallback with notification

### 7.2 Circuit Breaker Enhancements
- Separate breakers per failure type (resolve, playback, chat)
- Configurable thresholds per breaker
- Metrics export for breaker state
- Manual reset command for admins

### 7.3 Dead Letter Queue
- Failed tracks moved to DLQ with reason
- Admin command to retry/review DLQ
- Automatic retry with backoff

---

## Phase 8: Documentation & Developer Experience

### 8.1 API Documentation
- Sphinx/OpenAPI docs for webhook API
- Type stubs for public API
- Architecture decision records (ADRs) for major changes

### 8.2 Developer Tools
- `make dev-setup` - one-command dev environment
- Pre-commit hooks (already in Makefile)
- VS Code launch configs
- Debug logging presets

### 8.3 Operations Runbooks
- Deployment guide
- Troubleshooting flowchart
- Capacity planning
- Incident response procedures

---

## Phase 9: Testing Enhancements

### 9.1 Property-Based Testing
- Hypothesis for config validation
- Property tests for PlayQueue invariants
- Fuzzing for command parsing

### 9.2 Integration Tests
- Full engine lifecycle with fake mpv
- Chat adapter contract tests
- End-to-end scenario tests

### 9.3 Chaos Testing
- Random failure injection in CI
- Network partition simulation
- Resource exhaustion tests

---

## Phase 10: Final Validation & Release

### 10.1 Full Validation Suite
- Run `make all` (all verification checks)
- Run `make validate-all` (alias)
- Run `make full-validation` (source validation)
- Run `make security-check` + `make security-audit`
- Run `make test` on Windows + Linux

### 10.2 Release Preparation
- Update CHANGELOG.md with all changes
- Bump version (semantic versioning)
- Create signed release artifacts
- Generate SBOM and attestations
- Update all documentation

---

## Implementation Priority

| Priority | Phase | Effort | Impact |
|----------|-------|--------|--------|
| P0 | 1, 2 | Medium | High - Operations |
| P1 | 3, 7 | Medium | High - Integration/Resilience |
| P2 | 4, 6 | High | Medium - Extensibility/Performance |
| P3 | 5, 8, 9 | Medium | Medium - Security/DX/Quality |
| P4 | 10 | Low | High - Release Readiness |

---

## Success Criteria

- [ ] All existing 450 tests pass
- [ ] New tests cover all new functionality (>90% coverage)
- [ ] `make all` passes with zero warnings
- [ ] `make security-audit` shows 0 vulnerabilities in declared deps
- [ ] Performance benchmarks show no regression
- [ ] Documentation updated and consistent
- [ ] Release pipeline produces verified artifacts
- [ ] Zero critical/high findings in security review