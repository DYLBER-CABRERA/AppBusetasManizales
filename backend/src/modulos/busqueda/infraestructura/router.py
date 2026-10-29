"""Router del módulo búsqueda (B2)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from modulos.busqueda.aplicacion.consultas import BuscarHitos, BuscarRutasPorTexto, ConsultarRutasPorHito
from modulos.red import Hito, ParaderoCercano, RutaResumen
from nucleo.dependencias import RegistroUso, caso
from nucleo.esquemas import EsquemaBase, errores

router = APIRouter(tags=["Búsqueda"])


class RutasDeHito(EsquemaBase):
    cobertura: bool
    rutas: list[RutaResumen]
    paradero_mas_cercano: ParaderoCercano | None = None


@router.get("/busqueda/rutas", response_model=list[RutaResumen], responses=errores(400))
async def buscar_rutas_por_texto(
    q: str = Query(min_length=1, max_length=60),
    caso_uso: BuscarRutasPorTexto = Depends(caso("buscar_rutas_por_texto")),
    uso: RegistroUso = Depends(RegistroUso),
) -> list[dict]:
    resultado = await caso_uso(q)
    uso("busqueda")
    return resultado


@router.get("/busqueda/hitos", response_model=list[Hito], responses=errores(400))
async def buscar_hitos(
    q: str = Query(min_length=1, max_length=60),
    caso_uso: BuscarHitos = Depends(caso("buscar_hitos")),
    uso: RegistroUso = Depends(RegistroUso),
) -> list[dict]:
    resultado = await caso_uso(q)
    uso("busqueda")
    return resultado


@router.get("/hitos/{hito_id}/rutas", response_model=RutasDeHito, responses=errores(404))
async def consultar_rutas_por_hito(
    hito_id: UUID,
    caso_uso: ConsultarRutasPorHito = Depends(caso("consultar_rutas_por_hito")),
    uso: RegistroUso = Depends(RegistroUso),
) -> dict:
    resultado = await caso_uso(hito_id)
    uso("busqueda")
    return resultado
