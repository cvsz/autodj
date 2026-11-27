; AutoDJ - NSIS Installer Script
; Builds a professional Windows installer (.exe) for distribution
;
; Usage: makensis installer.nsi
; Requires: NSIS 3.08+ (makensis)
;
; This installer packages the built AutoDJ.exe + config + assets
; and creates a proper Windows installer with:
; - License page
; - Component selection
; - Directory selection
; - Start Menu shortcuts
; - Uninstaller
; - Registry entries for Add/Remove Programs
; - In-place upgrade that preserves existing user configuration
; - mpv + yt-dlp + VBCable driver
; - Per-user application installation; optional driver setup requires elevation

; -----------------------------------------------------------------------------
; Unicode & Compression
; -----------------------------------------------------------------------------
!define Unicode true
!define MUI_ABORTWARNING

; -----------------------------------------------------------------------------
; Metadata (overridable from command line)
; -----------------------------------------------------------------------------
!define /IfNDef APP_NAME "Camfrog AutoDJ"
!define /IfNDef APP_VERSION "0.3.20"
!define /IfNDef APP_PUBLISHER "ZEAZDEV COMPANY LIMITED"
!define /IfNDef APP_WEBSITE "https://github.com/cvsz/autodj"
!define /IfNDef APP_EXE "AutoDJ.exe"
; Keep in step with scripts/build_installer.ps1, windows-build.yml and release.yml,
; which all look for Camfrog-AutoDJ-Setup-<version>.exe (tests/test_im_detect_discover.py).
!define /IfNDef INSTALLER_NAME "Camfrog-AutoDJ-Setup-${APP_VERSION}.exe"
; Directory the finished installer is written to (build scripts pass /DOUTDIR=...).
; Relative paths resolve against the makensis working directory (repo root).
!define /IfNDef OUTDIR "."

; -----------------------------------------------------------------------------
; Version info for the executable manifest

; -----------------------------------------------------------------------------
; Manifest for Windows Vista+ (DPI awareness, UAC)
; -----------------------------------------------------------------------------
!define /IfNDef MANIFEST_INSTALL_DESC "${APP_NAME} ${APP_VERSION} Installer"

; -----------------------------------------------------------------------------
; General Settings
; -----------------------------------------------------------------------------
Name "${APP_NAME} ${APP_VERSION}"
OutFile "${OUTDIR}\${INSTALLER_NAME}"
InstallDir "$APPDATA\AutoDJ"
InstallDirRegKey HKCU "Software\AutoDJ" "InstallDir"
ShowInstDetails show
ShowUninstDetails show
RequestExecutionLevel user
XPStyle on
CRCCheck on
; Compressor is controlled by NSIS nsisconf.nsh (/FINAL).

; -----------------------------------------------------------------------------
; Modern UI 2
; -----------------------------------------------------------------------------
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "x64.nsh"

; Close a running AutoDJ (and an mpv) started from THIS install folder before
; files are replaced or removed: a running AutoDJ.exe is locked, so an upgrade
; stopped with "Error opening file for writing" and an uninstall left files
; behind.  Matched by path, so another copy or the user's own mpv is untouched.
!macro STOP_RUNNING_AUTODJ
    DetailPrint "Closing AutoDJ if it is running from $INSTDIR ..."
    nsExec::ExecToLog `powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "Get-Process AutoDJ,mpv -ErrorAction SilentlyContinue | Where-Object { $$_.Path -like '$INSTDIR\*' } | Stop-Process -Force -ErrorAction SilentlyContinue"`
    Pop $0
    Sleep 1000
!macroend

!define MUI_ICON "app.ico"
!define MUI_UNICON "app.ico"
!define MUI_WELCOMEPAGE_TITLE "Welcome to the ${APP_NAME} Setup Wizard"
!define MUI_WELCOMEPAGE_TEXT "This wizard will guide you through the installation of ${APP_NAME} ${APP_VERSION}.\n\nClick Next to continue."
!define MUI_FINISHPAGE_TITLE "Installation Complete"
!define MUI_FINISHPAGE_TEXT "Setup has finished installing ${APP_NAME} ${APP_VERSION} on your computer.\n\nClick Finish to close the wizard."
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APP_NAME} now"
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!define MUI_FINISHPAGE_LINK "https://github.com/cvsz/autodj"
!define MUI_FINISHPAGE_LINK_LOCATION "https://github.com/cvsz/autodj"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\README.md"

!define MUI_LICENSEPAGE_TEXT_TOP "Please review the license agreement before installing ${APP_NAME}."
!define MUI_LICENSEPAGE_TEXT_BOTTOM "If you accept the terms, click I Agree to continue. You must accept the agreement to install ${APP_NAME}."

