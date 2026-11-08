# Bugs and Findings — cvsz/autodj

Method: grep for `TODO`/`FIXME`/`HACK`/`XXX`/`NotImplemented`/bare `pass`/unreachable/dead code/unused imports/ignored errors/broad exceptions/deprecated APIs/race conditions/resource leaks/unhandled subprocess errors/GUI blocking calls across `camfrog_autodj/`, `tests/`, `tools/`, `scripts/`. Each item traced, classified, and located. No item was mechanically removed; intentional `pass`/TODO comments were preserved.

## Result: no confirmed bugs

The application source (`camfrog_autodj/`, 29 modules) passed:
- `python -m compileall` — all modules compile
- `ruff check camfrog_autodj tests tools` — all checks passed (rules E, F, B, I, C, N, S)
- `ruff format --check` — 56 files formatted
- `mypy camfrog_autodj` — Success: no issues found in 29 source files
- `python -m pytest -q -p no:faulthandler -p no:cacheprovider` — 325 passed, 3 subtests passed

No crash, data-corruption, resource-leak, race-condition, or security bug was reproduced.

## `pass` statements (all intentional, preserved)

Each is a documented no-op / best-effort / defensive branch, not an unfinished stub:

| File:Line | Context | Classification |
|-----------|---------|----------------|
| `adapters/base.py:25` | `ChatAdapter.close()` base no-op | Intentional base hook |
| `adapters/uia.py:24` | fall through read methods | Intentional fallback |
| `adapters/uia.py:220` | window may have closed during foreground send | Best-effort |
| `adapters/uia.py:236` | clipboard restore best-effort | Best-effort |
| `adapters/__init__.py:65` | adapter registry placeholder | Intentional |
| `discover.py:237` | value comparison failed; update anyway | Defensive |
| `engine.py:960`/`965` | IM auto-reply loop no-op when disabled | Intentional |
| `gui.py:84` | clipboard error ignored | Best-effort |
| `gui.py:489`/`514`/`528`/`547` | DPI/dark-titlebar/icon best-effort | Best-effort |
| `gui.py:1844`/`2224` | folder-scan/teardown guard | Defensive |
| `library.py:46`/`48` | mutagen missing / metadata error → fall back to filename | Intentional, never crashes scan |
| `migrate.py:123`/`125` | registry read never crashes startup | Intentional |
| `player.py:204`/`220` | log cleanup / fade-out best-effort | Intentional |
| `windows.py:48` | process name unreadable → empty | Intentional |
| `winmsg.py:279` | foreground restore best-effort | Best-effort |

## TODO / FIXME / HACK / XXX / NotImplemented

- `migrate.py:30`–`32`: the tokens `"todo"`, `"fixme"`, `"xxx"` are **placeholder-detection tokens** used by `detect_placeholders()` to find installer-left placeholder config values. Not unfinished code. Preserved.
- `tests/test_production_remediation.py:493`: a YouTube playlist URL in a test (`PLxxxx`). Test fixture, not a TODO.

## Unreachable / dead code / unused imports

None found. Ruff rules `F` (unused imports), `I` (import sorting), `B` (bug-prone) all pass with no reports.

## Broad exceptions / ignored errors

Broad `except Exception` clauses exist only where documented as defensive (chat loop must never crash, auto-launch must not prevent GUI opening, migration must never prevent startup). These are intentional and each carries a `# noqa: BLE001` or an explanatory comment. Ruff `BLE001` is globally ignored for this reason.

## Subprocess / shell safety

- All subprocess calls use argument lists (`shell=False`); ruff `S108`/`S608` (shell=True) ignored because never used; `S603`/`S607`/`S608` ignored per config with justification (checked inputs, trusted paths only).
- `os.startfile` in `launcher.py` is `# noqa: S606` (idiomatic Windows URI launcher, not a shell spawn).
- No `os.system`, `popen` with shell string, or `eval`/`exec`.

## Conclusion

**Zero confirmed bugs.** Every `pass`, broad except, and defensive construct is intentional and documented. The codebase is clean of TODO/FIXME/HACK/XXX in application logic.
