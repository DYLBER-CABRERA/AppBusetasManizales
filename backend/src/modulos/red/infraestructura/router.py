"""Router del módulo red. Solo traduce HTTP. Consulta pública (B2) implementada; gestión de la Secretaría: 501 (B5)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from modulos.red.aplicacion.consultas import (
    ConsultarParaderosCercanos,
    ConsultarRutasCercanas,
    ListarEmpresas,
    ListarRutas,
    ObtenerDetalleRuta,
)
from modulos.red.infraestructura.esquemas import (
    Empresa,
    Hito,
    HitoCrear,
    Paradero,
    ParaderoCercano,
    ParaderoCrear,
    ParaderoEditar,
    RutaCrear,
    RutaDetalle,
    RutaEditar,
    RutaResumen,
    RutasCercanas,
    ServicioAsignar,
    ServicioRuta,
)
from nucleo.autorizacion import Rol
from nucleo.dependencias import RegistroUso, caso, pendiente, requiere_rol
from nucleo.esquemas import errores

router = APIRouter(tags=["Red"])

_gestion = Depends(requiere_rol(Rol.SECRETARIA_MOVILIDAD, Rol.ADMINISTRADOR))


@router.get("/rutas/cercanas", response_model=RutasCercanas, responses=errores(400))
async def consultar_rutas_cercanas(
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
    radio_m: int | None = Query(default=None, alias="radioM", ge=50, le=5000),
    caso_uso: ConsultarRutasCercanas = Depends(caso("consultar_rutas_cercanas")),
    uso: RegistroUso = Depends(RegistroUso),
) -> dict:
    resultado = await caso_uso(lat, lng, radio_m)
    uso("mapa")
    return resultado


@router.get("/rutas", response_model=list[RutaResumen])
async def listar_rutas(
    caso_uso: ListarRutas = Depends(caso("listar_rutas")), uso: RegistroUso = Depends(RegistroUso)
) -> list[dict]:
    resultado = await caso_uso()
    uso("mapa")
    return resultado


@router.get("/rutas/{ruta_id}", response_model=RutaDetalle, responses=errores(404))
async def obtener_detalle_ruta(
    ruta_id: UUID,
    caso_uso: ObtenerDetalleRuta = Depends(caso("obtener_detalle_ruta")),
    uso: RegistroUso = Depends(RegistroUso),
) -> dict:
    resultado = await caso_uso(ruta_id)
    uso("detalle_ruta", ruta_id)
    return resultado


@router.get("/paraderos/cercanos", response_model=list[ParaderoCercano], responses=errores(400))
async def consultar_paraderos_cercanos(
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
    radio_m: int | None = Query(default=None, alias="radioM", ge=50, le=5000),
    ruta_id: UUID | None = Query(default=None, alias="rutaId"),
    caso_uso: ConsultarParaderosCercanos = Depends(caso("consultar_paraderos_cercanos")),
    uso: RegistroUso = Depends(RegistroUso),
) -> list[dict]:
    resultado = await caso_uso(lat, lng, radio_m, ruta_id)
    uso("mapa", ruta_id)
    return resultado


@router.get("/empresas", response_model=list[Empresa])
async def listar_empresas(caso_uso: ListarEmpresas = Depends(caso("listar_empresas"))) -> list[dict]:
    return await caso_uso()


# ---- Secretaría de Movilidad (S) y administrador (A) ----


@router.post(
    "/rutas", response_model=RutaDetalle, status_code=201, dependencies=[_gestion],
    responses=errores(400, 401, 403, 404, 409),
)
async def registrar_ruta(cuerpo: RutaCrear) -> RutaDetalle:
    pendiente()


@router.put(
    "/rutas/{ruta_id}", response_model=RutaDetalle, dependencies=[_gestion],
    responses=errores(400, 401, 403, 404, 409),
)
async def editar_ruta(ruta_id: UUID, cuerpo: RutaEditar) -> RutaDetalle:
    pendiente()


@router.delete(
    "/rutas/{ruta_id}", status_code=204, dependencies=[_gestion],
    responses=errores(401, 403, 404, 409),
)
async def eliminar_ruta(
    ruta_id: UUID, version: int = Query(ge=1), confirmar: bool = False
) -> Response:
    pendiente()


@router.post(
    "/rutas/{ruta_id}/servicios", response_model=ServicioRuta, status_code=201, dependencies=[_gestion],
    responses=errores(400, 401, 403, 404, 409),
)
async def asignar_ruta_a_empresa(ruta_id: UUID, cuerpo: ServicioAsignar) -> ServicioRuta:
    pendiente()


@router.delete(
    "/servicios/{servicio_id}", status_code=204, dependencies=[_gestion],
    responses=errores(401, 403, 404, 409),
)
async def retirar_ruta_de_empresa(
    servicio_id: UUID, version: int = Query(ge=1), confirmar: bool = False
) -> Response:
    pendiente()


@router.get("/paraderos", response_model=list[Paradero], dependencies=[_gestion], responses=errores(401, 403))
async def listar_paraderos() -> list[Paradero]:
    pendiente()


@router.post(
    "/paraderos", response_model=Paradero, status_code=201, dependencies=[_gestion],
    responses=errores(400, 401, 403, 409),
)
async def crear_paradero(cuerpo: ParaderoCrear) -> Paradero:
    pendiente()


@router.put(
    "/paraderos/{paradero_id}", response_model=Paradero, dependencies=[_gestion],
    responses=errores(400, 401, 403, 404, 409),
)
async def editar_paradero(paradero_id: UUID, cuerpo: ParaderoEditar) -> Paradero:
    pendiente()


@router.delete(
    "/paraderos/{paradero_id}", status_code=204, dependencies=[_gestion],
    responses=errores(401, 403, 404, 409),
)
async def eliminar_paradero(
    paradero_id: UUID, version: int = Query(ge=1), confirmar: bool = False
) -> Response:
    pendiente()


@router.post(
    "/hitos", response_model=Hito, status_code=201, dependencies=[_gestion],
    responses=errores(400, 401, 403),
)
async def crear_hito(cuerpo: HitoCrear) -> Hito:
    pendiente()
