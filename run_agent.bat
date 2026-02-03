@echo off

set PYTHONUTF8=1

chcp 65001 > nul

REM ===== CHECK REQUIRED ENVIRONMENT VARIABLES =====
if "%MOLTBOOK_PROJECT_PATH%"=="" (
    echo ERROR: MOLTBOOK_PROJECT_PATH environment variable is not set!
    echo Please set it in Windows System Environment Variables.
    echo Example: MOLTBOOK_PROJECT_PATH=C:\Users\YourName\Documents\MoltbookLocalAgent
    pause
    exit /b 1
)

REM ===== EXECUTION =====
cd /d "%MOLTBOOK_PROJECT_PATH%"

"%MOLTBOOK_PROJECT_PATH%\env\Scripts\python.exe" "%MOLTBOOK_PROJECT_PATH%\main.py" %* >> "%MOLTBOOK_PROJECT_PATH%\agent.log" 2>&1

REM ===== LOGGING =====
echo [%date% %time%] Moltbook agent executed with args: %* >> "%MOLTBOOK_PROJECT_PATH%\scheduler.log"

if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] ERROR: Exit code %ERRORLEVEL% >> "%MOLTBOOK_PROJECT_PATH%\scheduler.log"
)