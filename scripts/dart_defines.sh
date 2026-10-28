#!/usr/bin/env bash
# Imprime los --dart-define leyendo mobile/.env. Uso:
#   cd mobile && flutter run $(../scripts/dart_defines.sh)
#   cd mobile && flutter build apk --release $(../scripts/dart_defines.sh)
set -euo pipefail
f="$(dirname "$0")/../mobile/.env"
grep -E '^[A-Z_]+=' "$f" | sed 's/^/--dart-define=/' | tr '\n' ' '
