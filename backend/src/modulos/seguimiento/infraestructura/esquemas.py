"""Esquemas HTTP del módulo seguimiento (contrato §2.1, §2.6, §3)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from nucleo.esquemas import EsquemaBase


class BusetaEnVivo(EsquemaBase):
    buseta_id: UUID
    numero_lateral: str
    empresa: str
    servicio_id: UUID
    estado: Literal["activa", "sin_senal"]
    lat: float
    lng: float
    velocidad_kmh: float | None = None
    rumbo: float | None = None
    reportada_en: datetime
    mensaje: str | None = None


class BusetasEnVivo(EsquemaBase):
    seguimiento_disponible: bool
    unidades_en_servicio: int = Field(ge=0)
    calculado_en: datetime
    busetas: list[BusetaEnVivo]


class RangoEta(EsquemaBase):
    min_segundos: int
    max_segundos: int


class ResultadoEta(EsquemaBase):
    servicio_id: UUID
    empresa: str
    codigo_publico: str | None = None
    fuente: Literal["gps", "horario", "no_disponible"]
    eta_segundos: int | None = Field(default=None, description="Solo con fuente gps")
    rango: RangoEta | None = Field(default=None, description="Solo con fuente horario")
    buseta_numero_lateral: str | None = None
    ultima_senal_hace_s: int | None = None
    mensaje: str | None = None


class RespuestaEta(EsquemaBase):
    paradero_id: UUID
    ruta_id: UUID
    calculado_en: datetime
    resultados: list[ResultadoEta]


class PosicionEntrada(EsquemaBase):
    numero_lateral: str = Field(max_length=20)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    velocidad_kmh: float | None = Field(default=None, ge=0, le=150)
    rumbo: float | None = Field(default=None, ge=0, lt=360)
    reportada_en: datetime = Field(description="No más de 60 s en el futuro")


class LotePosiciones(EsquemaBase):
    posiciones: list[PosicionEntrada] = Field(min_length=1, max_length=100)


class PosicionRechazada(EsquemaBase):
    indice: int
    motivo: Literal[
        "coordenadas_invalidas", "fuera_de_zona", "fecha_futura", "fecha_invalida", "buseta_desconocida"
    ]


class ResultadoIngesta(EsquemaBase):
    aceptadas: int = Field(ge=0)
    descartadas: int = Field(ge=0, description="Posiciones más antiguas que la ya guardada")
    rechazadas: list[PosicionRechazada]
