"""Perfiles de usuario (lectura para autenticación y GET /yo; el CRUD de A01 llega en B5)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg.errors import UniqueViolation
from psycopg_pool import AsyncConnectionPool

from nucleo.errores import ErrorConflictoNegocio


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

    async def perfil_completo(self, usuario_id: UUID) -> dict[str, Any] | None:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(
                """select p.id as usuario_id, p.correo, p.nombre, p.apellido, p.celular, p.rol::text as rol, p.empresa_id,
                          e.nombre as empresa_nombre, p.activo
                   from perfil_usuario p left join empresa e on e.id = p.empresa_id where p.id = %s""",
                (usuario_id,),
            )
            filas = await cursor.fetchall()
        return filas[0] if filas else None

    async def crear_pasajero(self, usuario_id, correo, nombre, apellido, celular) -> dict[str, Any] | None:
        try:
            async with self._pool.connection() as conexion:
                cursor = await conexion.execute(
                    """insert into perfil_usuario (id, correo, nombre, apellido, celular, rol)
                       values (%s, %s, %s, %s, %s, 'pasajero') on conflict (id) do nothing returning id""",
                    (usuario_id, correo, nombre, apellido, celular),
                )
                creado = await cursor.fetchone()
        except UniqueViolation as exc:  # el índice único de correo (otro perfil ya usa ese correo)
            raise ErrorConflictoNegocio("Ese correo ya está asociado a otro perfil.") from exc
        return await self.perfil_completo(usuario_id) if creado else None
