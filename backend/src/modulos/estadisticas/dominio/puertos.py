"""Puertos de salida del módulo estadísticas."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID


class RepositorioEventosUso(Protocol):
    async def registrar(self, tipo: str, ruta_id: UUID | None) -> None:
        """Inserta un evento anónimo: sin usuario ni coordenadas (RD-17, RNF-01)."""
        ...
