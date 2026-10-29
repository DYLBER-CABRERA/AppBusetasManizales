"""Repositorio SQL del módulo operación (busetas, conductores, rodamientos y turnos de UNA empresa)."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.errors import UniqueViolation
from psycopg_pool import AsyncConnectionPool

from modulos.operacion.dominio.validador_rodamiento import TurnoDato
from nucleo.errores import ErrorConflictoNegocio, ErrorConflictoVersion, ErrorNoEncontrado


async def _fallo_de_version(conexion: AsyncConnection[Any], tabla: str, filtro: str, params: tuple[Any, ...]) -> Exception:
    """Distingue 404 de 409 cuando un `update … where version = %s` no afectó filas."""
    cursor = await conexion.execute(f"select version from {tabla} where {filtro}", params)  # noqa: S608 - tabla fija
    fila = await cursor.fetchone()
    return ErrorConflictoVersion(fila["version"]) if fila else ErrorNoEncontrado("El recurso no existe.")


class RepositorioOperacionSql:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def _consultar(self, sql: str, params: Any = None) -> list[dict[str, Any]]:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(sql, params)
            return await cursor.fetchall()

    async def servicios_de_empresa(self, empresa_id: UUID) -> list[dict[str, Any]]:
        return await self._consultar(
            """select s.id, s.ruta_id, r.nombre as ruta_nombre, s.empresa_id, e.nombre as empresa_nombre, s.codigo_publico,
                      s.codigo_interno, s.duracion_estandar_min, s.estado::text as estado, s.version
               from servicio_ruta s join ruta r on r.id = s.ruta_id join empresa e on e.id = s.empresa_id
               where s.empresa_id = %s and s.estado <> 'baja' and r.estado = 'activo' order by r.nombre""",
            (empresa_id,),
        )

    # ---- busetas ----

    async def listar_busetas(self, empresa_id: UUID) -> list[dict[str, Any]]:
        return await self._consultar(
            """select id, numero_lateral, placa, estado::text as estado, version
               from buseta where empresa_id = %s and estado <> 'baja' order by numero_lateral""",
            (empresa_id,),
        )

    async def crear_buseta(self, empresa_id: UUID, numero_lateral: str, placa: str | None) -> dict[str, Any]:
        try:
            filas = await self._consultar(
                """insert into buseta (empresa_id, numero_lateral, placa) values (%s, %s, %s)
                   returning id, numero_lateral, placa, estado::text as estado, version""",
                (empresa_id, numero_lateral, placa),
            )
        except UniqueViolation as exc:
            raise ErrorConflictoNegocio("Ya existe una buseta con ese número lateral en tu empresa.") from exc
        return filas[0]

    async def editar_buseta(self, empresa_id: UUID, buseta_id: UUID, version: int, cambios: dict[str, Any]) -> dict[str, Any]:
        try:
            async with self._pool.connection() as conexion:
                cursor = await conexion.execute(
                    """update buseta set numero_lateral = coalesce(%s, numero_lateral), placa = coalesce(%s, placa),
                              estado = coalesce(%s::estado_buseta, estado), version = version + 1
                       where id = %s and empresa_id = %s and version = %s
                       returning id, numero_lateral, placa, estado::text as estado, version""",
                    (cambios["numero_lateral"], cambios["placa"], cambios["estado"], buseta_id, empresa_id, version),
                )
                fila = await cursor.fetchone()
                if fila is None:
                    raise await _fallo_de_version(conexion, "buseta", "id = %s and empresa_id = %s", (buseta_id, empresa_id))
                return fila
        except UniqueViolation as exc:
            raise ErrorConflictoNegocio("Ya existe una buseta con ese número lateral en tu empresa.") from exc

    # ---- conductores ----

    async def listar_conductores(self, empresa_id: UUID) -> list[dict[str, Any]]:
        return await self._consultar(
            """select id, nombre, codigo, estado::text as estado, version
               from conductor where empresa_id = %s and estado <> 'baja' order by nombre""",
            (empresa_id,),
        )

    async def crear_conductor(self, empresa_id: UUID, nombre: str, codigo: str | None) -> dict[str, Any]:
        try:
            filas = await self._consultar(
                """insert into conductor (empresa_id, nombre, codigo) values (%s, %s, %s)
                   returning id, nombre, codigo, estado::text as estado, version""",
                (empresa_id, nombre, codigo),
            )
        except UniqueViolation as exc:
            raise ErrorConflictoNegocio("Ya existe un conductor con ese código en tu empresa.") from exc
        return filas[0]

    async def editar_conductor(
        self, empresa_id: UUID, conductor_id: UUID, version: int, cambios: dict[str, Any]
    ) -> dict[str, Any]:
        try:
            async with self._pool.connection() as conexion:
                cursor = await conexion.execute(
                    """update conductor set nombre = coalesce(%s, nombre), codigo = coalesce(%s, codigo),
                              estado = coalesce(%s::estado_registro, estado), version = version + 1
                       where id = %s and empresa_id = %s and version = %s
                       returning id, nombre, codigo, estado::text as estado, version""",
                    (cambios["nombre"], cambios["codigo"], cambios["estado"], conductor_id, empresa_id, version),
                )
                fila = await cursor.fetchone()
                if fila is None:
                    filtro = "id = %s and empresa_id = %s"
                    raise await _fallo_de_version(conexion, "conductor", filtro, (conductor_id, empresa_id))
                return fila
        except UniqueViolation as exc:
            raise ErrorConflictoNegocio("Ya existe un conductor con ese código en tu empresa.") from exc

    # ---- rodamientos ----

    async def recursos_de_empresa(self, empresa_id: UUID) -> dict[str, Any]:
        servicios = await self._consultar(
            "select id, duracion_estandar_min from servicio_ruta where empresa_id = %s and estado <> 'baja'", (empresa_id,)
        )
        busetas = await self._consultar("select id, numero_lateral from buseta where empresa_id = %s", (empresa_id,))
        conductores = await self._consultar("select id, nombre from conductor where empresa_id = %s", (empresa_id,))
        return {
            "servicios": {s["id"]: s["duracion_estandar_min"] for s in servicios},
            "busetas": {b["id"]: b["numero_lateral"] for b in busetas},
            "conductores": {c["id"]: c["nombre"] for c in conductores},
        }

    async def _turnos_de(self, rodamiento_ids: list[UUID]) -> dict[UUID, list[dict[str, Any]]]:
        por_rodamiento: dict[UUID, list[dict[str, Any]]] = {i: [] for i in rodamiento_ids}
        if not rodamiento_ids:
            return por_rodamiento
        filas = await self._consultar(
            """select id, rodamiento_id, servicio_ruta_id, buseta_id, conductor_id, hora_salida, hora_fin_estimada,
                      estado::text as estado
               from turno where rodamiento_id = any(%s) order by hora_salida, id""",
            (rodamiento_ids,),
        )
        for f in filas:
            dato = TurnoDato(
                f["servicio_ruta_id"], f["buseta_id"], f["conductor_id"], f["hora_salida"], f["hora_fin_estimada"], f["id"]
            )
            por_rodamiento[f["rodamiento_id"]].append({"datos": dato, "estado": f["estado"]})
        return por_rodamiento

    async def _con_turnos(self, cabeceras: list[dict[str, Any]]) -> list[dict[str, Any]]:
        turnos = await self._turnos_de([c["rodamiento_id"] for c in cabeceras])
        return [{**c, "turnos": turnos[c["rodamiento_id"]]} for c in cabeceras]

    async def listar_rodamientos(self, empresa_id: UUID, desde: date | None, hasta: date | None) -> list[dict[str, Any]]:
        cabeceras = await self._consultar(
            """select id as rodamiento_id, fecha, estado::text as estado, version from rodamiento
               where empresa_id = %s and (%s::date is null or fecha >= %s::date) and (%s::date is null or fecha <= %s::date)
               order by fecha desc""",
            (empresa_id, desde, desde, hasta, hasta),
        )
        return await self._con_turnos(cabeceras)

    async def obtener_rodamiento(self, empresa_id: UUID, rodamiento_id: UUID) -> dict[str, Any] | None:
        cabeceras = await self._consultar(
            """select id as rodamiento_id, fecha, estado::text as estado, version
               from rodamiento where id = %s and empresa_id = %s""",
            (rodamiento_id, empresa_id),
        )
        return (await self._con_turnos(cabeceras))[0] if cabeceras else None

    async def rodamiento_de_fecha(self, empresa_id: UUID, fecha: date) -> dict[str, Any] | None:
        filas = await self._consultar(
            "select id as rodamiento_id from rodamiento where empresa_id = %s and fecha = %s and estado <> 'anulado'",
            (empresa_id, fecha),
        )
        return filas[0] if filas else None

    @staticmethod
    async def _insertar_turnos(conexion: AsyncConnection[Any], rodamiento_id: UUID, turnos: list[TurnoDato]) -> None:
        for t in turnos:
            await conexion.execute(
                """insert into turno (rodamiento_id, servicio_ruta_id, buseta_id, conductor_id, hora_salida, hora_fin_estimada)
                   values (%s, %s, %s, %s, %s, %s)""",
                (rodamiento_id, t.servicio_id, t.buseta_id, t.conductor_id, t.hora_salida, t.hora_fin_estimada),
            )

    async def crear_rodamiento(self, empresa_id: UUID, fecha: date, turnos: list[TurnoDato]) -> UUID:
        try:
            async with self._pool.connection() as conexion:
                cursor = await conexion.execute(
                    "insert into rodamiento (empresa_id, fecha) values (%s, %s) returning id", (empresa_id, fecha)
                )
                rodamiento_id = (await cursor.fetchone())["id"]
                await self._insertar_turnos(conexion, rodamiento_id, turnos)
                return rodamiento_id
        except UniqueViolation as exc:
            raise ErrorConflictoNegocio("Tu empresa ya tiene un rodamiento para esa fecha.") from exc

    async def reemplazar_turnos(self, rodamiento_id: UUID, version: int, turnos: list[TurnoDato]) -> int:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(
                "update rodamiento set version = version + 1 where id = %s and version = %s returning version",
                (rodamiento_id, version),
            )
            fila = await cursor.fetchone()
            if fila is None:
                raise await _fallo_de_version(conexion, "rodamiento", "id = %s", (rodamiento_id,))
            await conexion.execute("delete from turno where rodamiento_id = %s", (rodamiento_id,))
            await self._insertar_turnos(conexion, rodamiento_id, turnos)
            return fila["version"]

    async def cambiar_estado(self, rodamiento_id: UUID, version: int, estado: str, usuario_id: UUID) -> int:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(
                """update rodamiento set estado = %s::estado_rodamiento, version = version + 1,
                          publicado_por = case when %s = 'publicado' then %s else publicado_por end,
                          publicado_en = case when %s = 'publicado' then now() else publicado_en end
                   where id = %s and version = %s returning version""",
                (estado, estado, usuario_id, estado, rodamiento_id, version),
            )
            fila = await cursor.fetchone()
            if fila is None:
                raise await _fallo_de_version(conexion, "rodamiento", "id = %s", (rodamiento_id,))
            return fila["version"]
