"""Puertos de salida del módulo red (consulta pública, B2). Los repositorios devuelven dicts en snake_case."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

Registro = dict[str, Any]


class RepositorioRutas(Protocol):
    async def rutas_cercanas(self, lat: float, lng: float, radio_m: int) -> list[Registro]:
        """Rutas activas con servicios; cada dict trae `distancia_m`. Orden: más cercana primero."""
        ...

    async def listar_activas(self) -> list[Registro]: ...

    async def resumenes(self, ruta_ids: list[UUID], distancias: dict[UUID, float] | None = None) -> list[Registro]:
        """Resumen (con servicios) de las rutas activas indicadas, en el mismo orden."""
        ...

    async def obtener_detalle(self, ruta_id: UUID) -> Registro | None:
        """Ruta activa con trazado GeoJSON, paraderos ordenados y servicios; None si no existe o está de baja."""
        ...

    async def paraderos_cercanos(self, lat: float, lng: float, radio_m: int, ruta_id: UUID | None) -> list[Registro]: ...

    async def paradero_mas_cercano(self, lat: float, lng: float) -> Registro | None: ...

    async def listar_empresas(self) -> list[Registro]: ...


class ProveedorAvisosVigentes(Protocol):
    async def vigentes(self, ruta_id: UUID | None, ahora: datetime) -> list[Registro]: ...
