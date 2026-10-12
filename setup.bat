@echo off
REM ============================================================
REM  One-time setup: create .venv, install deps, create .env
REM  Safe to re-run. Delete this file afterwards if you like.
REM ============================================================
setlocal

cd /d "%~dp0"
set "VENV_DIR=%CD%\.venv"
set "PYTHON=%VENV_DIR%\Scripts\python.exe"

title Upbit Pocket Manager - Setup

echo.
echo  ==============================================
echo   Upbit Pocket Manager - First-time setup
echo  ==============================================
echo.

if exist "%PYTHON%" (
    echo  [1/4] Updating existing .venv ...
) else (
    echo  [1/4] Creating virtual environment (.venv) ...
    where py >nul 2>&1
    if errorlevel 1 (
        python -m venv "%VENV_DIR%"
    ) else (
        py -3 -m venv "%VENV_DIR%"
    )
    if errorlevel 1 goto :fail
)

echo  [2/4] Updating pip ...
"%PYTHON%" -m pip install --upgrade pip --quiet

echo  [3/4] Installing dependencies ...
"%PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo  [4/4] Preparing .env ...
if exist ".env" (
    echo        .env already exists, leaving it untouched.
) else (
    copy ".env.example" ".env" >nul
    echo        created .env
)

echo.
echo  ==============================================
echo   Setup finished.
echo.
echo     Web UI      :  run_web.bat
echo     Terminal    :  run_cli.bat
echo.
echo   If .env is still empty, open it and paste your
echo   Upbit API keys (see below for details).
echo  ==============================================
echo.

if not exist ".env" goto :done

findstr /b /c:"UPBIT_OPEN_API_ACCESS_KEY=" ".env" | findstr /v "UPBIT_OPEN_API_ACCESS_KEY=" >nul
if errorlevel 1 goto :edit

findstr /b /c:"UPBIT_OPEN_API_SECRET_KEY=" ".env" | findstr /v "UPBIT_OPEN_API_SECRET_KEY=" >nul
if errorlevel 1 goto :edit

echo   API keys already filled in.
goto :done

:edit
echo.
echo   ------------------------------------------------------
echo    Open .env and paste your API keys:
echo.
echo      UPBIT_OPEN_API_ACCESS_KEY=...
echo      UPBIT_OPEN_API_SECRET_KEY=...
echo.
echo    Issue keys : https://upbit.com/mypage/open_api_management
echo    Required   : main pocket + [Pocket Management] permission
echo                  + register this PC's IP in the allow list
echo   ------------------------------------------------------
echo.
start notepad ".env"

:done
echo.
pause
exit /b 0

:fail
echo.
echo  [ERROR] Setup failed.
echo          Check your internet connection and that Python 3.9+ is installed.
echo.
pause
exit /b 1
