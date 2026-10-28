"""Dependencias FastAPI de autenticación. La autorización real vive en los casos de uso (recibe Identidad).

B0: el contrato queda declarado (esquemas de seguridad en OpenAPI). Sin credencial en un endpoint protegido
se responde 401; con credencial, la verificación del JWT es PENDIENTE (B4/B5) y el endpoint responde 501.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from nucleo.autorizacion import Identidad, Rol
from nucleo.errores import ErrorNoAutenticado, ErrorPendiente

esquema_bearer = HTTPBearer(auto_error=False, scheme_name="bearerAuth", bearerFormat="JWT")
esquema_clave_fuente = APIKeyHeader(name="X-Clave-Fuente", auto_error=False, scheme_name="claveFuente")


async def identidad_opcional(
    credenciales: HTTPAuthorizationCredentials | None = Security(esquema_bearer),
) -> Identidad | None:
    if credenciales is None:
        return None
    # PENDIENTE(B4): PuertoAutenticacion.verificar_token(jwt) -> Identidad (JWT de Supabase Auth).
    raise ErrorPendiente("PENDIENTE: la verificación del JWT se implementa en B4.")


def requiere_rol(*roles: Rol) -> Callable[..., object]:
    """Exige sesión. El filtro por rol y empresa se aplica en el caso de uso (CLAUDE.md §11)."""

    async def dependencia(
        credenciales: HTTPAuthorizationCredentials | None = Security(esquema_bearer),
        _identidad: Identidad | None = Depends(identidad_opcional),
    ) -> Identidad:
        if credenciales is None:
            raise ErrorNoAutenticado("Inicia sesión para continuar.")
        raise ErrorPendiente("PENDIENTE: la verificación del JWT se implementa en B4.")

    dependencia.__doc__ = "Roles permitidos: " + ", ".join(r.value for r in roles)
    return dependencia


async def clave_fuente(valor: str | None = Security(esquema_clave_fuente)) -> str:
    if not valor:
        raise ErrorNoAutenticado("Falta la cabecera X-Clave-Fuente.")
    return valor


def pendiente() -> None:
    """Respuesta 501 estándar para endpoints sin lógica todavía."""
    raise ErrorPendiente()
