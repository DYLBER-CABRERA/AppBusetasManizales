"""Utilidades compartidas por los scripts. Nunca imprime credenciales de la cadena de conexión."""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parents[1]
SEMILLAS = RAIZ / "supabase" / "semillas"
MIGRACIONES = RAIZ / "supabase" / "migraciones"
sys.path.insert(0, str(RAIZ / "src"))


def url_base_de_datos() -> str:
    from nucleo.configuracion import obtener_configuracion

    url = obtener_configuracion().database_url.get_secret_value()
    if not url:
        raise SystemExit("Falta DATABASE_URL en backend/.env")
    return url


def describir_destino(url: str) -> str:
    """host:puerto/base, sin usuario ni clave."""
    p = urlparse(url)
    return f"{p.hostname}:{p.port or 5432}{p.path}"


def conectar():  # noqa: ANN201
    import psycopg

    url = url_base_de_datos()
    print(f"Base de datos destino: {describir_destino(url)}")
    return psycopg.connect(url, prepare_threshold=None)
