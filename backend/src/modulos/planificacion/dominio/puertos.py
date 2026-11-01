"""Puertos de salida del módulo planificación (B6)."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID


class RepositorioPlanificacion(Protocol):
    async def rutas_de_paraderos(self, paradero_ids: list[UUID]) -> dict[UUID, set[UUID]]:
        """paradero_id → rutas activas (circulares) que lo incluyen."""
        ...


class ProveedorParaderos(Protocol):
    async def paraderos_cercanos(self, lat: float, lng: float, radio_m: int, ruta_id: UUID | None) -> list[dict[str, Any]]: ...
    async def paradero_mas_cercano(self, lat: float, lng: float) -> dict[str, Any] | None: ...
    async def resumenes(self, ruta_ids: list[UUID], distancias: dict[UUID, float] | None = None) -> list[dict[str, Any]]: ...


class ProveedorHito(Protocol):
    async def obtener_hito(self, hito_id: UUID) -> dict[str, Any] | None: ...


class ProveedorProgreso(Protocol):
    async def progresos_de_ruta(self, ruta_id: UUID) -> list[dict[str, Any]]:
        """Avance secuencial de cada parada de la ruta circular (SQL `progresos_paraderos_ruta`), ordenado por `orden`:
        orden, paradero_id, progreso_m, longitud_m. Un paradero que la ruta visita dos veces aparece dos veces."""
        ...
    async def servicios_para_eta(self, ruta_id: UUID) -> list[dict[str, Any]]: ...


class ProveedorHorarios(Protocol):
    async def horarios_de(self, servicio_ids: list[UUID]) -> list[dict[str, Any]]: ...
    async def frecuencias_de(self, servicio_ids: list[UUID]) -> list[dict[str, Any]]: ...
