## 0.3.8 — 2026-11-19

- **Private IM replies; join the room first** — the UIA adapter can now answer in the sender's open Camfrog IM window (`send_im`: background send verified by reading the IM history back, foreground paste as fallback). An IM from someone who is not in the room (`im_require_room_presence`, default on) is answered privately with "กรุณาเข้าห้อง {room} ก่อนถึงสามารถขอเพลงได้" (EN: "Please join room {room} before requesting songs."), at most once per `im_auto_reply_cooldown`; its command is still not executed. Outgoing IMs show in the IM viewer and are filtered as echoes. Presence comes from room activity seen since AutoDJ started (joins and room messages).
- **IM only from users in the room** — with `im_require_room_presence` (default on) an IM is now ignored entirely (no auto-reply, no plugin event, no command) unless its sender has been seen in the room (join notice or room message); this now applies to admins too, since a nickname alone is spoofable from outside the room. The IM still shows in the IM viewer. Camfrog leave notices are not detected, so a user who left counts as present until AutoDJ restarts.
- **IMs stay private** — incoming IMs were also written into the GUI room-chat log, and the IM auto-reply was posted into the public room as "[IM auto-reply to <user>] ...". IMs now appear only in the IM viewer; the auto-reply is sent only through an adapter that can send IMs (`send_im`) and is otherwise skipped (logged), never posted to the room.
- **No more false "cannot play" messages** — mpv often exits with code 1 at the end of a YouTube stream (dropped connection or hook error at EOF) after the whole song played; such tracks were marked FAILED and the room was told "เล่นไม่ได้: <title>". A non-zero exit after playing to within 5 s of the duration now counts as completed. Real failures are still logged and skipped with back-off, but are no longer announced in the room.
- **Room welcome** — new default `welcome_message_message`: "ยินดีต้อนรับ {user} เข้าสู่ {room} สถานีเพลง อัตโนมัติ 24/7 ชั่วโมง". Greetings still follow permission: admins get `admin_greeting_message`, everyone else the welcome. Blocked users are no longer greeted (they were welcomed on join and on their first message although every other path ignores them).
- **Freeze on the first private message (P0, found in a live Camfrog test)** — `Engine._handle_im_message` called `say()` while holding the non-reentrant `_chat_lock`; `say()` → `log_chat()` takes the same lock, so the chat loop deadlocked on the first IM and the GUI froze with it (`chat_snapshot`). IM auto-reply is on by default, so every 0.3.7 install was affected once IMs were read. The cooldown is now claimed under the lock and the reply sent outside it.
- **IM viewer missed the first message of every new chat** — a chat window that opens after startup already contains the first IM, and the reader treated it as old history. Lines from new windows are now delivered when their timestamp is recent (history in windows open at startup is still never replayed). The IM log is also updated under the lock the viewer reads with.
- Camfrog windows without an IM pane (buddy list, popups) are no longer re-scanned and logged on every poll.
- **GUI freezes** — Skip, Prev and Ctrl+Right ran `MpvPlayer.stop()` (fade-out plus up to 5 s waiting for mpv) on the Tk main thread; they now run in the background.
- **Discover button did nothing in the installed exe** — it ran `AutoDJ.exe -m camfrog_autodj --discover`, which argparse rejects in a PyInstaller build, and it blocked the window while running. It now calls the exe directly, runs in the background and shows the result.
- **`--discover` without UIA started the bot** — with `chat_reader`/`chat_sender` not set to `uia`, the flag fell through and launched AutoDJ normally; it now explains the requirement and exits.
- **Add files could leave the Add button disabled** — completion was counted with an unsynchronised `-= 1` from several worker threads; counting now happens on the Tk thread. The "queued" hint now shows the real queue position instead of always "#1".
- **Double-clicking a queued song could drop it** — moving it to the front was refused by the duplicate check after the song had been removed. The room announcement now names the real requester instead of "you".
- Engine callbacks that arrive after the window closed no longer raise in worker threads.
- **Dependencies** — consolidates the open Dependabot updates: webhook extra floors raised to `fastapi>=0.163.1`, `uvicorn>=0.54.0`, `pydantic>=2.14.3`, `httpx>=0.28.1`; hot-reload extra moves to `watchdog>=7.1.0,<8` (#236-#240). `github/codeql-action` 4.39.1 -> 4.39.3 (#186). `softprops/action-gh-release` 2.0.8 -> 3.0.4, moving the release step off the deprecated Node 20 runtime (#235). All pinned by commit SHA (verified against the release tags).
- **Audit Docker image** — base image `python:3.12-slim` -> `python:3.15-slim` (#185), and the image now installs the `webhook` and `hotreload` extras: with `[dev]` alone its build-time self-test failed at collection (`tests/test_webhook_server.py` needs fastapi) on any Python version.

## 0.3.7 — 2026-11-19

- **Webhook `/say`, `/shuffle`, `/repeat` never worked** — `Request` was imported inside the route factory, so with postponed annotations FastAPI treated `request` as a required query parameter and every call returned 422. Now imported at module level; covered by tests.
- **Webhook DoS hardening** — the raw-body middleware busy-looped forever after a client disconnect and buffered unbounded bodies before authentication. It now stops on `http.disconnect` (400) and caps bodies at 64 KiB (413). `/say` text and `/play` query are capped at 1000 characters. Blocking engine calls (skip, pause, resume, volume, status/queue/history snapshots, metrics) run in the thread pool instead of stalling the event loop.
- **Playback could stall forever on failed requests** — when every queued request had recently failed, the player popped nothing and the autoplay pool/default song was refused because "a request is waiting". Failed songs are now skipped for 10 minutes (time-bounded, not a never-forgetting list), the pool/default song plays meanwhile, and skipped requests keep their FIFO place.
- **Duplicate requests were announced as queued** — `PlayQueue.add_request` silently dropped same-title duplicates but returned the queue length, so chat said "queued at #N", stats were recorded and the playlist persisted a song that was never queued. It now returns 0 for a dropped duplicate and `!play`, `/aplay fav`, `!hbdp` and GUI requests report "already queued".
- **`!prev` could skip the current song without re-queueing** — the duplicate check refused the re-queue; it now forces the insert.
- **mpv IPC replies mis-parsed** — an mpv event line arriving before the reply made the whole read fail JSON parsing, so position/property queries spuriously returned "unavailable". Replies are now matched line-by-line by `request_id`.
- **Library scan followed Windows junctions** — `DirEntry.is_symlink()` is False for junctions; junction loops are now skipped (`is_junction()`, Python 3.12+).
- **IM pane reader** — skipped nothing (it compared against an unset `self.pid`), read UIA without the COM lock, and kept baselines for closed windows forever. Now skips the room/own windows, holds `com_lock`, and prunes closed windows.
- **Auto-update script** — paths with `)` (e.g. `Program Files (x86)`) broke the batch block, `%` in paths was expanded by cmd, and non-ASCII paths were mangled; paths are now quoted/escaped and the script switches to UTF-8 (`chcp 65001`).
- **`top_requests.json` lost updates** under concurrent requests; writes are now serialised.
- Search-track preloading now bumps the queue version so the GUI shows resolved titles.
- Validation: 630 passed; ruff, ruff format, mypy, compileall, bandit (0 issues) clean.

## 0.3.6 — 2026-11-19

- **Release follow-up** — ships the final UI/runtime hardening from PR #241: now-playing dashboard restored, full palette coverage with the soft-slate `zplayer-light`, logs in `<install>/logs/`, and demo playlist auto-load disabled.
- **Deployment config: no playlist auto-load, default song from startup** — the deployed `config.toml` sets `playlist_file`/`playlist_dir` empty and `default_track` to `https://www.youtube.com/watch?v=HhVVVgYsBYw`. The NSIS installer writes absolute `mpv_path`/`ytdlp_path` into `config.toml` at install time.
- All version sources, documentation and installer metadata synchronized to 0.3.6. Full suite: 610 passed / 0 skipped; ruff, mypy, bandit (all metrics 0), shellcheck clean; signed build verified.

## 0.3.5 — 2026-11-18

- **Feature: zPlayer GUI theme system** — new `camfrog_autodj/theme.py` provides three palettes (`zplayer-dark` default, `zplayer-neon`, `zplayer-light`) plus font/SVG helpers inspired by the TkinterEP projects (`ttkthemes`, `python-tkextrafont`, `python-tksvg`, `ttkwidgets`). The ideas are reimplemented with the standard library only (no GPL dependency); tkinter is imported lazily so console/headless runs stay tkinter-free. Select the theme with `ui_theme` in `config.toml` or the Settings panel (EN/TH labels included).
- **Feature: redesigned now-playing dashboard** — larger track title, dedicated info panel, separate up-next preview, expanded transport controls with a **Previous** button, resizable stage artwork and refreshed progress/volume styling.
- **Feature: `Engine.prev()`** — replays the most recent history track; wired to the new Previous button (`g_prev` in both languages).
- **Feature: `welcome_message_delay`** (0–3600 s, default 0) — optionally send the room welcome after a delay using an independent daemon timer (cancelled on shutdown), so it can never starve the shared command pool; configurable in Settings and documented in `config.example.toml`.
- **Feature: live theme switching** — changing `ui_theme` in Settings now restyles the open window (widget colours, cached canvas buttons/bars and canvas items) without a restart. `PillButton.STYLES` is rebuilt from the palette and a `shade()` helper derives hover states instead of hard-coded colours.
- **UI hardening: full palette coverage** — all remaining hard-coded dark-theme colours in list selections, settings banners, chat tags, vinyl/equaliser animations, particles, LEDs and status feedback now derive from the active palette, so `zplayer-neon` and `zplayer-light` are production-ready throughout the real Tk window.
- **Fix: now-playing card was invisible** — `_card(pad=1)` returned the inner frame, so the caller packed it twice and the outer bordered card (vinyl stage, equaliser, title, transport controls) was never packed. The dashboard is now fully visible; `zplayer-light` was retuned from stark white to a soft cool-slate palette with stronger contrast.
- **Fix: logs now live in the install folder** — `*.log` files are written to `<install>/logs/autodj.log` (rotating, APPDATA fallback when read-only); `logs/autodj.log` no longer nests as `logs/logs/`; the installer creates `$INSTDIR\logs` and preserves it on upgrade.
- **Fix: demo playlists no longer auto-load** — new `playlist_dir_autoload = false` gate stops `playlist/*.json` from filling the live request queue on startup; the main `playlist.json` behaviour is unchanged.
- **Fix: actionable GUI startup error** — `python -m camfrog_autodj --gui` now explains stale pip installs that shadow the bundled `gui.py`; `camfrog_autodj.gui` is listed explicitly in the PyInstaller hidden imports.
- **Feature: one-step client update on startup** — with `auto_update_enabled` and `auto_update_apply_on_start` (default true), running AutoDJ.exe checks GitHub, downloads the newest verified `AutoDJ.exe`, stages it and launches `autodj_update.bat` to replace the installed binary before the bot starts.
- **Release: full client build archive** — tagged releases now also ship `Camfrog-AutoDJ-Full-<version>.zip` (exe, installer, config example, bundled mpv when staged) with SHA-256 checksums and attestation.
- **Fix: `--log-json` was inert and silenced all console logging** — `_configure_logging()` is now actually called from startup and a console handler is always installed before the format is switched to JSON.
- **Fix: Settings could write invalid values** — saved settings are validated with the same `Config._validate()` rules as startup before anything reaches disk; a bad `ui_theme`/`welcome_message_delay` can no longer make the next launch fail closed.
- **Security: webhook replay cache is now atomic** under concurrent requests; plugin commands pass through the same cooldown/rate-limit gate as built-ins; IM history and chat-rate state are bounded; config temp files are written `0600` on POSIX; updater URLs require HTTPS and release tags are sanitized before being written into the batch swap script; workflow secrets and dispatch inputs are passed via `env:` instead of shell interpolation.
- **Build/supply chain** — optional webhook/hot-reload modules are explicit PyInstaller hidden imports, webhook/hot-reload dependencies have upper bounds to prevent a major-version surprise in a signed build, and all `# nosec` annotations were normalized to valid bandit syntax (all issue and confidence metrics are 0).
- **Version sources** — all build/installer/version metadata and current-state documentation synchronized to 0.3.5. Full test suite passes (GUI logic, theme palettes and version consistency) with zero warnings.

## 0.3.4 — 2026-11-18

- **Greet users when they enter the room** — the greeting used to fire only for admins (and a generic welcome on a user's first message). Now every user who enters is greeted by name once per cooldown: admins get `admin_greeting_message`, everyone else `welcome_message_message`, which supports `{user}` and `{room}` (new default: "สวัสดีครับคุณ {user} ยินดีต้อนรับเข้าห้องครับ"). Arrival is detected from the room's join notice via the new `join_line_regex` (default covers "X has joined/entered the room" and "X เข้าสู่ห้อง"; editable in Settings; "" turns it off). Without a join notice, users are still greeted on their first message, never twice. Joins count for IM room-presence, and plugins get `on_join(user)`. Greeting text no longer uses `str.format`, so a stray `{` in a custom message cannot crash it. The exact Camfrog join wording is not yet verified against a live room.

## 0.3.3 — 2026-11-18

Release-only follow-up to 0.3.2 (no application code change).

- **Fix: release workflow on a repository with immutable releases** — the release was published before its assets were attached, which immutable releases reject ("Cannot upload assets to an immutable release"); the `v0.3.2` tag was used up by an empty release and cannot be reused. The workflow now creates a draft, attaches `AutoDJ.exe`, the installer, the SBOM and `SHA256SUMS.txt`, then publishes it.

## 0.3.2 — 2026-11-18

- **Release pipeline fixes found by the first signed `v0.3.2` run** — `release.yml` validated without the `webhook`/`hotreload` extras or a Tk display (tests could not import), pinned a non-existent `softprops/action-gh-release` commit, and `build.ps1` loaded the PFX with `Get-PfxCertificate -Password`, which Windows PowerShell 5.1 (used by the workflow) does not have. The PFX is now loaded with `X509Certificate2`, and a `HashMismatch` re-sign with `signtool` also works from a PFX.
- **Merge #226 (Settings in the menu bar)** — Settings now opens as a panel inside the main window from the menu bar, combined with the 0.3.2 dialog fixes (visible rows, labelled toggles, pinned Save + status). Fixed two #226 defects while merging: the scroll container was created twice (lower half of the panel empty) and closing only hid the panel (one hidden panel leaked per open). The panel is now rebuilt on open and destroyed on close; the menu is retitled on language switch.
- **Fix: searched requests lost their "requested" status once resolved** (`_resolve_track_if_search` returned a fresh Track) — the next request could cut them, or they were silently dropped when another request waited. Requester and `is_request` are now preserved.
- **Fix: default song** — a local-file `default_track` was turned into a YouTube search; a failed lookup was retried (90 s yt-dlp timeout) every repeat, blocking the player thread; "Up next" announced a pool song when the default song actually follows.
- **Fix: welcome message, admin greeting, IM auto-reply and voteskip cooldowns** used `0.0` as "never" against `time.monotonic()` (seconds since boot) — on a PC up < 1 h (cooldown) the first greeting was silently skipped.
- **Fix: TTS never ducked the music** (`play_file` ignored `duck_volume`/`restore_volume`/`timeout`); `stop()` held the player lock up to 10 s, freezing the GUI position poll; `play()` could start mpv after shutdown, leaving music playing after AutoDJ exited.
- **Fix: options that did nothing** — `allow_play_in_room` (false = song requests by IM only) and `im_require_room_presence` are now enforced; `config_hot_reload` starts the file watcher; `webhook_enabled` starts the server (secret ≥ 16 chars, `webhook` extra); `plugins` are loaded and unknown commands reach them (`!stats`, `!plugins`); plugins get `track_start/track_end/track_failed`.
- **Fix: commands** — per-user request limit now covers every play alias (aplay, addm, ขอเพลง, เล่นเพลง, เปิดเพลง, hbdp); `!hbdp` and `!aplay fav` apply the same queue/length/live-stream rules as `!play` for non-admins; `!punishbot` cannot target admins; `!skipp` works for the requester; `!deletehistory N` removes the N most recent entries; IM commands accept an optional prefix (`!np` by IM); `!load` checks relative paths too; `!ai` replies use the EN/TH texts; `!topm` count is localized; help lists admin-only commands under admin; Router limits are checked under its lock; cooldown entries survive cleanup when `cooldown` > `rate_limit_window`; favorites saves from concurrent commands no longer lose entries.
- **Build/CI** — `win11-check` had a shell-level `ifeq` (broke `build-all` on Windows); cmd-only `if not exist` lines in sh recipes; `typecheck` and CI mypy now fail on errors; `sign` signs the existing exe via `tools/sign_exe.ps1`; `validate-installer`, `validate-windows`, `validate-windows-bat` defined; `mutation-smoke` no longer needs the +x bit; `make package` excludes dot-files (`.env`, `.git-credentials`), logs, user data, vendored binaries; installer keeps user-edited playlists (`SetOverwrite ifnewer`) and no longer fails to compile without the vendored mpv bundle; release workflow requires tag == package version, a CHANGELOG section, and Authenticode signing for tags.
- `config.example.toml` documents every option (added `auto_update_*`, `ai_*`).
- **Fix: release versioning** — tag `v0.3.1` was cut while `pyproject.toml` still said 0.3.0; all version sources (`pyproject.toml`, `__init__.py`, `installer.nsi`, `version_info.txt`, `install.bat`, `install.ps1`, `build_windows.ps1`, HTTP User-Agents) now say 0.3.2 and the version tests derive the expected value from `pyproject.toml`.

- **Feature: default song (`default_track`)** — plays at startup and again whenever the request queue is empty and nobody has requested for `autoplay_idle_timeout` (30 s); repeats until the next request; a dead link falls back to the autoplay pool for 10 min. Editable in Settings. Set in this install to `https://www.youtube.com/watch?v=HhVVVgYsBYw`.
- **Fix: request rule** — a request cuts *only* the default/autoplay song; a requested song always plays to the end and later requests queue **first come, first served**. Before, every `!play` called `_cut_current()` (skipped whatever played, so request #2 cut request #1) and inserted at the queue front (`position=0`, LIFO). Same rule for `/aplay fav` and `!hbdp`. (`commands.py`, `engine.py`, `playqueue.py`, `models.py`)
- **Fix: Settings dialog was unusable** — every input was hidden behind its row frame (Tk stacking order), labels had no text until a language switch, 43 rows printed the *next* row's title as a stray note, 30 toggles had no label, and Save/Close sat after ~120 rows of scrolling. Now all rows render, toggles are labelled (EN/TH), Save/Close are pinned at the bottom with an in-dialog status line.
- **Fix: Settings save** — results/errors were posted *into the Camfrog room* via `say()`; the live config was mutated before validation (a bad value left the engine half-updated); the header language choice was reverted on save; the dialog could not be reopened after its window was destroyed and later language switches crashed on its dead labels. Save now validates a copy and applies through `Engine._on_config_reload` (also refreshes player paths, AI, updater).
- **Feature: "what song is this?" auto-answer** — room lines containing `np_question_keywords` (default: เพลงอะไร, เพลงไร, เพลงชื่อ, ชื่อเพลง, เพลงนี้ชื่อ, what song, what's playing, song name) get the now-playing reply without a command; room-wide `np_question_cooldown` (20 s) stops floods; toggle `np_question_reply` (also in Settings). (`engine.py`, `config.py`, `gui.py`, `messages.py`)
- **Feature: `!np` shows live progress** — `… (1:05/3:20)`. Templates gain `{elapsed}`, `{remaining}`, `{eta}` (`msg_next = "เพลงต่อไป อีก {eta} …"` now means the real wait, not the next song's length).
- **Fix: "Up next" announced a different song than the one that played** — `PlayQueue.pop_pool()` ignored the track `peek()` had promised and picked a new random one. (`playqueue.py`)
- **Fix: autoplay stopped after one pass** — `pop_pool()` removed each track from the pool; the pool now loops forever with a shuffle bag (no repeat until every song has played).
- **Fix: repeat-one re-posted "Now playing" on every loop** — announced once per track.
- **Fix: GUI "Save settings" silently reset keys it does not list** (`ai_*`, `auto_update_*`, `webhook_secret`, `voteskip_cooldown`, `log_json*`) — every remaining Config key is now written. (`gui.py`)
- **Fix: sender adapter fallback** — a sender that was created but failed its self-test was kept when every candidate failed, instead of falling back to `NullAdapter`. (`adapters/__init__.py`)
- **Fix: `.github/scripts/post-review-comment.sh` missing closing `fi`** — the audit-comment workflow step died with a syntax error.
- **Hardening: bandit 0 issues** (`bandit -c pyproject.toml -r .`, config in `[tool.bandit]`) — runtime `assert`s replaced with explicit checks (stripped under `python -O`), swallowed exceptions now logged, `gh`/`powershell` resolved to absolute paths; remaining subprocess/urlopen sites carry reviewed `# nosec <id> - reason` notes. shellcheck clean on all tracked scripts. Third-party `starlette.testclient` deprecation filtered in pytest config.
- **Security: auto-update now verifies SHA-256 before staging `AutoDJ.exe.next`** — the digest comes from GitHub's per-asset `digest` field or a `<asset>.sha256` / `SHA256SUMS` release asset; downloads with no published digest or a mismatch are refused and the partial file deleted. (`camfrog_autodj/updater.py`)
- **Fix: updater offered downgrades** — any tag different from the running version counted as "new"; now only a strictly newer semantic version does. Exact asset-name match (so `AutoDJ.exe` never resolves to `AutoDJ.exe.sha256`), `auto_update_repo` restricted to `owner/name`, check interval floored at 300 s, settings read live from config.
- **Fix: frozen-exe path** — `apply_update()` defaulted to `<_MEIPASS>/../AutoDJ.exe` in PyInstaller builds; now uses `sys.executable`. The generated `autodj_update.bat` aborts/rolls back if a rename fails instead of deleting the old exe.
- **Privacy: no GitHub call when auto-update is disabled** — the engine ran a startup release check even with `auto_update_enabled = false`. Update announcements now come from the updater loop (once per tag).
- **Fix: AI replies never worked** — `AIClient._post_json` reused the updater's github.com-only URL guard, so every real provider was rejected. Now requires `https://` (plain `http://` only for loopback) and rejects URLs with embedded credentials. (`camfrog_autodj/ai.py`)
- **Privacy: AI no longer answers IMs in the public room** — the adapter can only post to the room, so replying leaked private-message content. IMs are not sent to the AI provider.
- **Fix: AI calls blocked the chat loop and ignored cooldown** — room replies now run on the executor and respect `ai_user_cooldown` (`can_reply` was never called). `!ai on/off/model/prompt` and config hot-reload now rebuild the client so changes take effect; model/prompt text keeps its original case.
- **Security: webhook HMAC hardened** — signature now covers `"<X-Timestamp>.<METHOD>.<path>." + body` with a 300 s window and a one-time replay cache (previously every empty-body request — health/skip/pause/resume — shared one permanent signature). Empty or <16-char secret fails closed (503) instead of HMAC with an empty key. Rate limiter returns a real 429 (was a 500) and prunes idle IPs. JSON fields on shuffle/repeat/say are type-checked. (`camfrog_autodj/webhook/`)
- **Fix: packaging** — `pyproject.toml` listed packages by hand and omitted `plugins`, `plugins.builtin` and `webhook`; a pip install crashed on import. Switched to `packages.find`.
- **Fix: `scripts/setup-git-credential-helper.sh`** wrote the plaintext credential store to a relative `D/.git-credentials` (inside whatever repo it ran in). Now uses `$GIT_CRED_FILE` (default `~/.git-credentials`), refuses paths inside the repo, and `chmod 600`s the file.
- **Security: `.dockerignore`** — the Dockerfile does `COPY . ./` but the context did not exclude `.config/` (gh CLI token store), `cert/`, or `docs/rea/` (malware archives, memory dumps, pcap); a local `docker build` would bake them into the image. Also excludes bundled mpv and runtime state.
- Tests: `tests/test_updater_ai_hardening.py` (new) and webhook replay/stale/cross-endpoint/weak-secret/429 cases.
- **CI: Linux test run aborted partway (`Aborted (core dumped)`)** — Tk widgets still referenced when a GUI test returned were finalised by a webhook TestClient worker thread, and Tcl aborts when its interpreter is torn down off the creating thread. New `tests/conftest.py` collects garbage on the main thread after every test. (Also failed on `main`.)
- **CI: Windows Build / release could not install mpv** — `choco install mpv --version=2024.01.01` does not exist on the Chocolatey feed. Pinned to the published `2024.9.26` and the step now adds the install directory to `PATH` when the package ships no shim. (Also failed on `main`.)
- **CI: real-Tk GUI tests skip when the runner's Tcl runtime is broken** — hosted Windows/Python 3.13 runners intermittently fail to bootstrap Tcl (`init.tcl` unreadable, `tcl_findLibrary` missing) when creating the App's interpreter; that environment fault now skips instead of failing the run.
- **Fix: config hot-reload fired twice for one save on Windows** — the polling watcher can see one write as two stat changes (size, then mtime) more than a debounce window apart, so the engine reloaded the same config twice. `ConfigWatcher` now skips a reload when the file's SHA-256 matches the last loaded content. (`camfrog_autodj/config_watcher.py`)
- **Fix: tagged releases could never be signed** — `release.yml` required `AUTODJ_PFX`/`AUTODJ_PFX_PASSWORD` or `AUTODJ_CERT_THUMBPRINT` but never mapped any secret into the step, so every `v*` tag failed the signing gate. The step now reads repository secrets `AUTODJ_PFX_BASE64` (decoded to a runner-temp `.pfx`), `AUTODJ_PFX_PASSWORD` and `AUTODJ_CERT_THUMBPRINT`.
- **Fix: `auto_update_enabled` hot-reload** — turning it off in a reload left the running loop calling GitHub; turning it on never started the loop. The loop now re-reads the flag every iteration and the reload starts it when newly enabled.
- **Security: IM room-presence check for plugin commands** — unknown commands went straight to plugins with only the block-list check, bypassing `im_require_room_presence`. Plugin commands now use the same channel rules as built-ins.
- **Fix: slow AI provider could stall commands** — AI replies ran on the 8-worker command executor, so several slow provider calls delayed `!skip` and friends. They now run on a dedicated 2-worker pool; further room lines are not sent to the AI while both are busy. Blocked users are no longer forwarded to the provider, and `ai_user_cooldown` (0–86400) / `ai_max_chars` (1–2000) are range-checked so a negative cooldown is rejected at load.

## 0.3.1
2026-11-17 (tag `v0.3.1`; package metadata still read 0.3.0 — fixed in 0.3.2)

- Auto-update client for `AutoDJ.exe` from GitHub releases (`camfrog_autodj/updater.py`, `!update`).
- Type annotations across the codebase; latent errors surfaced by `mypy --check-untyped-defs` fixed.

## 0.3.0
2026-11-09 (tag `v0.3.0`)

- Enterprise release: exception hierarchy, circuit breakers, rate limiting, health checks, IM viewer.
- Camfrog integrations: gift detection, avatar change, status indicators, upgrade/payment alerts, name colour tracking; Camfrog font registry read/write.
- Windows build pipeline and security code-scanning findings remediated; webhook hardening, voteskip cooldown, favorites capacity checks.

## 0.2.7
2026-11-07

- **Fix: GUI hangs when clicking Load Folder** — `library.scan_folder()` now skips symlinks (avoids cycle/reparse-point hangs on Windows) and caps returned tracks via a `limit` argument; `gui.load_folder()` disables the folder button while scanning, guards against reentrant clicks, and shows loaded/failed status. (`camfrog_autodj/library.py`, `camfrog_autodj/engine.py`, `camfrog_autodj/gui.py`)
- **Fix: chat-log race condition between engine and GUI poller** — `Engine.chat_log`/`chat_seq` are now guarded by `_chat_lock`; GUI reads via thread-safe `chat_snapshot()`. (`camfrog_autodj/engine.py`, `camfrog_autodj/gui.py`)
- **Fix: `save_settings()` could leave a half-written `config.toml` on crash** — writes atomically via temp file + `os.replace()` with a `.bak` backup, with `%APPDATA%\\Camfrog AutoDJ\\` relocation fallback. (`camfrog_autodj/gui.py`)
- **Fix: `MpvPlayer.play_file()` could block forever on a bad WAV** — 30s subprocess timeout. (`camfrog_autodj/player.py`)
- **Fix: folder scans in autoplay sources and `!load` could scan forever** — capped at 500 tracks. (`camfrog_autodj/engine.py`)
- **Fix: `Add files` button lacked busy state** — now shows resolving state with a pending counter, matching `Add`. (`camfrog_autodj/gui.py`)
- **Fix: Player music time countdown skipping** — The GUI now queries mpv via IPC (`get_property time-pos`) for the actual playback position instead of relying on wall-clock time. Added `MpvPlayer._cmd_get()` and `MpvPlayer.get_time_pos()` in `player.py`; `Engine.position()` in `engine.py` uses real mpv position with wall-clock fallback. Fixes the issue where the time display jumped (e.g., from 00:00 to 0:01) during playback.
- Resolve MPV and yt-dlp executable paths consistently, including Windows environment variables and app-relative paths.
- Preserve the user's `config.toml` across installer upgrades and retain user data during uninstall.
- Make source-validation output explicit and keep `clean-all` from deleting the tracked PyInstaller spec.
- **Security: removed default administrator** from `config.example.toml` (`admins = []`); Camfrog UI automation exposes only display nicks, so admin authorization is nickname-based and case-insensitive — operator must add their nick before running. Added authorization/spoofing regression tests (`tests/test_hardening.py`).
- **Security: release workflow gated** — `.github/workflows/release.yml` now requires validation (tests, lint, typecheck, secret scan) before any build artifact is produced; no automatic release publication.
- **Security: CodeQL analyzes Python** (was `actions` only); **Dependabot covers pip packages** (was GitHub Actions and Docker only).
- **Security: CODEOWNERS** requires independent review (`@policedbc`) for security-sensitive paths (workflows, installer scripts, SECURITY.md, config).
- **Docs: `docs/architecture.md` and `docs/release.md` rewritten** to describe AutoDJ (not the ztemplate template).
- **Docs: `IMPLEMENTATION-CHECKLIST.md` changed to evidence-based status tracking** (VERIFIED/PARTIALLY VERIFIED/UNVERIFIED/BLOCKED with evidence references).
- **Infra: replaced placeholder Dockerfile with local audit image `zpostgresql`** — `python:3.11-slim` based image (`zpostgresql:latest` / `zpostgresql:audit`) that installs the project with dev tools and self-verifies (ruff check/format, pytest) at build time; mirrors Linux CI (`git`, `python3-tk`, `xvfb`, `xauth`) and runs as non-root user `autodj`. Replaces the unusable `alpine:3.24` placeholder.
- **Fix: release typecheck gate** — `mypy camfrog_autodj` (release.yml Gate 1) failed on the release head due to unstubbed third-party dependencies (`pywinauto`, `pyttsx3`, `mutagen`, `yt_dlp`, `pyperclip`); added `[tool.mypy] ignore_missing_imports = true` to `pyproject.toml` so the gate validates AutoDJ's own code.
- **Fix: unused noqa on blind `Exception` catch** in `camfrog_autodj/__main__.py` — `ruff format` had stranded the `# noqa: BLE001` directive; directive moved onto the `Exception` line so `ruff check` and `ruff format --check` both pass.
- **Docs: ADR 0001** — documents the local audit Docker image and mypy CI gate configuration (`docs/adr/0001-local-audit-docker-image-and-mypy-gate.md`).

## 0.2.6

### Added
- **Official v0.2.6 Delivery & Recovery**: Complete release publication with verified Windows installer (`Camfrog-AutoDJ-Setup-0.2.6.exe`), standalone `AutoDJ.exe`, CycloneDX SBOM (`Camfrog-AutoDJ-v0.2.6.cdx.json`), and cryptographic Sigstore provenance attestation.
- **Workflow Hardening & Persistent Artifact Retention**: Integrated `actions/upload-artifact@v4` in `.github/workflows/release.yml` for persistent operational retention of release build artifacts.
- **SHA256 Manifest Generation**: Automated generation of `SHA256SUMS.txt` for all release assets.
- **YouTube Playlist Support**: Auto-detects YouTube playlist URLs (`youtube.com/playlist?list=...`, `watch?v=...&list=...`) and plays all videos in sequence.
- **Per-User Installation**: Installs to `%APPDATA%\Camfrog AutoDJ` (no admin rights required).
- **Settings Tab**: New ⚙️ Settings button in the GUI header to edit all settings live and save to `config.toml`.
- **Auto-Config Relocation**: If `config.toml` is in a protected location (e.g. Program Files), AutoDJ automatically copies it to `%APPDATA%\Camfrog AutoDJ\config.toml`.
- **Log Directory Auto-Creation**: Log directory is created automatically on first run.
- **Settings Button**: New ⚙️ gear icon in the header bar opens the Settings tab.
- **Relative Config Paths**: `config.example.toml` uses `%APPDATA%\Camfrog AutoDJ\mpv\...` paths for portability.
- **YouTube Playlist Support**: Auto-detects YouTube playlist URLs (`youtube.com/playlist?list=...`, `watch?v=...&list=...`) and plays all videos in sequence.
- **Installer**: Per-user installation to `%APPDATA%\Camfrog AutoDJ` (no admin required).
- **NSIS Installer**: Per-user install to `%APPDATA%\Camfrog AutoDJ`, HKCU registry, no admin required.

### Fixed
- **GUI ไม่ขึ้น (GUI won't open)**: `camfrog_autodj/__main__.py` — auto-discovery (`discover.apply()`) crashed with `ImportError` on `pywinauto.Desktop` before `App(eng).mainloop()` was reached, so the Tk window never appeared. Auto-discovery is now wrapped in `try/except` and logs a warning instead of crashing; `build_adapter()` failures fall back to `NullAdapter` so the GUI still opens without chat (user can run `--check`/`--discover` from inside it).
- **Camfrog adapter blocks GUI startup**: `camfrog_autodj/adapters/uia.py` `UiaAdapter.__init__()` called `resolve()` which polls up to 30s for a Camfrog window, blocking GUI launch. With `NullAdapter` fallback in `__main__.py`, this no longer blocks.
- **Playlist not in queue list box**: `camfrog_autodj/engine.py` `_load_all()` added `playlist.json` tracks to the autoplay *pool* (`add_pool`), but the GUI list box only shows the request *queue* (`add_request`). Playlist tracks are now added to `add_request` so they appear in the GUI and play before the autoplay pool. Dedupe against existing requests and history prevents re-queuing on restart.
- **Thread-safety data race on `e.current`**: `camfrog_autodj/commands.py` `_play()` read `e.current.source` outside `e.queue.lock`, racing with `_player_loop()` which writes `e.current`. Now read under the same lock.
- **Ungraceful shutdown**: `camfrog_autodj/engine.py` `shutdown()` did not wait for daemon threads. Thread references are now stored in `self._threads` and joined (5s timeout each) on shutdown.
- **Windows-only code crashes on Linux**: `camfrog_autodj/launcher.py`, `camfrog_autodj/tts.py`, `camfrog_autodj/winmsg.py` now call `_require_windows()` to raise a clear `RuntimeError` instead of crashing with obscure `ctypes`/`pywinauto` errors on non-Windows platforms.
- **`!load` path traversal**: `camfrog_autodj/commands.py` `_load()` now rejects absolute paths outside `music_dirs` (admin-only guard).
- **NSIS installer warnings**: `installer.nsi` — removed `docs\*.txt` file glob (no such files), removed unused `.onUninstSuccess` function, removed unused `GetDate` function (now called inline via `Call GetDate`), removed duplicate `Uninstall.lnk` shortcut, removed `SEC_SRC` section (Python source not shipped in installer). All 5 NSIS warnings eliminated.

### Changed
- `camfrog_autodj/engine.py`: `Engine.__init__` now accepts `cfg_path` (was missing, causing `TypeError` when `_run()` passed it). GUI buttons `do_discover()`/`do_check()` read `self.e.cfg_path`.

### Added
- `camfrog_autodj/adapters/__init__.py`: new `NullAdapter` — silent fallback when Camfrog cannot be reached; GUI stays open, chat degrades gracefully.
- `camfrog_autodj/engine.py`: `_threads` list tracking all daemon threads started by `start()`.

## 0.2.4

### Fixed
- `camfrog_autodj/adapters/uia.py` `_appeared()`: `norm_l` was referenced outside the `for l in new:` loop. When no new chat lines arrived, `norm_l` was never assigned, causing `UnboundLocalError` on every background chat send — messages retried endlessly (`send failed ... retrying once in 2s`). Moved the `bot_nick` match inside the loop so `norm_l` is always defined before use, and every new line is checked (not just the last one).
- `camfrog_autodj/adapters/uia.py` `_bg_fails`: consecutive-failure counter was read/written without a lock across reader and sender threads, causing a race condition. Now protected by `_bg_fails_lock`.
- `camfrog_autodj/adapters/uia.py` `messages()`: `self._view = None` was assigned outside `com_lock`, racing with `_lines()` which reads `self._view` inside the lock. Now assigned inside `com_lock`.
- `camfrog_autodj/winmsg.py`: three module-level functions were defined twice — `make_lparam` (lines 58 and 256), `pick_child` (lines 62 and 260), `show_noactivate` (lines 117 and 273). The second definition silently shadowed the first. Removed the duplicate block.
- `camfrog_autodj/webchat.py`: unused unpacked variable `node` → `_node` in `read_items()`.
- `camfrog_autodj/gui.py`: unused unpacked variables `r`/`lab` → `_r`/`_lab` in three `_vc` unpack sites; removed unnecessary `int(round(...))` in `px()`.
- `camfrog_autodj/visuals.py`: removed unnecessary `int(round(...))` in `rgb_to_hex()`.
- `camfrog_autodj/adapters/uia.py`: merged two `endswith()` calls into one with a tuple argument.
- `camfrog_autodj/doctor.py`: replaced unnecessary `dict(...)` call with a literal.
- `camfrog_autodj/engine.py`: replaced unnecessary `dict(...)` call with a literal in `snapshot()`.
- `camfrog_autodj/library.py`: replaced unnecessary `dict(...)` call with a literal in `_extract_exe()`.
- `camfrog_autodj/gui.py`: `add_files()` and `load_folder()` now check for `$DISPLAY`/`$WAYLAND_DISPLAY` before opening native file dialogs, and wrap in try/except — fixes hang on headless Linux.
- `camfrog_autodj/installer.nsi`: removed machine-specific `config.toml` from bundle (path hardcoded to one PC); config is now created by `install.ps1` on first run.
- `camfrog_autodj/tts.py`: **TTS did nothing with default config** — `eng.save_to_file()` and `eng.runAndWait()` were inside `if cfg.tts_voice:`, so with `tts_voice = ""` nothing was synthesised. Moved outside the `if`. Also added `TTS_TIMEOUT` (60s) so `synth()` no longer blocks forever if pyttsx3 is missing or hangs; each job independently imports pyttsx3 so the worker stays alive even if it's not installed.
- `camfrog_autodj/library.py`: **`ytsearch20:` autoplay sources always failed** — `is_url()` only matches `http://`/`https://`, so `ytsearch20:mandopop` was double-wrapped as `ytsearch1:ytsearch20:mandopop` and failed. Added `SEARCH_PREFIX` regex and `raw_target` parameter so operator-supplied `ytsearchN:` queries pass through unchanged. Also fixed `find_ytdlp()` to fall back to PATH yt-dlp when `mpv_path` is the default `"mpv"` (the previous code refused PATH lookup when mpv_path was set, ignoring a perfectly good yt-dlp on PATH).
- `camfrog_autodj/commands.py`: **`!play` from chat was not saved to `playlist.json`** — only admin/GUI requests were saved, so `!last` was always empty for chat requests. Added `e.playlist.add(tracks)` for chat requests too. Also fixed cooldown case-dodging (`"Bob"` and `"bob"` are now one person via `.lower()`) and `²` digit bypass in `!remove`/`!vol` (`isascii()` check).
- `camfrog_autodj/player.py`: **`mpv_timeout` killed every track longer than the timeout** — `p.wait(timeout=120)` capped total play time, cutting any track over 2 minutes. Changed to a grace period: `limit = duration + mpv_timeout`, checked via 0.5s polling loop; pauses are excluded from the countdown; unknown-duration (live) tracks have no limit. Added `POLL` constant and `_played()` helper.
- `camfrog_autodj/playlist.py`: **corrupt `playlist.json` was silently overwritten** — `load_playlist()` returned `[]` and `save_playlist()` would overwrite the bad file. Added `_unreadable()` check and `PlaylistStore.add()` now saves a `.corrupt-<timestamp>` backup before overwriting.
- `tests/test_hardening.py`: updated `FailingPlayer.play()` and `lambda` mocks to accept the new `duration` parameter on `MpvPlayer.play()`.

### Added
- GUI: `--discover` และ `--check` ปุ่มบน now-playing card (`🔍 ค้นหาห้องแชท` / `✓ ตรวจสอบการตั้งค่า`) ให้ผู้ดูแลระบบรัน auto-discovery และวินิจฉัยการตั้งค่าจากหน้าต่างเดสก์ท็อปโดยไม่ต้องเปิดเทอร์มินัล
- `installer.nsi`: รองรับหลายภาษาในตัวติดตั้ง (English + Thai) ผ่าน `MUI_LANGUAGE` macro; ไฟล์ `thai.nlf` รวมอยู่ใน repo (ต้องติดตั้งที่ `Contrib\Language\` ของ NSIS บนเครื่อง Windows ก่อนคอมไพล์)
- `camfrog_autodj/engine.py`: `Engine.__init__` no longer takes `cfg_path` (was an experiment, removed). Added `_speak_lock` so only one TTS clip plays at a time (overlapping TTS jobs would un-duck the music early). `load_source()` now recognises `ytsearchN:` queries as raw targets for autoplay sources.
- `camfrog_autodj/engine.py` shutdown order: `adapter.close()` before `exec.shutdown()` so sender threads release the adapter before it's closed.

### Testing
- Full suite: **97 passed, 1 skipped** (was 130 passed before test mock updates for the new `duration` parameter on `MpvPlayer.play()`).
- All command paths verified end-to-end via `--lang th --console` (Thai and English).

## 0.2.3
`make` on plain Windows PowerShell/cmd. **Automated Windows 11 installer (`install.ps1` / `install.bat`).**

### Added
- `install.ps1` / `install.bat`: Full-featured automated installer for Windows 11. Verifies OS, installs prerequisites (Python 3.11+, mpv, yt-dlp, VB-Cable) via winget or direct download, clones the project, installs Python dependencies, builds `AutoDJ.exe` with PyInstaller, creates `config.toml` with interactive prompts, creates Desktop/Start Menu shortcuts (including Config editor and Uninstaller), optional auto-start on login, and runs `AutoDJ.exe --check` for verification. Logs to `%TEMP%\autodj-install-<timestamp>.log`.

### Fixed
- `make help` (and every other target) failed on Windows with confusing cascading errors ("The system cannot find the path specified", then `awk` "CreateProcess ... failed") when `make` was installed but bash/awk/coreutils were not on PATH. `SHELL` no longer hard-codes the Linux path `/bin/bash` (now resolved via PATH, so it also works if Git Bash's `bash.exe` is on PATH without being at that exact path). More importantly, the Makefile now checks for `bash` up front and fails with ONE clear message explaining the two real options: run `make` from inside Git Bash, or skip `make` entirely and use `build.ps1` directly -- the Makefile is a convenience wrapper, not a requirement. The recipes are deliberately `python -c`/plain-command based (no awk/find/grep/cp/sed) and `SHELL` falls back to `cmd.exe /c` when `bash` is not on PATH, so plain PowerShell/cmd works too; from WSL2, `make build`/`build-clean`/`sign` automatically call the Windows `powershell.exe`. If `make` still not work on your shell, skip it: `python -m pip install -e . pyinstaller` then `.\build.ps1` builds and signs `AutoDJ.exe`, and `python -m pytest` runs the tests directly.
- In this working tree the same Windows-`make` problem was solved a different way (never released in 0.2.3): every recipe that needs Unix utilities (awk/find/grep/cp) was rewritten as a `python -c` one-liner and `SHELL` now falls back to `cmd.exe /c` when `bash` is not on PATH, so `make` works from plain PowerShell/cmd (and `make build`/`build-clean`/`sign` call `powershell.exe` automatically from WSL2). This Makefile superseded the released fail-fast version and is kept here; `make help` keeps a documented target list in `README.md`.
- Building from WSL2: `make build` drives `build.ps1` via WSL interop's `powershell.exe`. On a machine that also has PowerShell 7, the inherited `PSModulePath` contains PS7 module dirs, PS 5.1 resolves the **PS7** `Microsoft.PowerShell.Security` first, that load fails its authorization check, the Certificate provider never registers and the sign step dies with `Cannot find drive: 'Cert'`. `build.ps1` and `tools/sign_exe.ps1` now deselect the PS7-only dirs at startup (PS 5.1 only; pwsh 7 itself is unaffected), so `make build` and `make sign` finish cleanly: `AutoDJ 0.2.3` smoke test, `signature: Valid (Signature verified.)`, DigiCert timestamp.
- The **per-track** mpv spawn (`player.play`) did not set `CREATE_NO_WINDOW` on Windows (only the `play_file` path did), so every track started from the GUI flashed a black console window behind it. `play()` now uses the same `creationflags=0x08000000` as `doctor.py`/`library.py`/`play_file`, with two new regression tests in `tests/test_v030_fixes.py` (`N-player-2`).
- The mpv **video window** itself could still appear over the GUI: `_base()` sent `--no-video` but a user's own `mpv.conf` (e.g. `force-window=yes` or the pseudo-gui profile) re-enabled window creation even for audio-only playback. The player now sends `--force-window=no` on the top of every mpv command as well -- command-line options always override config files in mpv, so the bot's window policy can no longer be overridden. Covered by `N-player-3` tests.
- Scheme-less URLs (`youtube.com/watch?v=...`, `youtu.be/x`): `engine.resolve()` now prepends `https://` when the host matches `allowed_hosts` before the remote lookup (previously these were searched as library names and came back "not found"). An empty `!play` argument raises a friendly "nothing found" error instead of falling through to the library search.
- Router (`commands.handle`) now logs every received command at INFO (`command !<name> <arg> from <user>`, plus `admin` / blocked / cooldown drops), so the operator log shows what users actually requested and why a request was silently ignored.
- `_sender` retries a failed room send once after 2s; if the retry also fails it logs `send retry failed too, dropped:` and moves on instead of leaving the outbox stuck.
- UIA adapter (`adapters/uia.py`): all UIA/COM access is serialized behind a re-entrant `com_lock` (reader thread and sender no longer race); a failed chat read now drops `win = None` so the next poll re-attaches fresh instead of staying wedged with `An event was unable to invoke any of the subscribers` until restart. `send()` is a lock-wrapped wrapper around `_do_send` that clears cached controls on any exception.
- Background-send fast path: in `auto` mode, after 2 unconfirmed background sends in a row the bot skips the verify+fallback delay and goes straight to foreground paste, so announcements must not stack seconds of verify+fallback latency every track. `_send_bg` now writes text into the chat editor via UIA `ValuePattern.SetValue` before falling back to posted WM_CHAR (Chromium editors ignore posted keystrokes without focus), and foreground sends are verified too, with a WARNING when the line never appears in the room.
- `fmt_now`/`fmt_next`: a bad `msg_now`/`msg_next` template no longer raises — it falls back to the built-in text (a typo in the template can't kill the player-loop thread).
- `player.play()` now passes the resolved yt-dlp path (`ytdlp_path`, else yt-dlp next to mpv / PATH) to mpv's `--script-opts=ytdl_hook-ytdl_path` even when `ytdlp_path=""`, so title lookups and playback use the same yt-dlp.
- New `playlist.json` store (`playlist_file` config key, default `playlist.json`): tracks requested by users (`!play`, GUI request, `!load`) are appended to the file (deduplicated by source) and join the autoplay pool (random, looping); a missing or corrupt file is never fatal. New `!last` command (aliases `requested`, `ขอล่าสุด`) shows the most recently requested tracks; covered by `tests/test_play_flow.py`.

## 0.2.2
"Grand" GUI pass: a living, decorated now-playing stage.

### Added

## 0.2.5

### Added
- **Dynamic search resolution for playlist tracks**: Search-backed entries (`ytsearch1:...`) from starter playlist files are dynamically resolved to real YouTube URLs, verified video titles, and exact durations upon playback and via asynchronous lookahead queue preloading.
- **Automatic playlist update on resolve**: `PlaylistStore.update_source()` replaces resolved search queries in `playlist.json` with the real YouTube URL atomically, preventing repetitive search overhead on subsequent restarts.
- **Audio fade-in and fade-out**: Smooth volume ramping upon track playback start and skip/stop.
- **Dynamic loudness normalization**: Configurable dynamic audio normalization using FFmpeg `dynaudnorm` filter in mpv.
- **YouTube authentication & cookie support**: Optional `--cookies` file and `--cookies-from-browser` parameters passed securely to yt-dlp.
- **Dynamic voteskip threshold**: Optional dynamic quorum based on room participant count.
- **Per-user sliding rate limiting**: Monotonic sliding window cooldown and request limit to protect against chat flood.
- **Software Supply Chain Security**: Release workflow upgraded with automated CycloneDX SBOM generation and GitHub artifact attestation.

### Fixed
- **GUI ไม่ขึ้น (GUI won't open)**: `camfrog_autodj/__main__.py` — auto-discovery (`discover.apply()`) crashed with `ImportError` on `pywinauto.Desktop` before `App(eng).mainloop()` was reached, so the Tk window never appeared. Auto-discovery is now wrapped in `try/except` and logs a warning instead of crashing; `build_adapter()` failures fall back to `NullAdapter` so the GUI still opens without chat (user can run `--check`/`--discover` from inside it).
- **Camfrog adapter blocks GUI startup**: `camfrog_autodj/adapters/uia.py` `UiaAdapter.__init__()` called `resolve()` which polls up to 30s for a Camfrog window, blocking GUI launch. With `NullAdapter` fallback in `__main__.py`, this no longer blocks.
- **Playlist not in queue list box**: `camfrog_autodj/engine.py` `_load_all()` added `playlist.json` tracks to the autoplay *pool* (`add_pool`), but the GUI list box only shows the request *queue* (`add_request`). Playlist tracks are now added to `add_request` so they appear in the GUI and play before the autoplay pool. Dedupe against existing requests and history prevents re-queuing on restart.
- **Thread-safety data race on `e.current`**: `camfrog_autodj/commands.py` `_play()` read `e.current.source` outside `e.queue.lock`, racing with `_player_loop()` which writes `e.current`. Now read under the same lock.
- **Ungraceful shutdown**: `camfrog_autodj/engine.py` `shutdown()` did not wait for daemon threads. Thread references are now stored in `self._threads` and joined (5s timeout each) on shutdown.
- **Windows-only code crashes on Linux**: `camfrog_autodj/launcher.py`, `camfrog_autodj/tts.py`, `camfrog_autodj/winmsg.py` now call `_require_windows()` to raise a clear `RuntimeError` instead of crashing with obscure `ctypes`/`pywinauto` errors on non-Windows platforms.
- **`!load` path traversal**: `camfrog_autodj/commands.py` `_load()` now rejects absolute paths outside `music_dirs` (admin-only guard).
- **NSIS installer warnings**: `installer.nsi` — removed `docs\*.txt` file glob (no such files), removed unused `.onUninstSuccess` function, removed unused `GetDate` function (now called inline via `Call GetDate`), removed duplicate `Uninstall.lnk` shortcut, removed `SEC_SRC` section (Python source not shipped in installer). All 5 NSIS warnings eliminated.

### Changed
- `camfrog_autodj/engine.py`: `Engine.__init__` now accepts `cfg_path` (was missing, causing `TypeError` when `_run()` passed it). GUI buttons `do_discover()`/`do_check()` read `self.e.cfg_path`.

### Added
- `camfrog_autodj/adapters/__init__.py`: new `NullAdapter` — silent fallback when Camfrog cannot be reached; GUI stays open, chat degrades gracefully.
- `camfrog_autodj/engine.py`: `_threads` list tracking all daemon threads started by `start()`.

## 0.2.4

### Fixed
- `camfrog_autodj/adapters/uia.py` `_appeared()`: `norm_l` was referenced outside the `for l in new:` loop. When no new chat lines arrived, `norm_l` was never assigned, causing `UnboundLocalError` on every background chat send — messages retried endlessly (`send failed ... retrying once in 2s`). Moved the `bot_nick` match inside the loop so `norm_l` is always defined before use, and every new line is checked (not just the last one).
- `camfrog_autodj/adapters/uia.py` `_bg_fails`: consecutive-failure counter was read/written without a lock across reader and sender threads, causing a race condition. Now protected by `_bg_fails_lock`.
- `camfrog_autodj/adapters/uia.py` `messages()`: `self._view = None` was assigned outside `com_lock`, racing with `_lines()` which reads `self._view` inside the lock. Now assigned inside `com_lock`.
- `camfrog_autodj/winmsg.py`: three module-level functions were defined twice — `make_lparam` (lines 58 and 256), `pick_child` (lines 62 and 260), `show_noactivate` (lines 117 and 273). The second definition silently shadowed the first. Removed the duplicate block.
- `camfrog_autodj/webchat.py`: unused unpacked variable `node` → `_node` in `read_items()`.
- `camfrog_autodj/gui.py`: unused unpacked variables `r`/`lab` → `_r`/`_lab` in three `_vc` unpack sites; removed unnecessary `int(round(...))` in `px()`.
- `camfrog_autodj/visuals.py`: removed unnecessary `int(round(...))` in `rgb_to_hex()`.
- `camfrog_autodj/adapters/uia.py`: merged two `endswith()` calls into one with a tuple argument.
- `camfrog_autodj/doctor.py`: replaced unnecessary `dict(...)` call with a literal.
- `camfrog_autodj/engine.py`: replaced unnecessary `dict(...)` call with a literal in `snapshot()`.
- `camfrog_autodj/library.py`: replaced unnecessary `dict(...)` call with a literal in `_extract_exe()`.
- `camfrog_autodj/gui.py`: `add_files()` and `load_folder()` now check for `$DISPLAY`/`$WAYLAND_DISPLAY` before opening native file dialogs, and wrap in try/except — fixes hang on headless Linux.
- `camfrog_autodj/installer.nsi`: removed machine-specific `config.toml` from bundle (path hardcoded to one PC); config is now created by `install.ps1` on first run.
- `camfrog_autodj/tts.py`: **TTS did nothing with default config** — `eng.save_to_file()` and `eng.runAndWait()` were inside `if cfg.tts_voice:`, so with `tts_voice = ""` nothing was synthesised. Moved outside the `if`. Also added `TTS_TIMEOUT` (60s) so `synth()` no longer blocks forever if pyttsx3 is missing or hangs; each job independently imports pyttsx3 so the worker stays alive even if it's not installed.
- `camfrog_autodj/library.py`: **`ytsearch20:` autoplay sources always failed** — `is_url()` only matches `http://`/`https://`, so `ytsearch20:mandopop` was double-wrapped as `ytsearch1:ytsearch20:mandopop` and failed. Added `SEARCH_PREFIX` regex and `raw_target` parameter so operator-supplied `ytsearchN:` queries pass through unchanged. Also fixed `find_ytdlp()` to fall back to PATH yt-dlp when `mpv_path` is the default `"mpv"` (the previous code refused PATH lookup when mpv_path was set, ignoring a perfectly good yt-dlp on PATH).
- `camfrog_autodj/commands.py`: **`!play` from chat was not saved to `playlist.json`** — only admin/GUI requests were saved, so `!last` was always empty for chat requests. Added `e.playlist.add(tracks)` for chat requests too. Also fixed cooldown case-dodging (`"Bob"` and `"bob"` are now one person via `.lower()`) and `²` digit bypass in `!remove`/`!vol` (`isascii()` check).
- `camfrog_autodj/player.py`: **`mpv_timeout` killed every track longer than the timeout** — `p.wait(timeout=120)` capped total play time, cutting any track over 2 minutes. Changed to a grace period: `limit = duration + mpv_timeout`, checked via 0.5s polling loop; pauses are excluded from the countdown; unknown-duration (live) tracks have no limit. Added `POLL` constant and `_played()` helper.
- `camfrog_autodj/playlist.py`: **corrupt `playlist.json` was silently overwritten** — `load_playlist()` returned `[]` and `save_playlist()` would overwrite the bad file. Added `_unreadable()` check and `PlaylistStore.add()` now saves a `.corrupt-<timestamp>` backup before overwriting.
- `tests/test_hardening.py`: updated `FailingPlayer.play()` and `lambda` mocks to accept the new `duration` parameter on `MpvPlayer.play()`.

### Added
- GUI: `--discover` และ `--check` ปุ่มบน now-playing card (`🔍 ค้นหาห้องแชท` / `✓ ตรวจสอบการตั้งค่า`) ให้ผู้ดูแลระบบรัน auto-discovery และวินิจฉัยการตั้งค่าจากหน้าต่างเดสก์ท็อปโดยไม่ต้องเปิดเทอร์มินัล
- `installer.nsi`: รองรับหลายภาษาในตัวติดตั้ง (English + Thai) ผ่าน `MUI_LANGUAGE` macro; ไฟล์ `thai.nlf` รวมอยู่ใน repo (ต้องติดตั้งที่ `Contrib\Language\` ของ NSIS บนเครื่อง Windows ก่อนคอมไพล์)
- `camfrog_autodj/engine.py`: `Engine.__init__` no longer takes `cfg_path` (was an experiment, removed). Added `_speak_lock` so only one TTS clip plays at a time (overlapping TTS jobs would un-duck the music early). `load_source()` now recognises `ytsearchN:` queries as raw targets for autoplay sources.
- `camfrog_autodj/engine.py` shutdown order: `adapter.close()` before `exec.shutdown()` so sender threads release the adapter before it's closed.

### Testing
- Full suite: **97 passed, 1 skipped** (was 130 passed before test mock updates for the new `duration` parameter on `MpvPlayer.play()`).
- All command paths verified end-to-end via `--lang th --console` (Thai and English).

## 0.2.3
`make` on plain Windows PowerShell/cmd. **Automated Windows 11 installer (`install.ps1` / `install.bat`).**

### Added
- `install.ps1` / `install.bat`: Full-featured automated installer for Windows 11. Verifies OS, installs prerequisites (Python 3.11+, mpv, yt-dlp, VB-Cable) via winget or direct download, clones the project, installs Python dependencies, builds `AutoDJ.exe` with PyInstaller, creates `config.toml` with interactive prompts, creates Desktop/Start Menu shortcuts (including Config editor and Uninstaller), optional auto-start on login, and runs `AutoDJ.exe --check` for verification. Logs to `%TEMP%\autodj-install-<timestamp>.log`.

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
