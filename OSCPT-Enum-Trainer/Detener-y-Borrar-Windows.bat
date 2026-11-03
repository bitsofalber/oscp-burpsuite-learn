@echo off
cd /d "%~dp0"
echo ==========================================
echo    OSCPT-ENUM-TRAINER - LIMPIEZA
echo ==========================================
where docker >nul 2>nul
if errorlevel 1 (
  echo Docker no esta instalado o no se encuentra en el PATH.
  pause
  exit /b 1
)

echo Deteniendo laboratorio y eliminando todos los recursos...
docker compose down --rmi all --volumes --remove-orphans

echo.
echo ==========================================
echo  Limpieza completada con exito.
echo  Contenedor, red e imagen construida
echo  han sido eliminados.
echo ==========================================
echo.
pause
