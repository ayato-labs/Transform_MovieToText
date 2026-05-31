@echo off
setlocal
set "TITLE=Transform Movie to Text - Dev Launcher"
title %TITLE%

echo ==========================================
echo    %TITLE%
echo ==========================================

:: 1. Check for uv installation
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 'uv' is not installed or not in PATH.
    echo Please install uv from: https://github.com/astral-sh/uv
    pause
    exit /b 1
)

:: 2. Ensure environment is ready
echo [1/3] Syncing dependencies...
cmd /c uv sync
if %errorlevel% neq 0 (
    echo [ERROR] uv sync failed.
    pause
    exit /b 1
)

:: 3. Set development environment variables
:: We use APP_DEBUG=1 to see more logs in the console
set APP_DEBUG=1
:: Ensure OLLAMA_HOST is local
set OLLAMA_HOST=127.0.0.1:11434

:: 4. Start the application
echo [2/3] Initializing application...
echo [3/3] Launching Flet GUI...
echo ------------------------------------------
cmd /c uv run python main.py
echo ------------------------------------------

if %errorlevel% neq 0 (
    echo [ERROR] Application exited with code %errorlevel%
    pause
)

endlocal
