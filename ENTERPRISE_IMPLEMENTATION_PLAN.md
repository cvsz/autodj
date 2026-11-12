# Enterprise-Grade Implementation Plan — CamfrogAutoDJ

## Current State Assessment (VERIFIED)
- ✅ Tests: 336 passed, 2 failed (Linux-specific on Windows), 3 skipped
- ✅ Ruff: All checks passed
- ✅ Ruff Format: 95 files already formatted
- ✅ Mypy: Success — no issues in 42 source files
- ✅ CompileAll: No errors
- ✅ GitHub CLI: Both `cvsz` and `policedbc` authenticated
- ⚠️ ShellCheck: Not applicable on Windows (scripts are POSIX shell)

## Priority 1: Core Architecture Improvements

### 1.1 Webhook Module Refactoring (Critical)
**Issue**: Global mutable state (`_engine`, `_config`) in `webhook/server.py` — not thread-safe, breaks test isolation.
**Fix**: 
- Replace globals with dependency injection via FastAPI lifespan/app.state
- Make FastAPI/uvicorn imports lazy (inside functions) to avoid mandatory dependency
- Add proper type hints for all public APIs

### 1.2 Configuration Validation Enhancement
**Issue**: Config validation is solid but could benefit from:
- Cross-field validation (e.g., `auto_launch=true` requires `camfrog_exe` and `room`)
- Better error messages with config file line numbers
- Schema versioning for forward compatibility

### 1.3 Engine Circuit Breaker & Health Checks
**Status**: Already implemented but needs:
- Metrics export (Prometheus format) for monitoring
- More granular health check categories
- Configurable thresholds via config.toml

### 1.4 Audio Engine Robustness
**Status**: Good — one mpv per track, IPC control, graceful timeout
**Improvements**:
- Add audio format validation before playback
- Implement playback quality metrics (buffer health, underrun detection)
- Add support for multiple audio outputs (virtual cables)

## Priority 2: Type Safety & Code Quality

### 2.1 Strict Type Checking
- Enable `disallow_untyped_defs = true` in mypy config (incremental)
- Add type stubs for pywinauto, pyttsx3, mutagen where possible
- Fix any `Any` type escapes in public APIs

### 2.2 Protocol-Based Adapters
- Define `ChatAdapter` as a `Protocol` for better structural typing
- Add runtime verification for adapter implementations

### 2.3 Dataclass Validation
- Use `__post_init__` validation in all dataclasses
- Add `frozen=True` where appropriate for immutability

## Priority 3: Performance Optimizations

### 3.1 Library Scanning
- Implement incremental scanning (only changed files)
- Add metadata cache persistence across restarts (already partially done)
- Parallelize yt-dlp extractions with bounded concurrency

### 3.2 GUI Rendering
- Reduce animation tick rate when window is minimized/occluded
- Implement virtualized list for queue/history (only render visible items)
- Cache gradient computations for static UI elements

### 3.3 Chat Processing
- Batch chat line processing to reduce lock contention
- Use `collections.deque` with maxlen for all bounded buffers (already done)

## Priority 4: Security Hardening

### 4.1 Input Validation
- Sanitize all user-provided strings before sending to Camfrog
- Validate YouTube URLs against allowlist before resolution
- Rate-limit all external API calls (yt-dlp, webhook endpoints)

### 4.2 Secrets Management
- Ensure `.env` is never committed (already in .gitignore)
- Add runtime validation that no secrets are in config.toml
- Support reading secrets from Windows Credential Manager / keyring

### 4.3 Command Authorization
- Document nickname spoofing risk clearly (already in code comments)
- Add optional HMAC-signed command verification for webhook
- Implement audit logging for all admin commands

## Priority 5: Testing & Validation

### 5.1 Test Coverage
- Target: ≥90% line coverage for core modules (engine, player, queue, config)
- Add integration tests for: mpv IPC, UIA adapter, webhook server
- Add property-based tests for playlist/queue operations

### 5.2 Chaos Testing
- Simulate mpv crashes, hangs, IPC failures
- Test network partitions during yt-dlp resolution
- Verify graceful degradation under resource exhaustion

### 5.3 Performance Benchmarks
- Track startup time, memory usage, CPU under load
- Benchmark library scan with 10k+ files
- Measure GUI frame time under animation load

## Priority 6: Documentation & Operations

### 6.1 API Documentation
- Generate OpenAPI spec from webhook FastAPI app
- Document all config.toml options with examples
- Add architecture decision records (ADRs) for major choices

### 6.2 Operational Guides
- Runbook for common failure scenarios
- Capacity planning guide
- Upgrade/downgrade procedures

### 6.3 Changelog & Versioning
- Automate changelog from conventional commits
- Semantic versioning enforcement in CI

## Priority 7: CI/CD & Release Automation

### 7.1 GitHub Actions
- Matrix testing: Windows (latest), Ubuntu (latest), Python 3.11-3.13
- Dependency review on PRs
- Security scanning (bandit, safety, pip-audit)
- Automated release on tag push with GPG signing

### 7.2 Build Pipeline
- PyInstaller spec generation from shared template
- NSIS installer build on Windows
- AppImage/Flatpak on Linux (future)

## Implementation Order

| Phase | Tasks | Est. Effort | Dependencies |
|-------|-------|-------------|--------------|
| 1 | Webhook refactor, config cross-validation | 2-3 days | None |
| 2 | Type safety upgrades, protocol adapters | 1-2 days | Phase 1 |
| 3 | Performance optimizations | 2-3 days | Phase 1-2 |
| 4 | Security hardening | 1-2 days | Phase 1 |
| 5 | Test coverage & chaos tests | 3-4 days | Phase 1-4 |
| 6 | Documentation & ADRs | 1-2 days | Phase 1-5 |
| 7 | CI/CD pipeline | 1-2 days | Phase 1-6 |

**Total Estimated**: 11-18 days for full enterprise-grade readiness

## Success Criteria (Definition of Done)

- [ ] All tests pass on Windows + Linux CI
- [ ] Mypy strict mode passes (`disallow_untyped_defs=true`)
- [ ] Zero Ruff violations, zero format issues
- [ ] ≥90% test coverage on core modules
- [ ] Webhook module has no global mutable state
- [ ] Health check endpoint returns Prometheus metrics
- [ ] Documentation sync: README, config.example.toml, CHANGELOG, docs/
- [ ] GPG-signed commits, PR workflow documented and tested
- [ ] Release tag creates installer + checksums automatically