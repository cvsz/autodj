; Camfrog AutoDJ - NSIS Installer Script
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
; - Auto-uninstall of previous version before install
; - mpv + yt-dlp + VBCable driver

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "x64.nsh"

; -----------------------------------------------------------------------------
; Metadata
; -----------------------------------------------------------------------------
!define APP_NAME "Camfrog AutoDJ"
!define APP_VERSION "0.2.5"
!define APP_PUBLISHER "ZEAZDEV COMPANY LIMITED"
!define APP_WEBSITE "https://github.com/cvsz/autodj"
!define APP_EXE "AutoDJ.exe"
!define INSTALLER_NAME "Camfrog-AutoDJ-Setup-${APP_VERSION}.exe"

; -----------------------------------------------------------------------------
; General Settings
; -----------------------------------------------------------------------------
Name "${APP_NAME} ${APP_VERSION}"
OutFile "${INSTALLER_NAME}"
InstallDir "$PROGRAMFILES64\Camfrog AutoDJ"
InstallDirRegKey HKLM "Software\CamfrogAutoDJ" "InstallDir"
ShowInstDetails show
ShowUninstDetails show
RequestExecutionLevel admin
XPStyle on
CRCCheck on

; -----------------------------------------------------------------------------
; Modern UI 2
; -----------------------------------------------------------------------------
!define MUI_ICON "app.ico"
!define MUI_UNICON "app.ico"
!define MUI_WELCOMEPAGE_TITLE "Welcome to the ${APP_NAME} Setup Wizard"
!define MUI_WELCOMEPAGE_TEXT "This wizard will guide you through the installation of ${APP_NAME} ${APP_VERSION}.\n\nClick Next to continue."
!define MUI_FINISHPAGE_TITLE "Installation Complete"
!define MUI_FINISHPAGE_TEXT "Setup has finished installing ${APP_NAME} ${APP_VERSION} on your computer.\n\nClick Finish to close this wizard."
!define MUI_FINISHPAGE_RUN "AutoDJ.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APP_NAME} now"
!define MUI_FINISHPAGE_SHOWREADME "README.md"
!define MUI_FINISHPAGE_RUN_NOTCHECKED

!define MUI_LICENSEPAGE_TEXT_TOP "Please review the license agreement before installing ${APP_NAME}."
!define MUI_LICENSEPAGE_TEXT_BOTTOM "If you accept the terms, click I Agree to continue. You must accept the agreement to install ${APP_NAME}."

!define MUI_COMPONENTSPAGE_TEXT_TOP "Select the components you want to install. Required components are always installed."
!define MUI_COMPONENTSPAGE_TEXT_COMPLIST "Available components:"
!define MUI_COMPONENTSPAGE_TEXT_DESCRIPTION_TITLE "Description"
!define MUI_COMPONENTSPAGE_TEXT_DESCRIPTION_INFO "Hover over a component to see its description."

!define MUI_DIRECTORYPAGE_TEXT_TOP "Choose the installation folder for ${APP_NAME}."
!define MUI_DIRECTORYPAGE_TEXT_DESTINATION "Destination Folder"

!define MUI_INSTFILESPAGE_FINISHHEADER_TEXT "Installation Complete"
!define MUI_INSTFILESPAGE_FINISHTEXT "Click Finish to close the wizard."

; License
LicenseData "LICENSE"

; -----------------------------------------------------------------------------
; Components
; -----------------------------------------------------------------------------
Section "!MainProgram" SEC_MAIN
    SectionIn RO
    SetOutPath "$INSTDIR"
    File "dist\AutoDJ.exe"
    File "app.ico"
    File "README.md"
    File "CHANGELOG.md"
    File "LICENSE"
    File "config.example.toml"
    File /nonfatal "config.toml"
    File "run_autodj.py"
    ; config.toml is created by install.ps1 on first run (interactive prompts)
    ; do NOT bundle a machine-specific config.toml here
SectionEnd

Section /o "mpv + yt-dlp" SEC_MPV
    SetOutPath "$INSTDIR\mpv"
    File /nonfatal "mpv\mpv.exe"
    File /nonfatal "mpv\mpv.com"
    File /nonfatal "mpv\yt-dlp.exe"
    File /nonfatal "mpv\mpv-register.bat"
    File /nonfatal "mpv\mpv-unregister.bat"
    SetOutPath "$INSTDIR\mpv\_internal"
    File /nonfatal /r "mpv\_internal\*.*"
SectionEnd

Section /o "VBCable Virtual Audio Driver" SEC_VBCABLE
    SetOutPath "$INSTDIR\mpv\VBCABLE_Driver_Pack45"
    File /nonfatal "mpv\VBCABLE_Driver_Pack45\VBCABLE_Setup_x64.exe"
    File /nonfatal "mpv\VBCABLE_Driver_Pack45\VBCABLE_ControlPanel.exe"
    File /nonfatal "mpv\VBCABLE_Driver_Pack45\readme.txt"
    File /nonfatal /r "mpv\VBCABLE_Driver_Pack45\*.inf"
    File /nonfatal /r "mpv\VBCABLE_Driver_Pack45\*.cat"
    File /nonfatal /r "mpv\VBCABLE_Driver_Pack45\*.sys"
SectionEnd

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

Section "Tests (Development)" SEC_TESTS
    SetOutPath "$INSTDIR\tests"
    File /r "tests\*.py"
SectionEnd

Section "Install Scripts" SEC_SCRIPTS
    SetOutPath "$INSTDIR"
    File "install.ps1"
    File "install.bat"
SectionEnd

