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

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "x64.nsh"

; -----------------------------------------------------------------------------
; Metadata
; -----------------------------------------------------------------------------
!define APP_NAME "Camfrog AutoDJ"
!define APP_VERSION "0.2.3"
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

; 64-bit installer
InstallDir "$PROGRAMFILES64\Camfrog AutoDJ"

; -----------------------------------------------------------------------------
; Modern UI 2
; -----------------------------------------------------------------------------
!define MUI_ICON "src\app.ico"
!define MUI_UNICON "src\app.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "src\installer_banner.bmp"
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

; Language
!insertmacro MUI_LANGUAGE "English"

; License
LicenseData "LICENSE.md"

; -----------------------------------------------------------------------------
; Components
; -----------------------------------------------------------------------------
Section "!MainProgram" SEC_MAIN
    SectionIn RO
    SetOutPath "$INSTDIR"
    File "dist\AutoDJ.exe"
    File "src\app.ico"
    File "README.md"
    File "CHANGELOG.md"
    File "LICENSE.md"
    File "config.example.toml"
    File "src\run_autodj.py"
    ; Copy config.toml if exists (user may have customized)
    IfFileExists "config.toml" 0 +2
    File "config.toml"
SectionEnd

Section "Documentation" SEC_DOCS
    SetOutPath "$INSTDIR\docs"
    File /r "docs\*.md"
    File /r "docs\*.txt"
SectionEnd

Section "Python Scripts (Source)" SEC_SRC
    SetOutPath "$INSTDIR\src"
    File /r "camfrog_autodj\*.py"
    File /r "camfrog_autodj\adapters\*.py"
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
    File "uninstall.ps1"
SectionEnd

; -----------------------------------------------------------------------------
; Installer Logic
; -----------------------------------------------------------------------------
Function .onInit
    ; Verify we're on Windows
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

Function .onUninstSuccess
    HideWindow
    MessageBox MB_ICONINFORMATION|MB_OK "Camfrog AutoDJ has been successfully uninstalled."
FunctionEnd

; -----------------------------------------------------------------------------
; Shortcuts & Registry
; -----------------------------------------------------------------------------
Section -Post
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\Camfrog AutoDJ"
    CreateShortcut "$SMPROGRAMS\Camfrog AutoDJ\Camfrog AutoDJ.lnk" "$INSTDIR\AutoDJ.exe" "--gui" "$INSTDIR\app.ico" 0 "Music bot for Camfrog rooms"
    CreateShortcut "$SMPROGRAMS\Camfrog AutoDJ\Uninstall.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\app.ico" 0 "Uninstall Camfrog AutoDJ"
    CreateShortcut "$SMPROGRAMS\Camfrog AutoDJ\Edit Config.lnk" "notepad.exe" "$INSTDIR\config.toml" "" 0 "Edit configuration"
    CreateShortcut "$SMPROGRAMS\Camfrog AutoDJ\Uninstall.lnk" "$INSTDIR\uninstall.exe" "" "" 0 "Uninstall Camfrog AutoDJ"

    ; Desktop shortcut
    CreateShortcut "$DESKTOP\Camfrog AutoDJ.lnk" "$INSTDIR\AutoDJ.exe" "--gui" "$INSTDIR\app.ico" 0 "Music bot for Camfrog rooms"

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
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CamfrogAutoDJ" "InstallDate" "$(GetDate)"

    ; App Paths for CLI access
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\AutoDJ.exe" "" "$INSTDIR\AutoDJ.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\AutoDJ.exe" "Path" "$INSTDIR"
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
    Push $0
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
    Pop $0
FunctionEnd

; -----------------------------------------------------------------------------
; Modern UI Pages
; -----------------------------------------------------------------------------
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE
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

; -----------------------------------------------------------------------------
; Reserve Files (for installer itself)
; -----------------------------------------------------------------------------
ReserveFile "installer.bmp"  ; Optional: banner bitmap

; -----------------------------------------------------------------------------
; Source Files (adjust paths as needed)
; -----------------------------------------------------------------------------
; The actual files will be copied from the build output directory
; Usage: makensis /DVERSION=0.2.3 /DSRCDIR=..\dist installer.nsi