# Camfrog AutoDJ

Music bot for a Camfrog room: YouTube + local mp3/mp4 autoplay, `!commands`, now/next announcements, talk to room. Bot replies and GUI in English or Thai.

## What's new in 0.2.0
A full audit (see `AUDIT.md`) and a new look. Highlights: the bot no longer reads its own lines as commands; a broken track can no longer flood the room; `config.toml` mistakes are explained instead of crashing; YouTube lookups work with `yt-dlp.exe` or the bundled module; `AutoDJ.exe --check` diagnoses the setup; `!history`, `!block`, duplicate-request guard; and a redesigned GUI. Full list: `CHANGELOG.md`.

## Makefile (optional, for Linux/macOS/WSL/Git-Bash)
`make help` lists every target: `install`, `run-gui`/`run-console`/`run-headless`, `check`/`discover`/`windows`/`say`, `test`/`test-one`/`coverage`, `lint`/`fmt`/`typecheck`, `build`/`build-clean`/`sign` (wrap `build.ps1` -- still Windows PowerShell only; a clear message elsewhere), `release` (test -> build+sign -> package, one command), `package`, `clean`/`clean-all`/`distclean`.
`build.ps1` always signs by default (self-signed cert, created and trusted once); on top of that the Makefile passes through the same choices `build.ps1` already has: `make build PFX=cert.pfx PASSWORD=secret`, `make build THUMBPRINT=<hex>`, `make build SUBJECT="CN=My Company"`, `make build NOSIGN=1` (or the env vars `build.ps1` reads: `AUTODJ_PFX`, `AUTODJ_PFX_PASSWORD`, `AUTODJ_CERT_THUMBPRINT`). On Windows, run these from PowerShell with `make` installed (e.g. via `choco install make` or Git Bash), or just call `build.ps1` directly -- the Makefile is a convenience wrapper, not a requirement. The recipes are deliberately `python -c`/plain-command based (no awk/find/grep/cp/sed) and `SHELL` falls back to `cmd.exe /c` when `bash` is not on PATH, so plain PowerShell/cmd works too; from WSL2, `make build`/`build-clean`/`sign` automatically call the Windows `powershell.exe`. If `make` still not work on your shell, skip it: `python -m pip install -e . pyinstaller` then `.\build.ps1` builds and signs `AutoDJ.exe`, and `python -m pytest` runs the tests directly.

