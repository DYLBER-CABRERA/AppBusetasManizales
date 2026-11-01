"""Puerto de autenticación: JWT de Supabase Auth → Identidad (docs/03 §1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from nucleo.autorizacion import Identidad


@dataclass(frozen=True)
class SesionAuth:
    """Cuenta de Supabase Auth con sesión válida, exista o no su perfil (registro de pasajeros)."""

    usuario_id: UUID
    correo: str


class PuertoAutenticacion(Protocol):
    async def verificar_sesion(self, jwt: str) -> SesionAuth:
        """Valida el token con Supabase Auth SIN exigir perfil. 401 si es inválido; 503 si Auth no responde."""
        ...

    async def verificar_token(self, jwt: str) -> Identidad:
        """Lanza ErrorNoAutenticado si el token es inválido/expiró o el usuario está inactivo;
        ErrorServicioExterno si Supabase Auth no responde. Nunca registra el token."""
        ...
