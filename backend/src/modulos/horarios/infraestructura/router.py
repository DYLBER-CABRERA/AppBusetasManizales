"""Router del módulo horarios. Consulta pública (B2) implementada; edición del jefe: 501 (B4)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from modulos.horarios.aplicacion.consultas import ConsultarFrecuencias, ConsultarHorarios
from modulos.horarios.aplicacion.edicion import ActualizarFrecuenciasServicio, ActualizarHorariosServicio
from modulos.horarios.infraestructura.esquemas import (
    FrecuenciasActualizar,
    FrecuenciasDeServicio,
    FrecuenciasRuta,
    HorariosActualizar,
    HorariosDeServicio,
    HorariosRuta,
)
from nucleo.autorizacion import Identidad, Rol
from nucleo.dependencias import RegistroUso, caso, requiere_rol
from nucleo.esquemas import errores

router = APIRouter(tags=["Horarios"])

_jefe = requiere_rol(Rol.JEFE_OPERACIONES)


@router.get("/rutas/{ruta_id}/horarios", response_model=HorariosRuta, responses=errores(404))
async def consultar_horarios(
    ruta_id: UUID,
    caso_uso: ConsultarHorarios = Depends(caso("consultar_horarios")),
    uso: RegistroUso = Depends(RegistroUso),
) -> dict:
    resultado = await caso_uso(ruta_id)
    uso("horarios", ruta_id)
    return resultado


@router.get("/rutas/{ruta_id}/frecuencias", response_model=FrecuenciasRuta, responses=errores(404))
async def consultar_frecuencias(
    ruta_id: UUID,
    caso_uso: ConsultarFrecuencias = Depends(caso("consultar_frecuencias")),
    uso: RegistroUso = Depends(RegistroUso),
) -> dict:
    resultado = await caso_uso(ruta_id)
    uso("frecuencias", ruta_id)
    return resultado


@router.put(
    "/servicios/{servicio_id}/horarios", response_model=HorariosDeServicio, responses=errores(400, 401, 403, 404, 409),
)
async def actualizar_horarios_servicio(
    servicio_id: UUID,
    cuerpo: HorariosActualizar,
    identidad: Identidad = Depends(_jefe),
    caso_uso: ActualizarHorariosServicio = Depends(caso("actualizar_horarios_servicio")),
) -> dict:
    return await caso_uso(identidad, servicio_id, [h.model_dump() for h in cuerpo.horarios], cuerpo.version)


@router.put(
    "/servicios/{servicio_id}/frecuencias", response_model=FrecuenciasDeServicio,
    responses=errores(400, 401, 403, 404, 409),
)
async def actualizar_frecuencias_servicio(
    servicio_id: UUID,
    cuerpo: FrecuenciasActualizar,
    identidad: Identidad = Depends(_jefe),
    caso_uso: ActualizarFrecuenciasServicio = Depends(caso("actualizar_frecuencias_servicio")),
) -> dict:
    return await caso_uso(identidad, servicio_id, [f.model_dump() for f in cuerpo.frecuencias], cuerpo.version)
