@echo off
REM ==========================================================================
REM  QuietGate - one-click setup and run (Windows)
REM  1. creates .venv (if missing)      4. builds the synthetic test data (if missing)
REM  2. installs requirements.txt       5. runs unit tests + the evaluation
REM  3. downloads the models            6. starts the review page on PORT
REM  Usage:  run_project.bat            (port 6060)
REM          run_project.bat 7000       (custom port; avoid 6000, browsers block it)
REM ==========================================================================
setlocal
cd /d "%~dp0"
set PORT=%1
if "%PORT%"=="" set PORT=6060
set PYTHONIOENCODING=utf-8

where python >nul 2>nul || (echo [ERROR] Python 3.10+ not found on PATH. Install it from python.org first. & pause & exit /b 1)

if not exist ".venv\Scripts\python.exe" (
    echo [1/6] Creating virtual environment .venv ...
    python -m venv .venv || (echo [ERROR] could not create venv & pause & exit /b 1)
) else (
    echo [1/6] Using existing .venv
)
set PY=.venv\Scripts\python.exe

echo [2/6] Installing requirements ...
%PY% -m pip install --upgrade pip -q
%PY% -m pip install -r requirements.txt -q || (echo [ERROR] pip install failed & pause & exit /b 1)

echo [3/6] Downloading models (openWakeWord, Silero VAD, Vosk EN + KO) ...
%PY% -m quietgate.cli fetch-models || (echo [ERROR] model download failed & pause & exit /b 1)

if not exist "data\scenes\scene_29.flac" (
    echo [4/6] Building synthetic test scenes - needs internet once ...
    %PY% -m quietgate.cli make-data || (echo [ERROR] make-data failed & pause & exit /b 1)
) else (
    echo [4/6] Test data already present - skipping
)

echo [5/6] Running unit tests and evaluation ...
%PY% -m pytest -q || (echo [ERROR] unit tests failed & pause & exit /b 1)
%PY% -m quietgate.cli eval || (echo [ERROR] evaluation failed & pause & exit /b 1)
%PY% -m quietgate.diagnose --split test >nul

echo [6/6] Starting the review page on http://localhost:%PORT%  (Ctrl+C to stop)
%PY% app.py --port %PORT%
endlocal
