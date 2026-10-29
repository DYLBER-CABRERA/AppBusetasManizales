"""Router del módulo pasajero (U): favoritos y alertas de llegada (B6). Exige sesión de pasajero."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import Field

from modulos.pasajero.aplicacion.casos_de_uso import (
    MENSAJE_SESION,
    AgregarFavorito,
    CrearAlertaLlegada,
    EliminarAlerta,
    ListarAlertas,
    ListarFavoritos,
    QuitarFavorito,
)
from nucleo.autorizacion import Identidad, Rol
from nucleo.dependencias import caso, requiere_rol
from nucleo.esquemas import EsquemaBase, errores

router = APIRouter(tags=["Pasajero"])

_pasajero = Depends(requiere_rol(Rol.PASAJERO, mensaje=MENSAJE_SESION))


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


@router.get("/favoritos", response_model=list[Favorito], responses=errores(401, 403))
async def listar_favoritos(
    identidad: Identidad = _pasajero, caso_uso: ListarFavoritos = Depends(caso("listar_favoritos"))
) -> list[dict]:
    return await caso_uso(identidad)


@router.post(
    "/favoritos", response_model=Favorito, status_code=201,
    responses={200: {"model": Favorito, "description": "Ya existía"}, **errores(400, 401, 403, 404)},
)
async def agregar_favorito(
    cuerpo: FavoritoCrear,
    respuesta: Response,
    identidad: Identidad = _pasajero,
    caso_uso: AgregarFavorito = Depends(caso("agregar_favorito")),
) -> dict:
    favorito, creado = await caso_uso(identidad, cuerpo.tipo, cuerpo.ruta_id, cuerpo.paradero_id)
    if not creado:
        respuesta.status_code = 200
    return favorito


@router.delete("/favoritos/{favorito_id}", status_code=204, responses=errores(401, 403, 404))
async def quitar_favorito(
    favorito_id: UUID, identidad: Identidad = _pasajero, caso_uso: QuitarFavorito = Depends(caso("quitar_favorito"))
) -> Response:
    await caso_uso(identidad, favorito_id)
    return Response(status_code=204)


@router.get("/alertas-llegada", response_model=list[AlertaLlegada], responses=errores(401, 403))
async def listar_alertas(
    identidad: Identidad = _pasajero, caso_uso: ListarAlertas = Depends(caso("listar_alertas"))
) -> list[dict]:
    return await caso_uso(identidad)


@router.post("/alertas-llegada", response_model=AlertaLlegada, status_code=201, responses=errores(400, 401, 403, 404, 409))
async def crear_alerta_llegada(
    cuerpo: AlertaCrear,
    identidad: Identidad = _pasajero,
    caso_uso: CrearAlertaLlegada = Depends(caso("crear_alerta_llegada")),
) -> dict:
    return await caso_uso(identidad, cuerpo.ruta_id, cuerpo.paradero_id, cuerpo.distancia_aviso_m)


@router.delete("/alertas-llegada/{alerta_id}", status_code=204, responses=errores(401, 403, 404))
async def eliminar_alerta(
    alerta_id: UUID, identidad: Identidad = _pasajero, caso_uso: EliminarAlerta = Depends(caso("eliminar_alerta"))
) -> Response:
    await caso_uso(identidad, alerta_id)
    return Response(status_code=204)
