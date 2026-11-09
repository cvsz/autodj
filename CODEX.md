# CODEX.md — ZEAZ Codex Operating Instructions (AutoDJ)

Read `AGENTS.md` first. Use `ZEAZ-INTRODUCTION.md` as the shared execution framework.

## Project: Camfrog AutoDJ v0.2.8

**Repository:** https://github.com/cvsz/autodj  
**Type:** Production DJ automation platform (not template)  
**Stack:** Python 3.11+, Tkinter, mpv/yt-dlp, UIA  
**Platforms:** Windows (primary), Linux (headless/CI)

---

## Quick Reference

| File | Purpose |
|------|---------|
| `engine.py` | Core: Engine, player loop, chat loop, autoplay logic |
| `gui.py` | Tkinter GUI: App, animation, settings dialog, polling |
| `player.py` | mpv wrapper: IPC, play/stop, fade, position query |
| `library.py` | Scan/metadata: scan_folder, LocalIndex, remote_tracks |
| `commands.py` | Router: cooldown, rate limit, IM/room, admin/auth |
| `config.py` | Fail-closed TOML: Config, ConfigError, MessageStyle |
| `playlist.py` | Persistence: PlaylistStore, atomic JSON |
| `renderer.py` | Font/style preview: MessageRenderer, RenderedMessage |

---

## Operating Contract

1. **Inspect first** — `git status`, `git diff`, read target module
2. **Smallest safe change** — fix root cause, no scope creep
3. **Run validation** — pytest, ruff, mypy, compileall, shellcheck
4. **Evidence states** — `VERIFIED`/`PARTIALLY VERIFIED`/`UNVERIFIED`/`BLOCKED`/`NOT APPLICABLE`
5. **Never fabricate** — BLOCKED is honest, not failure
6. **Security first** — nickname auth spoofable, fail-closed, no shell=True

---

## AutoDJ-Specific Rules

### Audio Engine
- One mpv/track via `subprocess.Popen` + JSON IPC
- `mpv_timeout` = grace period (duration + timeout)
- Hang detection @0.5s; terminate → kill
- IPC logs cleaned; no leaks
- GUI polls position via IPC (`get_time_pos`) + wall-clock fallback

### GUI Concurrency
- Zero blocking on main thread
- All cross-thread via `tk.after(0, callback)`
- Reentrancy guards: `_loading_folder`, `_set_adding_state`
- Timers cancelled on close

### Library Safety
- **Never follow symlinks** — `is_symlink() → continue`
- Bounded: `max_dirs` (recursion), `limit` (tracks)
- Per-entry `PermissionError` caught
- `mutagen` errors → filename fallback

### Config
- Fail-closed `ConfigError` with line+column marker
- Atomic write: `.tmp` → `os.replace()` → `.bak`
- Auto-relocate to `%APPDATA%\Camfrog AutoDJ\`
- `MessageStyle` = GUI preview only (Camfrog = plain text)

### Security
- Nickname auth spoofable → documented, fail-closed (`admins = []`)
- IM requires room presence (`im_require_room_presence = true`)
- Blocked users silently ignored
- No `shell=True`, no `pickle`/`yaml.load`

---

## Validation Commands

```bash
# Full suite
python -m compileall -q camfrog_autodj tests tools
python -m pytest -q -p no:faulthandler -p no:cacheprovider
ruff check camfrog_autodj tests tools
ruff format --check camfrog_autodj tests tools
mypy camfrog_autodj
shellcheck scripts/*.sh tools/*.sh

# Security
git ls-files | grep -E '(\.env|id_rsa|.*\.pem|.*\.key$)'
git verify-commit HEAD
```

---

## BLOCKED Gates (Do Not Claim)

| Gate | Blocker | Evidence |
|------|---------|----------|
| PyInstaller `.exe` | Windows 11 + VS Build Tools | `docs/audit/windows-build-review.md` |
| NSIS installer | `makensis` + NSIS 3.0+ | `docs/audit/installer-review.md` |
| Authenticode sign | OV/EV cert + timestamp | `docs/reports/AUTODJ_AUTHENTICODE_VALIDATION.md` |
| Real mpv/yt-dlp | Hardware + media | `docs/audit/playback-engine-review.md` |
| Camfrog integration | Authorized test env | `docs/audit/camfrog-integration.md` |
| GPG signing | GPG_PASSPHRASE + TTY | `docs/audit/gpg-review-merge-evidence.md` |

---

## Change Workflow

1. `git status` — inspect exact state
2. Identify smallest missing capability
3. Add test/validation first
4. Implement minimal change
5. Run all validation gates
6. Update docs: `CHANGELOG.md`, `config.example.toml`, `messages.py`, manuals
7. PR → independent review (policedbc) → controlled merge (cvsz)

---

## Documentation Sync Checklist

When modifying behavior, update:
- [ ] `CHANGELOG.md` (Unreleased)
- [ ] `config.example.toml` (new keys)
- [ ] `messages.py` (EN + TH)
- [ ] `docs/autodj-commands.{en,th}.md`
- [ ] `docs/user-manual.{en,th}.md`
- [ ] `docs/admin-manual.{en,th}.md`
- [ ] Relevant `docs/audit/*.md`

---

## Key Invariants (Do Not Weaken)

- `engine.py`: `_player_loop` single-threaded; `_chat_loop` submits to executor
- `gui.py`: `refresh` @500ms, `_tick` @30fps; `save_settings` atomic + validated
- `player.py`: IPC for all control; `CREATE_NO_WINDOW` on Windows
- `library.py`: `scan_folder` never follows symlinks
- `commands.py`: IM play-only for non-admins; sliding window rate limit
- `config.py`: `_validate` order — type → choices → ranges → regex → semantic