!define MUI_COMPONENTSPAGE_TEXT_TOP "Select the components you want to install. Required components are always installed."
!define MUI_COMPONENTSPAGE_TEXT_COMPLIST "Available components:"
!define MUI_COMPONENTSPAGE_TEXT_DESCRIPTION_TITLE "Description"
!define MUI_COMPONENTSPAGE_TEXT_DESCRIPTION_INFO "Hover over a component to see its description."
!define MUI_COMPONENTSPAGE_SMALLDESC

!define MUI_DIRECTORYPAGE_TEXT_TOP "Choose the installation folder for ${APP_NAME}."
!define MUI_DIRECTORYPAGE_TEXT_DESTINATION "Destination Folder"

!define MUI_STARTMENUPAGE_DEFAULTFOLDER "AutoDJ"
!define MUI_STARTMENUPAGE_NODISABLE

!define MUI_INSTFILESPAGE_FINISHHEADER_TEXT "Installation Complete"
!define MUI_INSTFILESPAGE_FINISHTEXT "Click Finish to close the wizard."

; Header images (optional - uncomment if you have banner images)
; !define MUI_WELCOMEFINISHPAGE_BITMAP "contrib\graphics\ws9x-50.bmp"
; !define MUI_UNWELCOMEFINISHPAGE_BITMAP "contrib\graphics\ws9x-50.bmp"

; License

; -----------------------------------------------------------------------------
; Components
; -----------------------------------------------------------------------------
Section "!MainProgram" SEC_MAIN
    SectionIn RO
    SetOutPath "$INSTDIR"
    !insertmacro STOP_RUNNING_AUTODJ
    ; Log destination: AutoDJ writes autodj.log (and rotations) here so operators
    ; can read bot actions from the install folder. Keep logs on upgrades.
    CreateDirectory "$INSTDIR\logs"
    File "dist\AutoDJ.exe"
    File "dist\app.ico"
    File "dist\README.md"
    File "dist\CHANGELOG.md"
    File "dist\LICENSE"
    File /nonfatal "dist\ads-list.json"
    ; Preserve an existing user configuration during upgrades.
    ; Ship the staged template (dist\config.toml, copied from config.example.toml by the
    ; build scripts) -- never a developer's local, possibly secret-bearing config.toml.
    IfFileExists "$INSTDIR\config.toml" config_exists
    File "dist\config.toml"
config_exists:
    ; Bake this installation's absolute media-tool paths into config.toml.
    ; AutoDJ.exe handles this without starting the bot or the GUI.
    ExecWait '"$INSTDIR\AutoDJ.exe" --write-install-paths -c "$INSTDIR\config.toml"'
    ; config.toml can be customized by install.ps1 on first run (interactive prompts)
    File "dist\run_autodj.py"
    ; Client-friendly launchers (relative paths - work from any install folder)
    File "dist\start.bat"
    File "dist\check.bat"
    File "dist\readme.txt"
SectionEnd

Section "Playlist Directory" SEC_PLAYLIST
    SetOutPath "$INSTDIR\playlist"
    ; Never clobber playlists the user edited: only replace older copies on upgrade
    SetOverwrite ifnewer
    File /r "dist\playlist\*.json"
    SetOverwrite on
SectionEnd

; Full installer: scripts/build_installer.ps1 mirrors the repo's mpv\ folder (all of it:
; mpv.exe, mpv.com, yt-dlp.exe, _internal\, vbcable\, libbluray jars, register scripts,
; LICENSE.GPL) into dist\mpv\ and passes /DBUNDLE_MPV when it holds mpv.exe and
; yt-dlp.exe. The component is then installed by default and a missing file fails the
; build. Without the define (CI release builds: mpv\ is not in git) it stays optional
; and may be empty.
!ifdef BUNDLE_MPV
Section "mpv + yt-dlp (bundled)" SEC_MPV
!else
Section /o "mpv + yt-dlp" SEC_MPV
!endif
    ; Keep the bundled mpv inside our own install folder.  Never use $APPDATA\mpv:
    ; that is mpv's per-user config folder (mpv.conf, scripts, input.conf), and the
    ; uninstaller's RMDir /r would delete the user's own mpv settings.
    SetOutPath "$INSTDIR\mpv"
!ifdef BUNDLE_MPV
    File /r "dist\mpv\*.*"
!else ifndef NO_MPV
    File /nonfatal /r "dist\mpv\*.*"
!endif
    ; Register mpv as a media player for the current user (mpv --register writes HKCU).
    ; mpv.exe is called directly and hidden: mpv-register.bat ends with `pause` unless
    ; /S is passed, which stalled the installer on a console waiting for a key.
    IfFileExists "$INSTDIR\mpv\mpv.exe" 0 skip_register
    nsExec::ExecToLog '"$INSTDIR\mpv\mpv.exe" --register'
    Pop $0
    DetailPrint "mpv --register: exit code $0"
