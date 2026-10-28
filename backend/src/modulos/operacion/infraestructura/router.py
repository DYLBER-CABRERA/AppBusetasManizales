"""Router del módulo operación (J). B0: 501 PENDIENTE (lógica en B4). El jefe nunca envía empresaId."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import Field

from modulos.red import ServicioRuta
from nucleo.autorizacion import Rol
from nucleo.dependencias import pendiente, requiere_rol
from nucleo.esquemas import EsquemaBase, errores

router = APIRouter(tags=["Operación"], dependencies=[Depends(requiere_rol(Rol.JEFE_OPERACIONES))])

PATRON_HORA = r"^([01][0-9]|2[0-3]):[0-5][0-9]$"


class Buseta(EsquemaBase):
    id: UUID
    numero_lateral: str
    placa: str | None = None
    estado: Literal["activa", "fuera_servicio", "baja"]
    version: int


class BusetaCrear(EsquemaBase):
    numero_lateral: str = Field(min_length=1, max_length=20)
    placa: str | None = Field(default=None, max_length=10)


class BusetaEditar(EsquemaBase):
    numero_lateral: str | None = Field(default=None, min_length=1, max_length=20)
    placa: str | None = Field(default=None, max_length=10)
    estado: Literal["activa", "fuera_servicio", "baja"] | None = None
    version: int = Field(ge=1)


class Conductor(EsquemaBase):
    id: UUID
    nombre: str
    codigo: str | None = None
    estado: Literal["activo", "baja"]
    version: int


class ConductorCrear(EsquemaBase):
    nombre: str = Field(min_length=2, max_length=120)
    codigo: str | None = Field(default=None, max_length=20)


class ConductorEditar(EsquemaBase):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    codigo: str | None = Field(default=None, max_length=20)
    estado: Literal["activo", "baja"] | None = None
    version: int = Field(ge=1)


class TurnoEntrada(EsquemaBase):
    servicio_id: UUID
    buseta_id: UUID
    conductor_id: UUID | None = None
    hora_salida: str = Field(pattern=PATRON_HORA)
    hora_fin_estimada: str | None = Field(default=None, pattern=PATRON_HORA)


class Turno(TurnoEntrada):
    id: UUID | None = None
    numero_lateral: str | None = None
    estado: Literal["programado", "cancelado"] = "programado"


class Advertencia(EsquemaBase):
    codigo: Literal["solapamiento_buseta", "solapamiento_conductor"]
    mensaje: str
    turno_ids: list[UUID]


class Rodamiento(EsquemaBase):
    rodamiento_id: UUID
    fecha: str = Field(description="AAAA-MM-DD")
    estado: Literal["borrador", "publicado", "anulado"]
    version: int
    turnos: list[Turno]
    advertencias: list[Advertencia] = []


class RodamientoCrear(EsquemaBase):
    fecha: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    turnos: list[TurnoEntrada] = Field(min_length=1, max_length=2000)


class RodamientoActualizar(EsquemaBase):
    turnos: list[TurnoEntrada] = Field(min_length=1, max_length=2000)
    version: int = Field(ge=1)
    confirmar_reemplazo: bool = False


class SoloVersion(EsquemaBase):
    version: int = Field(ge=1)


@router.get("/mis-servicios", response_model=list[ServicioRuta], responses=errores(401, 403))
async def listar_servicios_de_mi_empresa() -> list[ServicioRuta]:
    pendiente()


@router.get("/busetas", response_model=list[Buseta], responses=errores(401, 403))
async def listar_busetas() -> list[Buseta]:
    pendiente()


@router.post("/busetas", response_model=Buseta, status_code=201, responses=errores(400, 401, 403, 409))
async def guardar_buseta(cuerpo: BusetaCrear) -> Buseta:
    pendiente()


@router.put("/busetas/{buseta_id}", response_model=Buseta, responses=errores(400, 401, 403, 404, 409))
async def editar_buseta(buseta_id: UUID, cuerpo: BusetaEditar) -> Buseta:
    pendiente()


@router.get("/conductores", response_model=list[Conductor], responses=errores(401, 403))
async def listar_conductores() -> list[Conductor]:
    pendiente()


@router.post(
    "/conductores", response_model=Conductor, status_code=201, responses=errores(400, 401, 403, 409)
)
async def guardar_conductor(cuerpo: ConductorCrear) -> Conductor:
    pendiente()


@router.put(
    "/conductores/{conductor_id}", response_model=Conductor, responses=errores(400, 401, 403, 404, 409)
)
async def editar_conductor(conductor_id: UUID, cuerpo: ConductorEditar) -> Conductor:
    pendiente()


@router.get("/rodamientos", response_model=list[Rodamiento], responses=errores(401, 403))
async def listar_rodamientos(
    desde: str | None = Query(default=None), hasta: str | None = Query(default=None)
) -> list[Rodamiento]:
    pendiente()


@router.post(
    "/rodamientos", response_model=Rodamiento, status_code=201, responses=errores(400, 401, 403, 409)
)
async def crear_rodamiento(cuerpo: RodamientoCrear) -> Rodamiento:
    pendiente()


@router.get("/rodamientos/{rodamiento_id}", response_model=Rodamiento, responses=errores(401, 403, 404))
async def obtener_rodamiento(rodamiento_id: UUID) -> Rodamiento:
    pendiente()


@router.put(
    "/rodamientos/{rodamiento_id}", response_model=Rodamiento, responses=errores(400, 401, 403, 404, 409)
)
async def actualizar_rodamiento(rodamiento_id: UUID, cuerpo: RodamientoActualizar) -> Rodamiento:
    pendiente()


@router.post(
    "/rodamientos/{rodamiento_id}/publicar", response_model=Rodamiento, responses=errores(401, 403, 404, 409)
)
async def publicar_rodamiento(rodamiento_id: UUID, cuerpo: SoloVersion) -> Rodamiento:
    pendiente()


@router.post(
    "/rodamientos/{rodamiento_id}/anular", response_model=Rodamiento, responses=errores(401, 403, 404, 409)
)
async def anular_rodamiento(rodamiento_id: UUID, cuerpo: SoloVersion) -> Rodamiento:
    pendiente()
