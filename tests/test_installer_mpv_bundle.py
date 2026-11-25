"""Full installer: the whole mpv folder is packaged and installed by default.

Before: SEC_MPV was optional and unchecked (``Section /o``), so a default install had
no mpv even when the installer carried it; ``File /nonfatal`` let a build without mpv
pass silently; the section ran ``mpv-register.bat`` without ``/S`` (the script ends in
``pause``, stalling the installer); and the uninstaller never unregistered mpv.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NSI = (ROOT / "installer.nsi").read_text(encoding="utf-8")
PS1 = (ROOT / "scripts" / "build_installer.ps1").read_text(encoding="utf-8")
SH = (ROOT / "scripts" / "build_installer_linux.sh").read_text(encoding="utf-8")


def _branches(text: str, define: str) -> tuple[str, str]:
    """Return the (ifdef, else) bodies of the first ``!ifdef define`` block."""
    m = re.search(rf"!ifdef {define}\n(.*?)!else\n(.*?)!endif", text, re.S)
    assert m, f"no !ifdef {define} ... !else ... !endif block"
    return m.group(1), m.group(2)


def _mpv_section() -> str:
    start = NSI.index("!ifdef BUNDLE_MPV\nSection")
    return NSI[start : NSI.index("SectionEnd", start)]


def test_bundled_mpv_section_is_selected_by_default():
    full, plain = _branches(_mpv_section(), "BUNDLE_MPV")
    assert re.search(r'^Section "[^"]+" SEC_MPV$', full.strip(), re.M), full
    assert "/o" not in full
    assert 'Section /o "mpv + yt-dlp" SEC_MPV' in plain


def test_bundled_mpv_files_are_mandatory_and_recursive():
    section = _mpv_section()
    file_block = section[section.index('SetOutPath "$INSTDIR\\mpv"') :]
    m = re.search(r"!ifdef BUNDLE_MPV\n(.*?)!else ifndef NO_MPV\n(.*?)!endif", file_block, re.S)
    assert m, file_block
    assert m.group(1).strip() == 'File /r "dist\\mpv\\*.*"'
    assert m.group(2).strip() == 'File /nonfatal /r "dist\\mpv\\*.*"'
    assert 'if ($NoMpv) { $nsisArgs += "/DNO_MPV" }' in PS1


def test_mpv_registration_never_waits_for_a_key():
    code = [ln for ln in _mpv_section().splitlines() if not ln.lstrip().startswith(";")]
    assert not any("mpv-register.bat" in ln for ln in code), code
    assert "nsExec::ExecToLog '\"$INSTDIR\\mpv\\mpv.exe\" --register'" in NSI
    # Silent installs must not stop on the success dialog.
    assert NSI.count("/SD IDOK") >= 2


def test_uninstaller_unregisters_only_its_own_mpv_and_app_path():
    uninstall = NSI[NSI.index("Section Uninstall") :]
    assert 'StrCmp $0 "$INSTDIR\\mpv\\mpv.exe" 0 mpv_unregister_done' in uninstall
    assert "--unregister" in uninstall
    assert uninstall.index("--unregister") < uninstall.index('RMDir /r "$INSTDIR\\mpv"')
    assert 'StrCmp $0 "$INSTDIR\\AutoDJ.exe" 0 +2' in uninstall


def test_uninstaller_removes_every_launcher_the_installer_adds():
    main = NSI[NSI.index('Section "!MainProgram" SEC_MAIN') : NSI.index("SectionEnd")]
    uninstall = NSI[NSI.index("Section Uninstall") :]
    for name in ("start.bat", "check.bat", "readme.txt", "run_autodj.py", "AutoDJ.exe"):
        assert f'File "dist\\{name}"' in main, name
        assert f'Delete "$INSTDIR\\{name}"' in uninstall, name


def test_build_scripts_mirror_the_mpv_folder_and_define_bundle():
    assert "robocopy $MpvDir $mpvDest /MIR" in PS1
    assert "Compare-Object @(Get-TreeListing $MpvDir) @(Get-TreeListing $mpvDest)" in PS1
    assert 'if ($bundleMpv) { $nsisArgs += "/DBUNDLE_MPV" }' in PS1
    assert "[switch]$RequireMpv" in PS1 and "[switch]$NoMpv" in PS1
    assert 'rsync -a --delete "$REPO_ROOT/mpv/" "$SRCDIR/mpv/"' in SH
    assert 'BUNDLE_MPV_DEFINE="/DBUNDLE_MPV"' in SH
