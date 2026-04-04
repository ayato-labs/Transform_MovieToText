@echo off
setlocal
cd /d "%~dp0.."

:: 0. Initialize Logger (Prioritize this above all)
:: We use a separate launcher.log to avoid file locking with the app
echo [%date% %time%] --- LAUNCHER START --- > launcher.log

echo ==========================================
echo   Movie to Text (Whisper) Startup
echo ==========================================
echo.

:: 1. Check for uv package manager
where uv >nul 2>&1
if %errorlevel% equ 0 (
    set "UV_CMD=uv"
    goto :check_venv
)

if exist "%~dp0uv.exe" (
    set "UV_CMD=%~dp0uv.exe"
    goto :check_venv
)

:: uv not found, download it
echo [INFO] uv is not installed. Downloading standalone uv...
echo [%date% %time%] Downloading uv.exe >> launcher.log
curl -L -o uv.exe https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.exe >> launcher.log 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Failed to download uv. Check internet connection.
    echo [%date% %time%] curl FAILED with code %errorlevel% >> launcher.log
    pause
    exit /b 1
)
set "UV_CMD=%~dp0uv.exe"

:check_venv
:: 2. Check for virtual environment
if exist ".venv" goto :launch_app

echo [INFO] First run or missing environment detected.
echo [INFO] Setting up isolated Python environment...
echo [INFO] Downloading Python and PyTorch (over 2GB). Please wait...
echo [%date% %time%] Setting up environment... >> launcher.log

"%UV_CMD%" python install 3.11 >> launcher.log 2>&1
"%UV_CMD%" venv --seed >> launcher.log 2>&1
"%UV_CMD%" pip install -e . >> launcher.log 2>&1

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Environment setup failed. See launcher.log for details.
    echo [%date% %time%] Setup FAILED with code %errorlevel% >> launcher.log
    pause
    exit /b 1
)
echo [INFO] Setup complete!
echo [%date% %time%] Setup SUCCESS >> launcher.log

:launch_app
echo [INFO] Launching application...
echo [%date% %time%] Launching python main.py... >> launcher.log


:: RUN APP (The app will handle app.log on its own)
"%UV_CMD%" run python main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited with error code %errorlevel%.
    echo [%date% %time%] App EXITED with code %errorlevel% >> launcher.log
    echo [TIP] If the window closed immediately, check app.log.
    pause
)

echo [%date% %time%] --- LAUNCHER FINISHED --- >> launcher.log
endlocal
