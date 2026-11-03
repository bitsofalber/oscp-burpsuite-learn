@echo off
cd /d "%~dp0"
echo ==========================================
echo        OSCPT-BURP-TRAINER
echo ==========================================
where docker >nul 2>nul
if errorlevel 1 (
  echo Docker no está instalado. Instala Docker Desktop.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Iniciar-Windows.ps1"
if errorlevel 1 (
  echo.
  echo El laboratorio ha finalizado con un error.
  pause
)
