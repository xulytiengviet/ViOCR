@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv || goto :failed
)
".venv\Scripts\python.exe" -c "import docx, PIL, pypdfium2" >nul 2>&1
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :failed
)
".venv\Scripts\python.exe" desktop.py || goto :failed
exit /b 0
:failed
echo See README.md for Windows setup.
pause
exit /b 1
