!include "MUI2.nsh"
!include "LogicLib.nsh"

Name "Test Silent"
OutFile "test_silent.exe"
RequestExecutionLevel user

!define MUI_PAGE_WELCOME
!define MUI_PAGE_INSTFILES
!define MUI_PAGE_FINISH

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

Section
    DetailPrint "Testing silent mode detection..."
    IfSilent silent_mode
    DetailPrint "Not silent"
    Goto end
silent_mode:
    DetailPrint "Silent mode detected"
end:
    DetailPrint "Done"
SectionEnd