## Setup (Windows)
1. Python 3.11+, [mpv](https://mpv.io), a virtual audio cable (e.g. VB-Cable).
2. `pip install -e .` and put `yt-dlp.exe` in the same folder as `mpv.exe` (or on PATH): mpv needs it to play YouTube. Set `mpv_path` to the full path. Then run `camfrog-autodj --check` (or `AutoDJ.exe --check`): it tells you in plain words what is still missing.
3. Camfrog mic = cable output. `audio_device` in config = cable input (`mpv --audio-device=help`).
4. `copy config.example.toml config.toml`: set `admins`, `bot_nick`, `music_dirs`, `lang`.
5. Open the room window and start AutoDJ: with `auto_discover = true` it finds the room window and chat/input controls and writes `window_title_re`, `view_*`, `input_*` to `config.toml` (backup `config.toml.bak`). `--discover` does just that and exits; `--no-discover` skips it. `--windows` lists every visible window with its exe (to see what Camfrog looks like); `--dump <title_re>` prints a window's control tree. `--say "test"` sends one line into the room and exits (checks that chat sending works). Manual fallback: `python tools/inspect_ui.py`.
6. Run:
   - `camfrog-autodj --gui` desktop window
   - `camfrog-autodj` headless
   - `camfrog-autodj --console` try commands without Camfrog (`--lang th`)

## GUI
A dark "studio" window: a spinning record and an animated equaliser while a track plays (the equaliser is decorative, it does not analyse the audio), a gradient progress bar, round Pause/Skip buttons, a volume slider, an ON AIR light, and shuffle / repeat chips. The right-hand panel has three tabs: **Queue** (remove/clear), **History** and **Room chat** (say in chat, speak with TTS). Add by URL / song name / path, load a folder, add files. TH / EN pills switch the language live.
Keys: `Space` pause/resume (when no text box has focus), `Ctrl+Right` skip. A red banner appears if `mpv` cannot be found. Display scaling (125 % / 150 %) is handled; the title bar follows Windows dark mode on recent Windows 10/11.

## Commands (prefix `!`; Thai aliases in brackets)
Everyone: `play` (เล่น), `np` (เพลงนี้), `next` (ถัดไป), `queue` (คิว), `history` (ประวัติ), `voteskip` (โหวตข้าม), `remove <n>` (ลบ), `help` (ช่วยเหลือ).
Requester/admin: `skip` (ข้าม).
Admin: `pause` (หยุดชั่วคราว), `resume` (เล่นต่อ), `vol` (เสียง), `shuffle` (สุ่ม), `repeat` (วนซ้ำ), `clear` (ล้างคิว), `load` (โหลด), `say` (พูด), `speak` (ออกเสียง), `block <nick>` (บล็อก) / `unblock <nick>` (เลิกบล็อก): a blocked nick's commands are ignored silently (admins cannot be blocked; also settable as `blocked_users` in config).

Non-admins: YouTube links only, 1 track, `max_duration`, no live, `max_requests_per_user`, and a song already queued or playing is refused. Name requests search `music_dirs` first, then YouTube.

## Auto launch
`auto_launch = true` starts `camfrog_exe`, opens `join_uri_template` for `room`, then waits for `window_title_re`. It does not call the control-server API. If the control-server agent already launches/joins Camfrog, keep `auto_launch = false`: AutoDJ waits for the room window.

## Sending to the room in the background
`send_mode` in config.toml: `background` posts the text (and a click + Enter) straight to the chat window's own handle, so Camfrog stays behind your other windows and your keyboard/clipboard are untouched. `foreground` is the old way (bring Camfrog up, paste, Enter; now restores your previous window and clipboard). `auto` (default) tries background, checks the line appeared in the room (`send_verify`), and only then falls back to foreground. Keep Camfrog un-minimised or on another desktop; a minimised window is restored without taking focus. Test with `AutoDJ.exe --say "test" -v`.

## GUI copy/paste
Ctrl+C/V/X/A now work on a Thai keyboard layout too (Tk only matched Latin keys), the chat log can be selected and copied, and every text box has a right-click menu (Cut/Copy/Paste/Select all).

## Build + sign AutoDJ.exe (one script)
`python -m pip install -e . pyinstaller`, then in PowerShell: `.\build.ps1` (or double-click `build_exe.bat`, same thing).
It first verifies that every package the exe must contain (yt-dlp, mutagen, pyttsx3, pywinauto, ...) is installed in the Python it will use (`tools\check_build_env.py`; a missing one used to give an exe that started fine and failed later with `No module named 'yt_dlp'`), checks the project, builds `dist\AutoDJ.exe` with `app.ico` and `version_info.txt` (company ZEAZDEV COMPANY LIMITED), copies `config.toml`, signs the exe (SHA256 + timestamp) and prints the signature status and SHA256.
- `-Clean` wipes `build\`, `dist\`, `AutoDJ.spec` first (use after changing icon/version/options). `-NoSign` builds only.
- Certificate, in order: `-Pfx file.pfx -Password ...` (or env `AUTODJ_PFX`, `AUTODJ_PFX_PASSWORD`), `-Thumbprint <hex>` (or env `AUTODJ_CERT_THUMBPRINT`), otherwise a self-signed cert for `-Subject` is reused or created once in your user store and trusted on this PC (one Windows confirmation dialog). It also writes `cert\autodj-codesign.cer` for other PCs.
- A self-signed cert is only trusted where that `.cer` is imported. Public distribution without SmartScreen warnings needs a real code-signing certificate (OV/EV or Azure Trusted Signing), then use `-Pfx`.
- The exe is built without UPX (fewer antivirus false positives) and started once with `--version` as a smoke test. `AutoDJ.spec` mirrors the options in `build.ps1`; edit `build.ps1`, not the spec.
- Close `AutoDJ.exe` before building (it cannot be rebuilt or signed while running). `camfrog_autodj/__init__.py` must contain only `__version__`.

## Chat reader (web view)
Messages are split at the avatar images of the room's history pane, so date headers, system lines and bodies that look like a time ("10:30") no longer corrupt parsing. `web_strict_body = false` restores joining of adjacent text. Regression test: `tests/test_webchat_dump.py` (shaped after a real room dump).

## Troubleshooting
- **`Cannot start: ... TOML syntax error`**: the message shows the offending line of `config.toml` with a `^` marker. Typical causes: a note or console output pasted into the file (for example the `Thumbprint: ...` line printed by `tools\make_cert.ps1`): delete it or put `#` in front. Or copy `config.example.toml` over `config.toml`. A misspelt setting is reported with a "did you mean" hint.
- **Nothing plays / "Could not play"**: run `AutoDJ.exe --check`. The log also shows mpv's own reason (for example `[ytdl_hook] ERROR: ...`). After 3 failed tracks in a row the bot stops announcing failures in the room and backs off (1, 2, 4 ... 30 s) so a broken setup cannot flood the chat.
- **`YouTube lookup is unavailable right now`** (in the room) / `yt-dlp not found` (in the log): put `yt-dlp.exe` next to `mpv.exe`, or set `ytdlp_path`, or rebuild with `build.ps1` (which now refuses to build without the `yt_dlp` package).
- **YouTube lookups started failing after working for weeks**: update yt-dlp (`yt-dlp -U`; if you only use the bundled module, rebuild after `pip install -U yt-dlp`). Recent yt-dlp versions may also want a JavaScript runtime such as deno on PATH; `--check` mentions it when none is found.
- **The bot answers its own help text / loops**: fixed in 0.2.0 (lines the bot posts are recognised by their text); still set `bot_nick` to the nickname the bot chats as so the GUI log labels them correctly.
- **High CPU**: raise `poll_interval` (default 0.5 s).
- **Need a log to send to someone**: `AutoDJ.exe --log-file autodj.log` (or `log_file` in config).

## Caveats

- The automated suite covers queue and command behavior (EN/TH), chat parsing, launcher flow (mocked), configuration validation, player failure/timeout handling, GUI logic against a strict fake Tk, and a CLI run using a fake mpv. Run `python -m pytest -q` to verify the current checkout.
- Real Camfrog room interaction, real mpv/yt-dlp playback and natural track completion, TTS voices, Windows launch/URI behavior, the rendered GUI on a real desktop, and the signed `AutoDJ.exe` build require validation on a Windows machine with those dependencies installed. Passing mock-based tests does not certify real audio playback.
- `mpv_timeout = 0` is the default so a song is not stopped based on elapsed wall-clock time. A positive value may be configured as a recovery limit if mpv hangs; with zero, a hung mpv process must be stopped manually.
