"""Router del módulo búsqueda. B0: 501 PENDIENTE (lógica en B2)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from modulos.red import Hito, ParaderoCercano, RutaResumen
from nucleo.dependencias import pendiente
from nucleo.esquemas import EsquemaBase, errores

router = APIRouter(tags=["Búsqueda"])


class RutasDeHito(EsquemaBase):
    cobertura: bool
    rutas: list[RutaResumen]
    paradero_mas_cercano: ParaderoCercano | None = None


@router.get("/busqueda/rutas", response_model=list[RutaResumen], responses=errores(400))
async def buscar_rutas_por_texto(q: str = Query(min_length=1, max_length=60)) -> list[RutaResumen]:
    pendiente()


@router.get("/busqueda/hitos", response_model=list[Hito], responses=errores(400))
async def buscar_hitos(q: str = Query(min_length=1, max_length=60)) -> list[Hito]:
    pendiente()


@router.get("/hitos/{hito_id}/rutas", response_model=RutasDeHito, responses=errores(404))
async def consultar_rutas_por_hito(hito_id: UUID) -> RutasDeHito:
    pendiente()
