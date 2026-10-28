"""Esquemas HTTP del módulo horarios (contrato §2.1, §2.3)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field

from nucleo.esquemas import EsquemaBase

TipoDia = Literal["lun_vie", "sabado", "dom_festivo"]
PATRON_HORA = r"^([01][0-9]|2[0-3]):[0-5][0-9]$"
PATRON_FIN_FRANJA = r"^(([01][0-9]|2[0-3]):[0-5][0-9]|24:00)$"


class Horario(EsquemaBase):
    tipo_dia: TipoDia
    primera_salida: str = Field(pattern=PATRON_HORA, examples=["05:30"])
    ultima_salida: str = Field(pattern=PATRON_HORA)
    cierre: str | None = Field(default=None, pattern=PATRON_HORA)
    nota: str | None = None


class HorariosDeServicio(EsquemaBase):
    servicio_id: UUID
    empresa_id: UUID
    empresa_nombre: str
    codigo_publico: str | None = None
    estado: Literal["completo", "parcial", "pendiente_actualizacion"]
    horarios: list[Horario]
    tipos_dia_pendientes: list[TipoDia]
    version: int


class HorariosRuta(EsquemaBase):
    tipo_dia_hoy: TipoDia
    servicios: list[HorariosDeServicio]


class HorariosActualizar(EsquemaBase):
    horarios: list[Horario] = Field(max_length=3)
    version: int = Field(ge=1)


class Frecuencia(EsquemaBase):
    tipo_dia: TipoDia
    franja_inicio: str = Field(pattern=PATRON_HORA)
    franja_fin: str = Field(pattern=PATRON_FIN_FRANJA, examples=["09:00"])
    minutos_min: int = Field(ge=1)
    minutos_max: int = Field(ge=1)
    nota: str | None = None


class FrecuenciasDeServicio(EsquemaBase):
    servicio_id: UUID
    empresa_id: UUID
    empresa_nombre: str
    frecuencias: list[Frecuencia]
    version: int


class FrecuenciasRuta(EsquemaBase):
    servicios: list[FrecuenciasDeServicio]


class FrecuenciasActualizar(EsquemaBase):
    frecuencias: list[Frecuencia]
    version: int = Field(ge=1)
