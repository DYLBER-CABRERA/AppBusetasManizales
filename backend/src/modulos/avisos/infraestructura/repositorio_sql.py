"""Repositorio SQL de avisos (lectura, B2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg_pool import AsyncConnectionPool

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


class RepositorioAvisosSql:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def vigentes(self, ruta_id: UUID | None, ahora: datetime) -> list[dict[str, Any]]:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(_VIGENTES, {"ahora": ahora, "ruta_id": ruta_id})
            return await cursor.fetchall()
