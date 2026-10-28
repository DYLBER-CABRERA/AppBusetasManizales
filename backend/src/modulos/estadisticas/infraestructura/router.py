"""Router del módulo estadísticas (J y A). B0: 501 PENDIENTE (lógica en B5).

La forma de la respuesta no está en docs/03; se toma de docs/referencia/openapi.yaml (EstadisticasUso).
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from nucleo.autorizacion import Rol
from nucleo.dependencias import pendiente, requiere_rol
from nucleo.esquemas import EsquemaBase, errores

router = APIRouter(tags=["Estadísticas"])


class TotalPorTipo(EsquemaBase):
    tipo: str
    total: int


class TotalPorRuta(EsquemaBase):
    ruta_id: UUID
    ruta_nombre: str
    total: int


class TotalPorDia(EsquemaBase):
    dia: date
    total: int


class EstadisticasUso(EsquemaBase):
    sin_datos: bool
    totales_por_tipo: list[TotalPorTipo] = []
    por_ruta: list[TotalPorRuta] = []
    por_dia: list[TotalPorDia] = []


@router.get(
    "/estadisticas/uso", response_model=EstadisticasUso,
    dependencies=[Depends(requiere_rol(Rol.JEFE_OPERACIONES, Rol.ADMINISTRADOR))],
    responses=errores(400, 401, 403),
)
async def consultar_estadisticas_uso(
    desde: date,
    hasta: date,
    empresa_id: UUID | None = Query(default=None, alias="empresaId", description="Solo administrador; el jefe lo ignora"),
) -> EstadisticasUso:
    pendiente()
