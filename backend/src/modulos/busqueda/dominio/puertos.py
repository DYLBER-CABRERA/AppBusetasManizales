"""Puertos de salida del módulo búsqueda (B2)."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

Registro = dict[str, Any]


class RepositorioBusqueda(Protocol):
    async def buscar_rutas(self, patron: str, texto: str) -> list[UUID]:
        """Ids de rutas activas por nombre o código (patrón LIKE ya normalizado y escapado)."""
        ...

    async def buscar_hitos(self, patron: str, texto: str) -> list[Registro]: ...

    async def obtener_hito(self, hito_id: UUID) -> Registro | None: ...

    async def rutas_por_hito(self, hito_id: UUID, radio_m: int) -> dict[UUID, float]:
        """ruta_id -> distancia al hito en metros, de la más cercana a la más lejana."""
        ...


class ProveedorResumenesRuta(Protocol):
    async def resumenes(self, ruta_ids: list[UUID], distancias: dict[UUID, float] | None = None) -> list[Registro]: ...


class ProveedorParaderoCercano(Protocol):
    async def paradero_mas_cercano(self, lat: float, lng: float) -> Registro | None: ...
