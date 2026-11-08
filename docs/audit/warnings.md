# Warnings — cvsz/autodj

## Lint warnings (Ruff)

`ruff check camfrog_autodj tests tools` → **All checks passed.** No warnings remain. The following rules are intentionally ignored per `pyproject.toml` with documented justification:

- `E501` — long paths/regexes are intentional.
- `B014`, `BLE001` — defensive broad/bare except clauses (chat loop must never crash).
- `S101` — assert used in tests and internal invariants.
- `S108`/`S307`/`S603`/`S607`/`S608` — subprocess never uses shell; argument lists only; paths resolved explicitly.

## ShellCheck warnings (style only, no errors)

All `.sh` scripts pass `bash -n`. ShellCheck reports only style suggestions:

| Script | Warning | Severity | Disposition |
|--------|---------|----------|-------------|
| `scripts/build_installer_linux.sh:77` | SC2181 — check exit code directly, not via `$?` | Style | Minor; script is Linux-only installer helper |
| `scripts/deploy-workflow-all-repos.sh:19` | SC2034 — `ACCOUNTS_FILE` unused | Style | Referenced externally / config |
| `scripts/gh-switch.sh:49,60,95,112` | SC2034 — unused locals | Style | gh-switch account helper |

None affect correctness. No `|| echo warning` suppression of failures is used anywhere.

## Doctor (`--check`) informational warnings

`doctor.run_checks` emits OK/WARN/INFO (never FAIL for non-critical): missing yt-dlp, missing JS runtime, empty admins, empty music_dirs, missing mutagen/pyttsx3, default bot_nick, empty audio_device. These are advisory, not errors.

## Conclusion

No warnings indicate defects. All remaining warnings are intentional, documented, or style-level only.
