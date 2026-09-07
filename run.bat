@echo off
title Mini YouTube Downloader - SnipGeek Edition
set PYTHONDONTWRITEBYTECODE=1

cd /d "%~dp0"

echo ========================================================
echo   MINI YOUTUBE DOWNLOADER (v1.2) - BY SNIPGEEK
echo ========================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python tidak terdeteksi di laptop Anda!
    echo Silakan download dan install Python 3.8+ dari https://www.python.org/
    echo.
    pause
    exit /b 1
)

python _engine\src\app.py

if errorlevel 1 (
    echo.
    echo [X] Terjadi error saat aplikasi berjalan.
    pause
)
