@echo off
cd /d "%~dp0"
set "PM2_HOME=%~dp0.pm2"
set "PATH=%PATH%;%APPDATA%\npm"
set "NODE_PATH=%APPDATA%\npm\node_modules;%APPDATA%\9router\runtime\node_modules"
set "PYTHONIOENCODING=utf-8"
title 9router Process Manager (9routerpm)
echo ==========================================================
echo           9router PROCESS MANAGER (9routerpm)
echo            AUTO-INSTALLER ^& BOOTSTRAPPER
echo ==========================================================
echo.

:: Giai phong cong 20127 neu co server dang chay ngam de tranh xung dot
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :20127 ^| findstr LISTENING') do (
    echo -- Phat hien cong 20127 dang ban ^(PID: %%a^). Dang tu dong tat de khoi dong lai...
    taskkill /F /PID %%a >nul 2>nul
    :: Doi 2 giay de he dieu hanh giai phong socket hoan toan
    ping 127.0.0.1 -n 3 >nul
)


:: 1. Kiem tra va Tu dong thiet lap Python virtual environment (venv)
echo [1/4] Kiem tra moi truong Python...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python chua duoc cai dat tren he thong hoac chua duoc them vao PATH!
    echo Vui long tai va cai dat Python tu trang chu python.org - Tich chon Add Python to PATH.
    pause
    exit /b
)

if not exist "venv\Scripts\python.exe" (
    echo.
    echo -- Khong tim thay venv. Dang tu dong khoi tao moi truong ao Python venv...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Khoi tao venv that bai! Vui long kiem tra phan quyen.
        pause
        exit /b
    )
    echo -- Khoi tao venv thanh cong!
)

:: Kiem tra va tu dong cai dat dependency Python
if not exist "venv\Scripts\uvicorn.exe" (
    echo.
    echo -- Dang tu dong cai dat cac thu vien Python FastAPI, Uvicorn...
    venv\Scripts\pip install fastapi uvicorn
    if %errorlevel% neq 0 (
        echo [ERROR] Cai dat thu vien Python that bai! Vui long kiem tra ket noi mang.
        pause
        exit /b
    )
    echo -- Cai dat thu vien thanh cong!
)

:: 2. Kiem tra Node.js (Bat buoc cho 9router proxy)
echo [2/4] Kiem tra Node.js...
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js chua duoc cai dat tren may tinh nay!
    echo Vi 9router proxy chay tren nen Node.js, ban bat buoc phai cai dat Node.js de tiep tuc.
    echo Vui long tai va cai dat tai: https://nodejs.org/
    pause
    exit /b
)
echo -- Node.js da san sang.

:: 3. Kiem tra va tu dong cai dat PM2
echo [3/4] Kiem tra PM2 (Process Manager)...
where pm2 >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo -- Khong tim thay PM2! Dang tu dong cai dat PM2 toan cuc qua npm...
    call npm install -g pm2
    
    :: Kiem tra lai xem da cai dat duoc chua
    where pm2 >nul 2>nul
    if %errorlevel% neq 0 (
        echo [WARNING] Cai dat PM2 tu dong qua npm gap loi hoac can chay CMD duoi quyen Administrator!
        echo Vui long mo CMD duoi quyen Administrator va chay lenh: npm install -g pm2
        pause
        exit /b
    )
    echo -- Cai dat PM2 thanh cong!
) else (
    echo -- PM2 da san sang.
)

:: 4. Khoi dong Web Server
echo.
echo [4/4] Moi thu da san sang! Dang khoi dong Web Server tren cong 20127...
echo.
echo ==========================================================
echo Giao dien quan ly se tu dong mo tren trinh duyet Web...
echo Dia chi: http://localhost:20127
echo.
echo Nhan Ctrl+C tai cua so nay neu muon tat server.
echo ==========================================================
echo.

:: Mo trinh duyet sau 2 giay de cho server khoi dong xong
start /b cmd /c "ping localhost -n 3 > nul && start http://localhost:20127"

:: Chay FastAPI Uvicorn Server
venv\Scripts\python -m uvicorn backend.main:app --host 0.0.0.0 --port 20127
pause
