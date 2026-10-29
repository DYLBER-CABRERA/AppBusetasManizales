"""Puertos de salida del módulo seguimiento (B3)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Protocol
from uuid import UUID

Registro = dict[str, Any]


class RepositorioPosiciones(Protocol):
    async def buscar_buseta(self, empresa_id: UUID, numero_lateral: str) -> Registro | None:
        """Buseta no dada de baja de la empresa: id, numero_lateral."""
        ...

    async def guardar_posicion(
        self, buseta_id: UUID, servicio_id: UUID | None, lat: float, lng: float,
        velocidad_kmh: float | None, rumbo: float | None, reportada_en: datetime,
    ) -> bool:
        """True si se guardó; False si era más antigua que la almacenada."""
        ...

    async def posiciones_de_ruta(self, ruta_id: UUID, ahora: datetime) -> list[Registro]:
        """Busetas con turno vigente en la ruta: buseta_id, numero_lateral, empresa, servicio_id, lat, lng,
        velocidad_kmh, rumbo, reportada_en."""
        ...

    async def unidades_en_servicio(self, ruta_id: UUID, ahora: datetime) -> int: ...

    async def posiciones_para_eta(self, servicio_ids: list[UUID], ruta_id: UUID, ahora: datetime) -> list[Registro]:
        """Posiciones de busetas con turno vigente en esos servicios, con `progreso_m` sobre la ruta."""
        ...

    async def limpiar_posiciones(self) -> None:
        """Solo para el demo (reloj simulado hacia atrás / reinicio)."""
        ...


class RepositorioRodamientos(Protocol):
    async def turno_vigente(self, empresa_id: UUID, numero_lateral: str, instante: datetime) -> UUID | None:
        """servicio_ruta_id del turno publicado que contiene el instante (SQL `turno_vigente`)."""
        ...

    async def ruta_de_servicio(self, servicio_id: UUID) -> UUID | None: ...


class RepositorioEta(Protocol):
    async def ruta_activa_existe(self, ruta_id: UUID) -> bool: ...

    async def progreso_paradero(self, ruta_id: UUID, paradero_id: UUID) -> Registro | None:
        """progreso_m y longitud_m del paradero en la ruta circular; None si el paradero no pertenece a la ruta."""
        ...

    async def servicios_para_eta(self, ruta_id: UUID) -> list[Registro]:
        """Servicios no dados de baja: servicio_id, empresa_nombre, codigo_publico, estado, duracion_estandar_min."""
        ...


class ProveedorHorarios(Protocol):
    async def horarios_de(self, servicio_ids: list[UUID]) -> list[Registro]: ...

    async def frecuencias_de(self, servicio_ids: list[UUID]) -> list[Registro]: ...


class ProveedorTipoDia(Protocol):
    def para_instante(self, instante: datetime) -> str: ...

    def para_fecha(self, fecha: date) -> str: ...


class RepositorioFuentesGps(Protocol):
    async def empresa_por_hash(self, hash_clave: str) -> Registro | None:
        """Credencial activa: credencial_id, empresa_id; None si no existe o está revocada."""
        ...

    async def marcar_uso(self, credencial_id: UUID, ahora: datetime) -> None: ...
