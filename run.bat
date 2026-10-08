@echo off
setlocal EnableExtensions

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

echo [OK] Python compatible encontrado.

REM ------------------------------------------------------------
REM 2. Create the virtual environment when it does not exist.
REM ------------------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creando entorno virtual .venv...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo.
        echo [ERROR] No se pudo crear el entorno virtual.
        echo.
        pause
        exit /b 1
    )
    echo [OK] Entorno virtual creado.
) else (
    echo [OK] Entorno virtual existente.
)

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"

REM ------------------------------------------------------------
REM 3. Validate the venv interpreter.
REM ------------------------------------------------------------
"%VENV_PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] El entorno virtual no tiene un Python compatible.
    echo [INFO] Eliminando .venv para recrearlo...
    rmdir /s /q ".venv"
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo recrear .venv.
        pause
        exit /b 1
    )
)

REM ------------------------------------------------------------
REM 4. Upgrade pip and install everything declared by pyproject.toml.
REM ------------------------------------------------------------
echo [INFO] Actualizando pip...
"%VENV_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo actualizar pip.
    echo [INFO] Revisa tu conexion a Internet.
    echo.
    pause
    exit /b 1
)

echo.
echo [INFO] Verificando e instalando dependencias del proyecto...
"%VENV_PYTHON%" -m pip install -e .
if errorlevel 1 (
    echo.
    echo [ERROR] No se pudieron instalar las dependencias de PitchPassKey.
    echo.
    pause
    exit /b 1
)

REM ------------------------------------------------------------
REM 5. Verify critical runtime imports before starting.
REM ------------------------------------------------------------
echo.
echo [INFO] Verificando componentes principales...
"%VENV_PYTHON%" -c "from PySide6 import QtWidgets; import mido, keyring, rtmidi"
if errorlevel 1 (
    echo.
    echo [ERROR] Falta un componente requerido para ejecutar PitchPassKey.
    echo [INFO] Ejecuta nuevamente este archivo para intentar reparar la instalacion.
    echo.
    pause
    exit /b 1
)

echo [OK] Dependencias verificadas.

REM ------------------------------------------------------------
REM 6. Start PitchPassKey with the virtual environment Python.
REM ------------------------------------------------------------
echo.
echo [INFO] Iniciando PitchPassKey...
echo.

"%VENV_PYTHON%" -m pitchpasskey
set "APP_EXIT_CODE=%errorlevel%"

echo.
if not "%APP_EXIT_CODE%"=="0" (
    echo [ERROR] PitchPassKey termino con codigo %APP_EXIT_CODE%.
    echo.
    pause
    exit /b %APP_EXIT_CODE%
)

echo [OK] PitchPassKey finalizado correctamente.
endlocal
exit /b 0
