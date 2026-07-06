@echo off
title 9routerpm - Go bo Windows Service 24/7

echo ==========================================================
echo         HE THONG GO BO DICH VU RUN 24/7 WINDOWS
echo ==========================================================
echo.

:: Yeu cau quyen Administrator tu dong
:checkPrivileges
NET FILE 1>NUL 2>NUL
if '%errorlevel%' == '0' ( goto gotPrivileges ) else ( goto getPrivileges )

:getPrivileges
if '%1'=='ELEV' (shift & goto gotPrivileges)
echo -- Dang yeu cau quyen Administrator de go bo Dich vu...
setlocal DisableDelayedExpansion
set "vbs=%temp%\getadmin.vbs"
echo Set UAC = CreateObject("Shell.Application") > "%vbs%"
echo UAC.ShellExecute "%~s0", "ELEV", "", "runas", 1 >> "%vbs%"
"%vbs%"
exit /B

:gotPrivileges
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PM2_HOME=%~dp0.pm2"
set "PATH=%PATH%;%APPDATA%\npm"

echo -- Dang dung va tat toan bo cac tien trinh PM2 (proxy & hermes)...
call pm2 kill >nul 2>nul

echo -- Dang dung Dich vu "9routerPMService"...
"%~dp0bin\nssm.exe" stop 9routerPMService >nul 2>nul

echo -- Dang xoa Dich vu khoi Windows...
"%~dp0bin\nssm.exe" remove 9routerPMService confirm
if %errorlevel% neq 0 (
    echo [ERROR] Go bo Windows Service that bai!
    pause
    exit /b
)

echo.
echo ==========================================================
echo [OK] GO BO WINDOWS SERVICE 24/7 THANH CONG!
echo ==========================================================
echo * Dich vu da duoc go sach se khoi he thong.
echo.
echo Nhap phim bat ky de ket thuc...
pause >nul
