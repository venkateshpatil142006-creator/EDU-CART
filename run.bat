@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Install Python 3.10+ and enable PATH.
  pause
  exit /b 1
)

if not exist .venv py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -r backend\requirements.txt
if errorlevel 1 goto :error
if exist .env for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do if not "%%A"=="" set "%%A=%%B"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
pause
exit /b 0
:error
echo Dependency installation failed. Check your internet connection and Python installation.
pause
exit /b 1
