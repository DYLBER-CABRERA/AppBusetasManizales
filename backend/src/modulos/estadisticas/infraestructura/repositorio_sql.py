"""Repositorio SQL de eventos de uso (escritura anónima, B2)."""

from __future__ import annotations

from uuid import UUID

from psycopg_pool import AsyncConnectionPool


class RepositorioEventosUsoSql:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def registrar(self, tipo: str, ruta_id: UUID | None) -> None:
        async with self._pool.connection() as conexion:
            await conexion.execute(
                "insert into evento_uso (tipo, ruta_id) values (%s::tipo_evento_uso, %s)", (tipo, ruta_id)
            )
