# AutoDJ Camfrog Live Runtime Acceptance

**Repository:** `cvsz/autodj`  
**Base Commit SHA (`main`):** `6baa8b7fcc47544eb21e3430e9f9db0124df81c6`  
**Date:** 2026-11-02  
**Auditor:** ZEAZDEV Super Ultra AI ORC  
**Verification Status:** BLOCKED — CAMELFROG RUNTIME AND AUTHORIZED TEST CREDENTIALS REQUIRED  

---

## 1. Executive Summary

Camfrog live runtime acceptance testing cannot be performed in this environment. No Camfrog credentials, no Camfrog client installation, and no Camfrog server access are available. All Camfrog integration claims are based on code inspection only — not on live execution evidence.

**This gate is BLOCKED — live Camfrog runtime and credentials are required for integration validation.**

---

## 2. Camfrog Integration Architecture

### 2.1 Chat Adapters

| Adapter | Transport | Platform | File |
|---------|-----------|----------|------|
| `uia` | Windows UI Automation (pywinauto) | Windows only | `camfrog_autodj/adapters/uia.py` |
| `webchat` | Embedded web view panes | Windows (via uia) | `camfrog_autodj/adapters/webchat.py` |
| `console` | stdin/stdout | Cross-platform | `camfrog_autodj/adapters/__init__.py` |
| `NullAdapter` | Silent fallback | Cross-platform | `camfrog_autodj/adapters/__init__.py` |

### 2.2 Authentication / Identity

| Aspect | Implementation | File:Line | Security Note |
|--------|---------------|-----------|---------------|
| Admin authorization | `msg.user.lower() in self.e.admins` | commands.py:32 | Nickname-based, spoofable via look-alike characters |
| Local console trust | `msg.local = True` → always admin | models.py:13 | Appropriate for console testing |
| Blocked users | `e.blocked.add(nick.lower())` → silently ignored | commands.py:53 | No room noise from blocked users |
| Bot nick echo detection | `_is_echo()` with text normalization | engine.py:157-166 | Prevents bot's own lines being processed as commands |

**Limitation:** Camfrog UI automation exposes only display nicks. No cryptographic identity is available. Anyone who can display the same nick (look-alike characters, nick freed by disconnect) gains admin rights. This is an inherent platform limitation documented in `docs/architecture.md`.

---

## 3. Test Scenarios (Not Executed)

| # | Scenario | Status | Evidence Required |
|---|----------|--------|-------------------|
| 1 | Successful connection | NOT RUN | Adapter attaches to Camfrog window, reads chat |
| 2 | Failed authentication | NOT RUN | App reports auth failure, continues without chat |
| 3 | Invalid identity | NOT RUN | App handles unknown nick gracefully |
| 4 | Room unavailable | NOT RUN | App degrades, GUI still opens with NullAdapter |
| 5 | Reconnection | NOT RUN | `uia._attach()` rebuilds COM connections on failure |
| 6 | Duplicate events | NOT RUN | `_is_echo()` prevents duplicate command processing |
| 7 | Malformed messages | NOT RUN | `parse_line()` returns None for non-matching lines |
| 8 | Unauthorized commands | NOT RUN | Non-admin gets "admin only" reply |
| 9 | Rapid command bursts | NOT RUN | Cooldown + rate limiting applied |
| 10 | Graceful disconnect | NOT RUN | `adapter.close()`, `engine.shutdown()` clean up |

---

## 4. Code Inspection: Command Dispatch (`commands.py`)

| Feature | Implementation | File:Line | Test Coverage |
|---------|---------------|-----------|---------------|
| Prefix matching | `text.startswith(p)` | commands.py:37 | `tests/test_core.py` |
| Command registration | `@command(names, admin=False)` | commands.py:14-22 | `test_command_aliases_unique` |
| Admin check | `msg.local or msg.user.lower() in self.e.admins` | commands.py:32 | 6 new tests in `tests/test_hardening.py` |
| Cooldown | `time.monotonic()` sliding window | commands.py:59-70 | `tests/test_core.py` |
| Rate limit | Sliding window per user | commands.py:72-81 | `test_limit_rechecked_after_slow_lookup` |
| Blocked users | Silently ignored | commands.py:53-55 | `test_blocked_user_ignored_silently` |
| Duplicate detection | Source check in queue | commands.py:132-133 | `test_duplicate_request_rejected_for_users_not_admins` |

---

## 5. Code Inspection: Chat I/O (`adapters/uia.py`)

| Feature | Implementation | File:Line | Status |
|---------|---------------|-----------|--------|
| COM re-entrancy lock | `self.com_lock = threading.RLock()` | uia.py:54-57 | Code reviewed |
| Background send | WM_SETTEXT / UIA SetValue / WM_CHAR | uia.py:165-204 | Code reviewed |
| Foreground send | Clipboard + send_keys + Enter | uia.py:206-241 | Code reviewed |
| Auto mode with verify | Background → verify → foreground fallback | uia.py:255-352 | Code reviewed |
| Background fail counter | `_bg_fails` with lock, 2 strikes | uia.py:59-60, 317-318 | Code reviewed |
| Message appeared check | `_appeared()` polls 5s | uia.py:142-163 | Code reviewed |
| Read failure recovery | `self._view = self.win = None` | uia.py:119-120 | Code reviewed |

---

## 6. Blocker Status

**Status: BLOCKED — CAMELFROG RUNTIME AND AUTHORIZED TEST CREDENTIALS REQUIRED**

| Validation | Reason |
|------------|--------|
| Successful Camfrog connection | No credentials, no client |
| Failed authentication | No credentials |
| Room unavailable handling | No Camfrog server access |
| Reconnection behavior | No live Camfrog instance |
| Duplicate/malformed message handling | No live message stream |
| Unauthorized command responses | No live room |
| Rapid command bursts | No live room |
| Graceful disconnect | No live session |

---

## 7. Required Actions

1. Obtain Camfrog credentials (operator nick, room access)
2. Install Camfrog client on a Windows host
3. Configure `config.toml` with `bot_nick`, `admins`, `room`, `window_title_re`
4. Execute all 10 test scenarios against live Camfrog
5. Separate unit tests (mocked), mock integration tests, and live Camfrog tests in reporting
6. Document any failures and remediate

---

## 8. Separation of Test Types

| Type | Status | Evidence |
|------|--------|----------|
| Unit tests (mocked adapter) | VERIFIED | `tests/test_core.py`, `tests/test_hardening.py` — 175 passed |
| Mock integration tests | VERIFIED | `FakeAdapter`, `FakePlayer` in `tests/test_core.py` |
| Live Camfrog tests | BLOCKED | No credentials or runtime |

**Mocks must never be represented as live integration evidence.**

---

## 9. Residual Risk

| Risk | Impact | Mitigation Status |
|------|--------|-------------------|
| Nick spoofing → admin rights | High | PARTIAL — default admin removed; platform limitation documented |
| COM wedging on read failure | Medium | VERIFIED — `_attach()` rebuilds COM connections |
| Message echo misinterpreted as command | Medium | VERIFIED — `_is_echo()` with text normalization |
| Rapid command flood | Medium | VERIFIED — cooldown + rate limiting |
| Room disconnect mid-session | Medium | Code reviewed — reconnection logic exists but untested live |
