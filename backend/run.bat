@echo off
REM Mykare Voice Agent - backend launcher (Windows)
REM Runs the LiveKit agent worker and the FastAPI server in parallel
REM by opening two new console windows.

cd /d "%~dp0"

REM ── 1. Virtualenv ──────────────────────────────────────────────────────
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

REM ── 2. Install deps if needed ──────────────────────────────────────────
if not exist ".venv\.installed" (
    echo Installing Python dependencies...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    echo done > .venv\.installed
)

REM ── 3. Verify .env exists ──────────────────────────────────────────────
if not exist ".env" (
    echo .env file is missing. Copy .env.example to .env and fill in your API keys first.
    pause
    exit /b 1
)

REM ── 4. One-time model download ─────────────────────────────────────────
if not exist ".venv\.models_downloaded" (
    echo Downloading VAD + turn-detector models (one-time)...
    python agent.py download-files
    echo done > .venv\.models_downloaded
)

REM ── 5. Launch BOTH processes in two new windows ────────────────────────
echo.
echo Starting LiveKit agent worker AND FastAPI HTTP server...
echo   - Agent worker will open in a new window
echo   - HTTP API will open in a new window at http://localhost:8000
echo.
echo Close those windows or press Ctrl+C in them to stop.
echo.

start "Mykare Agent Worker" cmd /k ".venv\Scripts\activate.bat && python agent.py dev"
start "Mykare HTTP API"     cmd /k ".venv\Scripts\activate.bat && uvicorn api:app --host 0.0.0.0 --port 8000 --reload"

echo Both processes launched. You can close this window.
timeout /t 5 > nul
