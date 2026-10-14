@echo off
setlocal
set "PYTHONUTF8=1"
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo Run install.cmd first.
    exit /b 2
)
"%~dp0.venv\Scripts\python.exe" -m r0env %*
exit /b %errorlevel%
