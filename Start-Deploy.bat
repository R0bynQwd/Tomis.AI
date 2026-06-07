@echo off
title TOMIS.AI - Automated AI Cluster Installer
setlocal enabledelayedexpansion

:: Verificare Administrator
openfiles >nul 2>&1
if %errorlevel% neq 0 (
    color 4F
    echo [ERROR] PLEASE RUN AS ADMINISTRATOR!
    pause
    exit /b
)

:: Parametrizare: %1=ROLE (MASTER/NODE/GENERATE/UPDATE_MODELS), %2=MASTER_IP, %3=TOKEN
set "ROLE=%1"
set "IP=%2"
set "TOKEN=%3"

if "%ROLE%"=="" (
    color 0A
    echo ===================================================
    echo             TOMIS.AI CLUSTER INSTALLER
    echo ===================================================
    echo.
    echo [1] Instalare MASTER (Genereaza config.json)
    echo [2] Instalare NOD (Conectare la Master)
    echo [3] Generare KIT-URI OFFLINE
    echo [4] ACTUALIZARE MODELE AI ^& UTILS
    echo.
    set /p CHOICE="Selection (1-4): "
    if "!CHOICE!"=="1" set "ROLE=MASTER"
    if "!CHOICE!"=="2" set "ROLE=NODE"
    if "!CHOICE!"=="3" set "ROLE=GENERATE"
    if "!CHOICE!"=="4" set "ROLE=UPDATE_MODELS"
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Deploy-Cluster.ps1" -Role "%ROLE%" -MasterIP "%IP%" -Token "%TOKEN%"

if "%ROLE%"=="MASTER" (
    echo.
    echo [SUCCESS] Master is being initialized.
    echo [INFO] Dashboard will be available at http://localhost:28001
)

pause
exit /b
