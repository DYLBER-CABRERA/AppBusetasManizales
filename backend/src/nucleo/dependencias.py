"""Dependencias FastAPI de autenticación. La autorización real vive en los casos de uso (recibe Identidad).

Sin credencial en un endpoint protegido → 401; token inválido → 401; rol no permitido → 403; si no, el endpoint
responde con su lógica (o 501 mientras su bloque no exista).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import BackgroundTasks, Query, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from nucleo.autorizacion import Identidad, Rol
from nucleo.errores import ErrorNoAutenticado, ErrorNoAutorizado, ErrorPendiente, ErrorServicioExterno, ErrorValidacion
from nucleo.eventos_uso import TipoEventoUso

esquema_bearer = HTTPBearer(auto_error=False, scheme_name="bearerAuth", bearerFormat="JWT")
esquema_clave_fuente = APIKeyHeader(name="X-Clave-Fuente", auto_error=False, scheme_name="claveFuente")


def _servicios(request: Request) -> Any:
    servicios = request.app.state.contenedor.servicios
    if servicios is None:
        raise ErrorServicioExterno("La base de datos no está configurada (DATABASE_URL).")
    return servicios


async def identidad_opcional(
    request: Request, credenciales: HTTPAuthorizationCredentials | None = Security(esquema_bearer)
) -> Identidad | None:
    """Sin credencial → None (endpoints públicos). Con credencial inválida → 401."""
    if credenciales is None:
        return None
    return await _servicios(request).autenticacion.verificar_token(credenciales.credentials)


def requiere_rol(*roles: Rol, mensaje: str = "Inicia sesión para continuar.") -> Callable[..., object]:
    """Exige sesión y uno de los roles. El filtro por empresa y la autorización fina viven en el caso de uso."""

    async def dependencia(
        request: Request, credenciales: HTTPAuthorizationCredentials | None = Security(esquema_bearer)
    ) -> Identidad:
        if credenciales is None:
            raise ErrorNoAutenticado(mensaje)
        identidad = await _servicios(request).autenticacion.verificar_token(credenciales.credentials)
        if identidad.rol not in roles:
            raise ErrorNoAutorizado("No tienes permiso para esta acción.")
        return identidad

    dependencia.__doc__ = "Roles permitidos: " + ", ".join(r.value for r in roles)
    return dependencia


async def clave_fuente(valor: str | None = Security(esquema_clave_fuente)) -> str:
    if not valor:
        raise ErrorNoAutenticado("Falta la cabecera X-Clave-Fuente.")
    return valor


def pendiente() -> None:
    """Respuesta 501 estándar para endpoints sin lógica todavía."""
    raise ErrorPendiente()


def caso(nombre: str) -> Callable[[Request], Any]:
    """Entrega el caso de uso `nombre` armado en `composicion.py` (los routers no crean nada)."""

    def dependencia(request: Request) -> Any:
        servicios = request.app.state.contenedor.servicios
        if servicios is None:
            raise ErrorServicioExterno("La base de datos no está configurada (DATABASE_URL).")
        return getattr(servicios, nombre)

    dependencia.__name__ = f"caso_{nombre}"
    return dependencia


class RegistroUso:
    """Registra un evento de uso anónimo DESPUÉS de responder (RD-17). Uso: `uso("detalle_ruta", ruta_id)`."""

    def __init__(self, request: Request, tareas: BackgroundTasks) -> None:
        servicios = request.app.state.contenedor.servicios
        self._registrar = servicios.registrar_evento_uso if servicios is not None else None
        self._tareas = tareas

    def __call__(self, tipo: TipoEventoUso, ruta_id: UUID | None = None) -> None:
        if self._registrar is not None:
            self._tareas.add_task(self._registrar, tipo, ruta_id)


async def identidad_de_gestion(
    request: Request, credenciales: HTTPAuthorizationCredentials | None = Security(esquema_bearer),
    empresa_id: UUID | None = Query(default=None, alias="empresaId", description="Solo administrador; el jefe lo ignora"),
) -> Identidad:
    """Endpoints del jefe: el jefe usa SIEMPRE la empresa de su token; el administrador (BR-07) debe indicar `empresaId`
    y actúa como jefe de esa empresa (identidad efectiva)."""
    if credenciales is None:
        raise ErrorNoAutenticado("Inicia sesión para continuar.")
    identidad = await _servicios(request).autenticacion.verificar_token(credenciales.credentials)
    if identidad.rol == Rol.JEFE_OPERACIONES:
        return identidad
    if identidad.rol != Rol.ADMINISTRADOR:
        raise ErrorNoAutorizado("No tienes permiso para esta acción.")
    if empresa_id is None:
        raise ErrorValidacion("Como administrador indica empresaId.")
    return Identidad(identidad.usuario_id, Rol.JEFE_OPERACIONES, str(empresa_id))
