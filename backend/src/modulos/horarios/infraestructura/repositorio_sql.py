"""Repositorio SQL de horarios y frecuencias (lectura, B2)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg_pool import AsyncConnectionPool


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
