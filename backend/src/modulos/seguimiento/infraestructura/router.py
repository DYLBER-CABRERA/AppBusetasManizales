"""Router del módulo seguimiento. B0: 501 PENDIENTE (lógica en B3)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from modulos.seguimiento.infraestructura.esquemas import (
    BusetasEnVivo,
    LotePosiciones,
    RespuestaEta,
    ResultadoIngesta,
)
from nucleo.dependencias import clave_fuente, pendiente
from nucleo.esquemas import errores

router = APIRouter(tags=["Seguimiento"])


@router.get("/rutas/{ruta_id}/busetas", response_model=BusetasEnVivo, responses=errores(404))
async def consultar_busetas_en_vivo(ruta_id: UUID) -> BusetasEnVivo:
    pendiente()


@router.get("/paraderos/{paradero_id}/eta", response_model=RespuestaEta, responses=errores(400, 404))
async def calcular_eta_paradero(
    paradero_id: UUID,
    ruta_id: UUID = Query(alias="rutaId"),
    servicio_id: UUID | None = Query(default=None, alias="servicioId"),
) -> RespuestaEta:
    pendiente()


@router.post(
    "/ingesta/posiciones", response_model=ResultadoIngesta, status_code=202,
    dependencies=[Depends(clave_fuente)], responses=errores(400, 401),
)
async def registrar_posiciones(cuerpo: LotePosiciones) -> ResultadoIngesta:
    pendiente()
