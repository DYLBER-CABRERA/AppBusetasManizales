"""Escribe ../contrato/openapi.json desde la app FastAPI (no toca ninguna base de datos)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

DESTINO = RAIZ.parent / "contrato" / "openapi.json"


def generar() -> str:
    from servidor import crear_app

    return json.dumps(crear_app().openapi(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> None:
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(generar(), encoding="utf-8", newline="\n")
    print(f"Contrato escrito en {DESTINO}")


if __name__ == "__main__":
    main()
