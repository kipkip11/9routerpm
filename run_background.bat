@echo off
cd /d "%~dp0"
set "PM2_HOME=%~dp0.pm2"
set "PATH=%PATH%;%APPDATA%\npm"
set "NODE_PATH=%APPDATA%\npm\node_modules;%APPDATA%\9router\runtime\node_modules"
set "PYTHONIOENCODING=utf-8"
title 9routerpm - Chay ngam

echo ==========================================================
echo           9router PROCESS MANAGER (9routerpm)
echo             KHOI DONG RUN BACKGROUND (PM2)
echo ==========================================================
echo.

:: 1. Kiem tra va Tu dong thiet lap Python virtual environment (venv)
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python chua duoc cai dat tren he thong hoac chua duoc them vao PATH!
    pause
    exit /b
)

if not exist "venv\Scripts\python.exe" (
    echo -- Dang khoi tao moi truong ao Python venv...
    python -m venv venv
)

if not exist "venv\Scripts\uvicorn.exe" (
    echo -- Dang cai dat cac thu vien Python...
    venv\Scripts\pip install fastapi uvicorn requests
) else (
    venv\Scripts\python -c "import requests" >nul 2>nul
    if %errorlevel% neq 0 (
        venv\Scripts\pip install requests
    )
)

:: 2. Kiem tra Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js chua duoc cai dat!
    pause
    exit /b
)

:: 3. Kiem tra PM2
where pm2 >nul 2>nul
if %errorlevel% neq 0 (
    echo -- Dang tu dong cai dat PM2 toan cuc...
    call npm install -g pm2
    where pm2 >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Khong the cai dat PM2! Vui long mo CMD quyen Admin va chay: npm install -g pm2
        pause
        exit /b
    )
)

:: 4. Giai phong cong 20127 cu neu co
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :20127 ^| findstr LISTENING') do (
    echo -- Giai phong cong 20127 cu (PID: %%a)...
    taskkill /F /PID %%a >nul 2>nul
    ping 127.0.0.1 -n 3 >nul
)

:: 5. Xoa server cu khoi PM2 neu ton tai (de tranh trung lap)
pm2 delete 9routerpm-server >nul 2>nul

:: 6. Khoi dong server trong PM2
echo -- Dang khoi dong Web Server ngam bang PM2...
pm2 start venv\Scripts\python.exe --name "9routerpm-server" -- -m uvicorn backend.main:app --host 0.0.0.0 --port 20127
if %errorlevel% neq 0 (
    echo [ERROR] Khoi dong server trong PM2 that bai!
    pause
    exit /b
)

echo.
echo ==========================================================
echo [OK] DA KHOI DONG SERVER 9routerpm CHAY NGAM THANH CONG!
echo.
echo * Server dang chay an duoi PM2 (Cong 20127).
echo * Ban co the tat cua so CMD nay ma server van hoat dong.
echo * De tat server, hay click dup vao file: stop_background.bat
echo ==========================================================
echo.

:: Mo trinh duyet Web
start http://localhost:20127
ping 127.0.0.1 -n 4 >nul
