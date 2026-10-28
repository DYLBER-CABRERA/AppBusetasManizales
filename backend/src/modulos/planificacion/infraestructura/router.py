"""Router del módulo planificación. B0: 501 PENDIENTE (lógica en B6)."""

from __future__ import annotations

from fastapi import APIRouter

from modulos.planificacion.infraestructura.esquemas import PlanificarEntrada, RespuestaPlanificacion
from nucleo.dependencias import pendiente
from nucleo.esquemas import errores

router = APIRouter(tags=["Planificación"])


@router.post("/viajes/planificar", response_model=RespuestaPlanificacion, responses=errores(400, 404))
async def planificar_viaje(cuerpo: PlanificarEntrada) -> RespuestaPlanificacion:
    pendiente()
