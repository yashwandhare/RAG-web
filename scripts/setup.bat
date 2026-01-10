@echo off
setlocal
cd /d "%~dp0\.."

echo == RAGex Setup (Windows) ==

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: 2. Venv
if not exist "backend\.venv" (
    echo Creating venv...
    python -m venv backend\.venv
)
call backend\.venv\Scripts\activate.bat

:: 3. Dependencies
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r backend\requirements.txt

:: 4. Playwright
echo Installing Playwright...
playwright install chromium

:: 5. Extension Setup (Download marked.js)
echo Setting up Browser Extension...
if not exist "extension\marked.min.js" (
    echo Downloading marked.min.js...
    powershell -Command "Invoke-WebRequest -Uri 'https://cdn.jsdelivr.net/npm/marked/marked.min.js' -OutFile 'extension\marked.min.js'"
)

:: 6. Env
if not exist "backend\.env" (
    if exist "backend\.env.example" (
        copy backend\.env.example backend\.env >nul
        echo [WARN] Created backend\.env. PLEASE EDIT IT.
    )
)

:: 7. Data Dir
if not exist "backend\data\chroma_db" mkdir "backend\data\chroma_db"

echo.
echo [SUCCESS] Setup complete. Run 'scripts\start.bat'
pause