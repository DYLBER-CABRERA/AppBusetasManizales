"""Puertos de salida del módulo estadísticas."""

from __future__ import annotations

from datetime import date
from typing import Any, Protocol
from uuid import UUID


class RepositorioEventosUso(Protocol):
    async def registrar(self, tipo: str, ruta_id: UUID | None) -> None:
        """Inserta un evento anónimo: sin usuario ni coordenadas (RD-17, RNF-01)."""
        ...

    async def estadisticas(self, empresa_id: UUID | None, desde: date, hasta: date) -> dict[str, list[dict[str, Any]]]:
        """{totales_por_tipo, por_ruta, por_dia}. Con `empresa_id`, solo eventos de rutas que opera esa empresa."""
        ...
