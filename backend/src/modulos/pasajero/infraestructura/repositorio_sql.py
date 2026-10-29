"""Repositorio SQL del pasajero: favoritos, alertas de llegada y progreso sobre el trazado."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg.errors import UniqueViolation
from psycopg_pool import AsyncConnectionPool

from nucleo.errores import ErrorConflictoNegocio

_FAVORITO = """f.id, f.tipo::text as tipo, f.ruta_id, f.paradero_id, coalesce(r.nombre, p.nombre) as nombre,
               coalesce(r.estado = 'activo', p.estado = 'activo', false) as disponible"""
_DESDE_FAVORITO = "from favorito f left join ruta r on r.id = f.ruta_id left join paradero p on p.id = f.paradero_id"
_ALERTA = "id, ruta_id, paradero_id, distancia_aviso_m, estado::text as estado, ultima_notificacion_en, version"


class _Base:

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def _filas(self, sql: str, params: Any = None) -> list[dict[str, Any]]:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(sql, params)
            return await cursor.fetchall()



class RepositorioFavoritosSql(_Base):
    async def listar(self, usuario_id: UUID) -> list[dict[str, Any]]:
        return await self._filas(
            f"select {_FAVORITO} {_DESDE_FAVORITO} where f.usuario_id = %s order by f.creado_en", (usuario_id,)
        )

    async def destino_existe(self, tipo: str, objetivo_id: UUID) -> bool:
        tabla = "ruta" if tipo == "ruta" else "paradero"
        return bool(await self._filas(f"select 1 from {tabla} where id = %s and estado = 'activo'", (objetivo_id,)))

    async def buscar(self, usuario_id: UUID, tipo: str, objetivo_id: UUID) -> dict[str, Any] | None:
        columna = "f.ruta_id" if tipo == "ruta" else "f.paradero_id"
        filas = await self._filas(
            f"select {_FAVORITO} {_DESDE_FAVORITO} where f.usuario_id = %s and {columna} = %s", (usuario_id, objetivo_id)
        )
        return filas[0] if filas else None

    async def crear(self, usuario_id: UUID, tipo: str, objetivo_id: UUID) -> dict[str, Any]:
        ruta, paradero = (objetivo_id, None) if tipo == "ruta" else (None, objetivo_id)
        filas = await self._filas(
            "insert into favorito (usuario_id, tipo, ruta_id, paradero_id) values (%s, %s::tipo_favorito, %s, %s) returning id",
            (usuario_id, tipo, ruta, paradero),
        )
        return (await self._filas(f"select {_FAVORITO} {_DESDE_FAVORITO} where f.id = %s", (filas[0]["id"],)))[0]

    async def eliminar(self, usuario_id: UUID, favorito_id: UUID) -> bool:
        filas = await self._filas(
            "delete from favorito where id = %s and usuario_id = %s returning id", (favorito_id, usuario_id)
        )
        return bool(filas)



class RepositorioAlertasSql(_Base):
    """Implementa RepositorioAlertas y RepositorioProgreso."""

    async def listar(self, usuario_id: UUID) -> list[dict[str, Any]]:
        return await self._filas(
            f"select {_ALERTA} from alerta_llegada where usuario_id = %s and estado <> 'desactivada' order by creada_en",
            (usuario_id,),
        )

    async def paradero_en_ruta_activa(self, ruta_id: UUID, paradero_id: UUID) -> bool:
        return bool(await self._filas(
            """select 1 from ruta_paradero rp join ruta r on r.id = rp.ruta_id join paradero p on p.id = rp.paradero_id
               where rp.ruta_id = %s and rp.paradero_id = %s and r.estado = 'activo' and p.estado = 'activo'""",
            (ruta_id, paradero_id),
        ))

    async def crear(self, usuario_id, telegram_chat_id, ruta_id, paradero_id, distancia_m) -> dict[str, Any]:
        try:
            filas = await self._filas(
                f"""insert into alerta_llegada (usuario_id, telegram_chat_id, ruta_id, paradero_id, sentido, distancia_aviso_m)
                    values (%s, %s, %s, %s, 'circular', %s) returning {_ALERTA}""",
                (usuario_id, telegram_chat_id, ruta_id, paradero_id, distancia_m),
            )
        except UniqueViolation as exc:
            raise ErrorConflictoNegocio("Ya tienes una alerta activa para ese paradero en esa ruta.") from exc
        return filas[0]

    async def desactivar(self, usuario_id: UUID, alerta_id: UUID) -> bool:
        filas = await self._filas(
            """update alerta_llegada set estado = 'desactivada', version = version + 1
               where id = %s and usuario_id = %s and estado <> 'desactivada' returning id""",
            (alerta_id, usuario_id),
        )
        return bool(filas)

    async def activas_de_ruta(self, ruta_id: UUID) -> list[dict[str, Any]]:
        return await self._filas(
            """select id, usuario_id, telegram_chat_id, ruta_id, paradero_id, distancia_aviso_m, ultima_notificacion_en
               from alerta_llegada where ruta_id = %s and estado <> 'desactivada'""",
            (ruta_id,),
        )

    async def marcar_notificada(self, alerta_id: UUID, cuando: datetime) -> None:
        await self._filas(
            "update alerta_llegada set estado = 'notificada', ultima_notificacion_en = %s where id = %s returning id",
            (cuando, alerta_id),
        )

    async def progreso_de_punto(self, ruta_id: UUID, lat: float, lng: float) -> dict[str, Any] | None:
        filas = await self._filas(
            """select progreso_m, desvio_m, longitud_m
               from progreso_en_ruta(%s::uuid, 'circular', %s::float8, %s::float8)""",
            (ruta_id, lat, lng),
        )
        return filas[0] if filas else None

    async def progreso_paradero(self, ruta_id: UUID, paradero_id: UUID) -> dict[str, Any] | None:
        filas = await self._filas(
            """select p.progreso_m, p.longitud_m from progreso_paradero(%(r)s::uuid, 'circular', %(p)s::uuid) p
               where exists (select 1 from ruta_paradero rp
                             where rp.ruta_id = %(r)s and rp.paradero_id = %(p)s and rp.sentido = 'circular')""",
            {"r": ruta_id, "p": paradero_id},
        )
        return filas[0] if filas else None
