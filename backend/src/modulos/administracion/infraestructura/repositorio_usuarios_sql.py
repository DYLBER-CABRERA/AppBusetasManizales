"""Perfiles de usuario (lectura para autenticación y GET /yo; el CRUD de A01 llega en B5)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg_pool import AsyncConnectionPool


class RepositorioUsuariosSql:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def perfil(self, usuario_id: UUID) -> dict[str, Any] | None:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(
                """select p.id as usuario_id, p.correo, p.rol::text as rol, p.empresa_id, e.nombre as empresa_nombre, p.activo
                   from perfil_usuario p left join empresa e on e.id = p.empresa_id
                   where p.id = %s""",
                (usuario_id,),
            )
            filas = await cursor.fetchall()
        return filas[0] if filas else None
