"""Escritura SQL de la red (paraderos, hitos, rutas y servicios). Transacciones por operación."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.errors import UniqueViolation
from psycopg_pool import AsyncConnectionPool

from nucleo.errores import ErrorConflictoNegocio, ErrorConflictoVersion, ErrorNoEncontrado

_PARADERO = """id, nombre, direccion, st_y(ubicacion::geometry) as lat, st_x(ubicacion::geometry) as lng,
               estado::text as estado, version"""
_SERVICIO = """s.id, s.ruta_id, r.nombre as ruta_nombre, s.empresa_id, e.nombre as empresa_nombre, s.codigo_publico,
               s.codigo_interno, s.duracion_estandar_min, s.estado::text as estado, s.version"""
_DUPLICADO_CODIGO = "El código público ya lo usa otro servicio de esa empresa."


def _wkt_circuito(coordenadas: list[tuple[float, float]]) -> str:
    """Línea que une los paraderos en orden y vuelve al primero (circuito, D-P02). `coordenadas` son (lat, lng)."""
    puntos = [*coordenadas, coordenadas[0]]
    return "SRID=4326;LINESTRING(" + ", ".join(f"{lng:.7f} {lat:.7f}" for lat, lng in puntos) + ")"


async def _uno(conexion: AsyncConnection[Any], sql: str, params: Any = None) -> dict[str, Any] | None:
    cursor = await conexion.execute(sql, params)
    return await cursor.fetchone()


async def _coordenadas(conexion: AsyncConnection[Any], paradero_ids: list[UUID]) -> list[tuple[float, float]]:
    cursor = await conexion.execute(
        """select u.pid, st_y(p.ubicacion::geometry) as lat, st_x(p.ubicacion::geometry) as lng
           from unnest(%s::uuid[]) with ordinality as u(pid, ord) join paradero p on p.id = u.pid order by u.ord""",
        (paradero_ids,),
    )
    return [(f["lat"], f["lng"]) for f in await cursor.fetchall()]


class RepositorioGestionRedSql:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def _filas(self, sql: str, params: Any = None) -> list[dict[str, Any]]:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(sql, params)
            return await cursor.fetchall()

    async def _fallo_version(self, tabla: str, filtro: str, params: tuple[Any, ...]) -> Exception:
        filas = await self._filas(f"select version from {tabla} where {filtro}", params)  # tabla fija
        return ErrorConflictoVersion(filas[0]["version"]) if filas else ErrorNoEncontrado("El recurso no existe.")

    # ---- paraderos y hitos ----
    async def listar_paraderos(self) -> list[dict[str, Any]]:
        return await self._filas(f"select {_PARADERO} from paradero where estado = 'activo' order by nombre")

    async def obtener_paradero(self, paradero_id: UUID) -> dict[str, Any] | None:
        filas = await self._filas(f"select {_PARADERO} from paradero where id = %s and estado = 'activo'", (paradero_id,))
        return filas[0] if filas else None

    async def hay_paradero_duplicado(self, nombre: str, lat: float, lng: float, excluir_id: UUID | None) -> bool:
        filas = await self._filas(
            """select 1 from paradero
               where estado = 'activo' and normalizar_texto(nombre) = normalizar_texto(%s)
                 and st_dwithin(ubicacion, st_setsrid(st_makepoint(%s::float8, %s::float8), 4326)::geography, 20)
                 and (%s::uuid is null or id <> %s::uuid)""",
            (nombre, lng, lat, excluir_id, excluir_id),
        )
        return bool(filas)

    async def crear_paradero(self, nombre: str, direccion: str | None, lat: float, lng: float) -> dict[str, Any]:
        filas = await self._filas(
            f"""insert into paradero (nombre, direccion, ubicacion)
                values (%s, %s, st_setsrid(st_makepoint(%s::float8, %s::float8), 4326)::geography) returning {_PARADERO}""",
            (nombre, direccion, lng, lat),
        )
        return filas[0]

    async def editar_paradero(self, paradero_id, version, nombre, direccion, lat, lng) -> dict[str, Any]:
        filas = await self._filas(
            f"""update paradero set nombre = %s, direccion = coalesce(%s, direccion),
                       ubicacion = st_setsrid(st_makepoint(%s::float8, %s::float8), 4326)::geography, version = version + 1
                where id = %s and version = %s and estado = 'activo' returning {_PARADERO}""",
            (nombre, direccion, lng, lat, paradero_id, version),
        )
        if not filas:
            raise await self._fallo_version("paradero", "id = %s", (paradero_id,))
        return filas[0]

    async def rutas_que_usan_paradero(self, paradero_id: UUID) -> list[dict[str, Any]]:
        return await self._filas(
            """select distinct r.id::text as "rutaId", r.nombre from ruta_paradero rp join ruta r on r.id = rp.ruta_id
               where rp.paradero_id = %s and r.estado = 'activo' order by r.nombre""",
            (paradero_id,),
        )

    async def dar_de_baja_paradero(self, paradero_id: UUID, version: int) -> None:
        filas = await self._filas(
            "update paradero set estado = 'baja', version = version + 1 where id = %s and version = %s returning id",
            (paradero_id, version),
        )
        if not filas:
            raise await self._fallo_version("paradero", "id = %s", (paradero_id,))

    async def crear_hito(self, nombre: str, tipo: str, alias: list[str], lat: float, lng: float) -> dict[str, Any]:
        filas = await self._filas(
            """insert into hito (nombre, tipo, alias, ubicacion)
               values (%s, %s::tipo_hito, %s, st_setsrid(st_makepoint(%s::float8, %s::float8), 4326)::geography)
               returning id, nombre, tipo::text as tipo, alias,
                         st_y(ubicacion::geometry) as lat, st_x(ubicacion::geometry) as lng""",
            (nombre, tipo, alias, lng, lat),
        )
        return filas[0]

    # ---- rutas ----
    async def paraderos_activos_existen(self, paradero_ids: list[UUID]) -> bool:
        filas = await self._filas("select count(*) as n from paradero where id = any(%s) and estado = 'activo'", (paradero_ids,))
        return filas[0]["n"] == len(set(paradero_ids))

    async def empresas_activas_existen(self, empresa_ids: list[UUID]) -> bool:
        filas = await self._filas("select count(*) as n from empresa where id = any(%s) and estado = 'activo'", (empresa_ids,))
        return filas[0]["n"] == len(set(empresa_ids))

    async def ruta_principal_valida(self, ruta_id: UUID) -> bool:
        return bool(await self._filas(
            "select 1 from ruta where id = %s and estado = 'activo' and ruta_principal_id is null", (ruta_id,)
        ))

    async def crear_ruta(self, nombre, ruta_principal_id, paradero_ids, servicios) -> UUID:
        try:
            async with self._pool.connection() as conexion:
                ruta = await _uno(
                    conexion,
                    "insert into ruta (nombre, tipo_recorrido, ruta_principal_id) values (%s, 'circular', %s) returning id",
                    (nombre, ruta_principal_id),
                )
                ruta_id = ruta["id"]
                coordenadas = await _coordenadas(conexion, paradero_ids)
                await conexion.execute(
                    "insert into ruta_trazado (ruta_id, sentido, trazado) values (%s, 'circular', st_geogfromtext(%s))",
                    (ruta_id, _wkt_circuito(coordenadas)),
                )
                await conexion.execute(
                    "select reemplazar_paraderos_de_ruta(%s::uuid, 'circular', %s::uuid[])", (ruta_id, paradero_ids)
                )
                for s in servicios:
                    await conexion.execute(
                        "insert into servicio_ruta (ruta_id, empresa_id, codigo_publico, codigo_interno) values (%s, %s, %s, %s)",
                        (ruta_id, s["empresa_id"], s.get("codigo_publico"), s.get("codigo_interno")),
                    )
                return ruta_id
        except UniqueViolation as exc:
            raise ErrorConflictoNegocio(_DUPLICADO_CODIGO) from exc

    async def editar_ruta(self, ruta_id, version, nombre, descripcion, paradero_ids) -> None:
        async with self._pool.connection() as conexion:
            fila = await _uno(
                conexion,
                """update ruta set nombre = coalesce(%s, nombre), descripcion = coalesce(%s, descripcion), version = version + 1
                   where id = %s and version = %s and estado = 'activo' returning id""",
                (nombre, descripcion, ruta_id, version),
            )
            if fila is None:
                raise await self._fallo_version("ruta", "id = %s", (ruta_id,))
            if paradero_ids is not None:
                coordenadas = await _coordenadas(conexion, paradero_ids)
                await conexion.execute(
                    "update ruta_trazado set trazado = st_geogfromtext(%s) where ruta_id = %s and sentido = 'circular'",
                    (_wkt_circuito(coordenadas), ruta_id),
                )
                await conexion.execute(
                    "select reemplazar_paraderos_de_ruta(%s::uuid, 'circular', %s::uuid[])", (ruta_id, paradero_ids)
                )

    async def turnos_futuros_de_ruta(self, ruta_id: UUID, desde: date) -> list[dict[str, Any]]:
        return await self._filas(
            """select t.id::text as "turnoId", to_char(r.fecha, 'YYYY-MM-DD') as fecha,
                      to_char(t.hora_salida, 'HH24:MI') as "horaSalida", b.numero_lateral as buseta
               from turno t join rodamiento r on r.id = t.rodamiento_id
               join servicio_ruta s on s.id = t.servicio_ruta_id join buseta b on b.id = t.buseta_id
               where s.ruta_id = %s and r.fecha >= %s and r.estado <> 'anulado' and t.estado = 'programado'
               order by r.fecha, t.hora_salida limit 50""",
            (ruta_id, desde),
        )

    async def dar_de_baja_ruta(self, ruta_id: UUID, version: int) -> None:
        filas = await self._filas("select dar_de_baja_ruta(%s::uuid, %s::integer) as ok", (ruta_id, version))
        if not filas[0]["ok"]:
            raise await self._fallo_version("ruta", "id = %s", (ruta_id,))

    # ---- servicios ----
    async def ruta_activa_existe(self, ruta_id: UUID) -> bool:
        return bool(await self._filas("select 1 from ruta where id = %s and estado = 'activo'", (ruta_id,)))

    async def empresa_opera_ruta(self, ruta_id: UUID, empresa_id: UUID) -> bool:
        return bool(await self._filas(
            "select 1 from servicio_ruta where ruta_id = %s and empresa_id = %s and estado <> 'baja'", (ruta_id, empresa_id)
        ))

    async def empresas_que_operan_ruta(self, ruta_id: UUID) -> list[UUID]:
        filas = await self._filas(
            "select empresa_id from servicio_ruta where ruta_id = %s and estado <> 'baja'", (ruta_id,)
        )
        return [f["empresa_id"] for f in filas]

    async def asignar_servicio(self, ruta_id, empresa_id, codigo_publico, codigo_interno) -> dict[str, Any]:
        try:
            filas = await self._filas(
                """insert into servicio_ruta (ruta_id, empresa_id, codigo_publico, codigo_interno) values (%s, %s, %s, %s)
                   returning id""",
                (ruta_id, empresa_id, codigo_publico, codigo_interno),
            )
        except UniqueViolation as exc:
            raise ErrorConflictoNegocio(_DUPLICADO_CODIGO) from exc
        return (await self._servicio(filas[0]["id"]))  # type: ignore[return-value]

    async def _servicio(self, servicio_id: UUID) -> dict[str, Any] | None:
        filas = await self._filas(
            f"""select {_SERVICIO} from servicio_ruta s join ruta r on r.id = s.ruta_id join empresa e on e.id = s.empresa_id
                where s.id = %s and s.estado <> 'baja'""",
            (servicio_id,),
        )
        return filas[0] if filas else None

    async def obtener_servicio(self, servicio_id: UUID) -> dict[str, Any] | None:
        return await self._servicio(servicio_id)

    async def turnos_futuros_de_servicio(self, servicio_id: UUID, desde: date) -> list[dict[str, Any]]:
        return await self._filas(
            """select t.id::text as "turnoId", to_char(r.fecha, 'YYYY-MM-DD') as fecha,
                      to_char(t.hora_salida, 'HH24:MI') as "horaSalida", b.numero_lateral as buseta
               from turno t join rodamiento r on r.id = t.rodamiento_id join buseta b on b.id = t.buseta_id
               where t.servicio_ruta_id = %s and r.fecha >= %s and r.estado <> 'anulado' and t.estado = 'programado'
               order by r.fecha, t.hora_salida limit 50""",
            (servicio_id, desde),
        )

    async def retirar_servicio(self, servicio_id: UUID, version: int, hoy: date) -> None:
        async with self._pool.connection() as conexion:
            fila = await _uno(
                conexion,
                "update servicio_ruta set estado = 'baja', version = version + 1 where id = %s and version = %s returning id",
                (servicio_id, version),
            )
            if fila is None:
                raise await self._fallo_version("servicio_ruta", "id = %s", (servicio_id,))
            await conexion.execute(
                """update turno set estado = 'cancelado'
                   where servicio_ruta_id = %s and estado = 'programado'
                     and rodamiento_id in (select id from rodamiento where fecha >= %s and estado <> 'anulado')""",
                (servicio_id, hoy),
            )
