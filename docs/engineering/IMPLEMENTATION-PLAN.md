# Enterprise Implementation Plan — Camfrog AutoDJ

**Target:** Production-grade, 100% complete, fully validated implementation  
**Version:** 0.2.9 → 0.3.0 (Enterprise)  
**Scope:** All systems — engine, GUI, commands, config, player, library, adapters, docs  
**Standard:** Enterprise / Production-Grade Ready  
**Evidence States:** VERIFIED / PARTIALLY VERIFIED / UNVERIFIED / BLOCKED / NOT APPLICABLE

---

## Phase 1: Audit & Gap Analysis (COMPLETE)

All source files read and understood:
- `camfrog_autodj/engine.py` — Core engine with chat loop, player loop, RE integrations
- `camfrog_autodj/gui.py` — Tkinter GUI with settings, chat, queue, history, IM viewer
- `camfrog_autodj/commands.py` — Command router with admin/IM security
- `camfrog_autodj/config.py` — Config dataclass with fail-closed validation
- `camfrog_autodj/player.py` — mpv player with IPC, IPC log cleanup, fade
- `camfrog_autodj/library.py` — yt-dlp extraction, local index, folder scanning
- `camfrog_autodj/commands.py` — Router with TOCTOU protection, rate limiting
- `camfrog_autodj/adapters/uia.py` — Windows UI Automation chat reader/sender
- `camfrog_autodj/adapters/base.py` — ChatMessage dataclass, ChatAdapter ABC
- `camfrog_autodj/messages.py` — EN/TH i18n strings
- `camfrog_autodj/renderer.py` — Message rendering (plain text only for sending)
- `camfrog_autodj/textutil.py` — clean_text, norm helpers
- `camfrog_autodj/visuals.py` — Pure animation helpers (no tkinter)
- `camfrog_autodj/tts.py` — Serialized TTS worker (COM STA thread safety)
- `camfrog_autodj/paths.py` — Executable path resolution
- `camfrog_autodj/windows.py` — Camfrog window enumeration/filtering
- `camfrog_autodj/winmsg.py` — Win32 posted message sender
- `camfrog_autodj/migrate.py` — Config migration with atomic writes
- `camfrog_autodj/doctor.py` — --check diagnostics
- `camfrog_autodj/discover.py` — Auto-discover room window and controls
- `camfrog_autodj/launcher.py` — Camfrog auto-launch
- `camfrog_autodj/playlist.py` — Persistent playlist.json with atomic writes
- `camfrog_autodj/playqueue.py` — Requests-first, pool-second play queue
- `camfrog_autodj/camfrog_font.py` — Camfrog registry font read/write
- `camfrog_autodj/clipkeys.py` — Tk-free clipboard key mapping

**Current validation state:** 375 tests pass, ruff/mypy/format/shellcheck clean.

---

## Phase 2: Enterprise-Grade Implementation

### 2.1 Type Safety & Architecture Improvements

| Issue | Location | Fix | Status |
|-------|----------|-----|--------|
| Missing return type hints | All modules | Add explicit return types | TODO |
| C901 complexity in `_chat_loop` | engine.py | Extract methods | TODO |
| C901 complexity in `_refresh` | gui.py | Extract methods | TODO |
| Missing `__all__` exports | All modules | Add `__all__` | TODO |
| Inconsistent exception hierarchy | All modules | Add `AutoDJError` base + specific exceptions | TODO |
| Missing input sanitization | engine.py, commands.py | Add input validation layer | TODO |
| No rate limiting on chat send | engine.py | Add per-nick message rate limiting | TODO |
| No health check endpoint | engine.py | Add `health_check()` method | TODO |
| No graceful degradation metrics | engine.py | Add failure tracking counters | TODO |

### 2.2 Robust Error Handling

| Issue | Location | Fix | Status |
|-------|----------|-----|--------|
| Broad except clauses | engine.py | Replace with specific exception types | TODO |
| Missing context in logs | All modules | Add structured logging with request IDs | TODO |
| Silent swallow of errors | commands.py | Always log with traceback | TODO |
| No circuit breaker | engine.py | Add circuit breaker for repeated failures | TODO |

### 2.3 Clean Architecture & Scalability

| Issue | Location | Fix | Status |
|-------|----------|-----|--------|
| Engine does too much | engine.py | Extract `ChatProcessor`, `PlaybackManager`, `ConfigManager` | TODO |
| GUI tightly coupled to engine | gui.py | Introduce interface/adapter boundary | TODO |
| No dependency injection | All modules | Add constructor injection where beneficial | TODO |

### 2.4 Missing Features to Complete

| Feature | Location | Fix | Status |
|---------|----------|-----|--------|
| IM viewer GUI settings | gui.py | Add IM settings to settings dialog | ✅ DONE |
| IM auto-reply config | config.py/gui.py | Add IM auto-reply fields | ✅ DONE |
| Name color tracking in GUI | renderer.py | Apply tracked nick colors to GUI preview | TODO |
| Config schema documentation | docs/ | Document every config key | TODO |
| Integration tests | tests/ | Add end-to-end integration tests | TODO |
| Penetration/security tests | tests/ | Add security test suite | TODO |

---

## Phase 3: Validation & Testing

All gates must pass:
- `python -m compileall -q camfrog_autodj tests tools`
- `ruff check camfrog_autodj tests tools`
- `ruff format --check camfrog_autodj tests tools`
- `mypy camfrog_autodj`
- `python -m pytest -q -p no:faulthandler -p no:cacheprovider`
- `shellcheck scripts/*.sh tools/*.sh`
- Integration tests pass
- Security/penetration tests pass

---

## Phase 4: Documentation

Update all docs:
- README.md — Feature list, configuration reference
- docs/architecture.md — System architecture
- docs/engineering/ — Implementation details
- docs/audit/ — Audit reports
- Final-Report.md — Comprehensive final report
- CHANGELOG.md — Version history

---

## Phase 5: Git Workflow

1. Create feature branch as cvsz
2. Implement all changes
3. Run validation gates
4. GPG-signed commit
5. Push branch
6. Open PR as cvsz
7. Switch to policedbc, review, approve
8. Switch back to cvsz, merge with --match-head-commit

---

**Current phase: Phase 2 — Enterprise Implementation**
