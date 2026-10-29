"""Router del módulo estadísticas (J y A).

La forma de la respuesta no está en docs/03; se toma de docs/referencia/openapi.yaml (EstadisticasUso).
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from modulos.estadisticas.aplicacion.consultar_estadisticas_uso import ConsultarEstadisticasUso
from nucleo.autorizacion import Identidad, Rol
from nucleo.dependencias import caso, requiere_rol
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


@router.get("/estadisticas/uso", response_model=EstadisticasUso, responses=errores(400, 401, 403))
async def consultar_estadisticas_uso(
    desde: date,
    hasta: date,
    empresa_id: UUID | None = Query(default=None, alias="empresaId", description="Solo administrador; el jefe lo ignora"),
    identidad: Identidad = Depends(requiere_rol(Rol.JEFE_OPERACIONES, Rol.ADMINISTRADOR)),
    caso_uso: ConsultarEstadisticasUso = Depends(caso("consultar_estadisticas_uso")),
) -> dict:
    return await caso_uso(identidad, desde, hasta, empresa_id)
