@echo off
setlocal

cd /d "%~dp0"

set "PYTHONW_EXE="

if exist "%LocalAppData%\Programs\Python\Python311\pythonw.exe" (
    set "PYTHONW_EXE=%LocalAppData%\Programs\Python\Python311\pythonw.exe"
)

if not defined PYTHONW_EXE (
    for /f "delims=" %%I in ('where pythonw 2^>nul') do (
        if not defined PYTHONW_EXE set "PYTHONW_EXE=%%I"
    )
)

if not defined PYTHONW_EXE (
    set "PYTHONW_EXE=python"
)

start "" "%PYTHONW_EXE%" "%~dp0run_master.py"
exit /b 0
