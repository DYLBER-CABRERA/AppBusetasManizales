"""Router del módulo planificación (B6): solo rutas directas (D-P07)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from modulos.planificacion.aplicacion.planificar_viaje import PlanificarViaje
from modulos.planificacion.infraestructura.esquemas import PlanificarEntrada, RespuestaPlanificacion
from nucleo.dependencias import RegistroUso, caso
from nucleo.esquemas import errores

router = APIRouter(tags=["Planificación"])


@router.post("/viajes/planificar", response_model=RespuestaPlanificacion, responses=errores(400, 404))
async def planificar_viaje(
    cuerpo: PlanificarEntrada,
    caso_uso: PlanificarViaje = Depends(caso("planificar_viaje")),
    uso: RegistroUso = Depends(RegistroUso),
) -> dict:
    resultado = await caso_uso(cuerpo.origen.model_dump(), cuerpo.destino.model_dump())
    uso("planificacion")
    return resultado
