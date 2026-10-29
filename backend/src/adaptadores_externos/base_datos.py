"""Pool asíncrono de psycopg (Supabase). Solo `composicion.py` lo crea."""

from __future__ import annotations

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


def crear_pool(cadena_conexion: str) -> AsyncConnectionPool:
    """Pool sin abrir; el *lifespan* lo abre. Sentencias preparadas desactivadas (transaction pooler de Supabase)."""
    return AsyncConnectionPool(
        cadena_conexion,
        open=False,
        min_size=1,
        max_size=5,
        timeout=10,
        kwargs={"row_factory": dict_row, "prepare_threshold": None},
    )
