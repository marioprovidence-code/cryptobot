
; NSIS Installer Script for Master Trader
; Install using: "C:\Program Files\NSIS\makensis.exe" installer.nsi

; MUI Settings
!include "MUI2.nsh"
!include "x64.nsh"

; App Settings
Name "Master Trader"
OutFile "Master_Trader_Setup.exe"
InstallDir "$PROGRAMFILES\MasterTrader"
RequestExecutionLevel admin

; MUI Settings
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

; Installer Sections
Section "Install"
    SetOutPath "$INSTDIR"
    
    ; Copy executable
    File "dist\MasterTrader.exe"
    
    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\Master Trader"
    CreateShortCut "$SMPROGRAMS\Master Trader\Master Trader.lnk" "$INSTDIR\MasterTrader.exe"
    CreateShortCut "$SMPROGRAMS\Master Trader\Uninstall.lnk" "$INSTDIR\uninstall.exe"
    CreateShortCut "$DESKTOP\Master Trader.lnk" "$INSTDIR\MasterTrader.exe"
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MasterTrader" "DisplayName" "Master Trader"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MasterTrader" "UninstallString" "$INSTDIR\uninstall.exe"
SectionEnd

; Uninstaller Section
Section "Uninstall"
    Delete "$INSTDIR\MasterTrader.exe"
    Delete "$INSTDIR\uninstall.exe"
    RMDir "$INSTDIR"
    Delete "$DESKTOP\Master Trader.lnk"
    Delete "$SMPROGRAMS\Master Trader\Master Trader.lnk"
    Delete "$SMPROGRAMS\Master Trader\Uninstall.lnk"
    RMDir "$SMPROGRAMS\Master Trader"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MasterTrader"
SectionEnd
