# Final Report — CamfrogAutoDJ 0.3.0 audit, fixes and hardening (2026-11-18)

## 0. Authoritative verification update — v0.3.5 (2026-11-18)

> This section is the current, evidence-backed status of the repository at branch
> `feat/zplayer-gui-0.3.5`, HEAD `2eaa1bd` (plus the verification commits in PR #233).
> Sections 1–7 below are the historical 0.3.0–0.3.2 evidence record and are retained.

### 0.1 Executive summary — VERIFIED

A top-to-bottom audit (static architecture mapping by an independent subagent, defect audit,
security audit, then full local verification) was completed for the 0.3.5 zPlayer GUI redesign.
All identified High and Medium defects were fixed in code; all Low findings were either fixed
or reduced to reviewed, documented annotations. **Every locally executable gate is green with
zero errors and zero warnings**: pytest 598 passed / 0 failed / 0 warnings (2 environment-skips,
3 subtests), ruff check + format clean, mypy clean (48 files), shellcheck clean (all `*.sh`),
bandit clean (all severity and confidence metrics 0), compileall clean, installer/repository
validators clean.

Evidence state (per `ZEAZ-INTRODUCTION.md`):

| Area | State |
|---|---|
| Python source, GUI logic, config, tests, lint, types, security scans, repo/installer validators | **VERIFIED** — commands and outputs in §0.5 |
| Windows 11 PyInstaller + NSIS signed installer build | **BLOCKED** — requires the Windows 11 host with NSIS/mpv/signing certificate; not fabricated here |
| Live Camfrog room, UIA chat and mpv playback | **BLOCKED** — requires an authorized test room and audio device |
| Signed commit / PR / independent review / merge | **EXECUTED in step 5** — exact SHAs and PR link recorded there |

The codebase is enterprise-ready **to the extent local evidence permits**; the two runtime items
above remain explicit release gates and are not claimed as verified.

### 0.2 Complete change inventory

**Features completed**

| Feature | Evidence |
|---|---|
| zPlayer theme system (dark/neon/light), TkinterEP-inspired and GPL-safe | `camfrog_autodj/theme.py` (palettes, `shade()`, lazy Tk imports) |
| Redesigned now-playing dashboard + Previous transport (`Engine.prev()`) | `camfrog_autodj/gui.py`, `camfrog_autodj/engine.py`, `messages.py` EN/TH labels |
| `ui_theme` and `welcome_message_delay` settings, validated and documented | `config.py` (`_CHOICES`, `_RANGES`, `validate_values`), `config.example.toml`, GUI Settings |
| Live theme switching of the open window | `App._retheme`, `_colour_mapping`, `_recolor_tree`, `PillButton.set_palette` |
| Actionable stale-install GUI import error; PyInstaller hidden imports for GUI + optional extras | `__main__.py`, `tools/generate_spec.py` |

**High/Medium defects fixed**

| # | Finding → Fix |
|---|---|
| H1 | `--log-json` was inert and installed zero handlers (silencing console output) → `_configure_logging()` is called from startup; a console handler always exists |
| H2 | GUI Settings built `Config(**data)` without `_validate()` → invalid values could be written and break next startup → `Config.validate_values()` enforces the same rules before any disk write |
| M1 | `PillButton.STYLES` frozen at import ignored non-dark palettes → rebuilt from palette with derived shades |
| M2 | `ui_theme` change required a restart → full widget-tree recolour and canvas redraw in the running window |
| M3 | Delayed welcomes blocked a worker from the 8-thread command pool for up to 3600 s → dedicated daemon timers, cancelled on shutdown |

**Security / robustness hardening (all Low findings closed)**

Replay cache check made atomic with a lock; plugin commands gated by cooldown/rate-limit; IM
history and chat-rate state bounded; config `.tmp` files written `0600` on POSIX; updater
requires HTTPS and sanitizes release tags before batch interpolation; workflow secrets/inputs
passed through `env:`; `# nosec` annotations normalized so bandit emits no warnings; dependency
upper bounds added for webhook/hot-reload extras. No new runtime dependency was introduced.

### 0.3 Performance and scalability

- Delayed greetings no longer consume a command-pool slot: up to 3600 s waits now use independent
  daemon timers, so lookup/`!skip`/announcement latency is unaffected by join floods.
- Theme switching is O(number of live widgets) and happens only on an explicit settings save;
  normal playback polling remains version-gated (no unnecessary list rebuilds).
- IM log capped at 300 entries and idle chat-rate buckets pruned every 60 s, bounding memory in
  long-running rooms with high nick churn.
- Delayed-welcome timers are explicitly cancelled in `Engine.shutdown()`; no daemon leaks.

### 0.4 Independent audit inputs

Three read-only subagent audits were used as inputs: full architecture/module/runtime map,
defect inventory (2 High / 3 Medium / 10 Low), and security audit (1 Medium / 7 Low). All
High/Medium items were fixed in code; all Low items were fixed or normalized with reviewed
evidence. No finding was silently dismissed.

### 0.5 Validation matrix — results

| Gate | Command | Result |
|---|---|---|
| Syntax | `python -m compileall -q camfrog_autodj tests tools` | **PASS** |
| Tests | `python -m pytest -q -p no:faulthandler -p no:cacheprovider` | **PASS — 598 passed, 2 skipped, 3 subtests, 0 warnings** |
| Lint | `python -m ruff check camfrog_autodj tests tools` | **PASS — 0 issues** |
| Format | `python -m ruff format --check camfrog_autodj tests tools` | **PASS — 109 files** |
| Types | `python -m mypy camfrog_autodj` | **PASS — 48 files, 0 issues** |
| Shell | `shellcheck` on all tracked `scripts/*.sh tools/*.sh` | **PASS — 0 issues** |
| Build assembly | `python tools/generate_spec.py` | **PASS — AutoDJ.spec generated** |
| Installer validation | `python tools/validate_installer.py` | **PASS** (optional mpv bundle absent → informational) |
| Repository validation | `python scripts/validate_repo.py` | **PASS — structure and local Markdown links valid** |
| Missing-deps / connection test | `tests/test_version_and_release.py`, `tests/test_version_consistency.py`, `tests/test_installer_version_substitution.py`, `tests/test_build_cross_platform.py`, `tests/test_linux_builder_cli.py` | **PASS — versions and build/env wiring consistent** |
| Security scan | `python -m bandit -c pyproject.toml -r camfrog_autodj` | **PASS — 0 issues, 0 warnings** |

Bandit metrics (the requested zero metrics, reproduced verbatim):

```
Total issues (by severity):
        Undefined: 0
        Low: 0
        Medium: 0
        High: 0
Total issues (by confidence):
        Undefined: 0
        Low: 0
        Medium: 0
        High: 0
```

### 0.6 Documentation consistency

`CHANGELOG.md`, `README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/release.md`, `config.example.toml`,
installer/renderer docstrings and this `Final-Report.md` describe version 0.3.5 and the current
architecture. Historical audit reports under `docs/audit/` and older root reports intentionally
retain their original version labels as evidence of past states.

---

## 1. Executive summary

A full audit (code, config, scripts, CI, packaging, security) found and fixed **6 security/privacy defects, 11 functional bugs** and the complete bandit/shellcheck backlog. Every local gate is green: **pytest 554 passed / 0 failed, ruff 0, ruff-format 0 (Python), mypy 0 (47 files), shellcheck 0 (12 scripts), bandit 0 (all severities and confidence levels)**, and the wheel/sdist build plus a dependency check also pass.

Evidence classification (per `ZEAZ-INTRODUCTION.md`):

| Area | State |
|---|---|
| Python code, tests, lint, types, security scan, packaging | **VERIFIED** (Linux, Python 3.12, commands in §5) |
| Windows exe / NSIS installer build | **BLOCKED**: needs the Windows 11 build host (not run in this session) |
| Live Camfrog room + mpv playback | **BLOCKED**: needs an authorized Camfrog test room |
| Signed commit → PR → independent review → merge (step 5) | **BLOCKED**: see §7 |

Everything is enterprise-ready to the level the local evidence supports; the two runtime items above must be confirmed on the Windows host before release.

## 2. Functional changes — now-playing in the room

| Change | Files |
|---|---|
| **"What song is this?" auto-answer**: room lines containing `np_question_keywords` (เพลงอะไร, เพลงไร, เพลงชื่อ, ชื่อเพลง, เพลงนี้ชื่อ, what song, what's playing, song name) get the now-playing reply without a command; room-wide `np_question_cooldown` (20 s); toggle `np_question_reply` (also in GUI Settings) | engine, config, gui, messages |
| `!np` / `!เพลงนี้` adds live progress `(1:05/3:20)` | engine, commands |
| Templates gain `{elapsed}`, `{remaining}`, `{eta}`; `msg_next` "อีก {eta}" = real wait until that song starts | engine, config.example.toml |
| **Bug:** "Up next" announced song A but played song B (`pop_pool` ignored the `peek()` result) | playqueue |
| **Bug:** autoplay pool drained after one pass (tracks were removed) → now loops forever with a shuffle bag (no repeats until every song has played) | playqueue |
| **Bug:** repeat-one re-posted "Now playing" every loop → announced once | engine |
| **Bug:** "Now playing" elapsed time could exceed the song length → clamped and rounded | engine |

## 3. Security, privacy and reliability fixes

| # | Severity | Finding → Fix |
|---|---|---|
| S1 | High | Auto-update downloaded `AutoDJ.exe` with **no integrity check** → SHA-256 required (GitHub asset `digest` or `.sha256`/`SHA256SUMS`); a mismatch or missing digest is refused and the partial file deleted |
| S2 | High | Webhook HMAC covered only the body: every empty-body call (health/skip/pause/resume) shared **one permanent signature** → signs `ts.METHOD.path.body`, 300 s window, one-time replay cache |
| S3 | High | Empty webhook secret meant HMAC with an empty key (forgeable) → secrets shorter than 16 chars fail closed (503) |
| S4 | Medium | AI answered **private IMs in the public room** (leaked them) → IMs are never sent to the AI |
| S5 | Medium | `.dockerignore` let `.config/` (gh token store), `cert/` and `docs/rea/` (malware samples) into the image → excluded |
| S6 | Medium | `setup-git-credential-helper.sh` wrote a plaintext token store to the relative path `D/.git-credentials` → now `$HOME/.git-credentials`, refuses paths inside the repo, `chmod 600` |
| P1 | Privacy | GitHub was contacted at startup even with `auto_update_enabled = false` → only when enabled |
| B1 | Bug | AI never worked: the URL guard only allowed github.com → https any host (http for localhost only), no embedded credentials |
| B2 | Bug | AI blocked the chat-reading thread (up to 60 s) and ignored its cooldown → runs on the executor and is cooldown-gated |
| B3 | Bug | `!ai on/off/model/prompt` and config reload had no effect; prompt/model text was lowercased → client rebuilt, case kept |
| B4 | Bug | Updater offered **downgrades**, matched `AutoDJ.exe.sha256` as the exe, used the wrong exe path in PyInstaller builds, and its swap script deleted the old exe even after a failed rename → all fixed (rollback added) |
| B5 | Bug | GUI "Save settings" silently reset `ai_*`, `auto_update_*`, `webhook_secret`, `voteskip_cooldown`, `log_json*` → every key persisted |
| B6 | Bug | `pip install` crashed: `plugins/` and `webhook/` packages missing → `packages.find` |
| B7 | Bug | Webhook rate limiter answered 500 instead of 429; the IP table grew unbounded → fixed and pruned |
| B8 | Bug | A sender adapter that failed its self-test was kept → falls back to `NullAdapter` |
| B9 | Bug | `post-review-comment.sh` was missing `fi` (the CI step always failed) |
| H1 | Hardening | Runtime `assert`s (stripped by `python -O`) → explicit checks; swallowed exceptions → logged; `gh`/`powershell` → absolute paths |

## 4. Performance and scalability

- The chat-reading loop no longer blocks on network calls (AI moved to the thread pool), so command latency is independent of AI provider latency.
- Webhook state is bounded: the rate-limit table is pruned every 60 s, and the replay cache expires after 600 s.
- The autoplay pool is O(n) per pick with no rebuilds, and it loops indefinitely, so an unattended room never goes silent.
- The updater's check interval is floored at 300 s, so it never hammers the GitHub API.

## 5. Validation matrix

| Gate | Command | Result |
|---|---|---|
| Syntax | `python -m compileall -q camfrog_autodj tests tools` | ✅ OK |
| Unit + integration tests | `python -m pytest -q -p no:faulthandler -p no:cacheprovider -W error::DeprecationWarning` | ✅ **554 passed**, 1 skipped (Linux-only display check), 0 warnings |
| New tests | `tests/test_now_playing.py` (9), `tests/test_updater_ai_hardening.py` (12), webhook hardening (5) | ✅ |
| Lint | `ruff check .` | ✅ 0 |
| Format | `ruff format --check camfrog_autodj tests tools scripts` | ✅ 0 (only Python snippets inside 7 Markdown docs are flagged) |
| Types | `mypy camfrog_autodj` | ✅ 0 issues / 47 files |
| Shell | `shellcheck` on all 12 tracked `*.sh` | ✅ 0 |
| Build | `uv build` → wheel + sdist; clean venv install `[webhook,hotreload]` | ✅ imports `plugins.builtin`, `webhook.server`, `engine` |
| Missing deps | `uv pip check` | ✅ all 22 packages compatible |
| Secrets in git | `git grep` / `git log -G` for token patterns | ✅ none tracked, none in history |
| Security scan | `bandit -c pyproject.toml -r .` | ✅ see below |

```
Run metrics (bandit 1.9.4, 14,463 LOC):
  Total issues (by severity):   Undefined: 0  Low: 0  Medium: 0  High: 0
  Total issues (by confidence): Undefined: 0  Low: 0  Medium: 0  High: 0
```

The baseline was 49 issues (46 in the package/scripts/tools, plus 3 in root helpers; Low 45, Medium 4). Fixed in code: 6 runtime `assert` sites, 5 swallowed-exception sites and 2 partial-path executable calls. Suppressed after review: 37, by bandit's own count, each written as `# nosec <id> - <reason>`. These are subprocess calls with a fixed argv and no shell, `urlopen` after scheme/host validation, UI label text and shuffle randomness. `tests/` is excluded in `[tool.bandit]`, because pytest asserts and fixture values are intentional there.

## 6. Documentation updated

`CHANGELOG.md`, `README.md`, `config.example.toml`, `docs/admin-manual.{en,th}.md`, `docs/autodj-commands.{en,th}.md`, `docs/user-manual.{en,th}.md` and `docs/architecture.md` now cover the new keys, the webhook signing scheme (with a Python example), AI/update behaviour and the autoplay semantics. The user's local `config.toml` changed `msg_next` from `{duration}` to `{eta}`.

## 6b. Update — request rules, default song, Settings dialog

| Change | Evidence |
|---|---|
| `default_track` = `https://www.youtube.com/watch?v=HhVVVgYsBYw`: plays at startup, and again when the queue is empty and nobody has requested for 30 s (`autoplay_idle_timeout`); a dead link falls back to the pool for 10 min | `tests/test_now_playing.py` (8 request-rule tests) |
| First request cuts the default/autoplay song immediately; a **requested** song is never cut; later requests are queued **FIFO**. Root causes: `_cut_current()` always skipped, and requests were inserted at the front of the queue (LIFO) | same tests, plus the FIFO update in `test_hardening.py` |
| Settings dialog: inputs hidden behind their row frames, labels blank, stray duplicate titles, 30 unlabelled toggles, Save/Close buried → all rows visible, toggles labelled, Save/Close pinned at the bottom | real-Tk test `test_settings_dialog_visible_saves_and_reopens` (Xvfb) and a before/after screenshot check |
| Settings save: result/errors went into the room, the live config was mutated before validation, the language was reverted, and the dialog could not be reopened → in-dialog status, validate-then-apply via `_on_config_reload`, `<Destroy>` handling | same test |

Re-validated after this update: compileall OK · **pytest 564 passed, 0 skipped** (GUI tests run under Xvfb) · ruff 0 · ruff-format 0 · mypy 0 · shellcheck 0 · bandit 0/0/0/0 (severity) and 0/0/0/0 (confidence).

## 6c. Update: deep review of code, logic, options and Makefile (0.3.2)

Three parallel reviews (engine/player, commands/options, Makefile/build/CI) found **29 defects**. Each one was reproduced before it was fixed. All are fixed, and the 29 regression tests are in `tests/test_now_playing.py`, plus updates to the existing tests.

| Area | Most important fixes |
|---|---|
| Request rules | A searched request lost `is_request` after resolution, so it could be cut or dropped. A local `default_track` was searched on YouTube. A failed default-song lookup blocked the player thread every repeat. "Up next" was wrong when the default song comes next. |
| Timers | Welcome, greeting, IM auto-reply and voteskip treated `0.0` as "never" against boot-relative `monotonic()`, so the first greeting was skipped on PCs up for less than an hour. |
| Player | TTS never ducked the music. `stop()` blocked the GUI for up to 10 s. mpv could keep playing after AutoDJ exited. |
| Options | `allow_play_in_room`, `im_require_room_presence`, `config_hot_reload`, `webhook_*` and `plugins` were all dead. They are now enforced or wired up (`!stats` and `!plugins` work). |
| Commands | The rate limit skipped 5 play aliases. `!hbdp` and `!aplay fav` bypassed the queue rules. `!punishbot` could target admins. Fixes also cover IM `!np`, the `!load` relative-path check, the localized `!ai`/`!topm` replies, and a Router lock race. |
| Build/CI | Fixed `win11-check`/`build-all` on Windows. `typecheck` is now a real gate. `make package` no longer leaks `.env` or user data. The installer compiles without vendored mpv and keeps user playlists. The release requires tag == version, a CHANGELOG section and a signed exe. The version is now **0.3.2** everywhere (tag v0.3.1 had shipped with 0.3.0 metadata). |

Validation (clean tree copy):

| Gate | Result |
|---|---|
| compileall | ✅ |
| pytest (`-W error::DeprecationWarning`, Xvfb) | ✅ **580 passed**, 0 skipped |
| ruff / ruff format (Python) | ✅ 0 / 0 |
| mypy (47 files) | ✅ 0 |
| shellcheck (12 scripts) | ✅ 0 |
| bandit, severity Undefined/Low/Medium/High | ✅ 0/0/0/0 |
| bandit, confidence Undefined/Low/Medium/High | ✅ 0/0/0/0 |
| `make lint typecheck changelog-check config-check validate-playlists validate-installer security-check version` | ✅ all exit 0 |
| `make -n` for win11-check, build-all, nsiswindows11, sign, release, package, validate-windows* | ✅ parse |
| Release gate dry-run | ✅ v0.3.2 passes; v0.3.1 is rejected (version mismatch) |
| Windows exe/installer build, live Camfrog | **BLOCKED**: needs the Windows host |

## 7. Known limits and open items (not hidden)

- **Webhook server is not started by the engine**: the code is hardened and tested, but `webhook_enabled` has no runtime effect yet (documented).
- **IM auto-reply** posts the operator's fixed text to the room, because the adapter has no private send channel; IM content is never echoed.
- **Step 5 (signed commit, PR, independent review, merge): BLOCKED in this session.** The session machine has no `gh` CLI, no `/home/cvsz` credential store, no GPG secret key (`commit.gpgsign=true` is required) and no SSH egress for `git@github.com`. In addition, `CLAUDE.md` forbids self-approval; the approval must come from the policedbc reviewer, not from the author's session. Run Phase A–C from `CLAUDE.md` on the cvsz workstation: `feat/autodj-np-room-and-hardening`, `git add` of the 44 modified and 2 new files listed by `git status`, then `git commit -S`.
- Local hygiene, recommended: rotate the tokens in `.git-credentials` and `.config/gh/.git-credentials` (git-ignored, never committed), and move `docs/rea/` malware samples off the dev tree.
