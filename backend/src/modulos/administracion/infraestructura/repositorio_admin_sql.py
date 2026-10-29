"""Repositorio SQL de administración: usuarios (perfiles), empresas, credenciales GPS y parámetros."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from nucleo.errores import ErrorConflictoNegocio, ErrorConflictoVersion, ErrorNoEncontrado

_USUARIO = "id, correo, nombre, rol::text as rol, empresa_id, activo, version"


class RepositorioAdminSql:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def _filas(self, sql: str, params: Any = None) -> list[dict[str, Any]]:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(sql, params)
            return await cursor.fetchall()

    async def _fallo_version(self, tabla: str, filtro: str, params: tuple[Any, ...]) -> Exception:
        filas = await self._filas(f"select version from {tabla} where {filtro}", params)  # tabla fija, no viene del usuario
        return ErrorConflictoVersion(filas[0]["version"]) if filas else ErrorNoEncontrado("El recurso no existe.")

    # ---- usuarios ----
    async def listar_usuarios(self, correo: str | None) -> list[dict[str, Any]]:
        return await self._filas(
            f"""select {_USUARIO} from perfil_usuario
                where %s::text is null or lower(correo) like '%%' || %s || '%%' order by correo""",
            (correo, correo),
        )

    async def obtener_usuario(self, usuario_id: UUID) -> dict[str, Any] | None:
        filas = await self._filas(f"select {_USUARIO} from perfil_usuario where id = %s", (usuario_id,))
        return filas[0] if filas else None

    async def correo_existe(self, correo: str) -> bool:
        return bool(await self._filas("select 1 from perfil_usuario where lower(correo) = %s", (correo,)))

    async def crear_perfil(self, usuario_id, correo, nombre, rol, empresa_id) -> dict[str, Any]:
        filas = await self._filas(
            f"""insert into perfil_usuario (id, correo, nombre, rol, empresa_id) values (%s, %s, %s, %s::rol_usuario, %s)
                returning {_USUARIO}""",
            (usuario_id, correo, nombre, rol, empresa_id),
        )
        return filas[0]

    async def editar_usuario(self, usuario_id, version, nombre, rol, empresa_id, activo) -> dict[str, Any]:
        filas = await self._filas(
            f"""update perfil_usuario set nombre = coalesce(%s, nombre), rol = %s::rol_usuario, empresa_id = %s,
                       activo = %s, version = version + 1
                where id = %s and version = %s returning {_USUARIO}""",
            (nombre, rol, empresa_id, activo, usuario_id, version),
        )
        if not filas:
            raise await self._fallo_version("perfil_usuario", "id = %s", (usuario_id,))
        return filas[0]

    async def contar_administradores_activos(self) -> int:
        filas = await self._filas("select count(*) as n from perfil_usuario where rol = 'administrador' and activo")
        return int(filas[0]["n"])

    # ---- empresas ----
    async def empresa_activa(self, empresa_id: UUID) -> bool:
        return bool(await self._filas("select 1 from empresa where id = %s and estado = 'activo'", (empresa_id,)))

    async def listar_empresas(self) -> list[dict[str, Any]]:
        return await self._filas("select id, nombre, estado::text as estado, version from empresa order by nombre")

    async def crear_empresa(self, nombre: str) -> dict[str, Any]:
        try:
            filas = await self._filas(
                "insert into empresa (nombre) values (%s) returning id, nombre, estado::text as estado, version", (nombre,)
            )
        except UniqueViolation as exc:
            raise ErrorConflictoNegocio("Ya existe una empresa con ese nombre.") from exc
        return filas[0]

    async def editar_empresa(self, empresa_id, version, nombre, estado) -> dict[str, Any]:
        try:
            filas = await self._filas(
                """update empresa set nombre = coalesce(%s, nombre), estado = coalesce(%s::estado_registro, estado),
                          version = version + 1
                   where id = %s and version = %s returning id, nombre, estado::text as estado, version""",
                (nombre, estado, empresa_id, version),
            )
        except UniqueViolation as exc:
            raise ErrorConflictoNegocio("Ya existe una empresa con ese nombre.") from exc
        if not filas:
            raise await self._fallo_version("empresa", "id = %s", (empresa_id,))
        return filas[0]

    # ---- credenciales GPS ----
    async def listar_credenciales(self, empresa_id: UUID) -> list[dict[str, Any]]:
        return await self._filas(
            "select id, nombre, activa, creada_en, ultimo_uso from credencial_fuente_gps "
            "where empresa_id = %s order by creada_en",
            (empresa_id,),
        )

    async def crear_credencial(self, empresa_id: UUID, nombre: str, hash_clave: str) -> dict[str, Any]:
        filas = await self._filas(
            """insert into credencial_fuente_gps (empresa_id, nombre, hash_clave) values (%s, %s, %s)
               returning id, nombre, activa, creada_en, ultimo_uso""",
            (empresa_id, nombre, hash_clave),
        )
        return filas[0]

    async def revocar_credencial(self, credencial_id: UUID) -> bool:
        filas = await self._filas("update credencial_fuente_gps set activa = false where id = %s returning id", (credencial_id,))
        return bool(filas)

    # ---- parámetros ----
    async def listar_parametros(self) -> list[dict[str, Any]]:
        return await self._filas(
            "select clave, valor, descripcion, minimo::float8 as minimo, maximo::float8 as maximo, version "
            "from parametro_global order by clave"
        )

    async def obtener_parametro(self, clave: str) -> dict[str, Any] | None:
        filas = await self._filas(
            "select clave, valor, descripcion, minimo::float8 as minimo, maximo::float8 as maximo, version "
            "from parametro_global where clave = %s",
            (clave,),
        )
        return filas[0] if filas else None

    async def actualizar_parametro(self, clave: str, valor: Any, version: int) -> dict[str, Any]:
        filas = await self._filas(
            """update parametro_global set valor = %s, version = version + 1 where clave = %s and version = %s
               returning clave, valor, descripcion, minimo::float8 as minimo, maximo::float8 as maximo, version""",
            (Jsonb(valor), clave, version),
        )
        if not filas:
            raise await self._fallo_version("parametro_global", "clave = %s", (clave,))
        return filas[0]
