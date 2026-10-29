"""Puertos de salida del módulo administración (B3b: perfil, autenticación y demo)."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID


class RepositorioUsuarios(Protocol):
    async def perfil(self, usuario_id: UUID) -> dict[str, Any] | None:
        """usuario_id, correo, rol, empresa_id, empresa_nombre, activo; None si no hay perfil."""
        ...


class PuertoSimulador(Protocol):
    """Lo que el panel de demo necesita del simulador de GPS (herramientas/simulador_gps.py)."""

    async def aplicar(self, escenario: dict[str, Any]) -> None: ...

    def estado(self) -> dict[str, Any]: ...
