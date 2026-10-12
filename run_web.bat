@echo off
REM ============================================================
REM  Upbit Pocket Manager - Web UI launcher
REM  Creates .venv on first run, installs deps, opens the
REM  dashboard in your browser at http://127.0.0.1:5000
REM
REM  NOTE: This file is intentionally ASCII-only so that cmd.exe
REM        parses it identically on any code page.
REM        Korean messages are printed by the Python app instead.
REM ============================================================
setlocal

cd /d "%~dp0"
set "VENV_DIR=%CD%\.venv"
set "PYTHON=%VENV_DIR%\Scripts\python.exe"

title Upbit Pocket Manager

echo.
echo  ==========================================
echo   Upbit Pocket Manager - Web UI
echo  ==========================================
echo.

if exist "%PYTHON%" goto :deps

echo  [1/3] Creating virtual environment (.venv) ...
where py >nul 2>&1
if errorlevel 1 (
    python -m venv "%VENV_DIR%"
) else (
    py -3 -m venv "%VENV_DIR%"
)
if errorlevel 1 goto :fail
echo        done.
goto :deps

:deps
echo  [2/3] Checking dependencies ...
"%PYTHON%" -c "import flask, requests, jwt" >nul 2>&1
if errorlevel 1 (
    echo        installing... (only needed once)
    "%PYTHON%" -m pip install --upgrade pip --quiet
    "%PYTHON%" -m pip install -r requirements.txt --quiet
    if errorlevel 1 goto :fail
) else (
    echo        already installed.
)

echo  [3/3] Starting web server ...
echo.
echo  ------------------------------------------------
echo   URL   : http://127.0.0.1:5000
echo   STOP  : close this window or press Ctrl+C
echo  ------------------------------------------------
echo.
echo.

"%PYTHON%" web.py
echo.
echo  Server stopped.
pause
exit /b 0

:fail
echo.
echo  [ERROR] Setup failed. Check that Python 3.9+ is installed.
echo          Then try running setup.bat again.
echo.
pause
exit /b 1
