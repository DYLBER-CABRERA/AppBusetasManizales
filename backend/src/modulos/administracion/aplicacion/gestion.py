"""Casos de uso de administración (A01 a A04). Solo el rol administrador (BR-07)."""

from __future__ import annotations

import secrets
from typing import Any
from uuid import UUID

from modulos.administracion.dominio.puertos import PuertoAltaUsuarios, RepositorioAdmin
from nucleo.autorizacion import Identidad, Rol, exigir_rol
from nucleo.errores import ErrorConflictoNegocio, ErrorNoEncontrado, ErrorValidacion
from nucleo.version_optimista import verificar_version

PERMISOS_POR_ROL = {
    "pasajero": ["consultar rutas, horarios y mapa", "favoritos y alertas de llegada"],
    "jefe_operaciones": ["asignar buseta y conductor", "armar y publicar el rodamiento",
                         "editar horarios y frecuencias de su empresa", "publicar avisos de su empresa",
                         "ver estadísticas de su empresa"],
    "secretaria_movilidad": ["crear, editar y eliminar rutas y paraderos", "asignar rutas a cada empresa",
                             "registrar cambios de movilidad"],
    "administrador": ["control total", "usuarios, roles y empresas", "parámetros", "claves de fuentes GPS",
                      "avisos del aplicativo", "panel de demo"],
}


def _admin(identidad: Identidad | None) -> Identidad:
    return exigir_rol(identidad, Rol.ADMINISTRADOR)


class _Base:
    def __init__(self, repositorio: RepositorioAdmin) -> None:
        self._repo = repositorio


class ListarRoles:
    async def __call__(self, identidad: Identidad | None) -> list[dict[str, Any]]:
        _admin(identidad)
        return [{"rol": r, "permisos": p} for r, p in PERMISOS_POR_ROL.items()]


class ListarUsuarios(_Base):
    async def __call__(self, identidad: Identidad | None, correo: str | None) -> list[dict[str, Any]]:
        _admin(identidad)
        return await self._repo.listar_usuarios(correo.strip().lower() if correo else None)


def _validar_rol_empresa(rol: str, empresa_id: UUID | None) -> None:
    if rol == "jefe_operaciones" and empresa_id is None:
        raise ErrorValidacion("El jefe de operaciones necesita una empresa.")
    if rol != "jefe_operaciones" and empresa_id is not None:
        raise ErrorValidacion("Solo el jefe de operaciones pertenece a una empresa.")


class CrearUsuario(_Base):
    def __init__(self, repositorio: RepositorioAdmin, altas: PuertoAltaUsuarios) -> None:
        super().__init__(repositorio)
        self._altas = altas

    async def __call__(
        self, identidad: Identidad | None, correo: str, nombre: str | None, rol: str, empresa_id: UUID | None
    ) -> dict[str, Any]:
        _admin(identidad)
        correo = correo.strip().lower()
        if "@" not in correo or correo.startswith("@") or correo.endswith("@"):
            raise ErrorValidacion("El correo no es válido.")
        _validar_rol_empresa(rol, empresa_id)
        if empresa_id is not None and not await self._repo.empresa_activa(empresa_id):
            raise ErrorNoEncontrado("La empresa no existe.")
        if await self._repo.correo_existe(correo):
            raise ErrorConflictoNegocio("Ya existe un usuario con ese correo.")
        usuario_id = await self._altas.crear_usuario(correo, nombre)
        return await self._repo.crear_perfil(usuario_id, correo, nombre, rol, empresa_id)


