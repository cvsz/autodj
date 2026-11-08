# Camfrog Integration — cvsz/autodj

**Honest classification: NOT tested against real Camfrog.** Chat read/send is via Windows UI Automation (`adapters/uia.py`, `webchat.py`, `windows.py`, `winmsg.py`). Unit tests use mocks/fakes only. No real authorized Camfrog test environment is available in this Linux environment, so **live Camfrog integration is NOT claimed to work.**

## Adapters audited

| Adapter | Role | Platform | Tested |
|---------|------|----------|--------|
| `base.py` | `ChatAdapter` ABC, `ChatMessage`, `parse_line`, `diff_lines` | all | Yes (mocks) |
| `console.py` | stdin/stdout chat for testing | all | Yes |
| `logtail.py` | read-only chat-log tail | all | partial |
| `uia.py` | Windows UI Automation reader + sender (background/foreground/auto) | Windows | mocks only |

## Audited behaviors

- Window discovery: `windows.resolve`/`candidates` (process-exe filter `(?i)camfrog`, title regex, exclude, index).
- Window title matching: `window_title_re`, `process_re`, `window_exclude_re`, `window_index`.
- Process detection: `exe_name()` via `QueryFullProcessImageNameW`.
- Chat reading: web-view panes (`webchat.py`) or Document/Edit controls; `line_regex` parsing; `diff_lines` for new lines.
- Chat sending: `send_mode` = background (posted messages via `winmsg`), foreground (focus+paste via `pyperclip`+`send_keys`), auto (background + verify + fallback).
- UI Automation: `pywinauto Desktop(backend="uia")`; `com_lock` (RLock) serializes reader/sender to avoid COM wedge.
- Clipboard integration: `pyperclip` copy/paste with best-effort restore (foreground mode).
- Message parsing: `parse_line` with `line_regex`; IM detection (`[IM]`/`IM ` prefix).
- Prefix handling: `prefix` (default `!`); IM commands need no prefix.
- Admin commands: fail-closed nickname-based auth (documented spoofable).
- Authorization: `admins` set; `blocked_users`; admins cannot be blocked.
- Reconnect/recovery: `UiaAdapter._attach` rebuilds COM wrapper on failure; reader drops `_view`/`win` on error and re-attaches.
- Logging: every chat line logged (bot `>>`, user `<<`).

## Windows-specific verification

BLOCKED — `pywinauto`/`pyperclip`/Win32 APIs are Windows-only; not importable/testable here. `doctor._check_windows_uia` reports FAIL if `pywinauto`/`pyperclip` missing.

## Tested failure modes (mocks)

- Wrong window selection → `RuntimeError` ("no visible window matches").
- Window closed → reader catches `OSError`/`RuntimeError`, re-attaches.
- Process restart → `launcher.ensure_room` waits for window.
- UI Automation failure → re-attach fresh COM connections.
- Invalid commands → ignored (no prefix / unknown command).
- Unauthorized commands → `admin_only` reply / silent block.
- Rate limits → cooldown + sliding-window limit with reply.
- Unicode messages → `clean_text` strips control chars; `pyperclip` keeps Thai/Unicode.
- Long messages → `max_msg_len` wrapping; continuation lines prefixed with `…` so they never look like commands.

## Duplicate message delivery

- `_remember_sent` + `_is_echo` (ECHO_TTL=120s) prevents the bot acting on its own echoed lines.
- `send_verify` in auto mode confirms appearance before accepting background send.
- `_bg_fails` backoff: after 2 unconfirmed background sends, falls to foreground.

## Conclusion

Camfrog integration is **architecturally complete but unverified against real Camfrog** in this environment. Classification: do not claim live Camfrog integration works. Real-Camfrog testing is BLOCKED.
