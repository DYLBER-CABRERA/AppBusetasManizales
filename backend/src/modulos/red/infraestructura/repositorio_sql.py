"""Repositorio SQL del módulo red (consulta pública). SQL escrito a mano; funciones PostGIS de la migración 0003."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg_pool import AsyncConnectionPool

_SERVICIOS = """
select s.ruta_id, s.id as servicio_id, s.empresa_id, e.nombre as empresa_nombre, s.codigo_publico
from servicio_ruta s join empresa e on e.id = s.empresa_id
where s.ruta_id = any(%s) and s.estado <> 'baja'
order by e.nombre
"""


class RepositorioRutasSql:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def _consultar(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(sql, params)
            return await cursor.fetchall()

    async def _con_servicios(self, filas: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ids = [f["id"] for f in filas]
        por_ruta: dict[UUID, list[dict[str, Any]]] = {i: [] for i in ids}
        if ids:
            for s in await self._consultar(_SERVICIOS, (ids,)):
                por_ruta[s["ruta_id"]].append({k: v for k, v in s.items() if k != "ruta_id"})
        for f in filas:
            f["servicios"] = por_ruta[f["id"]]
        return filas

    async def rutas_cercanas(self, lat: float, lng: float, radio_m: int) -> list[dict[str, Any]]:
        filas = await self._consultar(
            """select c.ruta_id as id, c.nombre, c.tipo_recorrido::text as tipo_recorrido, c.distancia_m,
                      (r.ruta_principal_id is not null) as es_variante
               from rutas_cercanas(%s::double precision, %s::double precision, %s::integer) c
               join ruta r on r.id = c.ruta_id
               order by c.distancia_m""",
            (lat, lng, radio_m),
        )
        return await self._con_servicios(filas)

    async def listar_activas(self) -> list[dict[str, Any]]:
        filas = await self._consultar(
            """select id, nombre, tipo_recorrido::text as tipo_recorrido, (ruta_principal_id is not null) as es_variante
               from ruta where estado = 'activo' order by normalizar_texto(nombre), id"""
        )
        return await self._con_servicios(filas)

    async def resumenes(self, ruta_ids: list[UUID], distancias: dict[UUID, float] | None = None) -> list[dict[str, Any]]:
        if not ruta_ids:
            return []
        filas = await self._consultar(
            """select id, nombre, tipo_recorrido::text as tipo_recorrido, (ruta_principal_id is not null) as es_variante
               from ruta where estado = 'activo' and id = any(%s)""",
            (ruta_ids,),
        )
        orden = {rid: i for i, rid in enumerate(ruta_ids)}
        filas.sort(key=lambda f: orden[f["id"]])
        for f in filas:
            f["distancia_m"] = (distancias or {}).get(f["id"])
        return await self._con_servicios(filas)

    async def obtener_detalle(self, ruta_id: UUID) -> dict[str, Any] | None:
        filas = await self._consultar(
            """select r.id, r.nombre, r.tipo_recorrido::text as tipo_recorrido, r.descripcion, r.ruta_principal_id,
                      (r.ruta_principal_id is not null) as es_variante, r.version, t.longitud_m,
                      st_asgeojson(t.trazado::geometry, 6)::jsonb as trazado
               from ruta r join ruta_trazado t on t.ruta_id = r.id and t.sentido = 'circular'
               where r.id = %s and r.estado = 'activo'""",
            (ruta_id,),
        )
        if not filas:
            return None
        ruta = (await self._con_servicios(filas))[0]
        ruta["distancia_m"] = None
        ruta["paraderos"] = await self._consultar(
            """select rp.orden, p.id as paradero_id, p.nombre,
                      st_y(p.ubicacion::geometry) as lat, st_x(p.ubicacion::geometry) as lng
               from ruta_paradero rp join paradero p on p.id = rp.paradero_id
               where rp.ruta_id = %s and rp.sentido = 'circular' order by rp.orden""",
            (ruta_id,),
        )
        return ruta

    async def paraderos_cercanos(self, lat: float, lng: float, radio_m: int, ruta_id: UUID | None) -> list[dict[str, Any]]:
        return await self._consultar(
            """select paradero_id, nombre, lat, lng, distancia_m
               from paraderos_cercanos(%s::double precision, %s::double precision, %s::integer, %s::uuid)""",
            (lat, lng, radio_m, ruta_id),
        )

    async def paradero_mas_cercano(self, lat: float, lng: float) -> dict[str, Any] | None:
        filas = await self._consultar(
            """with punto as (select st_setsrid(st_makepoint(%s::double precision, %s::double precision), 4326)::geography as g)
               select p.id as paradero_id, p.nombre, st_y(p.ubicacion::geometry) as lat, st_x(p.ubicacion::geometry) as lng,
                      st_distance(p.ubicacion, punto.g) as distancia_m
               from paradero p cross join punto
               where p.estado = 'activo' order by p.ubicacion <-> punto.g limit 1""",
            (lng, lat),
        )
        return filas[0] if filas else None

    async def listar_empresas(self) -> list[dict[str, Any]]:
        return await self._consultar("select id, nombre from empresa where estado = 'activo' order by nombre")
