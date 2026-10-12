@echo off
REM ============================================================
REM  Upbit Pocket Manager - Terminal CLI launcher
REM
REM  Usage (arguments are passed straight through):
REM    run_cli.bat                        show all pocket balances
REM    run_cli.bat pockets                list pockets
REM    run_cli.bat check                  test connection / permissions
REM    run_cli.bat move                   move one asset (dry run)
REM    run_cli.bat move-all --execute     move every asset (execute)
REM    run_cli.bat history --limit 50     transfer history
REM ============================================================
setlocal

cd /d "%~dp0"
set "VENV_DIR=%CD%\.venv"
set "PYTHON=%VENV_DIR%\Scripts\python.exe"

title Upbit Pocket Manager CLI

if not exist "%PYTHON%" (
    echo  Creating virtual environment (.venv) ...
    where py >nul 2>&1
    if errorlevel 1 (
        python -m venv "%VENV_DIR%"
    ) else (
        py -3 -m venv "%VENV_DIR%"
    )
    if errorlevel 1 goto :fail
)

"%PYTHON%" -c "import requests, jwt" >nul 2>&1
if errorlevel 1 (
    echo  Installing dependencies ... (only needed once)
    "%PYTHON%" -m pip install -r requirements.txt --quiet
    if errorlevel 1 goto :fail
)

"%PYTHON%" main.py %*
echo.
pause
exit /b 0

:fail
echo.
echo  [ERROR] Setup failed. Check that Python 3.9+ is installed.
echo          Then try running setup.bat again.
echo.
pause
exit /b 1
