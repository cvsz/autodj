# Roadmap — zAutoDJ

zAutoDJ (formerly AutoDJ) is a music bot for Camfrog rooms: YouTube + local MP3/MP4
autoplay, `!` commands, now/next announcements, TTS, bilingual EN/TH GUI and chat,
webhook API, multi-platform streaming, AI `!ai ask`, config hot reload, audit logging.
Current version: **0.4.0**.

---

## Released (0.4.0)

- **Renamed to zAutoDJ**: exe `zAutoDJ.exe`; installer `zAutoDJ-Setup-<v>.exe`; default folder `%APPDATA%\zAutoDJ`; Start Menu/Desktop/Apps & Features show zAutoDJ
- **Upgrade path**: installer keeps pre-0.4.0 install folder, re-points shortcuts and autostart to `zAutoDJ.exe`, removes old `AutoDJ.exe`; config, logs and playlists untouched
- **Auto-update from 0.3.x**: finds the new `zAutoDJ.exe`
- **Not renamed**: `bot_nick`/requester "AutoDJ", the `autodj` Python package, the repository, `AUTODJ_*` environment variables
- **Single instance per config**: named mutex prevents double posts and double mpv
- **No-argument launch opens the GUI**: windowed build with no console no longer starts an invisible headless bot
- **Own account never greeted**: account nick learned from echoes; welcome/admin/mic greeting skip it
- **Background sends verified**: focus checked before paste/Enter; VK-based Ctrl+V works under Thai keyboard layout; room-list guard; user-idle wait; elevated-window diagnosis
- **`!ai` answers only `!ai ask`**: ordinary chat never sent to the AI provider; per-user cooldown; max 2 in flight; masked AI key in Settings
- **IM fixes**: private messages read from room pane; IM window late-pane recheck; IM worker off reader thread; old IMs not replayed
- **Room bots never greeted**: `greeting_ignore`, `greeting_ignore_regex` (default `(?i)bot$`)
- **Auto ads held while room chat is closed**: adapters report `room_ready`
- **Song overrun fixed**: mpv position read twice at grace expiry; end check with 2 s IPC timeout + `eof-reached`
- **Room history replay fixed**: `diff_lines` anchors on the last shared line; old lines not replayed
- **Webhook**: HMAC signature + timestamp + replay cache; body size cap; rate limiting; CORS safe defaults
- **Streaming**: thread-safe stream registry, JWT auth, API keys, platform adapters (Camfrog/YouTube/TikTok/Facebook), recorder/transcoder stubs (disabled by default)
- **Config hot reload**: `config_hot_reload`; settings pushed to adapters without restart
- **Audit logging**: structured JSON logging option; health check endpoint; `/webhook/metrics` Prometheus endpoint

---

## In progress / next release

| Item | Description | Priority |
|------|-------------|----------|
| Config schema documentation | Document all `config.toml` keys with types, ranges, and examples | P1 |
| `__all__` exports in all modules | Explicit public API surface | P2 |
| Extract `ChatProcessor`, `PlaybackManager`, `ConfigManager` from Engine | Engine does too much; separate concerns | P1 |
| GUI–Engine interface boundary | Reduce tight coupling between `gui.py` and `engine.py` | P1 |
| Dependency injection | Replace module-level references with injected dependencies | P2 |

---

## Future optional modules

| Item | Description | Priority |
|------|-------------|----------|
| End-to-end integration tests (real Camfrog/mpv) | Needs authorized Camfrog test environment | P1 (BLOCKED without environment) |
| Penetration/security test suite | Dedicated security test module | P2 |
| Signed config verification | Replay/nonce protection for config changes | P3 |
| Rate limit persistence | Survive restarts (currently in-memory only) | P3 |
| macOS support | Not tested; primary platform is Windows | P3 |
| ARM64 support | Not tested | P3 |
| SBOM/provenance workflows | Supply-chain transparency | P3 |
| OpenSSF Scorecard workflow | Security posture scoring | P3 |
| Container vulnerability scanning | Docker image scanning | P3 |
| Documentation site starter | Centralized docs hub | P3 |

---

## Release process

1. Developer (cvsz): create feature branch from `main`, implement, run validation gates (`pytest`, `ruff`, `mypy`, `compileall`, `shellcheck`), GPG-signed commit, push, open PR
2. Reviewer (policedbc): independent review of exact HEAD SHA, verify checks green, verify commit signature, approve
3. Developer (cvsz): confirm CI green, independent approval, no merge conflicts, merge with `--merge --match-head-commit`
4. Release: `release.yml` runs on `v*` tags only; builds and signs `zAutoDJ.exe` + installer; publishes to GitHub Releases

Never force-push, bypass branch protection, self-approve, or merge with pending checks.  
Pushed tags are never moved or deleted.

---

## Deprecated / removed

- `AutoDJ.exe` name (replaced by `zAutoDJ.exe` in 0.4.0; migration script preserves shortcuts)
- v0.3.11 / v0.3.12 tags exist but were never published (release runs failed); v0.3.13 published but lacked optional hot-reload/webhook packages; use 0.3.14 or later
- `AutoDJ` Config fallback folder (`%APPDATA%\AutoDJ`) kept only for pre-0.4.0 relocated configs; new installs use `%APPDATA%\zAutoDJ`

---

Generated repositories should adopt only modules appropriate to their stack, threat model,
operating environment, and compliance needs.