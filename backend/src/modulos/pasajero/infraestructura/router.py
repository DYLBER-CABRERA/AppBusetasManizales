"""Router del módulo pasajero (U). B0: 501 PENDIENTE (lógica en B6)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import Field

from nucleo.autorizacion import Rol
from nucleo.dependencias import pendiente, requiere_rol
from nucleo.esquemas import EsquemaBase, errores

router = APIRouter(tags=["Pasajero"], dependencies=[Depends(requiere_rol(Rol.PASAJERO))])


class Favorito(EsquemaBase):
    id: UUID
    tipo: Literal["ruta", "paradero"]
    ruta_id: UUID | None = None
    paradero_id: UUID | None = None
    nombre: str | None = None
    disponible: bool = Field(description="false si la ruta o el paradero fue dado de baja")


class FavoritoCrear(EsquemaBase):
    tipo: Literal["ruta", "paradero"]
    ruta_id: UUID | None = None
    paradero_id: UUID | None = None


class AlertaLlegada(EsquemaBase):
    id: UUID
    ruta_id: UUID
    paradero_id: UUID
    distancia_aviso_m: int
    estado: Literal["activa", "notificada", "desactivada"]
    ultima_notificacion_en: datetime | None = None
    version: int


class AlertaCrear(EsquemaBase):
    ruta_id: UUID
    paradero_id: UUID
    distancia_aviso_m: int | None = Field(default=None, ge=50, le=2000)


@router.get("/favoritos", response_model=list[Favorito], responses=errores(401))
async def listar_favoritos() -> list[Favorito]:
    pendiente()


@router.post(
    "/favoritos", response_model=Favorito, status_code=201,
    responses={200: {"model": Favorito, "description": "Ya existía"}, **errores(400, 401, 404)},
)
async def agregar_favorito(cuerpo: FavoritoCrear) -> Favorito:
    pendiente()


@router.delete("/favoritos/{favorito_id}", status_code=204, responses=errores(401, 404))
async def quitar_favorito(favorito_id: UUID) -> Response:
    pendiente()


@router.get("/alertas-llegada", response_model=list[AlertaLlegada], responses=errores(401))
async def listar_alertas() -> list[AlertaLlegada]:
    pendiente()


@router.post(
    "/alertas-llegada", response_model=AlertaLlegada, status_code=201, responses=errores(400, 401, 404, 409)
)
async def crear_alerta_llegada(cuerpo: AlertaCrear) -> AlertaLlegada:
    pendiente()


@router.delete("/alertas-llegada/{alerta_id}", status_code=204, responses=errores(401, 404))
async def eliminar_alerta(alerta_id: UUID) -> Response:
    pendiente()
