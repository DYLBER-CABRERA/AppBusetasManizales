"""Repositorio SQL de búsqueda (B2). `normalizar_texto` y `rutas_por_hito` vienen de la migración 0003."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg_pool import AsyncConnectionPool

_COLUMNAS_HITO = """h.id, h.nombre, h.tipo::text as tipo, h.alias,
                    st_y(h.ubicacion::geometry) as lat, st_x(h.ubicacion::geometry) as lng"""


class RepositorioBusquedaSql:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def _consultar(self, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(sql, params)
            return await cursor.fetchall()

    async def buscar_rutas(self, patron: str, texto: str) -> list[UUID]:
        filas = await self._consultar(
            """select r.id
               from ruta r
               where r.estado = 'activo' and (
                 normalizar_texto(r.nombre) like %(patron)s
                 or exists (
                   select 1 from servicio_ruta s
                   where s.ruta_id = r.id and s.estado <> 'baja'
                     and (s.codigo_publico = %(texto)s or s.codigo_publico like %(patron)s
                          or normalizar_texto(coalesce(s.codigo_interno, '')) like %(patron)s)))
               order by (normalizar_texto(r.nombre) = %(texto)s) desc,
                        exists (select 1 from servicio_ruta s where s.ruta_id = r.id and s.codigo_publico = %(texto)s) desc,
                        normalizar_texto(r.nombre)
               limit 20""",
            {"patron": patron, "texto": texto},  # type: ignore[arg-type]
        )
        return [f["id"] for f in filas]

    async def buscar_hitos(self, patron: str, texto: str) -> list[dict[str, Any]]:
        return await self._consultar(
            f"""select {_COLUMNAS_HITO}
                from hito h
                where h.estado = 'activo' and (
                  normalizar_texto(h.nombre) like %(patron)s
                  or exists (select 1 from unnest(h.alias) a where normalizar_texto(a) like %(patron)s))
                order by (normalizar_texto(h.nombre) = %(texto)s) desc, normalizar_texto(h.nombre)
                limit 20""",
            {"patron": patron, "texto": texto},  # type: ignore[arg-type]
        )

    async def obtener_hito(self, hito_id: UUID) -> dict[str, Any] | None:
        filas = await self._consultar(
            f"select {_COLUMNAS_HITO} from hito h where h.id = %s and h.estado = 'activo'", (hito_id,)
        )
        return filas[0] if filas else None

    async def rutas_por_hito(self, hito_id: UUID, radio_m: int) -> dict[UUID, float]:
        filas = await self._consultar(
            "select ruta_id, distancia_m from rutas_por_hito(%s::uuid, %s::integer) order by distancia_m",
            (hito_id, radio_m),
        )
        return {f["ruta_id"]: f["distancia_m"] for f in filas}
