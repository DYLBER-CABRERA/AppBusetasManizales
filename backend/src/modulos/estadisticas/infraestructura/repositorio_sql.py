"""Repositorio SQL de eventos de uso (escritura anónima, B2)."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from psycopg_pool import AsyncConnectionPool


class RepositorioEventosUsoSql:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def registrar(self, tipo: str, ruta_id: UUID | None) -> None:
        async with self._pool.connection() as conexion:
            await conexion.execute(
                "insert into evento_uso (tipo, ruta_id) values (%s::tipo_evento_uso, %s)", (tipo, ruta_id)
            )

    async def estadisticas(self, empresa_id: UUID | None, desde: date, hasta: date) -> dict[str, list[dict[str, Any]]]:
        filtro = """e.ocurrido_en >= %(desde)s::date::timestamp at time zone 'America/Bogota'
                    and e.ocurrido_en < (%(hasta)s::date + 1)::timestamp at time zone 'America/Bogota'
                    and (%(empresa)s::uuid is null or e.ruta_id in (
                         select s.ruta_id from servicio_ruta s where s.empresa_id = %(empresa)s::uuid and s.estado <> 'baja'))"""
        params = {"desde": desde, "hasta": hasta, "empresa": empresa_id}
        consultas = {
            "totales_por_tipo": f"select e.tipo::text as tipo, count(*)::int as total from evento_uso e where {filtro} "
                                "group by e.tipo order by total desc",
            "por_ruta": f"select r.id as ruta_id, r.nombre as ruta_nombre, count(*)::int as total from evento_uso e "
                        f"join ruta r on r.id = e.ruta_id where {filtro} group by r.id, r.nombre order by total desc",
            "por_dia": f"select (e.ocurrido_en at time zone 'America/Bogota')::date as dia, count(*)::int as total "
                       f"from evento_uso e where {filtro} group by 1 order by 1",
        }
        resultado: dict[str, list[dict[str, Any]]] = {}
        async with self._pool.connection() as conexion:
            for clave, sql in consultas.items():
                cursor = await conexion.execute(sql, params)
                resultado[clave] = await cursor.fetchall()
        return resultado
