@echo off
setlocal
echo ==========================================
echo   Whisper Direct Capture Test (ASCII)
echo ==========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv folder NOT found.
    pause
    exit /b 1
)

echo [1/3] Running Python script...
echo [!] PLEASE PLAY AUDIO NOW (Recording for 5 seconds)
echo.

.venv\Scripts\python.exe tests/diagnostic/test_whisper_direct.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Script failed. Check messages above.
) else (
    echo.
    echo [2/3] Finished!
    echo [3/3] Please check:
    echo   - Output text ABOVE.
    echo   - Audio file: tests/direct_test.wav
    echo.
)

echo.
pause
