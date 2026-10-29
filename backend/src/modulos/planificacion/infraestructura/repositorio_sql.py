"""Repositorio SQL de planificación (lectura)."""

from __future__ import annotations

from uuid import UUID

from psycopg_pool import AsyncConnectionPool


class RepositorioPlanificacionSql:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def rutas_de_paraderos(self, paradero_ids: list[UUID]) -> dict[UUID, set[UUID]]:
        resultado: dict[UUID, set[UUID]] = {}
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(
                """select rp.paradero_id, rp.ruta_id from ruta_paradero rp join ruta r on r.id = rp.ruta_id
                   where rp.paradero_id = any(%s) and rp.sentido = 'circular' and r.estado = 'activo'""",
                (paradero_ids,),
            )
            for fila in await cursor.fetchall():
                resultado.setdefault(fila["paradero_id"], set()).add(fila["ruta_id"])
        return resultado
