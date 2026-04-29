@echo off
REM Mykare Voice Agent - frontend launcher (Windows)

cd /d "%~dp0"

REM ── 1. Install deps if needed ──────────────────────────────────────────
if not exist "node_modules" (
    echo Installing frontend dependencies (this takes about 1 minute)...
    call npm install
)

REM ── 2. Make sure .env exists ───────────────────────────────────────────
if not exist ".env" (
    echo Creating .env from template...
    copy .env.example .env
)

REM ── 3. Launch dev server ───────────────────────────────────────────────
echo.
echo Starting Vite dev server at http://localhost:5173
echo   (Make sure the backend is also running.)
echo.

call npm run dev