class EditarUsuario(_Base):
    async def __call__(
        self, identidad: Identidad | None, usuario_id: UUID, cambios: dict[str, Any], version: int
    ) -> dict[str, Any]:
        _admin(identidad)
        actual = await self._repo.obtener_usuario(usuario_id)
        if actual is None:
            raise ErrorNoEncontrado("El usuario no existe.")
        verificar_version(version, actual["version"])
        rol = cambios.get("rol") or actual["rol"]
        empresa = cambios["empresa_id"] if cambios.get("empresa_id") is not None else (
            actual["empresa_id"] if rol == "jefe_operaciones" else None
        )
        _validar_rol_empresa(rol, empresa)
        if empresa is not None and not await self._repo.empresa_activa(empresa):
            raise ErrorNoEncontrado("La empresa no existe.")
        activo = actual["activo"] if cambios.get("activo") is None else cambios["activo"]
        deja_de_ser_admin = actual["rol"] == "administrador" and actual["activo"] and (rol != "administrador" or not activo)
        if deja_de_ser_admin and await self._repo.contar_administradores_activos() <= 1:
            raise ErrorConflictoNegocio("No se puede quitar el rol ni desactivar al último administrador.")
        return await self._repo.editar_usuario(
            usuario_id, version, cambios.get("nombre"), rol, empresa, activo
        )


class ListarEmpresasAdmin(_Base):
    async def __call__(self, identidad: Identidad | None) -> list[dict[str, Any]]:
        _admin(identidad)
        return await self._repo.listar_empresas()


class CrearEmpresa(_Base):
    async def __call__(self, identidad: Identidad | None, nombre: str) -> dict[str, Any]:
        _admin(identidad)
        return await self._repo.crear_empresa(nombre.strip())


class EditarEmpresa(_Base):
    async def __call__(
        self, identidad: Identidad | None, empresa_id: UUID, nombre: str | None, estado: str | None, version: int
    ) -> dict[str, Any]:
        _admin(identidad)
        return await self._repo.editar_empresa(empresa_id, version, nombre.strip() if nombre else None, estado)


class ListarCredencialesGps(_Base):
    async def __call__(self, identidad: Identidad | None, empresa_id: UUID) -> list[dict[str, Any]]:
        _admin(identidad)
        if not await self._repo.empresa_activa(empresa_id):
            raise ErrorNoEncontrado("La empresa no existe.")
        return await self._repo.listar_credenciales(empresa_id)


class CrearCredencialGps(_Base):
    def __init__(self, repositorio: RepositorioAdmin, hashear: Any) -> None:
        super().__init__(repositorio)
        self._hash = hashear

    async def __call__(self, identidad: Identidad | None, empresa_id: UUID, nombre: str) -> dict[str, Any]:
        _admin(identidad)
        if not nombre.strip():
            raise ErrorValidacion("El nombre es obligatorio.")
        if not await self._repo.empresa_activa(empresa_id):
            raise ErrorNoEncontrado("La empresa no existe.")
        clave = secrets.token_urlsafe(32)  # se devuelve UNA vez; en BD solo el hash SHA-256
        credencial = await self._repo.crear_credencial(empresa_id, nombre.strip(), self._hash(clave))
        return {**credencial, "clave": clave}


class RevocarCredencialGps(_Base):
    async def __call__(self, identidad: Identidad | None, credencial_id: UUID) -> None:
        _admin(identidad)
        if not await self._repo.revocar_credencial(credencial_id):
            raise ErrorNoEncontrado("La credencial no existe.")


class ListarParametros(_Base):
    async def __call__(self, identidad: Identidad | None) -> list[dict[str, Any]]:
        _admin(identidad)
        return await self._repo.listar_parametros()


class ConfigurarParametro(_Base):
    async def __call__(self, identidad: Identidad | None, clave: str, valor: Any, version: int) -> dict[str, Any]:
        _admin(identidad)
        actual = await self._repo.obtener_parametro(clave)
        if actual is None:
            raise ErrorNoEncontrado("El parámetro no existe.")
        verificar_version(version, actual["version"])
        if isinstance(actual["valor"], dict):
            if not isinstance(valor, dict) or set(valor) != set(actual["valor"]):
                raise ErrorValidacion("El valor debe ser un objeto con las mismas claves.")
        else:
            if isinstance(valor, bool) or not isinstance(valor, int | float):
                raise ErrorValidacion("El valor debe ser un número.")
            if actual["minimo"] is not None and valor < actual["minimo"]:
                raise ErrorValidacion(f"El valor mínimo permitido es {actual['minimo']:g}.")
            if actual["maximo"] is not None and valor > actual["maximo"]:
                raise ErrorValidacion(f"El valor máximo permitido es {actual['maximo']:g}.")
        return await self._repo.actualizar_parametro(clave, valor, version)

