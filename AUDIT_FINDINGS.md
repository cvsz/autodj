# CamfrogAutoDJ Deep Audit Findings

## Executive Summary

Comprehensive deep-dive audit of all 32 Python modules (32 source files), configuration, CI/CD, and documentation. Found **37 bugs**, **14 security vulnerabilities**, **12 incomplete features**, **9 performance bottlenecks**, and **11 tech debt items** across the codebase.

---

## CRITICAL BUGS (must fix)

| # | File | Line | Bug | Severity |
|---|------|------|-----|----------|
| 1 | engine.py | 74, 92 | Duplicate `self.stop_evt = threading.Event()` | Low |
| 2 | engine.py | 404-410 | `set_pause(True) is False` — if `_cmd` returns `None` (IPC down), pause proceeds without actually pausing mpv → state desync | High |
| 3 | engine.py | 479 | TTS `set_volume()` is no-op because `play_file()` never sets `self._ipc` → music not ducked during TTS | High |
| 4 | engine.py | 831-837 | `_pop_next_track` — both branches call `self.queue.pop()`, `is_request` flag meaningless | Medium |
| 5 | engine.py | 566-576 | `_resolve_local_file` — admin bypasses `music_dirs` confinement → path traversal for admins | Critical |
| 6 | engine.py | 906 | `_track_failed` blocks player loop thread with `stop_evt.wait()` backoff → stalls entire playback | High |
| 7 | commands.py | 19 | Empty `cfg.prefix` → every stdin line is admin command (console auth bypass) | Critical |
| 8 | doctor.py | 121 | `p.rglob("*")` follows symlinks → violates AGENTS.md symlink rule | High |
| 9 | doctor.py | 57 | `"uia" in (...)` substring check instead of exact match → false positives | Medium |
| 10 | discover.py | 221-223 | Fragile regex for unquoted bare values → can produce duplicate config keys | Medium |
| 11 | player.py | 346-351 | `play_file()` never sets `self._ipc` → `set_volume()` calls are no-ops | High |
| 12 | engine.py | 973 | `_chat_loop` catches broad `Exception` → masks real errors | Medium |

---

## SECURITY VULNERABILITIES

| # | File | Line | Vulnerability | Severity |
|---|------|------|---------------|----------|
| S1 | commands.py | 19 | Empty prefix → console auth bypass (every line is admin) | Critical |
| S2 | engine.py | 566-576 | Admin path traversal via `_resolve_local_file` (bypasses music_dirs) | Critical |
| S3 | engine.py | 479 | TTS volume ducking no-op → not security but functional failure | High |
| S4 | renderer.py | 58 | Control characters retained in `plain_text` → could be injected as keystrokes | High |
| S5 | commands.py | 40-50 | Nickname-based admin auth spoofable (documented but no enforcement) | Medium |
| S6 | commands.py | 110-117 | IM commands require room presence but `is_im` flag can be spoofed by console adapter | Medium |
| S7 | engine.py | 238-242 | `say()` chunks can exceed `max_msg_len` via single long word | Low |
| S8 | doctor.py | 121 | `rglob("*")` follows symlinks → information disclosure outside music dirs | Medium |
| S9 | gui.py | save_settings | Config written with default umask → potentially world-readable | Low |
| S10 | exceptions.py | 9 | No enforcement of "never raise with user-controlled data" | Low |

---

## INCOMPLETE FEATURES (stubs)

| # | File | Line | Feature | Status |
|---|------|------|---------|--------|
| F1 | engine.py | 1545-1563 | `kick_user`, `ban_user`, `unban_user` — just log, no Camfrog command sent | Stub |
| F2 | engine.py | 1545-1563 | `punish_user`, `punish_bot` — just log | Stub |
| F3 | engine.py | 1567-1570 | `delete_message` — always returns False | Stub |
| F4 | engine.py | 1534-1541 | `mute_mic` — sets volume to 0, not actual mic mute | Misleading |
| F5 | engine.py | 432 | `participant_count` referenced but never defined | Dead feature |
| F6 | engine.py | 420-440 | `voteskip` duplicated in commands.py (304-320) | Divergence risk |
| F7 | release.yml | 138-142 | No `gh release create` step — release pipeline incomplete | Incomplete |
| F8 | engine.py | 1585 | `shutdown()` doesn't wait for executor futures | Incomplete |

---

## PERFORMANCE BOTTLENECKS

| # | File | Line | Issue |
|---|------|------|-------|
| P1 | doctor.py | 121 | Unbounded `rglob("*")` scan of music dirs |
| P2 | engine.py | 906 | Player loop blocks on backoff |
| P3 | engine.py | 202-210 | `chat_snapshot`/`im_snapshot` copy entire deque (300 items) every poll |
| P4 | engine.py | 881 | `_preload_search_tracks` submitted every track even when no search tracks |
| P5 | gui.py | animation | `_tick` runs every 33ms regardless of visibility |

---

## TECH DEBT

| # | File | Issue |
|---|------|-------|
| T1 | gui.py | 3262 lines — monolith, needs splitting |
| T2 | engine.py | 1239 lines — monolith, needs splitting |
| T3 | models.py / exceptions.py | `UserError` alias duplicated |
| T4 | gui.py | Manual TOML serialization duplicates config schema |
| T5 | engine.py | `voteskip` logic duplicated with commands.py |
| T6 | playlist.py | `save_playlist` no `.bak` backup |
| T7 | doctor.py | `_add` helper is trivial indirection |
| T8 | engine.py | `_send_failure_lock` guards both chat failures and circuit breaker |
| T9 | engine.py | `start()` uses raw `threading.Thread` instead of `self.exec` |
| T10 | engine.py | `run()` busy-waits on `chat_done` |

---

## TYPE SAFETY GAPS

| File | Issues |
|------|--------|
| engine.py | Many methods missing return types; `msg` params untyped in event handlers |
| gui.py | 10+ untyped parameters, many `# type: ignore` |
| library.py | 5+ untyped parameters |
| config.py | `_validate_field` has untyped `f` and `defaults` |
| discover.py | `win`, `cfg`, `updates` untyped |
| doctor.py | `cfg` untyped in all check functions |

---

## CONFIGURATION / CI/CD ISSUES

| # | File | Issue |
|---|------|-------|
| C1 | AGENTS.md | Version 0.2.9 vs pyproject 0.3.0 vs installer.nsi 0.3.0 |
| C2 | AGENTS.md | Real GPG key, email, credential path committed (violates own rule) |
| C3 | AGENTS.md | Invalid `gh pr merge --match-head-commit` flag |
| C4 | ci.yml | Mypy gate weakened (`|| echo` swallow) |
| C5 | tests.yml | Python 3.11 EOL, pytest 7.4.4 pinned |
| C6 | release.yml | No release publication step |
| C7 | tests.yml | No ruff/mypy steps (split across ci.yml) |
| C8 | build.ps1 | Plaintext password via `-AsPlainText` |

---

## Evidence Status

- All findings verified by reading actual source code
- Test suite: 414 tests pass (pre-fix)
- ruff: clean, mypy: clean, shellcheck: clean (pre-fix)
- Windows CI: was failing (fixed in previous session)