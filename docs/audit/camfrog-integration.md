# Camfrog Integration — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Status:** Reviewed; live integration NOT IMPLEMENTED on this host

## Adapters

| Adapter | File | Role | Platform |
|---------|------|------|----------|
| `base.py` | `adapters/base.py` | `ChatAdapter` ABC, `ChatMessage`, `parse_line`, `diff_lines` | Cross-platform |
| `console.py` | `adapters/console.py` | stdin/stdout chat for testing (`!play x` = admin; `nick: text` = user; `im nick: text`) | Cross-platform |
| `logtail.py` | `adapters/logtail.py` | read-only chat log tail; read-only `send` | Cross-platform |
| `uia.py` | `adapters/uia.py` | Windows UI Automation; web view + text control layouts; background/foreground send modes | Windows only |
| `winmsg.py` | `winmsg.py` | posted Win32 messages to chat HWND (no focus/clipboard steal) | Windows only |
| `webchat.py` | `webchat.py` | embedded web-view chat parsing (avatar-split message boundaries) | Windows only |

## Key behaviors

- Composite adapter: reader + sender may differ (`chat_reader`/`chat_sender`).
- `NullAdapter`: fallback when Camfrog unreachable; GUI still opens; chat degrades gracefully (warning logged, messages dropped visibly).
- UIA is COM-based: reader/sender threads share a `threading.RLock` (`com_lock`) to avoid wedging COM.
- `send_mode`: `background` (posted messages, no focus change), `foreground` (focus + paste, restores clipboard/window), `auto` (background + verify, then foreground fallback).
- Duplicate delivery avoided: engine `_remember_sent`/`_is_echo` (echo TTL 120 s) ignores the bot's own lines; `_appeared` verifies background sends before accepting.
- Authorization: nickname-based admin (documented spoofable), fail-closed empty admin list, blocked users ignored.

## What was NOT tested (and not claimed)

- Real Camfrog client: no authorized Camfrog test environment on this host.
- UI Automation against a live window: Windows-only, requires pywinauto + Camfrog.
- Clipboard integration live: Windows-only.
- `--discover`, `--windows`, `--dump`, `--say`: require Camfrog window / pywinauto.

**Live Camfrog integration is classified NOT IMPLEMENTED / BLOCKED. Mocks alone do not prove integration correctness.** Per policy, no claim of successful live Camfrog integration is made.

## Failure modes reviewed

Wrong window selection, window closed, process restart, chat control unavailable, UIA failure, clipboard failure, invalid commands, unauthorized commands, rate limits, Unicode messages, long messages — handled in `uia.py`/`engine.py`/`commands.py` with logging and graceful degradation. Not executed live.
