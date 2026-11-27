# zAutoDJ

**Music bot for Camfrog rooms — YouTube + local MP3/MP4 autoplay, `!` commands, now/next announcements, TTS, bilingual EN/TH GUI and chat.**

Formerly **AutoDJ**. Renamed to zAutoDJ in v0.4.0.

---

## Bridge status

`main` is green — all validation gates pass (pytest 965 passed / 1 skipped / 3 subtests passed, ruff clean, mypy clean, compileall clean). All 297 pull requests merged. No open PRs. No unresolved Critical/High findings.

| Verification | Result | Evidence |
|--------------|--------|----------|
| Build (`compileall`) | PASS | `python -m compileall -q autodj tests tools` → exit 0 |
| Tests (`pytest`) | PASS | 965 passed, 1 skipped, 3 subtests passed |
| Lint (`ruff check`) | PASS | All checks passed |
| Format (`ruff format --check`) | PASS | 183 files already formatted |
| Type checking (`mypy`) | PASS | No issues found in 68 source files |
| Secrets scan | Clean | `git ls-files | grep -E '(\.env|id_rsa|.*\.pem|.*\.key$)' \| grep -v '\.env.example$'` → empty |
| Pull requests | All merged | 297 PRs; latest #297 docs: sync pull-request count to 296 (latest #296); no open/draft PRs |
| Branch | `main` | Up to date with `origin/main`, working tree clean |

> On this Windows host the default pytest temp directory is access-denied. Always pass `--basetemp` to a writable directory (e.g. `C:\Users\cvsz.ZEAZ\AppData\Local\Temp\opencode\pytest`).

---

## Social preview

When this repository is shared on social channels, the preview shows:

**zAutoDJ — Music bot for Camfrog rooms**  
YouTube + local MP3/MP4 autoplay · `!` commands · now/next announcements · TTS · bilingual EN/TH GUI and chat · webhook API · multi-platform streaming · AI `!ai ask`  
https://github.com/cvsz/autodj · v0.4.0 · Python 3.11+ · All gates green

*(Add a `docs/assets/social-preview.png` banner image to render a graphical preview. This placeholder documents the intended preview text; no image file is committed in this session.)*

---

## What's new in 0.4.0

- **Renamed to zAutoDJ**: the program is `zAutoDJ.exe`; the installer is `zAutoDJ-Setup-<version>.exe`; default folder `%APPDATA%\zAutoDJ`; Start Menu, Desktop and Apps & Features show zAutoDJ.
- **Upgrade path**: the installer keeps a pre-0.4.0 install folder, re-points your shortcuts (and autostart) to `zAutoDJ.exe`, removes the old `AutoDJ.exe`. `config.toml`, logs and playlists are not touched. A config the program had moved to `%APPDATA%\AutoDJ` is still used.
- **Auto-update from 0.3.x** finds the new `zAutoDJ.exe`.
- **Not renamed**: the bot's nick in the room (`bot_nick`, your setting) and the internal Python package `autodj`.
- **Single instance per config**: named mutex prevents double posts and double mpv.
- **No-argument launch opens the GUI**: windowed build with no console no longer starts an invisible headless bot.

See [CHANGELOG.md](CHANGELOG.md) for the full release history (0.4.0 back to 0.2.x).

---

## What zAutoDJ does

| Capability | Description |
|------------|-------------|
| **YouTube + local playback** | Plays YouTube URLs/searches and local MP3/MP4 via mpv + yt-dlp |
| **Command system** | 30+ `!` commands with Thai aliases (`!play`, `!queue`, `!voteskip`, `!np`, admin commands, …) |
| **Auto-playlist** | Persistent JSON storage; autoplay pool when no requests arrive |
| **Now/Next announcements** | Announces current and next track; TTS support |
| **Bilingual GUI & chat** | English and Thai interface and replies; live language switching |
| **Camfrog RE integrations** | Gift detection, avatar change, status indicators, upgrade/payment alerts, name-color tracking (GUI preview only) |
| **IM viewer** | Private/instant messages shown in the IM tab; auto-reply with cooldown |
| **Enterprise architecture** | Circuit breakers, per-nick rate limiting, health check endpoint, structured exceptions |
| **Webhook API** | FastAPI server with HMAC-SHA256 signature + timestamp + replay cache; rate limiting; CORS-safe defaults |
| **Multi-platform streaming** | Stream registry, JWT auth, API keys; Camfrog/YouTube/TikTok/Facebook adapters (disabled by default) |
| **Config hot reload** | Settings pushed to adapters without restart |
| **Structured logging** | JSON log option; health check; `/webhook/metrics` Prometheus endpoint |
| **AI `!ai ask`** | Optional chat-completion via OpenAI-compatible API (NVIDIA catalog default); fail-closed, masked key in Settings |

