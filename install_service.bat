@echo off
setlocal enabledelayedexpansion
title 9routerpm - Setup Windows Service 24/7

echo ==========================================================
echo         HE THONG CAI DAT DICH VU RUN 24/7 CHO WINDOWS
echo ==========================================================
echo.

:: 1. Yeu cau quyen Administrator tu dong
:checkPrivileges
NET FILE 1>NUL 2>NUL
if '%errorlevel%' == '0' ( goto gotPrivileges ) else ( goto getPrivileges )

:getPrivileges
if '%1'=='ELEV' (shift & goto gotPrivileges)
echo -- Dang yeu cau quyen Administrator de dang ky Dich vu Windows...
setlocal DisableDelayedExpansion
set "vbs=%temp%\getadmin.vbs"
echo Set UAC = CreateObject("Shell.Application") > "%vbs%"
echo UAC.ShellExecute "%~s0", "ELEV", "", "runas", 1 >> "%vbs%"
"%vbs%"
exit /B

:gotPrivileges
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: 2. Kiem tra va tao Virtual Environment Python neu chua co
echo -- Kiem tra moi truong ao Python venv...
if not exist "%~dp0venv\Scripts\python.exe" (
    echo -- Khong tim thay venv. Dang tao moi truong ao python...
    python -m venv "%~dp0venv"
)
if not exist "%~dp0venv\Scripts\uvicorn.exe" (
    echo -- Dang cai dat cac thu vien phu tro cho API Server...
    "%~dp0venv\Scripts\pip" install fastapi uvicorn
)

:: 3. Tai ve NSSM neu chua co
echo -- Kiem tra va tai cong cu NSSM...
"%~dp0venv\Scripts\python.exe" "%~dp0download_nssm.py"
if not exist "%~dp0bin\nssm.exe" (
    echo [ERROR] Khong the tai nssm.exe! Vui long kiem tra ket noi Internet.
    pause
    exit /b
)

:: 4. Giai phong cong 20127 cu neu co
echo -- Dang giai phong cong 20127...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :20127 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>nul
)

:: 5. Xoa Windows Service cu neu co
echo -- Dang kiem tra va don dep Windows Service cu...
"%~dp0bin\nssm.exe" stop 9routerPMService >nul 2>nul
"%~dp0bin\nssm.exe" remove 9routerPMService confirm >nul 2>nul

:: 6. Dang ky Windows Service moi qua NSSM
echo -- Dang dang ky Windows Service "9routerPMService" chay 24/7...
"%~dp0bin\nssm.exe" install 9routerPMService "%~dp0venv\Scripts\python.exe" "-m uvicorn backend.main:app --host 0.0.0.0 --port 20127"
if %errorlevel% neq 0 (
    echo [ERROR] Dang ky Windows Service that bai!
    pause
    exit /b
)

:: Cấu hình các tham số dịch vụ
"%~dp0bin\nssm.exe" set 9routerPMService AppDirectory "%~dp0"
"%~dp0bin\nssm.exe" set 9routerPMService DisplayName "9router Process Manager Service"
"%~dp0bin\nssm.exe" set 9routerPMService Description "Dich vu giam sat va duy tri he thong 9router Proxy va Hermes Agent hoat dong 24/24"
"%~dp0bin\nssm.exe" set 9routerPMService Start SERVICE_AUTO_START

:: Cau hinh them bien moi truong PM2_HOME, APPDATA_USER, USERPROFILE_USER va LOCALAPPDATA_USER cho Service chay dong bo
"%~dp0bin\nssm.exe" set 9routerPMService AppEnvironmentExtra PM2_HOME="%~dp0.pm2" APPDATA_USER="%APPDATA%" USERPROFILE_USER="%USERPROFILE%" LOCALAPPDATA_USER="%LOCALAPPDATA%"

:: Cau hinh tu dong khoi dong lai khi co loi xay ra (auto recovery)
"%~dp0bin\nssm.exe" set 9routerPMService AppExit Default Restart
"%~dp0bin\nssm.exe" set 9routerPMService AppThrottle 1500

:: 7. Khoi dong Windows Service
echo -- Dang khoi dong Dich vu Windows...
"%~dp0bin\nssm.exe" start 9routerPMService

echo.
echo ==========================================================
echo [OK] CAI DAT WINDOWS SERVICE 24/7 THANH CONG!
echo ==========================================================
echo * Dich vu "9routerPMService" dang chay an he thong 24/24.
echo * Tu dong khoi dong cung Windows truoc ca khi dang nhap.
echo * Tu dong dung day va mo lai tat ca proxy / hermes khi bi crash.
echo * Dia chi truy cap: http://localhost:20127
echo.
echo Nhap phim bat ky de ket thuc...
pause >nul
