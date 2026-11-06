# Windows Qualification — Camfrog AutoDJ

**Repository:** cvsz/autodj  
**Branch:** `feat/autodj-enhancements-and-fixes`  
**HEAD SHA:** `a918e68`  
**Application version:** `0.2.6`  
**Assessment date:** 2026-11-06  
**Assessor:** AUSI Windows Qualification Engineer  
**Environment:** Linux (x86_64), Python 3.14.4 — NO Windows, NO Camfrog, NO mpv available  

---

## 0. Executive Summary

This environment is Linux. Windows-specific functionality (UI Automation, mpv IPC, PyInstaller freeze, NSIS installer, TTS via SAPI5, clipboard via pyperclip on Windows) **cannot be executed or verified here**. Per AUSI evidence rules, a Linux test cannot prove Windows UI Automation works, a mocked mpv cannot prove real audio output works, and a successful PyInstaller build cannot prove the installer works.

**Classification: WINDOWS QUALIFICATION NOT ACHIEVED in this environment.** All Windows-specific claims are classified UNVERIFIED, not assumed working. A Windows machine with Camfrog installed is required to complete Windows qualification.

---

## 1. Real vs Simulated Verification Matrix

| Capability | Verified on | Method | Status |
|------------|-------------|--------|--------|
| Pure-Python logic (config, commands, queue, library parsing) | Linux | pytest (315 tests) | VERIFIED |
| `Config.load()` validation, `_RANGES`, `_CHOICES`, `_REGEXES` | Linux | pytest | VERIFIED |
| `Router.handle` IM/no-prefix, admin, cooldown, rate limit | Linux | pytest (mocked `ChatMessage`) | VERIFIED |
| `PlayQueue.add_request(position=...)`, threading | Linux | pytest | VERIFIED |
| `Engine.seek()` delegation to fake player | Linux | pytest (fake `SeekablePlayer`) | VERIFIED |
| Auto-reply `_load_auto_reply_messages`, rotation, path resolution | Linux | pytest | VERIFIED |
| `library.scan_folder` bad-file skip, `local_track` exception catch | Linux | pytest (mutagen mocked/absent) | VERIFIED |
| GUI TOML writer logic (auto_reply_* fields) | Linux | pytest (tomllib round-trip) | VERIFIED |
| Ruff lint on new code | Linux | ruff | VERIFIED |
| UI Automation (`adapters/uia.py`) | Windows only | — | UNVERIFIED |
| `winmsg.py` Windows message posting | Windows only | — | UNVERIFIED |
| `launcher.py` Camfrog auto-launch | Windows only | — | UNVERIFIED |
| `MpvPlayer` real mpv process + IPC | Windows/Linux with mpv | — | UNVERIFIED (no mpv here) |
| `tts.py` pyttsx3 SAPI5 voices | Windows only | — | UNVERIFIED (no pyttsx3 here) |
| `pyperclip` clipboard on Windows | Windows only | — | UNVERIFIED |
| PyInstaller `AutoDJ.spec` build | Windows | — | UNVERIFIED |
| NSIS `installer.nsi` build | Windows | — | UNVERIFIED |
| Installer per-user `%APPDATA%`, upgrade preserves data | Windows | — | UNVERIFIED |
| Code signing | Windows + cert | — | UNVERIFIED |
| Real Camfrog client integration | Windows + Camfrog | — | UNVERIFIED |
| Real audio playback through mpv | Windows + mpv | — | UNVERIFIED |

---

## 2. Why Each Limitation Exists

| Limitation | Reason | AUSI evidence classification |
|------------|--------|------------------------------|
| No Windows OS | This is a Linux environment | UNVERIFIED |
| No Camfrog client | Camfrog is Windows-only, not installed | UNVERIFIED |
| No mpv binary | mpv not installed | UNVERIFIED |
| No pyttsx3 / mutagen | Not installed in this Python environment | UNVERIFIED (Linux) |
| No PyInstaller freeze test | Not run; would require Windows | UNVERIFIED |
| No NSIS installer test | Not run; would require Windows | UNVERIFIED |
| No code signing | No signing certificate available | UNVERIFIED |

Per AUSI rules: these are **UNVERIFIED**, not "passed." They are not assumed to work. They require a Windows qualification environment.

---

## 3. What CAN Be Verified on Linux

The portable, platform-independent components are fully verified:

- Configuration loading and validation (`config.py`)
- Command parsing, authorization, cooldown, rate limiting (`commands.py`)
- Play queue behavior (`playqueue.py`)
- Seek delegation (`engine.py` → `player.py` interface)
- Auto-reply message loading, rotation, path resolution (`engine.py`)
- Library URL parsing, host validation, bad-file resilience (`library.py`)
- Chat message parsing (`adapters/base.py`)
- Message sanitisation (`textutil.py`)
- Track model, time formatting (`models.py`)

These are verified by the 315-test suite on Linux.

---

## 4. What Must Be Verified on Windows (Before Release)

| Check | Procedure | Environment |
|-------|-----------|-------------|
| UI Automation finds Camfrog room window | Run `AutoDJ.exe --discover`; verify window/control resolution | Windows 10/11 + Camfrog |
| IM messages produce `is_im=True` | Send IM from Camfrog; inspect adapter output | Windows + Camfrog |
| Real mpv playback + seek | Play a local MP3; call `Engine.seek()`; verify position changes | Windows + mpv |
| Auto-reply loop sends to room | Enable auto-reply; observe messages appear in Camfrog room | Windows + Camfrog |
| PyInstaller build | `build.ps1`; verify `AutoDJ.exe` launches | Windows |
| NSIS installer | Build installer; install/upgrade/uninstall; verify data preserved | Windows |
| Code signing | Sign `AutoDJ.exe` + installer; verify signature | Windows + cert |

---

## 5. Evidence Classification Summary

| Area | Classification | Basis |
|------|----------------|-------|
| Portable Python logic | VERIFIED | 315 pytest tests on Linux |
| Windows-only code paths | UNVERIFIED | No Windows/Camfrog/mpv available |
| Build/packaging/signing | UNVERIFIED | No PyInstaller/NSIS/cert available |
| Real Camfrog integration | UNVERIFIED | No Camfrog client available |
| Real audio playback | UNVERIFIED | No mpv available |

---

## 6. Next Actions for Windows Qualification

1. Provision a Windows 10/11 machine with Camfrog installed.
2. Install mpv and yt-dlp.
3. Run `AutoDJ.exe --check` and `AutoDJ.exe --discover`.
4. Verify IM command handling end-to-end with real Camfrog.
5. Verify auto-reply loop sends messages to the room.
6. Run PyInstaller build (`build.ps1`) and NSIS installer.
7. Code-sign artifacts.
8. Record results in this document; reclassify UNVERIFIED → VERIFIED where evidence supports.

---
*End of Windows Qualification Assessment*