skip_register:
SectionEnd

; VB-CABLE: the full installer copies the setup files that are in mpv\vbcable\ but does
; not install the driver (it needs administrator rights). Run
; mpv\vbcable\VBCABLE_Setup_x64.exe as administrator, or install.ps1, which downloads
; Driver Pack 46 from vb-audio.com and runs its setup.

Section "Documentation" SEC_DOCS
    SetOutPath "$INSTDIR\docs"
    File /r "docs\*.md"
SectionEnd

Section "Tools & Scripts" SEC_TOOLS
    SetOutPath "$INSTDIR\tools"
    File /r "tools\*.py"
    File /r "tools\*.ps1"
    File /r "tools\*.sh"
SectionEnd

Section "Install Scripts" SEC_SCRIPTS
    SetOutPath "$INSTDIR"
    File "install.ps1"
    File "install.bat"
SectionEnd

; -----------------------------------------------------------------------------
; Installer Logic
; -----------------------------------------------------------------------------
; Upgrade in place. The previous uninstaller is intentionally not invoked:
; automatic removal could destroy user configuration or interrupt a running app.

Function .onInit
    ; Verify we're on Windows 64-bit.
    ${IfNot} ${RunningX64}
        MessageBox MB_ICONSTOP "This installer requires a 64-bit version of Windows."
        Abort
    ${EndIf}
FunctionEnd

Function .onInstSuccess
    HideWindow
!ifdef BUNDLE_MPV
    MessageBox MB_ICONINFORMATION|MB_OK "AutoDJ has been installed successfully.$\n$\nmpv, yt-dlp and the VB-CABLE setup files are in $INSTDIR\mpv.$\n$\nThe VB-CABLE driver is not installed automatically: run mpv\vbcable\VBCABLE_Setup_x64.exe as administrator, or install.ps1." /SD IDOK
!else
    MessageBox MB_ICONINFORMATION|MB_OK "AutoDJ has been installed successfully.$\n$\nmpv and yt-dlp are not bundled in this installer: run install.ps1, or set mpv_path in config.toml.$\n$\nRun install.ps1 to set up VB-CABLE." /SD IDOK
!endif
FunctionEnd

; -----------------------------------------------------------------------------
; Shortcuts & Registry
; -----------------------------------------------------------------------------
Section -Post
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\AutoDJ"
    CreateShortcut "$SMPROGRAMS\AutoDJ\AutoDJ.lnk" "$INSTDIR\AutoDJ.exe" "--gui" "$INSTDIR\app.ico" 0 SW_SHOWNORMAL "" "Music bot for Camfrog rooms"
    CreateShortcut "$SMPROGRAMS\AutoDJ\Uninstall.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\app.ico" 0 SW_SHOWNORMAL "" "Uninstall AutoDJ"
    CreateShortcut "$SMPROGRAMS\AutoDJ\Edit Config.lnk" "notepad.exe" "$INSTDIR\config.toml" "" 0 SW_SHOWNORMAL "" "Edit configuration"

    ; Desktop shortcut
    CreateShortcut "$DESKTOP\AutoDJ.lnk" "$INSTDIR\AutoDJ.exe" "--gui" "$INSTDIR\app.ico" 0 SW_SHOWNORMAL "" "Music bot for Camfrog rooms"

    ; Registry entries for Add/Remove Programs (per-user)
    ; Required values per NSIS Appendix D
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AutoDJ" "DisplayName" "AutoDJ"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AutoDJ" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AutoDJ" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AutoDJ" "URLInfoAbout" "${APP_WEBSITE}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AutoDJ" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AutoDJ" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AutoDJ" "QuietUninstallString" '"$INSTDIR\uninstall.exe" /S'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AutoDJ" "DisplayIcon" "$INSTDIR\app.ico"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AutoDJ" "HelpLink" "${APP_WEBSITE}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AutoDJ" "URLUpdateInfo" "${APP_WEBSITE}"
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AutoDJ" "NoModify" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AutoDJ" "NoRepair" 1
    ; Save install directory for uninstaller to read ($INSTDIR may differ in uninstaller context)
    WriteRegStr HKCU "Software\AutoDJ" "InstallDir" "$INSTDIR"

    ; App Paths for CLI access (per-user)
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\App Paths\AutoDJ.exe" "" "$INSTDIR\AutoDJ.exe"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\App Paths\AutoDJ.exe" "Path" "$INSTDIR"

    ; Register bundled media tools only when the optional component is present.
    IfFileExists "$INSTDIR\mpv\mpv.exe" media_tools_present media_tools_absent
