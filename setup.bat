@echo off
REM ============================================================
REM  Recepta - One-Click Setup Script for New PC
REM  Run as Administrator for best results
REM ============================================================

title Recepta Setup - New PC

echo.
echo ========================================
echo    Recepta - AI Receptionist Setup
echo ========================================
echo.

REM ─── Step 0: Check Python ────────────────────────────────────────
echo [1/7] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo     Python not found! Download from: https://www.python.org/downloads/
    echo     Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
python --version
echo     [OK] Python is installed
echo.

REM ─── Step 1: Clone Repository ────────────────────────────────────
echo [2/7] Cloning Recepta from GitHub...
if exist "Recepta" (
    echo     Recepta folder already exists. Updating...
    cd Recepta
    git pull
) else (
    git clone https://github.com/Murad150/Recepta-AI-Voice-Receptionist-.git Recepta
    cd Recepta
)
echo     [OK] Repository ready
echo.

REM ─── Step 2: Create Virtual Environment ──────────────────────────
echo [3/7] Creating virtual environment...
if exist "venv" (
    echo     Virtual environment already exists
) else (
    python -m venv venv
)
echo     [OK] Virtual environment ready
echo.

REM ─── Step 3: Install Python Packages ─────────────────────────────
echo [4/7] Installing Python packages...
call venv\Scripts\activate.bat
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo     Trying simplified requirements...
    pip install -r requirements-simple.txt
)
echo     [OK] Python packages installed
echo.

REM ─── Step 4: Install Ollama ──────────────────────────────────────
echo [5/7] Checking Ollama...
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo     [ACTION REQUIRED] Ollama not found!
    echo     Please download and install from:
    echo     https://ollama.com/download
    echo.
    echo     After installing, run these commands manually:
    echo       1. ollama pull llama3.2:3b
    echo       2. ollama pull nomic-embed-text
    echo.
    pause
) else (
    echo     [OK] Ollama is installed
    echo     Pulling LLM models (this may take 5-10 mins)...
    ollama pull llama3.2:3b
    ollama pull nomic-embed-text
    echo     [OK] Models downloaded
)
echo.

REM ─── Step 5: Install Docker ──────────────────────────────────────
echo [6/7] Checking Docker...
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo     [ACTION REQUIRED] Docker not found!
    echo     Please download and install from:
    echo     https://docs.docker.com/desktop/setup/install/windows-install/
    echo.
    echo     After installing, run this command:
    echo       docker compose -f docker/docker-compose.yml up -d speaches
    echo.
    pause
) else (
    echo     [OK] Docker is installed
    echo     Starting Speaches STT server...
    docker compose -f docker/docker-compose.yml up -d speaches
    echo     [OK] Speaches is running
)
echo.

REM ─── Step 6: Create .env File ────────────────────────────────────
echo [7/7] Setting up configuration...
if not exist ".env" (
    (
        echo OLLAMA_BASE_URL=http://localhost:11434
        echo OLLAMA_MODEL=llama3.2:3b
        echo OLLAMA_EMBEDDING_MODEL=nomic-embed-text
        echo SPEACHES_BASE_URL=http://localhost:8000
        echo SPEACHES_API_KEY=recepta-local
        echo LIVEKIT_URL=wss://your-project.livekit.cloud
        echo LIVEKIT_API_KEY=
        echo LIVEKIT_API_SECRET=
    ) > .env
    echo     [OK] .env file created
) else (
    echo     [OK] .env file already exists
)
echo.

REM ─── Done! ───────────────────────────────────────────────────────
echo ========================================
echo    Setup Complete!
echo ========================================
echo.
echo What to do next:
echo.
echo   Run Health Check:
echo     python main.py --check
echo.
echo   Test Dental Agent:
echo     python main.py --industry dental --business "My Clinic"
echo.
echo   Test Other Industries:
echo     python main.py --industry legal --business "Law Firm"
echo     python main.py --industry hvac --business "HVAC Co"
echo     python main.py --industry real_estate --business "Realty"
echo.
echo ========================================
pause
