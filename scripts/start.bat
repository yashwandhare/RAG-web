@echo off
setlocal

:: Navigate to repo root
cd /d "%~dp0\.."

:: 1. Activate Venv
if exist "backend\.venv\Scripts\activate.bat" (
    call backend\.venv\Scripts\activate.bat
) else (
    echo [ERROR] Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)

:: 2. Set Environment Variables
set TOKENIZERS_PARALLELISM=false
set PYTHONWARNINGS=ignore::UserWarning

:: 3. Start Server
echo Starting Backend at http://127.0.0.1:8000...
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level info