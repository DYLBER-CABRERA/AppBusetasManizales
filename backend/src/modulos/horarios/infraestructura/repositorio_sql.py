"""Repositorio SQL de horarios y frecuencias (lectura, B2)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from nucleo.errores import ErrorConflictoVersion, ErrorNoEncontrado


class RepositorioHorariosSql:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def _consultar(self, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(sql, params)
            return await cursor.fetchall()

    async def ruta_activa_existe(self, ruta_id: UUID) -> bool:
        return bool(await self._consultar("select 1 from ruta where id = %s and estado = 'activo'", (ruta_id,)))

    async def servicios_de_ruta(self, ruta_id: UUID) -> list[dict[str, Any]]:
        return await self._consultar(
            """select s.id as servicio_id, s.empresa_id, e.nombre as empresa_nombre, s.codigo_publico, s.version
               from servicio_ruta s join empresa e on e.id = s.empresa_id
               where s.ruta_id = %s and s.estado <> 'baja' order by e.nombre""",
            (ruta_id,),
        )

    async def horarios_de(self, servicio_ids: list[UUID]) -> list[dict[str, Any]]:
        if not servicio_ids:
            return []
        return await self._consultar(
            """select servicio_ruta_id as servicio_id, tipo_dia::text as tipo_dia, primera_salida, ultima_salida, cierre, nota
               from horario where servicio_ruta_id = any(%s)
               order by case tipo_dia when 'lun_vie' then 1 when 'sabado' then 2 else 3 end""",
            (servicio_ids,),
        )

    async def frecuencias_de(self, servicio_ids: list[UUID]) -> list[dict[str, Any]]:
        if not servicio_ids:
            return []
        return await self._consultar(
            """select servicio_ruta_id as servicio_id, tipo_dia::text as tipo_dia, inicio_minuto, fin_minuto,
                      minutos_min, minutos_max, nota
               from frecuencia where servicio_ruta_id = any(%s)
               order by case tipo_dia when 'lun_vie' then 1 when 'sabado' then 2 else 3 end, inicio_minuto""",
            (servicio_ids,),
        )

    # ---- edición del jefe (B4) ----

    async def servicio_de_empresa(self, servicio_id: UUID, empresa_id: UUID) -> dict[str, Any] | None:
        filas = await self._consultar(
            """select s.id as servicio_id, s.empresa_id, e.nombre as empresa_nombre, s.codigo_publico, s.version
               from servicio_ruta s join empresa e on e.id = s.empresa_id
               where s.id = %s and s.empresa_id = %s and s.estado <> 'baja'""",
            (servicio_id, empresa_id),
        )
        return filas[0] if filas else None

    @staticmethod
    async def _subir_version(conexion: AsyncConnection[Any], servicio_id: UUID, version: int) -> int:
        cursor = await conexion.execute(
            "update servicio_ruta set version = version + 1 where id = %s and version = %s returning version",
            (servicio_id, version),
        )
        fila = await cursor.fetchone()
        if fila is not None:
            return fila["version"]
        cursor = await conexion.execute("select version from servicio_ruta where id = %s", (servicio_id,))
        actual = await cursor.fetchone()
        if actual is None:
            raise ErrorNoEncontrado("El servicio no existe.")
        raise ErrorConflictoVersion(actual["version"])

    async def reemplazar_horarios(self, servicio_id: UUID, version: int, horarios: list[Any]) -> int:
        async with self._pool.connection() as conexion:
            nueva = await self._subir_version(conexion, servicio_id, version)
            await conexion.execute("delete from horario where servicio_ruta_id = %s", (servicio_id,))
            for h in horarios:
                await conexion.execute(
                    """insert into horario (servicio_ruta_id, tipo_dia, primera_salida, ultima_salida, cierre, nota)
                       values (%s, %s::tipo_dia, %s, %s, %s, %s)""",
                    (servicio_id, h.tipo_dia, h.primera_salida, h.ultima_salida, h.cierre, h.nota),
                )
        return nueva

    async def reemplazar_frecuencias(self, servicio_id: UUID, version: int, franjas: list[Any]) -> int:
        async with self._pool.connection() as conexion:
            nueva = await self._subir_version(conexion, servicio_id, version)
            await conexion.execute("delete from frecuencia where servicio_ruta_id = %s", (servicio_id,))
            for f in franjas:
                await conexion.execute(
                    """insert into frecuencia
                         (servicio_ruta_id, tipo_dia, inicio_minuto, fin_minuto, minutos_min, minutos_max, nota)
                       values (%s, %s::tipo_dia, %s, %s, %s, %s, %s)""",
                    (servicio_id, f.tipo_dia, f.inicio_minuto, f.fin_minuto, f.minutos_min, f.minutos_max, f.nota),
                )
        return nueva
