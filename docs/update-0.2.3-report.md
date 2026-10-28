# Deep compare: working tree `camfrog-autodj` (0.2.2) vs official `camfrog-autodj-0.2.3` zip

Compared: full recursive diff of both trees (excluding `.venv/`, `build/`, `dist/`, caches, `docs/`, `cert/`, `__pycache__`).
Zip extracted to `/tmp/opencode/cmp/0.2.3` (53 files). Differential backup of every edited file: `/tmp/opencode/cmp/backup/`.

## The headline (opposite of the assumption)

The zip is the **official 0.2.3 release** = 0.2.2 + exactly ONE functional change (the Windows-`make` fix).
The working tree, although its version string still said `0.2.2`, already **contains unreleased post-0.2.2 work**
(the "v0.3.0 fixes" list, see `tests/test_v030_fixes.py`) — code the zip does *not* have. Verified by running
the suite: all 15 `test_v030_fixes.py` tests pass against the working-tree code (94/94 total).

Zip internal timestamps: newest content ~Oct 28 05:05 (Makefile/CHANGELOG/README/version bump session).
Working-tree v0.3.0 fixes were applied ~Oct 28 06:25, cert/sign tooling redesign ~11:50–11:59 — **after** the release.

## File-by-file verdict

| File | Working tree | Zip 0.2.3 | Verdict |
| --- | --- | --- | --- |
| `camfrog_autodj/config.py` | has `search_limit` field + `(1,50)` range validation | older, no `search_limit` | **keep tree** (N-cfg-1) |
| `camfrog_autodj/library.py` | `remote_tracks(..., search_limit=...)`, `ytsearch{n}:` | hard-coded `ytsearch1:` | **keep tree** (N-lib-1) |
| `camfrog_autodj/engine.py` | `_remote(..., search_limit=None)` wired from config | no param | **keep tree** (N-eng-1) |
| `camfrog_autodj/player.py` | `play_file` sets `creationflags=CREATE_NO_WINDOW` on `nt` | plain `subprocess.run` (console flash) | **keep tree** (N-player-1) |
| `camfrog_autodj/tts.py` | thread-safe single-engine worker via dedicated thread + queue | naive `pyttsx3.init()` per call (COM STA, not thread-safe) | **keep tree** (N-tts-1) |
| `camfrog_autodj/webchat.py` | `find_web_panes` debug-logs when the view pane is absent | silent `None` return | **keep tree** (N-web-1) |
| `camfrog_autodj/messages.py` | `error` = real sentence (EN/TH) | `error` = bare word "error" | **keep tree** (N-msg-1) |
| `config.example.toml` | documents `search_limit` | older | **keep tree** |
| `tests/test_v030_fixes.py` | 15 regression tests | absent | **keep tree** (local-only file) |
| `build.ps1`, `tools/sign_exe.ps1`, `tools/make_cert.ps1`, `.gitignore` | cert lives in `cert/`, `sign_exe` auto-finds/creates self-signed cert + 3 timestamp-server fallbacks | `.cer` in project root, `sign_exe` demands `-Pfx`/`-Thumbprint`, single timestamp server | **keep tree** (newer redesign) |
| `Makefile` | NEWER design (11:59 Oct 28): recipes are `python -c`/plain commands (no awk/find/grep/cp), `SHELL` falls back to `cmd.exe /c`, `make build` calls `powershell.exe` from WSL2 (works on this machine) | released fail-fast design (05:04 Oct 28): requires bash, one clear `$(error ...)` | **keep tree**; same problem solved a different way; superseded design documented in CHANGELOG |
| `README.md` (Makefile paragraph) | pre-0.2.3 wording | Git-Bash-only wording (matches zip Makefile, not ours) | **merged**: tree wording + note that recipes avoid Unix utils/PS works/WSL works |
| `AutoDJ.spec` | same options, no header comment | documented header comment | **merged**: comment ported (cosmetic; regenerating via build.ps1 makes the file moot) |
| `__init__.py`, `pyproject.toml`, `version_info.txt` | `0.2.2` / `0.2.2.0` | `0.2.3` / `0.2.3.0` | **adopt zip**: version bookkeeping is the one thing the tree genuinely lacked |
| `CHANGELOG.md` | top entry 0.2.2 | has official **0.2.3** section | **adopt zip** entry |

Knock-on files fixed at the same time (all equivalent to the zip's intent):

- `tests/` and sources untouched otherwise (no file regression).

## Result of the update

- `make version` prints `0.2.3`; `make changelog-check` passes; `CHANGELOG.md` has the release entry.
- `python3 -m pytest tests/ -q` → **94 passed** (this includes the fifteen v0.3.0 regression tests).
- No stale `0.2.2` references remain in `pyproject.toml`, `version_info.txt`, `camfrog_autodj/`.

## Caveat / recommendation

This tree is effectively **0.3.0-pre**: a `dist/AutoDJ.exe` built from it now would be labelled 0.2.3 but would
include the unreleased v0.3.0 fixes (search_limit, TTS worker, CREATE_NO_WINDOW, descriptive error text, webchat
debug log) plus the cert/sign redesign. Two honest options going forward:

1. Tag the next build 0.2.3 and ship as-is (accept that this 0.2.3 ≠ the official 0.2.3 zip beyond the Makefile part), or
2. Rename the next release **0.3.0**: extend the `0.2.3` changelog entry into `0.3.0` documenting the v0.3.0 fixes
   (the candidates are already itemised in `tests/test_v030_fixes.py` N-tts-1/N-player-1/N-lib-1/N-cfg-1/N-msg-1/N-web-1/N-eng-1).

Recommended: option 2.
