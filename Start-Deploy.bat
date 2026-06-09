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

:: Parametrizare: %1=ROLE (MASTER/NODE/GENERATE/UPDATE_MODELS/EMULATE), %2=MASTER_IP, %3=TOKEN
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
    echo [5] EMULARE SARCINI / TEST MONITORIZARE
    echo [6] GPU DIAGNOSTICS
    echo.
    set /p CHOICE="Selection (1-6): "
    if "!CHOICE!"=="1" set "ROLE=MASTER"
    if "!CHOICE!"=="2" set "ROLE=NODE"
    if "!CHOICE!"=="3" set "ROLE=GENERATE"
    if "!CHOICE!"=="4" set "ROLE=UPDATE_MODELS"
    if "!CHOICE!"=="5" set "ROLE=EMULATE"
    if "!CHOICE!"=="6" set "ROLE=GPU_DIAG"
)

:: GPU Diagnostics
if "%ROLE%"=="GPU_DIAG" (
    color 0E
    echo.
    echo [GPU DIAGNOSTICS] Scanning cluster nodes...
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "kubectl describe nodes 2>nul | Select-String -Pattern 'Name:|accelerator|nvidia.com' | head -20"
    echo.
    echo [GPU CAPABILITY] Checking for nvidia-smi...
    nvidia-smi 2>nul || (
        echo [WARNING] nvidia-smi not available. Install NVIDIA CUDA Toolkit.
        timeout /t 3 /nobreak
    )
    pause
    exit /b
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Deploy-Cluster.ps1" -Role "%ROLE%" -MasterIP "%IP%" -Token "%TOKEN%"

if "%ROLE%"=="MASTER" (
    echo.
    echo [SUCCESS] Master is being initialized.
    echo [INFO] Dashboard will be available on port 28001 via the physical NIC IP.
)

pause
exit /b