---

## Architecture

```
zAutoDJ.exe (frozen PyInstaller binary)
├── autodj/__main__.py   — CLI entry point (--gui, --console, --check, --discover, --say, …)
├── autodj/engine.py     — Engine: chat loop, playback loop, command router, autoplay pool
├── autodj/commands.py   — Router: command registration, admin auth, cooldowns, rate limits
├── autodj/config.py     — Config: TOML loading, fail-closed validation, defaults
├── autodj/player.py     — MpvPlayer: one mpv per track, IPC control, fade in/out
├── autodj/library.py    — Library: yt-dlp lookups, local file scanning, URL parsing
├── autodj/playlist.py   — PlaylistStore: persistent playlist.json (atomic write, dedup)
├── autodj/playqueue.py  — PlayQueue: requests-first queue + autoplay pool, shuffle/repeat
├── autodj/discover.py   — Auto-discover: finds Camfrog window and chat controls
├── autodj/adapters/     — Chat adapters: uia (primary), webchat, console, null
├── autodj/gui.py        — GUI: Tk studio window with queue/history/chat/TTS
├── autodj/doctor.py     — --check: plain-language setup diagnostics
├── autodj/messages.py   — All user-facing strings (EN + TH)
├── autodj/textutil.py   — Text sanitisation
├── autodj/tts.py        — Text-to-speech via pyttsx3 (SAPI)
├── autodj/paths.py      — Executable path resolution
├── autodj/windows.py    — Window enumeration for Camfrog discovery
├── autodj/winmsg.py     — Windows message posting for background chat
├── autodj/webhook/      — FastAPI webhook server with HMAC verification
├── autodj/stream/       — Multi-platform streaming (registry, auth, adapters)
├── autodj/plugins/      — Plugin system (stats, help builtins)
└── autodj/ai.py         — AI chat-completion client (!ai ask only)
```

Full architecture: [docs/architecture.md](docs/architecture.md) and [docs/autodj-blueprint.md](docs/autodj-blueprint.md).

---

## Bridge Status — subsystem connectivity

| Subsystem | Status | Evidence |
|-----------|--------|----------|
| Audio engine (mpv IPC, one process/track) | VERIFIED | `autodj/player.py`; hang detection 0.5 s poll; graceful timeout |
| GUI (Tkinter, cross-thread via `tk.after(0)`) | VERIFIED | `autodj/gui.py`; reentrancy guards; timer cleanup on close |
| Library scan (no symlinks, bounded recursion) | VERIFIED | `autodj/library.py`; `tests/test_library_scan_safety.py`, `tests/test_doctor_symlinks.py` |
| Config (fail-closed TOML, atomic writes) | VERIFIED | `autodj/config.py`; `tests/test_config_*.py` |
| Command router (rate limit, TOCTOU lock) | VERIFIED | `autodj/commands.py:Router`; `tests/test_admin_commands.py` |
| Chat adapters (uia / webchat / console / logtail) | VERIFIED (code) | `autodj/adapters/`; real Camfrog BLOCKED (no authorized env) |
| Webhook API (HMAC, replay cache, body cap) | VERIFIED (code) | `autodj/webhook/auth.py`, `server.py`; `tests/test_webhook_server.py` |
| Multi-platform streaming (registry, JWT auth) | VERIFIED (code) | `autodj/stream/`; adapters disabled by default |
| AI `!ai ask` (fail-closed, no network unless enabled) | VERIFIED (code) | `autodj/ai.py`; `tests/test_ai_ask.py` |
| Config hot reload | VERIFIED (code) | `autodj/config_watcher.py`; `tests/test_config_hot_reload.py` |
| Installer (NSIS, mpv bundle) | NOT RUN | Requires makensis + signing certificate |
| PyInstaller build (`build.ps1`) | NOT RUN | Requires code-signing cert + GPG TTY for pinentry |
| Real Camfrog / mpv / YouTube runtime | BLOCKED | Requires authorized Camfrog test environment + mpv/yt-dlp |

