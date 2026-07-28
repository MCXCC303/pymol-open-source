; ============================================================================
; PyMOL Open Source - NSIS Windows Installer
;
; Prerequisites:
;   - NSIS 3.x installed (https://nsis.sourceforge.io/)
;   - PyMOL portable bundle built at ${PYMOL_DIST_DIR}
;
; Build:
;   makensis /DPYMOL_VERSION=3.2.0 /DPYMOL_DIST_DIR=dist\PyMOL installer.nsi
;
; ============================================================================

; --- Includes ---------------------------------------------------------------

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

; --- Defines ----------------------------------------------------------------

!ifndef PYMOL_VERSION
    !define PYMOL_VERSION "3.2.0"
!endif

!ifndef PYMOL_DIST_DIR
    !define PYMOL_DIST_DIR "dist\PyMOL"
!endif

!define PRODUCT_NAME "PyMOL"
!define PRODUCT_PUBLISHER "Schrodinger, Inc."
!define PRODUCT_WEB_SITE "https://pymol.org"
!define PRODUCT_DIR_REGKEY "Software\${PRODUCT_NAME}"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"

; --- General configuration --------------------------------------------------

Name "${PRODUCT_NAME} ${PYMOL_VERSION}"
OutFile "PyMOL-${PYMOL_VERSION}-Windows-x86_64-Setup.exe"
InstallDir "$PROGRAMFILES64\${PRODUCT_NAME}"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" "InstallDir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
ShowInstDetails show
ShowUnInstDetails show

; --- MUI configuration ------------------------------------------------------

!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; Welcome page
!define MUI_WELCOMEPAGE_TITLE "PyMOL ${PYMOL_VERSION} Setup"
!define MUI_WELCOMEPAGE_TEXT "This wizard will install PyMOL ${PYMOL_VERSION}, a molecular visualization system.\r\n\r\nPyMOL is open-source software. See LICENSE for details."

; License page
!define MUI_LICENSEPAGE_CHECKBOX
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\packaging\NOTICE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Language
!insertmacro MUI_LANGUAGE "English"

; --- Installer sections -----------------------------------------------------

Section "PyMOL" SecMain
    SetShellVarContext all
    SetOutPath "$INSTDIR"

    ; Copy all files from the PyMOL bundle directory
    File /r "${PYMOL_DIST_DIR}\*"

    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\PyMOL.lnk" \
        "$INSTDIR\PyMOL.exe" "" "$INSTDIR\PyMOL.exe" 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall PyMOL.lnk" \
        "$INSTDIR\Uninstall.exe" "" "$INSTDIR\Uninstall.exe" 0
    CreateShortCut "$DESKTOP\PyMOL.lnk" \
        "$INSTDIR\PyMOL.exe" "" "$INSTDIR\PyMOL.exe" 0

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Registry entries
    WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "InstallDir" "$INSTDIR"
    WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "Version" "${PYMOL_VERSION}"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PYMOL_VERSION}"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\PyMOL.exe"
    WriteRegDWORD HKLM "${PRODUCT_UNINST_KEY}" "NoModify" 1
    WriteRegDWORD HKLM "${PRODUCT_UNINST_KEY}" "NoRepair" 1

    ; Estimate size
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "${PRODUCT_UNINST_KEY}" "EstimatedSize" "$0"

    ; Add to PATH (optional)
    ; Uncomment to add to system PATH:
    ; EnVar::SetHKCU
    ; EnVar::AddValue "PATH" "$INSTDIR"

SectionEnd

; --- Uninstaller section ----------------------------------------------------

Section "Uninstall"
    SetShellVarContext all

    ; Remove shortcuts
    Delete "$SMPROGRAMS\${PRODUCT_NAME}\PyMOL.lnk"
    Delete "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall PyMOL.lnk"
    RMDir "$SMPROGRAMS\${PRODUCT_NAME}"
    Delete "$DESKTOP\PyMOL.lnk"

    ; Remove installed files
    RMDir /r "$INSTDIR"

    ; Remove registry entries
    DeleteRegKey HKLM "${PRODUCT_UNINST_KEY}"
    DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"

SectionEnd
