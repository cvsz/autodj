# Architecture Review — Camfrog AutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Status:** Reviewed; architecture is sound, no rewrite recommended

## Package structure

`camfrog_autodj/` — `__init__.py` (version only), `__main__.py` (CLI + orchestration), `config.py`, `models.py`, `paths.py`, `library.py`, `playlist.py`, `playqueue.py`, `player.py`, `engine.py`, `commands.py`, `messages.py`, `migrate.py`, `discover.py`, `doctor.py`, `launcher.py`, `tts.py`, `textutil.py`, `clipkeys.py`, `visuals.py`, `webchat.py`, `gui.py`, `adapters/{base,console,logtail,uia}.py`, `windows.py`, `winmsg.py`.

## Module boundaries

- `__main__.py` parses args, loads/migrates/relocates config, builds adapter + engine, runs GUI or headless.
- `Engine` owns chat, queue, playlist, player, router, and background threads.
- `MpvPlayer` owns the mpv subprocess and IPC.
- `ChatAdapter` ABC isolates chat platforms; `Composite` splits reader/sender; `NullAdapter` degrades gracefully.
- `gui.py` (Tk) is the only GUI toolkit; all cross-thread UI updates use `tk.after(0, ...)`.

## Circular dependencies

None found. `adapters/uia.py` imports `..windows` and `..webchat` lazily inside methods (Windows-only imports), avoiding import-time hard dependencies on non-Windows platforms.

## Type hints / dataclasses

`from __future__ import annotations` used throughout; `Track` is a dataclass; `Config` is a dataclass with validation. `mypy ignore_missing_imports = true` (dependencies ship no stubs).

## Conclusion

Maintain the existing architecture. No unnecessary rewrite. The one test gap (library scan symlink safety) was closed with `tests/test_library_scan_safety.py` without changing architecture.
