"""Router del módulo avisos: GET público (B2) y publicar/retirar por rol (B4)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import Field

from modulos.avisos.aplicacion.consultar_avisos_vigentes import ConsultarAvisosVigentes
from modulos.avisos.aplicacion.gestion import PublicarAviso, RetirarAviso
from nucleo.autorizacion import Identidad, Rol
from nucleo.dependencias import caso, requiere_rol
from nucleo.esquemas import EsquemaBase, errores

router = APIRouter(tags=["Avisos"])


class Aviso(EsquemaBase):
    id: UUID
    origen: Literal["empresa", "movilidad", "aplicativo"]
    empresa_id: UUID | None = None
    empresa_nombre: str | None = None
    tipo_cambio: Literal["cierre", "desvio", "obra", "condicion"] | None = None
    titulo: str
    cuerpo: str
    desde: datetime
    hasta: datetime | None = None
    ruta_ids: list[UUID] = []
    paradero_ids: list[UUID] = []


class AvisoCrear(EsquemaBase):
    # Se persiste en aviso.tipo_cambio (decisión del equipo); el caso de uso llega en B4/B5.
    tipo_cambio: Literal["cierre", "desvio", "obra", "condicion"] | None = None
    titulo: str = Field(min_length=1, max_length=120)
    cuerpo: str = Field(min_length=1, max_length=2000, description="El máximo operativo lo da longitud_max_aviso")
    ruta_ids: list[UUID] = []
    paradero_ids: list[UUID] = []
    desde: datetime | None = None
    hasta: datetime | None = None


@router.get("/avisos", response_model=list[Aviso])
async def consultar_avisos_vigentes(
    ruta_id: UUID | None = Query(default=None, alias="rutaId"),
    caso_uso: ConsultarAvisosVigentes = Depends(caso("consultar_avisos_vigentes")),
) -> list[dict]:
    return await caso_uso(ruta_id)


_publicadores = requiere_rol(Rol.JEFE_OPERACIONES, Rol.SECRETARIA_MOVILIDAD, Rol.ADMINISTRADOR)


@router.post("/avisos", response_model=Aviso, status_code=201, responses=errores(400, 401, 403, 404))
async def publicar_aviso(
    cuerpo: AvisoCrear,
    identidad: Identidad = Depends(_publicadores),
    caso_uso: PublicarAviso = Depends(caso("publicar_aviso")),
) -> dict:
    return await caso_uso(
        identidad, cuerpo.titulo, cuerpo.cuerpo, cuerpo.tipo_cambio, cuerpo.ruta_ids, cuerpo.paradero_ids,
        cuerpo.desde, cuerpo.hasta,
    )


@router.delete("/avisos/{aviso_id}", status_code=204, responses=errores(401, 403, 404))
async def retirar_aviso(
    aviso_id: UUID,
    identidad: Identidad = Depends(_publicadores),
    caso_uso: RetirarAviso = Depends(caso("retirar_aviso")),
) -> Response:
    await caso_uso(identidad, aviso_id)
    return Response(status_code=204)
