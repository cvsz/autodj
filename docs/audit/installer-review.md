# Installer Review — cvsz/autodj

**BLOCKED — Windows-only.** NSIS (`makensis`) and `install.ps1` require Windows 11. No installer was built or tested here. Nothing is assumed.

## Installer.nsi audited (source inspection)

- Per-user installation to `%APPDATA%\Camfrog AutoDJ` (no admin rights required) — README 0.2.6 highlight.
- HKCU registry, no admin required.
- Shortcuts: Desktop, Start Menu, Config editor, Uninstaller.
- `config.toml` handling: nonfatal / optional (PRs #23/#24/#47); bundled standard config.toml (#64).
- mpv + yt-dlp + VBCable: marked optional/nonfatal (#48); post-install `mpv-register.bat` + VBCable silent execution (#66).
- Upgrade behavior: auto-uninstall old version (#17).
- Uninstall: Start Menu → Uninstall or `uninstall.ps1`.
- Version checks, reinstallation, Windows compatibility: documented in `install.ps1`.

## Verification items not executable here

| Item | State | Reason |
|------|-------|--------|
| `makensis` build | BLOCKED | Windows + NSIS |
| Install directory / upgrade / uninstall | BLOCKED | Windows runtime |
| Shortcuts / file permissions | BLOCKED | Windows runtime |
| User data preservation | BLOCKED | Windows runtime |
| Version checks / rollback / reinstallation | BLOCKED | Windows runtime |
| `install.ps1` end-to-end (Python/mpv/yt-dlp via winget) | BLOCKED | Windows 11 + winget |

## Existing artifacts (not produced by this audit)

`dist/Camfrog-AutoDJ-Setup-0.2.6.exe`, `dist/Camfrog-AutoDJ-Setup-0.2.8.exe`, `dist/Camfrog-AutoDJ-Setup-0.2.8.zip` are present in the repo but are **pre-existing artifacts**, not built or signed in this audit. Their signatures were not verified; no claim is made about them.

## Conclusion

Installer reviewed by source inspection only. Build/install/test on Windows is BLOCKED and must be done before any release claim.
