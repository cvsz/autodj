# Changelog

## 0.2.3
`make` on plain Windows PowerShell/cmd.

### Fixed
- `make help` (and every other target) failed on Windows with confusing cascading errors ("The system cannot find the path specified", then `awk` "CreateProcess ... failed") when `make` was installed but bash/awk/coreutils were not on PATH. `SHELL` no longer hard-codes the Linux path `/bin/bash` (now resolved via PATH, so it also works if Git Bash's `bash.exe` is on PATH without being at that exact path). More importantly, the Makefile now checks for `bash` up front and fails with ONE clear message explaining the two real options: run `make` from inside Git Bash, or skip `make` entirely and use `build.ps1` / `python -m pytest` directly (which is what `make` wraps anyway and needs no Unix tools at all).
- In this working tree the same Windows-`make` problem was solved a different way (never released in 0.2.3): every recipe that needs Unix utilities (awk/find/grep/cp) was rewritten as a `python -c` one-liner and `SHELL` now falls back to `cmd.exe /c` when `bash` is not on PATH, so `make` works from plain PowerShell/cmd (and `make build`/`build-clean`/`sign` call `powershell.exe` automatically from WSL2). This Makefile superseded the released fail-fast version and is kept here; `make help` keeps a documented target list in `README.md`.
- Building from WSL2: `make build` drives `build.ps1` via WSL interop's `powershell.exe`. On a machine that also has PowerShell 7, the inherited `PSModulePath` contains PS7 module dirs, PS 5.1 resolves the **PS7** `Microsoft.PowerShell.Security` first, that load fails its authorization check, the Certificate provider never registers and the sign step dies with `Cannot find drive: 'Cert'`. `build.ps1` and `tools/sign_exe.ps1` now deselect the PS7-only dirs at startup (PS 5.1 only; pwsh 7 itself is unaffected), so `make build` and `make sign` finish cleanly: `AutoDJ 0.2.3` smoke test, `signature: Valid (Signature verified.)`, DigiCert timestamp.
- The **per-track** mpv spawn (`player.play`) did not set `CREATE_NO_WINDOW` on Windows (only the `play_file` path did), so every track started from the GUI flashed a black console window behind it. `play()` now uses the same `creationflags=0x08000000` as `doctor.py`/`library.py`/`play_file`, with two new regression tests in `tests/test_v030_fixes.py` (`N-player-2`).
- The mpv **video window** itself could still appear over the GUI: `_base()` sent `--no-video` but a user's own `mpv.conf` (e.g. `force-window=yes` or the pseudo-gui profile) re-enabled window creation even for audio-only playback. The player now sends `--force-window=no` on the top of every mpv command as well -- command-line options always override config files in mpv, so the bot's window policy can no longer be overridden. Covered by `N-player-3` tests.
- Scheme-less URLs (`youtube.com/watch?v=...`, `youtu.be/x`): `engine.resolve()` now prepends `https://` when the host matches `allowed_hosts` before the remote lookup (previously these were searched as library names and came back "not found"). An empty `!play` argument raises a friendly "nothing found" error instead of falling through to the library search.
- Router (`commands.handle`) now logs every received command at INFO (`command !<name> <arg> from <user>`, plus `admin` / blocked / cooldown drops), so the operator log shows what users actually requested and why a request was silently ignored.
- `_sender` retries a failed room send once after 2s; if the retry also fails it logs `send retry failed too, dropped:` and moves on instead of leaving the outbox stuck.
- UIA adapter (`adapters/uia.py`): all UIA/COM access is serialized behind a re-entrant `com_lock` (reader thread and sender no longer race); a failed chat read now drops `win = None` so the next poll re-attaches fresh instead of staying wedged with `An event was unable to invoke any of the subscribers` until restart. `send()` is a lock-wrapped wrapper around `_do_send` that clears cached controls on any exception.
- Background-send fast path: in `auto` mode, after 2 unconfirmed background sends in a row the bot skips the verify+fallback delay and goes straight to foreground paste, so announcements no longer stall seconds per track. `_send_bg` now writes text into the chat editor via UIA `ValuePattern.SetValue` before falling back to posted WM_CHAR (Chromium editors ignore posted keystrokes without focus), and foreground sends are verified too, with a WARNING when the line never appears in the room.
- `fmt_now`/`fmt_next`: a bad `msg_now`/`msg_next` template no longer raises — it falls back to the built-in text (a typo in the template can't kill the player-loop thread).
- `player.play()` now passes the resolved yt-dlp path (`ytdlp_path`, else yt-dlp next to mpv / PATH) to mpv's `--script-opts=ytdl_hook-ytdl_path` even when `ytdlp_path=""`, so title lookups and playback use the same yt-dlp.
- New `playlist.json` store (`playlist_file` config key, default `playlist.json`): tracks requested by users (`!play`, GUI request, `!load`) are appended to the file (deduplicated by source) and join the autoplay pool (random, looping); a missing or corrupt file is never fatal. New `!last` command (aliases `requested`, `ขอล่าสุด`) shows the most recently requested tracks; covered by `tests/test_play_flow.py`.

## 0.2.2
"Grand" GUI pass: a living, decorated now-playing stage.

### Added
- The now-playing panel now has a drifting aurora backdrop (slow colour bands) with a twinkling starfield behind the record, and ~26 soft particles orbiting it that brighten and dim with the music.
- A burst of ~22 confetti pieces fires from the record whenever a new track starts (including the first).
- The whole window now has a thin border that glows pink in time with the music while a track plays, and fades out when paused/idle.
- The AUTODJ wordmark in the header has a soft duplicate-text glow behind it.
- `camfrog_autodj/visuals.py`: `aurora_offset`, `make_particles`/`particle_pos`, `confetti_burst`/`confetti_pos` (pure functions, unit-tested, no Tk needed to test them).

### Fixed
- An internal naming collision: the new window-border-glow state was stored under the same attribute (`self._glow`) already used for the vinyl's halo-ring canvas items, so turning on the border glow crashed the animation loop (`TypeError` mixing a float with a list) every frame while a track played. Caught by `tests/test_gui_logic.py` before release; renamed to `self._border_glow`.

## 0.2.1
Dev-convenience `Makefile` (cross-platform: Linux/macOS/WSL/Git-Bash with `make`; the Windows `.exe` is still built by `build.ps1`, which the Makefile just wraps).

### Added
- `Makefile` with targets for install, run (gui/console/headless), `check`/`discover`/`windows`/`say`, test (`test`, `test-v`, `test-one`, `coverage`), `lint`/`fmt`/`typecheck` (use `ruff`/`black`/`mypy` if installed, fall back gracefully otherwise), `build`/`build-clean`/`sign` (wrap `build.ps1`/`tools/sign_exe.ps1` on Windows; a clear message elsewhere), a one-shot `release` target (changelog check -> test -> build+sign -> package), `package` (zip the source tree), and housekeeping (`clean`/`clean-all`/`distclean`). `make help` lists everything.
- `make build`/`build-clean`/`sign`/`release` take `PFX=`, `PASSWORD=`, `THUMBPRINT=`, `SUBJECT=`, `NOSIGN=1` and pass them straight through to `build.ps1`'s own signing options (same env vars also still work). With none of these, `build.ps1` already signs automatically (self-signed certificate, created/trusted once) -- the Makefile does not change that default, it just exposes the same choices `build.ps1` always had.
- `tools/minipytest.py` and `tools/mutate.sh` are now part of the shipped project (previously only used ad hoc), so `make test` and `make mutation-smoke` work out of the box even before `pip install -e .[dev]`.
- `tools/package.py`: the zip-building logic `make package` uses.

### Fixed
- `tools/minipytest.py` resolved the project root incorrectly when given a single test file (`make test-one T=tests/x.py`): `camfrog_autodj` was not importable. Also did not understand pytest's `file.py::test_name` node-id syntax (silently ran zero tests). Both fixed.
- The Makefile's original `package` target built the zip with a multi-line heredoc inside a recipe; `make` runs each recipe line in its own shell by default, so the heredoc never worked (`make package` failed every time). Moved into `tools/package.py`.
- `make coverage` printed a raw `No module named coverage` twice instead of a clear message when the optional `coverage` package is not installed.

## 0.2.0
Audit release (details and evidence in `AUDIT.md`) plus a new GUI.

### Fixed
- **Bot reacted to its own chat lines.** The `!help` reply began with `!play ...`; when `bot_nick` did not match the account's real nick it was executed as a play request. Help now starts with a label, wrapped continuation lines can no longer start with the command prefix, and lines the bot posted are recognised when they come back from the room.
- **A failing track could flood the room.** With mpv missing or yt-dlp unavailable and a non-empty autoplay pool the player retried in a tight loop (measured: ~9,900 attempts and ~29,700 queued chat messages in half a second). Failures now back off (1, 2, 4 ... 30 s), are announced at most 3 times in a row, and the reason from mpv's own log is written to the log.
- **`No module named 'yt_dlp'` in AutoDJ.exe.** Lookups use `yt-dlp.exe` (next to mpv, on PATH, or `ytdlp_path`) when present and fall back to the module; if neither exists the room gets a short message and the log says exactly what to do. `build.ps1` now refuses to build when a required package is missing, bundles yt-dlp with `--collect-all`, builds without UPX, and smoke-tests the exe.
- **`config.toml` errors crashed with a traceback.** Now: the offending line with a `^`, a hint, exit code 2. Unknown settings get "did you mean", wrong types/values (`admins = "nick"` used to become the admin set `{n,i,c,k}`), bad regexes and out-of-range numbers are reported by name.
- `!remove` could remove a different request if the queue shifted (and so could the GUI's Remove button): removal is now by identity.
- A user could exceed `max_requests_per_user` by firing requests while earlier lookups were still running: limits are re-checked atomically after the lookup.
- Auto-discovery could write an unreadable config (and wrote it non-atomically): values are escaped, the result is validated before saving, the write is atomic.
- `pause`/`resume` no longer claim success when mpv's control pipe was not ready.
- GUI: one exception in the polling loop froze the window forever; the chat box grew without limit.
- Control characters in text sent to the room (typed as keystrokes) are stripped. Reloading a folder no longer duplicates the autoplay pool. The send throttle wakes up at shutdown. More worker threads, so a slow lookup does not block `!skip`.

### Added
- `--check` (diagnose mpv, yt-dlp, JS runtime hint, folders, admins, optional packages, Camfrog window), `--version`, `--log-file` / `log_file`.
- `!history` (`!ประวัติ`), `!block` / `!unblock` and `blocked_users`, refusal of songs already queued or playing, `ytdlp_path`, `poll_interval`.
- GUI redesign: neon dark theme, spinning record, animated equaliser, gradient progress, custom volume slider, ON AIR light, Queue / History / Chat tabs, shuffle/repeat chips, keyboard shortcuts, mpv-missing banner, HiDPI + dark title bar on Windows.
- Tests: 78 (was 32), including regression tests for each fix, a strict fake Tk for the GUI logic, and a pre-flight for the build environment. CI workflow, `.gitignore`, pytest settings.

### Changed
- Test fixture `make()` now returns a distinct source per request (the duplicate guard needs it).
