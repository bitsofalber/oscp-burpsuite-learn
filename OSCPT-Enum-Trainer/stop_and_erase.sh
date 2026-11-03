#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "=========================================="
echo "    OSCPT-ENUM-TRAINER - STOP & ERASE"
echo "=========================================="
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker no está instalado o no se encuentra en el PATH."
  exit 1
fi

echo "Deteniendo laboratorio y eliminando todos los recursos..."
docker compose down --rmi all --volumes --remove-orphans

echo
echo "=========================================="
echo " Limpieza completada con éxito."
echo " Contenedores, red e imágenes locales"
echo " han sido eliminados por completo."
echo "=========================================="
