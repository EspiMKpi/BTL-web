@echo off
REM ──────────────────────────────────────────────────────────────────────────
REM run.bat — start the VozFlix FastAPI backend locally (Windows)
REM Usage:  run.bat          (default port 8000)
REM         run.bat 9000     (custom port)
REM ──────────────────────────────────────────────────────────────────────────

SET PORT=%1
IF "%PORT%"=="" SET PORT=8000

REM Activate venv if present
IF EXIST ".venv\Scripts\activate.bat" (
    CALL .venv\Scripts\activate.bat
)

REM Load .env
IF EXIST ".env" (
    FOR /F "usebackq tokens=1,* delims==" %%A IN (".env") DO (
        REM Skip comments and empty lines
        IF NOT "%%A"=="" IF NOT "%%A"=="#" SET "%%A=%%B"
    )
)

echo Starting VozFlix API on http://localhost:%PORT%
uvicorn app.main:app --reload --port %PORT% --host 0.0.0.0
