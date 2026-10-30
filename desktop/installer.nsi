Unicode True
!include "MUI2.nsh"
; Alternate identifiers allow lifecycle checks beside an existing user install.
!ifndef APP_ID
  !define APP_ID "ResumeOptimizerDesktop"
!endif
!ifndef APP_LABEL
  !define APP_LABEL "Resume Optimizer Desktop"
!endif
!ifndef SETUP_OUT
  !define SETUP_OUT "..\dist\ResumeOptimizerDesktopSetup.exe"
!endif
!ifndef GUI_EXE
  !define GUI_EXE "ResumeOptimizerDesktop.exe"
!endif
!ifndef WORKER_EXE
  !define WORKER_EXE "ResumeOptimizerWorker.exe"
!endif
!ifndef APP_MUTEX
  !define APP_MUTEX "Local\ResumeOptimizerDesktop"
!endif
!ifndef DISPLAY_VERSION
  !define DISPLAY_VERSION "0.3.2"
!endif
!ifndef MODEL_FILENAME
  !define MODEL_FILENAME "Qwen3.5-2B-Q4_K_M.gguf"
!endif
!ifdef LARGE_MODEL
  ; NSISBI supports an all-in-one offline EXE beyond standard NSIS's 2 GiB.
  OutFileMode aio
!endif
Name "${APP_LABEL}"
OutFile "${SETUP_OUT}"
InstallDir "$LOCALAPPDATA\Programs\${APP_ID}"
InstallDirRegKey HKCU "Software\${APP_ID}" "InstallDir"
RequestExecutionLevel user
SetCompressor lzma
!ifndef BUNDLE_DIR
  !define BUNDLE_DIR "..\dist\ResumeOptimizerDesktop"
!endif
!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
Function .onInit
  System::Call 'kernel32::OpenMutexW(i 0x100000, i 0, w "${APP_MUTEX}") p.r0'
  ${If} $0 != 0
    System::Call 'kernel32::CloseHandle(p r0)'
    MessageBox MB_OK "Close ${APP_LABEL} before installing or upgrading."
    Abort
  ${EndIf}
FunctionEnd
Function un.onInit
  System::Call 'kernel32::OpenMutexW(i 0x100000, i 0, w "${APP_MUTEX}") p.r0'
  ${If} $0 != 0
    System::Call 'kernel32::CloseHandle(p r0)'
    MessageBox MB_OK "Close ${APP_LABEL} before uninstalling."
    Abort
  ${EndIf}
FunctionEnd
Section "Application"
  SetOutPath "$INSTDIR"
  File /r /x "*.gguf" "${BUNDLE_DIR}\*"
  ; GGUF weights compress poorly. Storing them directly avoids minutes of
  ; compression/decompression work on inexpensive CPUs.
  SetOutPath "$INSTDIR\_internal\desktop-assets\models"
  SetCompress off
  File "${BUNDLE_DIR}\_internal\desktop-assets\models\${MODEL_FILENAME}"
  SetCompress auto
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateShortcut "$DESKTOP\${APP_LABEL}.lnk" "$INSTDIR\${GUI_EXE}"
  CreateDirectory "$SMPROGRAMS\${APP_LABEL}"
  CreateShortcut "$SMPROGRAMS\${APP_LABEL}\${APP_LABEL}.lnk" "$INSTDIR\${GUI_EXE}"
  CreateShortcut "$SMPROGRAMS\${APP_LABEL}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\${APP_ID}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "DisplayName" "${APP_LABEL}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "DisplayVersion" "${DISPLAY_VERSION}"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "NoRepair" 1
SectionEnd
Section "Uninstall"
  Delete "$DESKTOP\${APP_LABEL}.lnk"
  Delete "$SMPROGRAMS\${APP_LABEL}\${APP_LABEL}.lnk"
  Delete "$SMPROGRAMS\${APP_LABEL}\Uninstall.lnk"
  RMDir "$SMPROGRAMS\${APP_LABEL}"
  Delete "$INSTDIR\${GUI_EXE}"
  Delete "$INSTDIR\${WORKER_EXE}"
  RMDir /r "$INSTDIR\_internal"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\${APP_ID}"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}"
  ; User drafts and exports live elsewhere and are always preserved.
SectionEnd
