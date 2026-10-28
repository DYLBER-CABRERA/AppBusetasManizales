#!/usr/bin/env bash
# Crea los archivos de entorno a partir de los .env.example SIN sobrescribir los existentes.
set -euo pipefail
cd "$(dirname "$0")/.."
copiar() { # origen destino
  if [ -e "$2" ]; then echo "= ya existe: $2 (no se toca)"; else cp "$1" "$2"; echo "+ creado:    $2"; fi
}
copiar backend/.env.example   backend/.env
copiar web-admin/.env.example web-admin/.env.local
copiar mobile/.env.example    mobile/.env
echo
echo "Ahora edita los 3 archivos y reemplaza los valores TU_PROYECTO / tu_*_key / cambia_esto_*."
