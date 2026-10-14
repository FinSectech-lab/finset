@echo off
setlocal
set "PYTHONUTF8=1"
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo Run install.cmd first.
    pause
    exit /b 2
)
"%~dp0.venv\Scripts\python.exe" -m r0env acceptance --output "%~dp0acceptance-results" %*
set "R0ENV_RESULT=%errorlevel%"
echo Reports are in acceptance-results. Exit 2 means unverified, NOT passed.
pause
exit /b %R0ENV_RESULT%