media_tools_present:
    WriteRegStr HKCU "Software\AutoDJ" "mpv_path" "$INSTDIR\mpv\mpv.exe"
    WriteRegStr HKCU "Software\AutoDJ" "ytdlp_path" "$INSTDIR\mpv\yt-dlp.exe"
    Goto media_tools_registry_done
media_tools_absent:
    DeleteRegValue HKCU "Software\AutoDJ" "mpv_path"
    DeleteRegValue HKCU "Software\AutoDJ" "ytdlp_path"
media_tools_registry_done:
SectionEnd

; -----------------------------------------------------------------------------
; Uninstaller
; -----------------------------------------------------------------------------
Function un.onInit
    ReadRegStr $INSTDIR HKCU "Software\AutoDJ" "InstallDir"
    ${If} $INSTDIR == ""
        StrCpy $INSTDIR "$APPDATA\AutoDJ"
    ${EndIf}
FunctionEnd

Section Uninstall
    !insertmacro STOP_RUNNING_AUTODJ
    ; Remove shortcuts
    Delete "$SMPROGRAMS\AutoDJ\AutoDJ.lnk"
    Delete "$SMPROGRAMS\AutoDJ\Edit Config.lnk"
    Delete "$SMPROGRAMS\AutoDJ\Uninstall.lnk"
    RMDir /r "$SMPROGRAMS\AutoDJ"
    Delete "$DESKTOP\AutoDJ.lnk"
    Delete "$SMPROGRAMS\AutoDJ\Uninstall.lnk"

    ; Remove Startup shortcut if exists
    Delete "$APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\AutoDJ.lnk"

    ; Remove application registration without deleting unrelated app settings.
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AutoDJ"
    ; App Paths entries belong to whichever copy registered last: remove them (and the
    ; mpv media-player registration made by SEC_MPV) only when they point into THIS
    ; install folder, so another AutoDJ or mpv on the PC keeps working.
    ReadRegStr $0 HKCU "Software\Microsoft\Windows\CurrentVersion\App Paths\AutoDJ.exe" ""
    StrCmp $0 "$INSTDIR\AutoDJ.exe" 0 +2
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\App Paths\AutoDJ.exe"
    ReadRegStr $0 HKCU "Software\Microsoft\Windows\CurrentVersion\App Paths\mpv.exe" ""
    StrCmp $0 "$INSTDIR\mpv\mpv.exe" 0 mpv_unregister_done
    IfFileExists "$INSTDIR\mpv\mpv.exe" 0 mpv_unregister_done
    nsExec::ExecToLog '"$INSTDIR\mpv\mpv.exe" --unregister'
    Pop $0
mpv_unregister_done:
    DeleteRegValue HKCU "Software\AutoDJ" "InstallDir"
    DeleteRegValue HKCU "Software\AutoDJ" "mpv_path"
    DeleteRegValue HKCU "Software\AutoDJ" "ytdlp_path"
    DeleteRegKey /ifempty HKCU "Software\AutoDJ"

    ; Remove application-owned files and directories only.
    ; Keep config.toml, playlist.json, logs, playlists, and other user-created data.
    ; Do NOT remove $INSTDIR itself: user data may still reside here.
    Delete "$INSTDIR\AutoDJ.exe"
    Delete "$INSTDIR\app.ico"
    Delete "$INSTDIR\README.md"
    Delete "$INSTDIR\CHANGELOG.md"
    Delete "$INSTDIR\LICENSE"
    Delete "$INSTDIR\run_autodj.py"
    ; Launchers and the client readme installed by SEC_MAIN (were left behind).
    Delete "$INSTDIR\start.bat"
    Delete "$INSTDIR\check.bat"
    Delete "$INSTDIR\readme.txt"
    Delete "$INSTDIR\install.ps1"
    Delete "$INSTDIR\install.bat"
    Delete "$INSTDIR\uninstall.exe"
    Delete "$INSTDIR\ads-list.json"
    RMDir /r "$INSTDIR\mpv"
    RMDir /r "$INSTDIR\playlist"
    RMDir /r "$INSTDIR\docs"
    RMDir /r "$INSTDIR\tools"
SectionEnd

; -----------------------------------------------------------------------------
; Modern UI Pages
; -----------------------------------------------------------------------------
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; -----------------------------------------------------------------------------
; Languages
; -----------------------------------------------------------------------------
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Thai"

; NOTE: To enable Thai language in the installer, copy thai.nlf to:
;   C:\Program Files (x86)\NSIS\Contrib\Language\thai.nlf
; on the Windows machine where you run makensis.
; Without thai.nlf, the installer falls back to English only.

; -----------------------------------------------------------------------------
; Source Files (adjust paths as needed)
; -----------------------------------------------------------------------------
; The actual files will be copied from the build output directory
; Usage: makensis /DAPP_VERSION=0.2.6 installer.nsi

