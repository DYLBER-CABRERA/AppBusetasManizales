"""Router del módulo operación (J). Solo traduce HTTP; el jefe nunca envía empresaId (sale del token)."""

from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import Field

from modulos.operacion.aplicacion.casos_de_uso import (
    ActualizarRodamiento,
    AnularRodamiento,
    CrearRodamiento,
    GuardarBuseta,
    GuardarConductor,
    ListarBusetas,
    ListarConductores,
    ListarRodamientos,
    ListarServiciosDeMiEmpresa,
    ObtenerRodamiento,
    PublicarRodamiento,
)
from modulos.red import ServicioRuta
from nucleo.autorizacion import Identidad
from nucleo.dependencias import caso, identidad_de_gestion
from nucleo.errores import ErrorValidacion
from nucleo.esquemas import EsquemaBase, errores

router = APIRouter(tags=["Operación"])

_jefe = Depends(identidad_de_gestion)

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


def _fecha(texto: str | None) -> date | None:
    if texto is None:
        return None
    try:
        return date.fromisoformat(texto)
    except ValueError as exc:
        raise ErrorValidacion("La fecha debe tener el formato AAAA-MM-DD.") from exc


def _turnos(entradas: list[TurnoEntrada]) -> list[dict]:
    return [t.model_dump() for t in entradas]


@router.get("/mis-servicios", response_model=list[ServicioRuta], responses=errores(401, 403))
async def listar_servicios_de_mi_empresa(
    identidad: Identidad = _jefe, caso_uso: ListarServiciosDeMiEmpresa = Depends(caso("listar_servicios_de_mi_empresa"))
) -> list[dict]:
    return await caso_uso(identidad)


@router.get("/busetas", response_model=list[Buseta], responses=errores(401, 403))
async def listar_busetas(
    identidad: Identidad = _jefe, caso_uso: ListarBusetas = Depends(caso("listar_busetas"))
) -> list[dict]:
    return await caso_uso(identidad)


@router.post("/busetas", response_model=Buseta, status_code=201, responses=errores(400, 401, 403, 409))
async def guardar_buseta(
    cuerpo: BusetaCrear, identidad: Identidad = _jefe, caso_uso: GuardarBuseta = Depends(caso("guardar_buseta"))
) -> dict:
    return await caso_uso(identidad, cuerpo.numero_lateral, cuerpo.placa)


@router.put("/busetas/{buseta_id}", response_model=Buseta, responses=errores(400, 401, 403, 404, 409))
async def editar_buseta(
    buseta_id: UUID,
    cuerpo: BusetaEditar,
    identidad: Identidad = _jefe,
    caso_uso: GuardarBuseta = Depends(caso("guardar_buseta")),
) -> dict:
    return await caso_uso(
        identidad, cuerpo.numero_lateral or "", cuerpo.placa, buseta_id, cuerpo.version, cuerpo.estado
    )


@router.get("/conductores", response_model=list[Conductor], responses=errores(401, 403))
async def listar_conductores(
    identidad: Identidad = _jefe, caso_uso: ListarConductores = Depends(caso("listar_conductores"))
) -> list[dict]:
    return await caso_uso(identidad)


@router.post("/conductores", response_model=Conductor, status_code=201, responses=errores(400, 401, 403, 409))
async def guardar_conductor(
    cuerpo: ConductorCrear, identidad: Identidad = _jefe, caso_uso: GuardarConductor = Depends(caso("guardar_conductor"))
) -> dict:
    return await caso_uso(identidad, cuerpo.nombre, cuerpo.codigo)


@router.put("/conductores/{conductor_id}", response_model=Conductor, responses=errores(400, 401, 403, 404, 409))
async def editar_conductor(
    conductor_id: UUID,
    cuerpo: ConductorEditar,
    identidad: Identidad = _jefe,
    caso_uso: GuardarConductor = Depends(caso("guardar_conductor")),
) -> dict:
    return await caso_uso(identidad, cuerpo.nombre, cuerpo.codigo, conductor_id, cuerpo.version, cuerpo.estado)


@router.get("/rodamientos", response_model=list[Rodamiento], responses=errores(400, 401, 403))
async def listar_rodamientos(
    desde: str | None = Query(default=None),
    hasta: str | None = Query(default=None),
    identidad: Identidad = _jefe,
    caso_uso: ListarRodamientos = Depends(caso("listar_rodamientos")),
) -> list[dict]:
    return await caso_uso(identidad, _fecha(desde), _fecha(hasta))


@router.post("/rodamientos", response_model=Rodamiento, status_code=201, responses=errores(400, 401, 403, 404, 409))
async def crear_rodamiento(
    cuerpo: RodamientoCrear, identidad: Identidad = _jefe, caso_uso: CrearRodamiento = Depends(caso("crear_rodamiento"))
) -> dict:
    return await caso_uso(identidad, _fecha(cuerpo.fecha), _turnos(cuerpo.turnos))


@router.get("/rodamientos/{rodamiento_id}", response_model=Rodamiento, responses=errores(401, 403, 404))
async def obtener_rodamiento(
    rodamiento_id: UUID, identidad: Identidad = _jefe, caso_uso: ObtenerRodamiento = Depends(caso("obtener_rodamiento"))
) -> dict:
    return await caso_uso(identidad, rodamiento_id)


@router.put("/rodamientos/{rodamiento_id}", response_model=Rodamiento, responses=errores(400, 401, 403, 404, 409))
async def actualizar_rodamiento(
    rodamiento_id: UUID,
    cuerpo: RodamientoActualizar,
    identidad: Identidad = _jefe,
    caso_uso: ActualizarRodamiento = Depends(caso("actualizar_rodamiento")),
) -> dict:
    return await caso_uso(identidad, rodamiento_id, _turnos(cuerpo.turnos), cuerpo.version, cuerpo.confirmar_reemplazo)


@router.post("/rodamientos/{rodamiento_id}/publicar", response_model=Rodamiento, responses=errores(401, 403, 404, 409))
async def publicar_rodamiento(
    rodamiento_id: UUID,
    cuerpo: SoloVersion,
    identidad: Identidad = _jefe,
    caso_uso: PublicarRodamiento = Depends(caso("publicar_rodamiento")),
) -> dict:
    return await caso_uso(identidad, rodamiento_id, cuerpo.version)


@router.post("/rodamientos/{rodamiento_id}/anular", response_model=Rodamiento, responses=errores(401, 403, 404, 409))
async def anular_rodamiento(
    rodamiento_id: UUID,
    cuerpo: SoloVersion,
    identidad: Identidad = _jefe,
    caso_uso: AnularRodamiento = Depends(caso("anular_rodamiento")),
) -> dict:
    return await caso_uso(identidad, rodamiento_id, cuerpo.version)
