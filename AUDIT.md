# AutoDJ 0.1.0 -> 0.2.0: audit and review

## Scope and method
Everything in the repository was read: engine, commands, queue, player, library, config, discovery, UI Automation and web-chat parsing, Windows message layer, GUI, build/sign scripts, tests. Findings were **reproduced on the original code before being fixed**, each fix has a regression test, and the tests were **mutation-checked** (each fix deliberately broken in a scratch copy; the matching test failed every time). The real command-line entry point was also run end to end against a fake `mpv`.

### What could NOT be verified here
No Windows, Camfrog, real mpv, real yt-dlp, PowerShell or on-screen Tk in the review environment. So: `build.ps1`, UI Automation, background sending, TTS and **how the new GUI looks** are untested by me. The GUI's logic and every option name it passes to Tk are exercised against a strict fake (`tests/fake_tk.py`), and `test_gui_smoke` runs against real Tk wherever a display exists. Please run `python -m pytest`, `AutoDJ.exe --check`, and open the GUI once.

## Findings
| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| F1 | High | Bot executes its own `!help` reply as a command when `bot_nick` differs from the account nick (reproduced: junk request queued). Your `config.toml` does not set `bot_nick`. | Fixed |
| F2 | High | A track that fails to play is retried with no delay and announced every time. Reproduced: 9,896 attempts and 29,689 queued chat messages in 0.5 s. | Fixed |
| F3 | High | `AutoDJ.exe` built without the `yt_dlp` module (never verified at build time): every YouTube/name request failed. Also mpv cannot play YouTube without `yt-dlp.exe`, which was only a README note. | Fixed + `--check` |
| F4 | Medium | Invalid `config.toml` => raw traceback. (You hit this: `Thumbprint: ...` printed by `make_cert.ps1` had been pasted into the file.) | Fixed |
| F5 | Medium | No config validation. Verified: `admins = "zdevz"` silently became the admin set `{d,e,v,z}`. Wrong types, bad regexes, out-of-range values were accepted. | Fixed |
| F6 | Medium | `!remove` / GUI Remove act on a queue position that can shift between lookup and removal. | Fixed |
| F7 | Medium | `max_requests_per_user` checked before a multi-second lookup only; overlapping requests bypass it. | Fixed |
| F8 | Low-Med | Auto-discovery could write invalid TOML (value with a newline) and wrote non-atomically. | Fixed |
| F9 | Low | mpv ran with `--really-quiet`; failures were undiagnosable. | Fixed (log file captured on failure) |
| F10 | Low | `pause`/`resume` flipped state even when mpv rejected the command. | Fixed |
| F11 | Low | GUI poll loop dies on one exception; chat widget unbounded; GUI Remove by index. | Fixed |
| F12 | Low | Control characters in outgoing text were typed into the room. Duplicate autoplay entries on reload. Non-interruptible send sleep. 4 workers. | Fixed |
| F13 | Info | `AutoDJ.spec` stale vs `build.ps1`; UPX raises antivirus false positives. | Fixed (`--noupx`, spec regenerated) |
| F14 | High | `adapters/uia.py` `_appeared()`: `norm_l` referenced outside its defining loop → `UnboundLocalError` on every background chat send; messages retried endlessly. | Fixed (moved `bot_nick` match inside the loop) |
| F15 | High | `winmsg.py`: `make_lparam`, `pick_child`, `show_noactivate` defined twice at module scope; second definition silently shadowed the first. | Fixed (removed duplicate block) |

## Open items / recommendations (not changed)
- **O1 Admin = display nick only.** Anyone who can show the same nick (look-alike characters, a nick freed by a disconnect) gets admin rights. Keep `admins` short and check how your room handles duplicate/similar nicks.
- **O2 CPU.** The UIA reader walks ~600 child controls twice a second. Unmeasured; `poll_interval` is the knob.
- **O3 Camfrog UI automation is inherently version-fragile** (control indexes, `line_regex`). `--check` and auto-discovery help; nothing else can.
- **O4 One-file exe** unpacks on every start and is what antivirus engines dislike most. Consider `--onedir` plus an installer if you distribute it.
- **O5 yt-dlp ages quickly.** A bundled module goes stale; prefer a `yt-dlp.exe` next to mpv and run `yt-dlp -U`. Recent versions may need a JS runtime (deno) for YouTube (`--check` hints at it).
- **O6 TTS** (`pyttsx3` on SAPI from worker threads) is untested.
- **O7 Secrets hygiene.** `build.ps1` copies your live `config.toml` into `dist\`; do not share `dist\` as is. Prefer the `AUTODJ_PFX_PASSWORD` environment variable over `-Password` (it lands in shell history).
- **O8 No persisted state:** queue, volume and shuffle reset on restart.
- **O9** mpv's control pipe name is predictable; any local process of the same user could control playback. Low risk on a personal PC.

## Verification summary
- Tests: 32 -> 78 (0.2.3 release) -> **130 passed, 1 skipped** (current tree, `python -m pytest -q -p no:faulthandler -p no:cacheprovider`). 7 mutation checks, all caught.
- End to end (real `python -m camfrog_autodj --console` + fake mpv): failing track -> one announcement + mpv's reason in the log; good track -> plays, `!history`, `!block`, `!help` behave; `--check`, `--version`, and four kinds of broken config give readable messages and exit codes.
- All Thai command paths verified end-to-end (`!ช่วยเหลือ`, `!เล่น`, `!เพลงนี้`, `!ข้าม`, `!บล็อก`, `!คิว`, `!ประวัติ`, `!สุ่ม`, `!วนซ้ำ`, `!เสียง`, `!ล้างคิว`, `!พูด`, `!ออกเสียง`, `!โหลด`, `!บล็อก`, `!เลิกบล็อก`, `!โหวตข้าม`, `!ลบ`, `!np`, `!ถัดไป`).
