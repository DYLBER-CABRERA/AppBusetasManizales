"""Credenciales de fuentes GPS (lectura para la ingesta; el CRUD del administrador llega en B5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg_pool import AsyncConnectionPool


class RepositorioFuentesGpsSql:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def empresa_por_hash(self, hash_clave: str) -> dict[str, Any] | None:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(
                "select id as credencial_id, empresa_id from credencial_fuente_gps where hash_clave = %s and activa",
                (hash_clave,),
            )
            filas = await cursor.fetchall()
        return filas[0] if filas else None

    async def marcar_uso(self, credencial_id: UUID, ahora: datetime) -> None:
        async with self._pool.connection() as conexion:
            await conexion.execute("update credencial_fuente_gps set ultimo_uso = %s where id = %s", (ahora, credencial_id))