---

## Security

**Nickname-based admin authorization is spoofable** — any Camfrog user can adopt an admin's nick. This is documented in-code and treated as a known design limit. Fail-closed: when `admins = []` no user is admin.

Key controls:
- Fail-closed config validation with exact line + `^` marker (`ConfigError`)
- Atomic config writes (temp + `os.replace()` + `.bak`)
- Auto-relocation to `%APPDATA%\zAutoDJ\` when config is not writable
- No `shell=True`; all `subprocess` calls use argument lists
- No unsafe deserialization — only `tomllib` and `json`
- One mpv process per track; JSON IPC via named pipe / Unix socket
- Hang detection at 0.5 s; terminate → kill after grace period
- `mpv_timeout` is a grace period (duration + timeout), never a hard cap
- GUI off main thread; cross-thread updates via `tk.after(0, ...)`
- Library scan: never follows symlinks; bounded recursion and results
- Webhook HMAC-SHA256 signature + timestamp + replay cache; body size cap; rate limiting
- Stream JWT auth (HS256) scoped per stream + action
- Auto-update: SHA-256 + pinned ZEAZDEV Authenticode signer
- Secrets never tracked: `.env.example` only; real `.env` and `config.toml.*` gitignored
- All commits GPG-signed

Full policy: [SECURITY.md](SECURITY.md). Report vulnerabilities through SECURITY.md, not public issues.

---

## Setup (Windows)

1. Install Python 3.11+, [mpv](https://mpv.io), and a virtual audio cable (e.g. VB-Cable).
2. `pip install -e .` and put `yt-dlp.exe` in the same folder as `mpv.exe` (or on PATH). Set `mpv_path` in `config.toml`.
3. Camfrog mic = cable output. `audio_device` = cable input (`mpv --audio-device=help`).
4. `copy config.example.toml config.toml`: set `admins`, `bot_nick`, `music_dirs`, `lang`.
5. Open the room window and start zAutoDJ. With `auto_discover = true` it finds the room window and chat/input controls and writes them to `config.toml` (backup `config.toml.bak`). `--discover` does just that and exits.
6. Run:
   - `zAutoDJ.exe --gui` — desktop window (default when double-clicked)
   - `zAutoDJ.exe` — headless bot
   - `zAutoDJ.exe --console` — chat via stdin/stdout (no Camfrog)
   - `zAutoDJ.exe --check` — verify setup and exit

Full installer: [docs/windows-install.md](docs/windows-install.md). Automated installer: `install.ps1` / `install.bat`.

---

## GUI

A dark "studio" window: spinning record and animated equaliser while a track plays (equaliser is decorative), gradient progress bar, round Pause/Skip buttons, volume slider, ON AIR light, shuffle/repeat chips. Right-hand panel has tabs: **Queue**, **History**, **Room chat**, **IM** (private messages), **Settings**.

Keys: `Space` pause/resume (when no text box has focus), `Ctrl+Right` skip. A red banner appears if mpv cannot be found. Display scaling (125%/150%) is handled; the title bar follows Windows dark mode.

TH/EN pills switch the language live.

---

## Commands (prefix `!`; Thai aliases in brackets)

Everyone: `np` (เพลงนี้), `next` (ถัดไป), `queue` (คิว), `history` (ประวัติ), `voteskip` (โหวตข้าม), `remove <n>` (ลบ), `help` (ช่วยเหลือ), `mute` (ปิดไมค์), `unmute` (เปิดไมค์), `welcome` (ต้อนรับ).

Requester/admin: `skip` (ข้าม).

Admin: `pause`, `resume`, `vol`, `shuffle`, `repeat`, `clear`, `load`, `say`, `speak`, `block`/`unblock`, `blockbot`/`unblockbot`, `kick`, `ban`, `unban`, `punish`, `punishbot`, `deletehistory <all\|N>`, `delete <msg id>`, `welcome <text>`, `ai on\|off\|status\|model <id>\|prompt <text>`, `update` / `update apply`.

A blocked nick's commands are ignored silently (admins cannot be blocked; also settable as `blocked_users` in config).

**"What song is this?"** Room lines containing `np_question_keywords` get the `!np` reply without a command; room-wide cooldown `np_question_cooldown` (default 20 s).

**Play commands (`!play`, `!request`, `!req`, `!p`, `!เล่น`, `!ขอเพลง`, `!เล่นเพลง`) now work only via IM (private message).** Room users must DM the bot. Admins can still use in room.

Non-admins: YouTube links only, 1 track, `max_duration`, no live, `max_requests_per_user`, and a song already queued or playing is refused. Name requests search `music_dirs` first, then YouTube.

Full command reference: [docs/autodj-commands.en.md](docs/autodj-commands.en.md) / [docs/autodj-commands.th.md](docs/autodj-commands.th.md).

---

## Sending to the room in the background

`send_mode` in `config.toml`: `background` posts text straight to the chat window's handle; `foreground` brings Camfrog up and pastes; `auto` (default) tries background, verifies the line appeared, then falls back to foreground. The bot verifies focus before paste/Enter, waits for 2.5 s of user idle, never types into another application, and diagnoses elevated foreground windows.

Test with `zAutoDJ.exe --say "test" -v`.

---

## Build + sign zAutoDJ.exe

```powershell
python -m pip install -e . pyinstaller
.\build.ps1
```

It verifies every package the exe must contain, builds `dist\zAutoDJ.exe` with `app.ico` and `version_info.txt` (company ZEAZDEV COMPANY LIMITED), signs the exe (SHA256 + timestamp), and runs a smoke test.

- `-Clean` wipes `build\`, `dist\`, `AutoDJ.spec` first.
- `-NoSign` builds only.
- Certificate: `-Pfx file.pfx -Password …` (or env `AUTODJ_PFX`, `AUTODJ_PFX_PASSWORD`), `-Thumbprint <hex>` (or env `AUTODJ_CERT_THUMBPRINT`), otherwise a self-signed cert is reused or created once.
- Close `zAutoDJ.exe` before building.

Full installer with the bundled mpv folder:

```powershell
.\scripts\build_installer.ps1 -RequireMpv -Version 0.4.0 -OutDir .
```

See [docs/WINDOWS_BUILD.md](docs/WINDOWS_BUILD.md).

---

## Configuration

`config.toml` is the runtime settings file (fail-closed TOML). Copy `config.example.toml` to `config.toml` and edit. Invalid values raise `ConfigError` with the exact line and a `^` marker.

Key sections: Identity, Chat, Window Discovery, Audio, Library, Queue Limits, YouTube, Rate Limiting, Auto-reply, IM, Admin Features, Welcome, Mic Greeting, RE Integrations, Webhook, Config Hot Reload, Plugins, JSON Logging, Auto-update, AI, Multi-platform streaming.

Full config reference: `config.example.toml` and [docs/config.example.toml](config.example.toml).

Environment variables (`.env`, gitignored — shell/tooling only): `AUTODJ_PFX`, `AUTODJ_PFX_PASSWORD`, `AUTODJ_CERT_THUMBPRINT`, `AUTODJ_CACHE_DIR`, `GPG_PASSPHRASE`. The application reads `config.toml` for runtime settings; `.env` is only for shell/tooling variables consumed via `os.environ.get()`.

---

## Validation

| Gate | Command | Result |
|------|---------|--------|
| Compile | `python -m compileall -q autodj tests tools` | PASS |
| Tests | `python -m pytest -q -p no:faulthandler -p no:cacheprovider --basetemp="<writable-dir>"` | 964 passed, 1 skipped |
| Lint | `ruff check autodj tests tools` | PASS |
| Format | `ruff format --check autodj tests tools` | PASS |
| Types | `mypy autodj` | PASS (68 files) |
| Shell | `shellcheck scripts/*.sh tools/*.sh` | NOT RUN (shellcheck not installed on this Windows host) |
| Secrets | `git ls-files \| grep -E '(\.env\|id_rsa\|.*\.pem\|.*\.key$)' \| grep -v '\.env.example$'` | Clean |

Full CI: `.github/workflows/ci.yml`, `.github/workflows/tests.yml`, `.github/workflows/windows-build.yml`, `.github/workflows/release.yml`, `.github/workflows/codeql.yml`, `.github/workflows/dependency-review.yml`.

---

## Verification summary

| Verification | Result | Evidence |
|--------------|--------|----------|
| Build | PASS | `python -m compileall -q autodj tests tools` → exit 0 |
| Ruff lint | PASS | `ruff check autodj tests tools` → All checks passed |
| Ruff format | PASS | `ruff format --check autodj tests tools` → 183 files already formatted |
| Type checking | PASS | `mypy autodj` → Success: no issues found in 68 source files |
| ShellCheck | NOT RUN | `shellcheck` not installed on this Windows host |
| Pytest (unit/func/integration) | PASS | 965 passed, 1 skipped, 3 subtests passed |
| Missing dependency tests | PASS | Covered by build-env check pattern; all import tests pass |
| Security audit | PASS | Bandit 0 findings; no committed secrets; all commits GPG-signed |
| Docker build | NOT APPLICABLE | No Dockerfile-based release; Windows PyInstaller + NSIS |
| Runtime validation | BLOCKED | Real Camfrog/mpv requires authorized test environment |

The skipped test needs a signed exe; it passes 16/16 when one is provided.

---

## Documentation

| Document | Purpose |
|----------|---------|
| [AGENTS.md](AGENTS.md) | Canonical agent instruction file — operating rules, security rules, validation gates, PR workflow |
| [SECURITY.md](SECURITY.md) | Security policy, threat model, controls, vulnerability reporting |
| [ROADMAP.md](ROADMAP.md) | Release roadmap, future modules, release process |
| [ZEAZ-INTRODUCTION.md](ZEAZ-INTRODUCTION.md) | ZEAZ engineering execution framework + project-specific tail |
| [OPENCODE.md](OPENCODE.md) | OpenCode agent instructions |
| [CLAUDE.md](CLAUDE.md) | Claude Code agent instructions |
| [GEMINI.md](GEMINI.md) | Gemini agent instructions |
| [CHANGELOG.md](CHANGELOG.md) | Full release history |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Architecture overview |
| [docs/architecture.md](docs/architecture.md) | Detailed architecture |
| [docs/autodj-blueprint.md](docs/autodj-blueprint.md) | Complete module/feature blueprint |
| [docs/admin-manual.en.md](docs/admin-manual.en.md) | Administrator manual (EN) |
| [docs/admin-manual.th.md](docs/admin-manual.th.md) | Administrator manual (TH) |
| [docs/user-manual.en.md](docs/user-manual.en.md) | User manual (EN) |
| [docs/user-manual.th.md](docs/user-manual.th.md) | User manual (TH) |
| [docs/windows-install.md](docs/windows-install.md) | Windows installation |
| [docs/WINDOWS_BUILD.md](docs/WINDOWS_BUILD.md) | Windows build |
| [docs/autodj-commands.en.md](docs/autodj-commands.en.md) | Command reference (EN) |
| [docs/autodj-commands.th.md](docs/autodj-commands.th.md) | Command reference (TH) |
| [Final-Report.md](Final-Report.md) | Complete release and verification report |

---

## GitHub workflow (cvsz ↔ policedbc)

All changes go through pull requests on `main`. Branch protection requires independent review.

1. **Developer (cvsz):** `gh auth switch -u cvsz`, create branch from `main`, implement, validate, `git commit -S`, push, `gh pr create`
2. **Reviewer (policedbc):** `gh auth switch -u policedbc`, review exact HEAD SHA, verify checks green and commit signature, `gh pr review --approve` (not self-approval)
3. **Developer (cvsz):** `gh auth switch -u cvsz`, verify CI green + approval + no merge conflicts, `gh pr merge --merge --match-head-commit`

Rules: never force-push, bypass branch protection, self-approve, or merge with pending checks. GPG signing required for feature commits and merge commits.

---

## Caveats

- No public Camfrog bot API. Chat read/send is UI Automation (`adapters/uia.py`): control indexes and `line_regex` must be tuned per Camfrog version.
- Not tested: real Camfrog, mpv, yt-dlp, TTS (Thai voice must be installed in Windows), Windows launch/URI, `build.ps1` on non-Windows.
- Check room rules and Camfrog terms before running a bot.
- `shellcheck` not installed on this Windows host; shell validation is `NOT RUN` locally (covered by CI where available).
- Real Camfrog/mpv/YouTube runtime validation is `BLOCKED` without an authorized test environment.

---

## License

[LICENSE](LICENSE)

---

*zAutoDJ v0.4.0 — https://github.com/cvsz/autodj · PR #293 merged (fix TTS IPC duck/restore)*