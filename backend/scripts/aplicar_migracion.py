"""Aplica UN archivo de migración nuevo (p. ej. 0006) a una BD ya migrada. Las migraciones nuevas son idempotentes.

Uso (desde backend/):
  python scripts/aplicar_migracion.py 0006_perfil_pasajero.sql             # simulacro: muestra el SQL, NO se conecta
  python scripts/aplicar_migracion.py 0006_perfil_pasajero.sql --aplicar   # ejecuta en UNA transacción sobre DATABASE_URL
"""

from __future__ import annotations

import sys

from _comun import MIGRACIONES, conectar


def main() -> int:
    argumentos = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(argumentos) != 1:
        raise SystemExit("Indica el archivo, p. ej.: python scripts/aplicar_migracion.py 0006_perfil_pasajero.sql [--aplicar]")
    archivo = MIGRACIONES / argumentos[0]
    if archivo.parent != MIGRACIONES or not archivo.is_file():
        raise SystemExit(f"No existe la migración {argumentos[0]} en supabase/migraciones/")
    sql = archivo.read_text(encoding="utf-8")
    if "--aplicar" not in sys.argv:
        print(f"Modo simulacro: no se tocó ninguna base. SQL de {archivo.name}:\n")
        print(sql)
        print("Usa --aplicar para ejecutarla en DATABASE_URL.")
        return 0
    with conectar() as conexion:  # una transacción: si algo falla, no queda nada
        conexion.execute(sql)
    print(f"Migración {archivo.name} aplicada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
