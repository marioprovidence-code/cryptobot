"""
Build standalone .exe using PyInstaller
Run: python build_exe.py
"""
import os
import shutil
import subprocess
import sys

ICON_SOURCE = 'Crypto BOT icon.png'
CONVERTED_ICON_PATH = os.path.join('dist', 'master_trader_icon.ico')


def prepare_icon(source_path: str, output_path: str) -> str | None:
    """Convert PNG icon to ICO for PyInstaller. Returns path or None on failure."""
    if not os.path.exists(source_path):
        print(f"[WARN] Icon not found: {source_path}")
        return None

    try:
        from PIL import Image  # Lazy import so Pillow is optional during development
    except ImportError:
        print("[WARN] Pillow not installed. Install with 'pip install pillow' to bundle the icon.")
        return None

    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with Image.open(source_path) as image:
            image = image.convert("RGBA")
            sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
            image.save(output_path, format="ICO", sizes=sizes)
        print(f"[OK] Converted icon to ICO: {output_path}")
        return output_path
    except Exception as exc:
        print(f"[WARN] Could not convert icon to ICO: {exc}")
        return None


def build_exe():
    """Build standalone executable"""
    print("[*] Building Master Trader EXE...")
    
    # Create dist folder if needed
    os.makedirs('dist', exist_ok=True)
    
    # Prepare icon for PyInstaller
    icon_flag = []
    data_flags = []
    if os.path.exists(ICON_SOURCE):
        print(f"[OK] Found icon: {ICON_SOURCE}")
        converted_icon = prepare_icon(ICON_SOURCE, CONVERTED_ICON_PATH)
        if converted_icon:
            icon_flag = [f'--icon={converted_icon}']
        else:
            print("[WARN] Continuing without custom icon.")
        data_flags = [f"--add-data={os.path.abspath(ICON_SOURCE)}{os.pathsep}."]
    else:
        print(f"[WARN] Icon not found: {ICON_SOURCE}. EXE will use the default icon.")
    
    # PyInstaller command
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',  # Single executable file
        '--windowed',  # No console window
        '--name=MasterTrader',  # Executable name
        '--hidden-import=sklearn',
        '--hidden-import=xgboost',
        '--hidden-import=matplotlib',
        '--hidden-import=binance',
        '--hidden-import=pandas',
        '--hidden-import=numpy',
        '--hidden-import=requests',
        '--hidden-import=optuna',
        '--hidden-import=tkinter',
        '--clean',
        '--distpath=dist',
    ] + icon_flag + data_flags + ['master_gui.py']
    
    try:
        result = subprocess.run(cmd, check=True)
        print("[OK] EXE built successfully!")
        print("[*] Location: dist/MasterTrader.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Build failed: {e}")
        return False


def create_installer_script():
    """Create NSIS installer script"""
    nsis_script = r'''
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
'''
    
    with open('installer.nsi', 'w') as f:
        f.write(nsis_script)
    
    print("[OK] Created installer.nsi")
    print("     To build installer, run: makensis.exe installer.nsi")
    print("     (Requires NSIS to be installed)")


def create_desktop_shortcut():
    """Create desktop shortcut for Master Trader"""
    try:
        import winreg
        from pathlib import Path
        
        # Get desktop path
        desktop = Path.home() / "Desktop"
        shortcut_name = "Master Trader.lnk"
        
        # This is a simple approach - for full VBS shortcut creation:
        vbs_code = f'''
Dim objShell, strShortcutPath, strTargetPath, objShortcut
Set objShell = WScript.CreateObject("WScript.Shell")
strShortcutPath = "{desktop}\\{shortcut_name}"
strTargetPath = "{os.path.abspath('dist/MasterTrader.exe')}"

Set objShortcut = objShell.CreateShortcut(strShortcutPath)
objShortcut.TargetPath = strTargetPath
objShortcut.WorkingDirectory = "{os.path.abspath('.')}"
objShortcut.IconLocation = "{os.path.abspath('Crypto BOT icon.png')}"
objShortcut.Save
'''
        
        vbs_file = 'create_shortcut.vbs'
        with open(vbs_file, 'w') as f:
            f.write(vbs_code)
        
        # Execute VBS script
        os.system(f'cscript.exe "{vbs_file}"')
        os.remove(vbs_file)
        
        print(f"[OK] Desktop shortcut created: {desktop}\\{shortcut_name}")
        return True
    except Exception as e:
        print(f"[WARNING] Could not create desktop shortcut: {e}")
        return False


def main():
    print("=" * 60)
    print("MASTER TRADER - EXE & INSTALLER BUILDER")
    print("=" * 60)
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("\n[ERROR] PyInstaller not found!")
        print("Install with: pip install pyinstaller")
        sys.exit(1)
    
    # Build EXE
    if build_exe():
        print("\n" + "=" * 60)
        print("[OK] BUILD COMPLETE!")
        print("=" * 60)
        print("\nDeliverables:")
        print("  1. Standalone EXE: dist/MasterTrader.exe")
        print("  2. Ready to distribute and run on any Windows machine")
        
        # Create desktop shortcut
        print("\n" + "-" * 60)
        print("Creating Desktop Shortcut...")
        create_desktop_shortcut()
        
        # Create installer script
        print("\n" + "-" * 60)
        print("Creating NSIS Installer...")
        create_installer_script()
        
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print("1. Test the EXE: dist/MasterTrader.exe")
        print("2. Desktop shortcut created on your Desktop")
        print("3. For installer (optional):")
        print("   - Install NSIS from: https://nsis.sourceforge.io")
        print("   - Run: makensis.exe installer.nsi")
        print("   - This creates: Master_Trader_Setup.exe")
        print("=" * 60)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()