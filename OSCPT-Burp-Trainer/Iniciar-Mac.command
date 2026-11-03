#!/bin/bash
set -u
cd "$(dirname "$0")"

PROJECT="OSCPT-Burp-Trainer"
CLEANING_UP=0

cleanup() {
  if [ "$CLEANING_UP" -eq 1 ]; then return; fi
  CLEANING_UP=1
  echo
  echo "=========================================="
  echo " Limpiando recursos del laboratorio..."
  echo "=========================================="
  docker compose down --rmi all --volumes --remove-orphans
  echo
  echo "Laboratorio detenido. Contenedores, red, volumen de datos e imagen del proyecto eliminados."
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "=========================================="
echo "       OSCPT-BURP-TRAINER"
echo "=========================================="
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker no está instalado. Instala Docker Desktop y vuelve a intentarlo."
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker Desktop no está iniciado. Ábrelo y vuelve a intentarlo."
  exit 1
fi

echo "Iniciando laboratorio..."
echo "Acceso: http://localhost:8010/"
echo "Para detenerlo y borrar sus recursos, pulsa Ctrl+C."
docker compose up --build