; -----------------------------------------------------------------------------
; Installer Logic
; -----------------------------------------------------------------------------
; Check for existing installation and uninstall it first before installing new version
Function CheckExistingInstall
    Push $R0
    ReadRegStr $R0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CamfrogAutoDJ" "UninstallString"
    ${If} $R0 != ""
        DetailPrint "Existing installation found. Removing old version..."
        ExecWait "$R0 /S"
        DetailPrint "Old version removed."
    ${EndIf}
    Pop $R0
FunctionEnd

Function .onInit
    ; Check for existing installation and uninstall it first
    Call CheckExistingInstall

    ; Verify we're on Windows 64-bit
    ${If} ${RunningX64}
        StrCpy $INSTDIR "$PROGRAMFILES64\Camfrog AutoDJ"
    ${Else}
        MessageBox MB_ICONSTOP "This installer requires a 64-bit version of Windows."
        Abort
    ${EndIf}
FunctionEnd

Function .onInstSuccess
    HideWindow
    MessageBox MB_ICONINFORMATION|MB_OK "Camfrog AutoDJ has been successfully installed!$\n$\nYou can now run it from the Start Menu or Desktop shortcut."
FunctionEnd

; -----------------------------------------------------------------------------
; Shortcuts & Registry
; -----------------------------------------------------------------------------
Section -Post
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\Camfrog AutoDJ"
    CreateShortcut "$SMPROGRAMS\Camfrog AutoDJ\Camfrog AutoDJ.lnk" "$INSTDIR\AutoDJ.exe" "--gui" "$INSTDIR\app.ico" 0 SW_SHOWNORMAL "" "Music bot for Camfrog rooms"
    CreateShortcut "$SMPROGRAMS\Camfrog AutoDJ\Uninstall.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\app.ico" 0 SW_SHOWNORMAL "" "Uninstall Camfrog AutoDJ"
    CreateShortcut "$SMPROGRAMS\Camfrog AutoDJ\Edit Config.lnk" "notepad.exe" "$INSTDIR\config.toml" "" 0 SW_SHOWNORMAL "" "Edit configuration"

    ; Desktop shortcut
    CreateShortcut "$DESKTOP\Camfrog AutoDJ.lnk" "$INSTDIR\AutoDJ.exe" "--gui" "$INSTDIR\app.ico" 0 SW_SHOWNORMAL "" "Music bot for Camfrog rooms"

    ; Registry entries for Add/Remove Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CamfrogAutoDJ" "DisplayName" "Camfrog AutoDJ"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CamfrogAutoDJ" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CamfrogAutoDJ" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CamfrogAutoDJ" "URLInfoAbout" "${APP_WEBSITE}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CamfrogAutoDJ" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CamfrogAutoDJ" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CamfrogAutoDJ" "DisplayIcon" "$INSTDIR\app.ico"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CamfrogAutoDJ" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CamfrogAutoDJ" "NoRepair" 1
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CamfrogAutoDJ" "HelpLink" "${APP_WEBSITE}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CamfrogAutoDJ" "URLUpdateInfo" "${APP_WEBSITE}"
    Call GetDate
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CamfrogAutoDJ" "InstallDate" $0

    ; App Paths for CLI access
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\AutoDJ.exe" "" "$INSTDIR\AutoDJ.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\AutoDJ.exe" "Path" "$INSTDIR"

    ; mpv path for AutoDJ to find mpv.exe
    WriteRegStr HKLM "Software\CamfrogAutoDJ" "mpv_path" "$INSTDIR\mpv\mpv.exe"
    WriteRegStr HKLM "Software\CamfrogAutoDJ" "ytdlp_path" "$INSTDIR\mpv\yt-dlp.exe"
SectionEnd

; -----------------------------------------------------------------------------
; Uninstaller
; -----------------------------------------------------------------------------
Section Uninstall
    ; Remove shortcuts
    Delete "$SMPROGRAMS\Camfrog AutoDJ\Camfrog AutoDJ.lnk"
    Delete "$SMPROGRAMS\Camfrog AutoDJ\Edit Config.lnk"
    Delete "$SMPROGRAMS\Camfrog AutoDJ\Uninstall.lnk"
    RMDir /r "$SMPROGRAMS\Camfrog AutoDJ"
    Delete "$DESKTOP\Camfrog AutoDJ.lnk"
    Delete "$SMPROGRAMS\Camfrog AutoDJ\Uninstall.lnk"

    ; Remove Startup shortcut if exists
    Delete "$APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Camfrog AutoDJ.lnk"

    ; Remove registry entries
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CamfrogAutoDJ"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\AutoDJ.exe"
    DeleteRegKey HKLM "Software\CamfrogAutoDJ"

    ; Remove files
    RMDir /r "$INSTDIR"
SectionEnd

; -----------------------------------------------------------------------------
; Custom Functions
; -----------------------------------------------------------------------------
Function GetDate
    Push $1
    Push $2
    Push $3
    System::Call 'kernel32::GetLocalTime(i.r0)'
    IntOp $0 $0 + 1900  ; year
    IntOp $1 $1 + 1     ; month (0-based)
    IntOp $2 $2 + 0     ; day
    StrCpy $1 "0$1"
    StrCpy $2 "0$2"
    StrCpy $3 $0
    StrCpy $0 "$3$1$2"
    Pop $3
    Pop $2
    Pop $1
FunctionEnd

; -----------------------------------------------------------------------------
; Modern UI Pages
; -----------------------------------------------------------------------------
!insertmacro MUI_PAGE_WELCOME
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
; Usage: makensis /DVERSION=0.2.3 /DSRCDIR=..\dist installer.nsi
