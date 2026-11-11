# Plan — Fix `make build*` for Windows 11 and Linux cross-platform builder (camfrog-autodj)

## Global constraints

- Windows path must keep using `build.ps1` unchanged in behavior (flags, signing, smoke test).
- Version must always equal `pyproject.toml`'s `version`; no hard-coded "0.2.3"/"0.3.0" literals in substitution code.
- Keep Makefile conventions: `logs/` build logging, `##` help comments, `ifeq ($(OS),Windows_NT)` dispatch style.

## Tasks

**Task 1 — Fix version plumbing (all platforms).**
Change every caller to `/DAPP_VERSION=<v>` (the `/IfNDef` default yields to a command-line define). Make the regex/sed substitutions version-agnostic (`APP_VERSION\s+"[^"]+"` → new value) as defense-in-depth. Touch: `scripts/build_installer.ps1:89,102`, `scripts/build_installer_linux.sh:68,75`, `.github/workflows/release.yml:107` (strip a leading `v` from `github.ref_name` so it matches the pyproject format). Add a pytest that runs each script's substitution against a fixture nsi with default `9.9.9` and asserts output contains the pyproject version.

**Task 2 — Cross-platform `build`/`build-clean`/`build-all` dispatch.**
In the Makefile, remove the Linux `exit 1` from `build`, `build-clean`, `build-all`; the `ifeq` Windows branch stays as-is, the Linux branch delegates to the new Wine build (Task 3) and then the Linux installer (Task 4). `build-all` on Linux = env check → Wine exe build → NSIS installer. Windows-only targets (`win11-check`, `mpv-check`, `nsis-check`, `trustsign`) keep their guards.

**Task 3 — New `scripts/build_exe_linux.sh` (Wine + PyInstaller).**
Env checks: `wine` or `wine64`; Windows Python in the Wine prefix (path overridable, e.g. `WINE_PYTHON`) with PyInstaller installed — actionable error messages with install hints. Run `python -m PyInstaller <spec>` under Wine with the same flags as `build.ps1`; copy `config.example.toml → dist/config.toml`, mpv handling, and the installer file set, mirroring `build.ps1`. Skip signing with a printed notice; smoke test `wine dist/AutoDJ.exe --version` guarded by `AUTODJ_SKIP_SMOKE=1`. **DRY:** extract the PyInstaller flags into one shared source used by both `build.ps1` and this script — a checked-in `AutoDJ.spec` (⚠️ `build.ps1` `-Clean` deletes `$Name.spec`; the clean list must be adjusted or the spec regenerated from a shared generator before each build).

**Task 4 — Fix `build-all-linux` / `build_installer_linux.sh`.**
Detection order: native `makensis` on PATH → `$NSIS_PATH` → Wine `makensis.exe` fallback; drop the hard `wine64` requirement when native makensis is present. Fix `REQUIRED_FILES` (`LICENSE`, drop `uninstall.ps1`), and make paths robust when `SRCDIR != dist`. Mirror the same detection logic in Makefile instead of duplicating the hardcoded check.

**Task 5 — Makefile hygiene in build* scope.**
Fix `sign` (`-NoSign=false` → plain `build.ps1` invocation). `wine64 || wine` detection. Help text updated to say `build*` works on both platforms.

**Task 6 — Verification.**
- Linux: `bash -n` all touched scripts; `shellcheck scripts/*.sh`; `make -n build`, `make -n build-clean`, `make -n build-all` print correct per-OS recipes; `make validate-installer` passes; new version-substitution test passes.
- Windows 11 (human gate): `make build`, `make build-all`, `make sign`; bump pyproject to `0.3.1` and confirm installer is named/versioned `0.3.1`.

## Review focus / risks

1. Wine path translation (`/mnt/d/...` ↔ `z:\...`) — spec must be path-agnostic.
2. Native Linux makensis compatibility with plugins in `installer.nsi`.
3. Spec file vs `-Clean` deletion — easiest silent regression.
4. CI parity: `release.yml` calls `build.ps1 -Clean` — must still work after spec-file refactor.
5. Unsigned Linux artifacts must be clearly labeled in output.
