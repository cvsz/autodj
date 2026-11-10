# TODO / FIXME / HACK / XXX / Stub Inventory — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Method:** Grep across `camfrog_autodj/`, `tests/`, `tools/`, `scripts/` for TODO, FIXME, HACK, XXX, NotImplemented, bare `pass`, placeholders.

## Convention applied

Per policy: "Do not mechanically remove intentional pass statements or TODO comments." Items below are classified as **intentional** (documented defensive / best-effort / fake-stub) or **actionable**. None were removed without justification.

## Intentional `pass` statements (retained)

| File | Line | Context | Classification |
|------|------|---------|----------------|
| `camfrog_autodj/adapters/base.py` | 25 | `ChatAdapter.close()` no-op base | Intentional — base no-op, adapters override |
| `camfrog_autodj/adapters/__init__.py` | 65 | `NullAdapter.close()` | Intentional — NullAdapter holds no resources |
| `camfrog_autodj/library.py` | 48 | `mutagen` metadata error fallback | Intentional — never crash folder scan on bad metadata |
| `camfrog_autodj/engine.py` | 960, 965 | `_im_auto_reply_loop` polling sleep | Intentional — idle loop |
| `camfrog_autodj/player.py` | 204, 220 | fade-out OSError/ValueError | Intentional — fade-out is best-effort |
| `camfrog_autodj/gui.py` | 84 | `_do_clip` TclError | Intentional — clipboard best-effort |
| `camfrog_autodj/gui.py` | 489, 514, 528 | DPI / dark titlebar / icon | Intentional — best-effort Windows visuals |
| `camfrog_autodj/gui.py` | 547 | `_folder_scan_timeout` except | Intentional — timer already canceled |
| `camfrog_autodj/gui.py` | 1844 | folder dialog failure | Intentional — dialog failure is non-fatal |
| `camfrog_autodj/migrate.py` | 123, 125 | registry read exceptions | Intentional — never let registry reads crash startup |
| `tests/fake_tk.py` | multiple | Fake Tk stub methods | Intentional — headless test double |
| `tests/test_core.py:63`, `test_hardening.py:804/815`, `test_play_flow.py:32/46` | various | Test stubs / no-op assertions | Intentional — test doubles |

## TODO / FIXME / HACK / XXX markers

None found as actionable code debt. The tokens "todo", "fixme", "xxx" appear only in `migrate.py:30-32` as placeholder-detection tokens (data, not code comments).

## NotImplemented / stubs

None found in production code. All abstract methods (`ChatAdapter.messages`, `ChatAdapter.send`) are implemented by `ConsoleAdapter`, `LogTailAdapter`, `UiaAdapter`, and `NullAdapter`.

## Conclusion

No actionable TODO/FIXME/HACK/XXX or unimplemented stubs remain in production code. All `pass` statements are documented, intentional, and safe.
