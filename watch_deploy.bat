@echo off
echo ========================================================
echo   Iniciando Watcher do Sistema QRZ (Auto-Deploy)
echo ========================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0watch_deploy.ps1"
echo.
pause
