"""Repositorio SQL de seguimiento: posiciones, turnos vigentes y datos para el ETA (funciones PostGIS de 0003)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg_pool import AsyncConnectionPool


class RepositorioSeguimientoSql:
    """Implementa RepositorioPosiciones, RepositorioRodamientos y RepositorioEta."""

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def _consultar(self, sql: str, params: Any = None) -> list[dict[str, Any]]:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(sql, params)
            return await cursor.fetchall()

    # ---- RepositorioPosiciones ----

    async def buscar_buseta(self, empresa_id: UUID, numero_lateral: str) -> dict[str, Any] | None:
        filas = await self._consultar(
            "select id, numero_lateral from buseta where empresa_id = %s and numero_lateral = %s and estado <> 'baja'",
            (empresa_id, numero_lateral),
        )
        return filas[0] if filas else None

    async def guardar_posicion(
        self, buseta_id: UUID, servicio_id: UUID | None, lat: float, lng: float,
        velocidad_kmh: float | None, rumbo: float | None, reportada_en: datetime,
    ) -> bool:
        filas = await self._consultar(
            """select guardar_posicion(%s::uuid, %s::uuid, %s::double precision, %s::double precision,
                                       %s::real, %s::real, %s::timestamptz) as guardada""",
            (buseta_id, servicio_id, lat, lng, velocidad_kmh, rumbo, reportada_en),
        )
        return bool(filas[0]["guardada"])

    async def posiciones_de_ruta(self, ruta_id: UUID, ahora: datetime) -> list[dict[str, Any]]:
        return await self._consultar(
            """select b.id as buseta_id, b.numero_lateral, e.nombre as empresa, pb.servicio_ruta_id as servicio_id,
                      st_y(pb.ubicacion::geometry) as lat, st_x(pb.ubicacion::geometry) as lng,
                      pb.velocidad_kmh, pb.rumbo, pb.reportada_en
               from posicion_buseta pb
               join buseta b on b.id = pb.buseta_id
               join empresa e on e.id = b.empresa_id
               join servicio_ruta s on s.id = pb.servicio_ruta_id
               where s.ruta_id = %(ruta)s and s.estado <> 'baja' and b.estado = 'activa'
                 and turno_vigente(b.empresa_id, b.numero_lateral, %(ahora)s) = pb.servicio_ruta_id""",
            {"ruta": ruta_id, "ahora": ahora},
        )

    async def unidades_en_servicio(self, ruta_id: UUID, ahora: datetime) -> int:
        filas = await self._consultar(
            """select count(distinct b.id) as total
               from buseta b
               join servicio_ruta s on s.empresa_id = b.empresa_id and s.ruta_id = %(ruta)s and s.estado <> 'baja'
               where b.estado = 'activa' and turno_vigente(b.empresa_id, b.numero_lateral, %(ahora)s) = s.id""",
            {"ruta": ruta_id, "ahora": ahora},
        )
        return int(filas[0]["total"])

    async def posiciones_para_eta(self, servicio_ids: list[UUID], ruta_id: UUID, ahora: datetime) -> list[dict[str, Any]]:
        if not servicio_ids:
            return []
        return await self._consultar(
            """select pb.servicio_ruta_id as servicio_id, b.numero_lateral, pb.velocidad_kmh, pb.reportada_en, pr.progreso_m
               from posicion_buseta pb
               join buseta b on b.id = pb.buseta_id
               cross join lateral progreso_en_ruta(
                 %(ruta)s::uuid, 'circular', st_y(pb.ubicacion::geometry), st_x(pb.ubicacion::geometry)) pr
               where pb.servicio_ruta_id = any(%(servicios)s) and b.estado = 'activa'
                 and turno_vigente(b.empresa_id, b.numero_lateral, %(ahora)s) = pb.servicio_ruta_id""",
            {"ruta": ruta_id, "servicios": servicio_ids, "ahora": ahora},
        )

    async def limpiar_posiciones(self) -> None:
        async with self._pool.connection() as conexion:
            await conexion.execute("delete from posicion_buseta")

    # ---- RepositorioRodamientos ----

    async def turno_vigente(self, empresa_id: UUID, numero_lateral: str, instante: datetime) -> UUID | None:
        filas = await self._consultar(
            "select turno_vigente(%s::uuid, %s::text, %s::timestamptz) as servicio_id",
            (empresa_id, numero_lateral, instante),
        )
        return filas[0]["servicio_id"]

    async def ruta_de_servicio(self, servicio_id: UUID) -> UUID | None:
        filas = await self._consultar("select ruta_id from servicio_ruta where id = %s", (servicio_id,))
        return filas[0]["ruta_id"] if filas else None

    # ---- RepositorioEta ----

    async def ruta_activa_existe(self, ruta_id: UUID) -> bool:
        return bool(await self._consultar("select 1 from ruta where id = %s and estado = 'activo'", (ruta_id,)))

    async def progreso_paradero(self, ruta_id: UUID, paradero_id: UUID) -> dict[str, Any] | None:
        filas = await self._consultar(
            """select p.progreso_m, p.longitud_m
               from progreso_paradero(%(ruta)s::uuid, 'circular', %(paradero)s::uuid) p
               where exists (select 1 from ruta_paradero rp
                             where rp.ruta_id = %(ruta)s and rp.paradero_id = %(paradero)s and rp.sentido = 'circular')""",
            {"ruta": ruta_id, "paradero": paradero_id},
        )
        return filas[0] if filas else None

    async def servicios_para_eta(self, ruta_id: UUID) -> list[dict[str, Any]]:
        return await self._consultar(
            """select s.id as servicio_id, e.nombre as empresa_nombre, s.codigo_publico, s.estado::text as estado,
                      s.duracion_estandar_min
               from servicio_ruta s join empresa e on e.id = s.empresa_id
               where s.ruta_id = %s and s.estado <> 'baja' order by e.nombre""",
            (ruta_id,),
        )
