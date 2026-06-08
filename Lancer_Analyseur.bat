@echo off
title STM32 Log Analyzer — AI Diagnostic Tool
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║        STM32 Log Analyzer — AI Diagnostic Tool      ║
echo  ║             Powered by Groq AI (Llama 3.1)          ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

REM ─── Detect Python (checks PATH and common install locations) ───
set PYTHON_EXE=

REM Try Python from PATH first (recommended)
where python >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_EXE=python
    goto :python_found
)

REM Try py launcher (Windows Python Launcher)
where py >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_EXE=py
    goto :python_found
)

REM Common install paths as fallback
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
) do (
    if exist %%P (
        set PYTHON_EXE=%%P
        goto :python_found
    )
)

echo  [ERROR] Python not found on this system.
echo  Please install Python 3.10+ from https://python.org
echo  Make sure to check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:python_found
echo  [OK] Python detected: %PYTHON_EXE%

REM ─── Check .env file exists ───────────────────────────────────
if not exist ".env" (
    echo  [WARNING] .env file not found.
    if exist ".env.example" (
        echo  Copying .env.example to .env ...
        copy ".env.example" ".env" >nul
        echo  [ACTION REQUIRED] Open .env and set your GROQ_API_KEY.
        echo.
        notepad .env
        pause
    ) else (
        echo  [ERROR] Neither .env nor .env.example found.
        echo  Create a .env file with: GROQ_API_KEY=gsk_your_key_here
        echo.
        pause
        exit /b 1
    )
)

REM ─── Check and install dependencies ───────────────────────────
echo  [..] Checking dependencies...
%PYTHON_EXE% -c "import PySide6; import groq; from dotenv import load_dotenv" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!!] Missing dependencies — Installing now...
    %PYTHON_EXE% -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo  [ERROR] Dependency installation failed.
        echo  Run manually: pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo  [OK] Dependencies installed successfully.
) else (
    echo  [OK] All dependencies are available.
)

echo.
echo  Starting application...
echo.

REM ─── Launch application ───────────────────────────────────────
%PYTHON_EXE% main.py

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] The application encountered an error.
    echo  Please check the error message above.
    echo.
    pause
)
