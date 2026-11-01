"""Esquemas HTTP del módulo planificación (contrato §3, D-P07: solo rutas directas)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from modulos.red import ParaderoCercano
from nucleo.esquemas import EsquemaBase


class Lugar(EsquemaBase):
    """Exactamente una forma: coordenadas (lat y lng) o hitoId. Texto libre queda fuera (D-P06)."""

    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    hito_id: UUID | None = None

    @model_validator(mode="after")
    def _una_forma(self) -> Lugar:
        por_punto = self.lat is not None and self.lng is not None
        parcial = (self.lat is None) != (self.lng is None)
        if parcial or por_punto == (self.hito_id is not None):
            raise ValueError("Indica coordenadas (lat y lng) o hitoId, solo una de las dos formas.")
        return self


class PlanificarEntrada(EsquemaBase):
    origen: Lugar
    destino: Lugar


class OpcionViaje(EsquemaBase):
    tipo: Literal["directa"] = "directa"
    ruta_id: UUID
    servicio_id: UUID
    paradero_origen: ParaderoCercano
    paradero_destino: ParaderoCercano
    caminata_min: float
    espera_min: float
    bus_min: float
    total_min: float


MotivoCodigo = Literal["sin_paraderos_origen", "sin_paraderos_destino", "sin_ruta_directa", "sin_servicio_en_horario"]


class AlternativaCercana(EsquemaBase):
    """Ruta que pasa cerca del origen o del destino, con su paradero más cercano a ese punto (sugerencia de alternativa)."""

    lado: Literal["origen", "destino"]
    ruta_id: UUID
    ruta_nombre: str
    paradero: ParaderoCercano


class RespuestaPlanificacion(EsquemaBase):
    opciones: list[OpcionViaje]
    motivo: str | None = None
    paradero_mas_cercano: ParaderoCercano | None = None
    motivo_codigo: MotivoCodigo | None = Field(default=None, description="Solo sin opciones; distingue el motivo")
    alternativas: list[AlternativaCercana] = Field(
        default_factory=list, description="Solo con motivoCodigo `sin_ruta_directa`: rutas que pasan junto al origen y al destino"
    )
