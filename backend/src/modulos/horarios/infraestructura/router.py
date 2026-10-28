"""Router del módulo horarios. B0: 501 PENDIENTE."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from modulos.horarios.infraestructura.esquemas import (
    FrecuenciasActualizar,
    FrecuenciasDeServicio,
    FrecuenciasRuta,
    HorariosActualizar,
    HorariosDeServicio,
    HorariosRuta,
)
from nucleo.autorizacion import Rol
from nucleo.dependencias import pendiente, requiere_rol
from nucleo.esquemas import errores

router = APIRouter(tags=["Horarios"])

_jefe = Depends(requiere_rol(Rol.JEFE_OPERACIONES))


@router.get("/rutas/{ruta_id}/horarios", response_model=HorariosRuta, responses=errores(404))
async def consultar_horarios(ruta_id: UUID) -> HorariosRuta:
    pendiente()


@router.get("/rutas/{ruta_id}/frecuencias", response_model=FrecuenciasRuta, responses=errores(404))
async def consultar_frecuencias(ruta_id: UUID) -> FrecuenciasRuta:
    pendiente()


@router.put(
    "/servicios/{servicio_id}/horarios", response_model=HorariosDeServicio, dependencies=[_jefe],
    responses=errores(400, 401, 403, 404, 409),
)
async def actualizar_horarios_servicio(servicio_id: UUID, cuerpo: HorariosActualizar) -> HorariosDeServicio:
    pendiente()


@router.put(
    "/servicios/{servicio_id}/frecuencias", response_model=FrecuenciasDeServicio, dependencies=[_jefe],
    responses=errores(400, 401, 403, 404, 409),
)
async def actualizar_frecuencias_servicio(
    servicio_id: UUID, cuerpo: FrecuenciasActualizar
) -> FrecuenciasDeServicio:
    pendiente()
