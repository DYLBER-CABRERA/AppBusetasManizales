"""Esquemas HTTP del módulo red (contrato: docs/03-contrato-api.md §2.1, §2.4)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field

from nucleo.esquemas import EsquemaBase

TipoHito = Literal["hito", "barrio", "sector", "universidad", "hospital", "terminal", "otro"]


class ServicioResumen(EsquemaBase):
    servicio_id: UUID
    empresa_id: UUID
    empresa_nombre: str
    codigo_publico: str | None = None


class RutaResumen(EsquemaBase):
    id: UUID
    nombre: str
    tipo_recorrido: Literal["circular"] = "circular"
    es_variante: bool = False
    distancia_m: float | None = None
    servicios: list[ServicioResumen]


class ParaderoCercano(EsquemaBase):
    paradero_id: UUID
    nombre: str
    lat: float
    lng: float
    distancia_m: float


class RutasCercanas(EsquemaBase):
    rutas: list[RutaResumen]
    paradero_mas_cercano: ParaderoCercano | None = None


class GeoJsonLineString(EsquemaBase):
    type: Literal["LineString"] = "LineString"
    coordinates: list[list[float]] = Field(min_length=2, description="[lng, lat]")


class ParadaEnRuta(EsquemaBase):
    orden: int = Field(ge=1)
    paradero_id: UUID
    nombre: str
    lat: float
    lng: float


class AvisoVigente(EsquemaBase):
    id: UUID
    origen: Literal["empresa", "movilidad", "aplicativo"]
    empresa_nombre: str | None = None
    titulo: str
    cuerpo: str


class RutaDetalle(RutaResumen):
    descripcion: str | None = None
    ruta_principal_id: UUID | None = None
    longitud_m: float | None = None
    trazado: GeoJsonLineString
    paraderos: list[ParadaEnRuta]
    avisos: list[AvisoVigente] = []
    version: int


class ServicioCrearEntrada(EsquemaBase):
    empresa_id: UUID
    codigo_publico: str | None = Field(default=None, pattern=r"^[0-9]+$", max_length=6)
    codigo_interno: str | None = Field(default=None, max_length=20)


class RutaCrear(EsquemaBase):
    nombre: str = Field(min_length=2, max_length=120)
    tipo_recorrido: Literal["circular"] = "circular"
    ruta_principal_id: UUID | None = None
    paradero_ids: list[UUID] = Field(min_length=2, description="Paraderos en orden de recorrido")
    servicios: list[ServicioCrearEntrada] = Field(min_length=1)
    confirmar_compartida: bool = False


class RutaEditar(EsquemaBase):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    descripcion: str | None = None
    paradero_ids: list[UUID] | None = None
    version: int = Field(ge=1)


class ServicioRuta(EsquemaBase):
    id: UUID
    ruta_id: UUID
    ruta_nombre: str | None = None
    empresa_id: UUID
    empresa_nombre: str | None = None
    codigo_publico: str | None = None
    codigo_interno: str | None = None
    duracion_estandar_min: int | None = None
    estado: Literal["activo", "suspendido", "baja"]
    version: int


class ServicioAsignar(EsquemaBase):
    empresa_id: UUID
    codigo_publico: str | None = Field(default=None, pattern=r"^[0-9]+$", max_length=6)
    codigo_interno: str | None = Field(default=None, max_length=20)
    confirmar_compartida: bool = False


class Paradero(EsquemaBase):
    id: UUID
    nombre: str
    direccion: str | None = None
    lat: float
    lng: float
    estado: Literal["activo", "baja"]
    version: int


class ParaderoCrear(EsquemaBase):
    nombre: str = Field(min_length=2, max_length=120)
    direccion: str | None = None
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class ParaderoEditar(EsquemaBase):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    direccion: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    version: int = Field(ge=1)


class Hito(EsquemaBase):
    id: UUID
    nombre: str
    tipo: TipoHito
    alias: list[str] = []
    lat: float
    lng: float


class HitoCrear(EsquemaBase):
    nombre: str = Field(min_length=2, max_length=120)
    tipo: TipoHito = "hito"
    alias: list[str] = []
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class Empresa(EsquemaBase):
    id: UUID
    nombre: str
