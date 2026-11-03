#!/bin/bash
set -u
cd "$(dirname "$0")"

echo "=========================================="
echo "    OSCPT-ENUM-TRAINER - LIMPIEZA"
echo "=========================================="
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker no está instalado o no se encuentra en el PATH."
  read -p "Pulsa [ENTER] para salir..."
  exit 1
fi

echo "Deteniendo laboratorio y eliminando todos los recursos..."
docker compose down --rmi all --volumes --remove-orphans

echo
echo "=========================================="
echo " ¡Limpieza completada con éxito!"
echo " Contenedor, red e imagen construida"
echo " han sido eliminados por completo."
echo "=========================================="
echo
read -p "Pulsa [ENTER] para cerrar esta ventana..."
