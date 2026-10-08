@echo off
setlocal EnableExtensions EnableDelayedExpansion

title PitchPassKey

cd /d "%~dp0"

echo.
echo ========================================
echo           PitchPassKey Launcher
echo ========================================
echo.

REM ------------------------------------------------------------
REM 1. Find a suitable Python installation.
REM ------------------------------------------------------------
set "PYTHON_CMD="

where py >nul 2>&1
if not errorlevel 1 (
    py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
    where python >nul 2>&1
    if not errorlevel 1 (
        python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=python"
    )
)

if not defined PYTHON_CMD (
    echo [ERROR] Python 3.10 or newer was not found.
    echo.
    echo Install Python 3.10+ and run this file again.
    echo.
    pause
    exit /b 1
)

echo [OK] Compatible Python found.

REM ------------------------------------------------------------
REM 2. Create the virtual environment when it does not exist.
REM ------------------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating virtual environment .venv...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo.
        echo [ERROR] Unable to create the virtual environment.
        echo.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment already exists.
)

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"
set "READY_FILE=%CD%\.venv\.pitchpasskey-ready"

REM ------------------------------------------------------------
REM 3. Install only when the environment is not ready.
REM    Use "run.bat --repair" to force a dependency refresh.
REM ------------------------------------------------------------
set "NEEDS_INSTALL=0"

if /I "%~1"=="--repair" set "NEEDS_INSTALL=1"
if not exist "%READY_FILE%" set "NEEDS_INSTALL=1"

if "%NEEDS_INSTALL%"=="0" (
    "%VENV_PYTHON%" -c "import pitchpasskey.app, mido, keyring, rtmidi" >nul 2>&1
    if errorlevel 1 set "NEEDS_INSTALL=1"
)

if "%NEEDS_INSTALL%"=="1" (
    echo.
    echo [INFO] Instalando o reparando dependencias del proyecto...
    "%VENV_PYTHON%" -m pip install -e .
    if errorlevel 1 (
        echo.
        echo [ERROR] Unable to install PitchPassKey dependencies.
        echo.
        pause
        exit /b 1
    )
    >"%READY_FILE%" echo ready
    echo [OK] Dependencies installed.
) else (
    echo [OK] Dependencies already installed.
)

REM ------------------------------------------------------------
REM 4. Verify critical runtime imports before starting.
REM ------------------------------------------------------------
echo.
echo [INFO] Verifying core components...
"%VENV_PYTHON%" -c "import pitchpasskey.app, mido, keyring, rtmidi"
if errorlevel 1 (
    echo.
    echo [ERROR] The installation is incomplete.
    echo [INFO] Run "run.bat --repair" to repair it.
    echo.
    pause
    exit /b 1
)

echo [OK] Dependencies verified.

REM ------------------------------------------------------------
REM 5. Start PitchPassKey with the virtual environment Python.
REM ------------------------------------------------------------
echo.
echo [INFO] Starting PitchPassKey...
echo.

"%VENV_PYTHON%" -m pitchpasskey
set "APP_EXIT_CODE=%errorlevel%"

echo.
if not "%APP_EXIT_CODE%"=="0" (
    echo [ERROR] PitchPassKey exited with code %APP_EXIT_CODE%.
    echo.
    pause
    exit /b %APP_EXIT_CODE%
)

echo [OK] PitchPassKey finished successfully.
endlocal
exit /b 0
