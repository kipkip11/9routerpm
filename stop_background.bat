@echo off
cd /d "%~dp0"
set "PM2_HOME=%~dp0.pm2"
set "PATH=%PATH%;%APPDATA%\npm"
title 9routerpm - Dung chay ngam

echo ==========================================================
echo           9router PROCESS MANAGER (9routerpm)
echo             DUNG VA XOA SERVER CHAY NGAM (PM2)
echo ==========================================================
echo.

where pm2 >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Khong tim thay PM2 tren he thong!
    pause
    exit /b
)

echo -- Dang dung va xoa server khoi PM2...
pm2 delete 9routerpm-server

echo.
echo ==========================================================
echo [OK] DA DUNG WEB SERVER CHAY NGAM THANH CONG!
echo ==========================================================
echo.
ping 127.0.0.1 -n 3 >nul
