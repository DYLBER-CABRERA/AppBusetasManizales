"""Puerto de autenticación: JWT de Supabase Auth → Identidad (docs/03 §1)."""

from __future__ import annotations

from typing import Protocol

from nucleo.autorizacion import Identidad


class PuertoAutenticacion(Protocol):
    async def verificar_token(self, jwt: str) -> Identidad:
        """Lanza ErrorNoAutenticado si el token es inválido/expiró o el usuario está inactivo;
        ErrorServicioExterno si Supabase Auth no responde. Nunca registra el token."""
        ...
