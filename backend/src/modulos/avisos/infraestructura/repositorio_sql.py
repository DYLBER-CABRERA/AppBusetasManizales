"""Repositorio SQL de avisos (lectura, B2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg_pool import AsyncConnectionPool

from modulos.avisos.dominio.politica import DefinicionAviso

_VIGENTES = """
select a.id, a.origen::text as origen, a.empresa_id, e.nombre as empresa_nombre, a.tipo_cambio, a.titulo, a.cuerpo,
       a.desde, a.hasta,
       coalesce((select array_agg(distinct f.ruta_id) from aviso_afecta f
                 where f.aviso_id = a.id and f.ruta_id is not null), '{}') as ruta_ids,
       coalesce((select array_agg(distinct f.paradero_id) from aviso_afecta f
                 where f.aviso_id = a.id and f.paradero_id is not null), '{}') as paradero_ids
from aviso a
left join empresa e on e.id = a.empresa_id
where a.estado = 'activo' and a.desde <= %(ahora)s and (a.hasta is null or a.hasta > %(ahora)s)
  and (%(ruta_id)s::uuid is null or exists (
        select 1 from aviso_afecta f
        where f.aviso_id = a.id
          and (f.ruta_id = %(ruta_id)s::uuid
               or f.paradero_id in (select rp.paradero_id from ruta_paradero rp where rp.ruta_id = %(ruta_id)s::uuid))))
order by a.desde desc, a.id
"""


_POR_ID = _VIGENTES.split("from aviso a", 1)[0] + """from aviso a
left join empresa e on e.id = a.empresa_id
where a.id = %(id)s"""


class RepositorioAvisosSql:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def vigentes(self, ruta_id: UUID | None, ahora: datetime) -> list[dict[str, Any]]:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(_VIGENTES, {"ahora": ahora, "ruta_id": ruta_id})
            return await cursor.fetchall()

    # ---- publicación y retiro (B4) ----

    async def _filas(self, sql: str, params: Any) -> list[dict[str, Any]]:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(sql, params)
            return await cursor.fetchall()

    async def rutas_de_empresa(self, empresa_id: UUID) -> set[UUID]:
        filas = await self._filas(
            """select distinct s.ruta_id from servicio_ruta s join ruta r on r.id = s.ruta_id
               where s.empresa_id = %s and s.estado <> 'baja' and r.estado = 'activo'""",
            (empresa_id,),
        )
        return {f["ruta_id"] for f in filas}

    async def existen_destinos(self, ruta_ids: list[UUID], paradero_ids: list[UUID]) -> bool:
        filas = await self._filas(
            """select (select count(*) from ruta where id = any(%s) and estado = 'activo') as rutas,
                      (select count(*) from paradero where id = any(%s) and estado = 'activo') as paraderos""",
            (ruta_ids, paradero_ids),
        )
        return filas[0]["rutas"] == len(set(ruta_ids)) and filas[0]["paraderos"] == len(set(paradero_ids))

    async def crear(
        self, definicion: DefinicionAviso, autor_id: UUID, titulo: str, cuerpo: str, desde: datetime, hasta: datetime | None,
        ruta_ids: list[UUID], paradero_ids: list[UUID],
    ) -> dict[str, Any]:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(
                """insert into aviso (origen, empresa_id, tipo_cambio, titulo, cuerpo, desde, hasta, autor_id)
                   values (%s::origen_aviso, %s, %s, %s, %s, %s, %s, %s) returning id""",
                (definicion.origen, definicion.empresa_id, definicion.tipo_cambio, titulo, cuerpo, desde, hasta, autor_id),
            )
            aviso_id = (await cursor.fetchone())["id"]
            for ruta_id in dict.fromkeys(ruta_ids):
                await conexion.execute("insert into aviso_afecta (aviso_id, ruta_id) values (%s, %s)", (aviso_id, ruta_id))
            for paradero_id in dict.fromkeys(paradero_ids):
                await conexion.execute(
                    "insert into aviso_afecta (aviso_id, paradero_id) values (%s, %s)", (aviso_id, paradero_id)
                )
            cursor = await conexion.execute(_POR_ID, {"id": aviso_id})
            return await cursor.fetchone()

    async def obtener_activo(self, aviso_id: UUID) -> dict[str, Any] | None:
        filas = await self._filas(
            "select origen::text as origen, empresa_id from aviso where id = %s and estado = 'activo'", (aviso_id,)
        )
        return filas[0] if filas else None

    async def retirar(self, aviso_id: UUID) -> None:
        async with self._pool.connection() as conexion:
            await conexion.execute("update aviso set estado = 'retirado' where id = %s", (aviso_id,))
