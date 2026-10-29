"""Router del módulo seguimiento (B3): busetas en vivo, ETA e ingesta de posiciones. Solo traduce HTTP."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from modulos.seguimiento.aplicacion.casos_de_uso import (
    AutenticarFuenteGps,
    CalcularEtaParadero,
    ConsultarBusetasEnVivo,
    RegistrarPosiciones,
)
from modulos.seguimiento.dominio.validacion_posicion import PosicionEntrante
from modulos.seguimiento.infraestructura.esquemas import (
    BusetasEnVivo,
    LotePosiciones,
    RespuestaEta,
    ResultadoIngesta,
)
from nucleo.dependencias import RegistroUso, caso, clave_fuente
from nucleo.esquemas import errores

router = APIRouter(tags=["Seguimiento"])


@router.get("/rutas/{ruta_id}/busetas", response_model=BusetasEnVivo, responses=errores(404))
async def consultar_busetas_en_vivo(
    ruta_id: UUID,
    caso_uso: ConsultarBusetasEnVivo = Depends(caso("consultar_busetas_en_vivo")),
    uso: RegistroUso = Depends(RegistroUso),
) -> dict:
    resultado = await caso_uso(ruta_id)
    uso("busetas_vivo", ruta_id)
    return resultado


@router.get("/paraderos/{paradero_id}/eta", response_model=RespuestaEta, responses=errores(400, 404))
async def calcular_eta_paradero(
    paradero_id: UUID,
    ruta_id: UUID = Query(alias="rutaId"),
    servicio_id: UUID | None = Query(default=None, alias="servicioId"),
    caso_uso: CalcularEtaParadero = Depends(caso("calcular_eta_paradero")),
    uso: RegistroUso = Depends(RegistroUso),
) -> dict:
    resultado = await caso_uso(paradero_id, ruta_id, servicio_id)
    uso("eta", ruta_id)
    return resultado


@router.post("/ingesta/posiciones", response_model=ResultadoIngesta, status_code=202, responses=errores(400, 401))
async def registrar_posiciones(
    cuerpo: LotePosiciones,
    clave: str = Depends(clave_fuente),
    autenticar: AutenticarFuenteGps = Depends(caso("autenticar_fuente_gps")),
    caso_uso: RegistrarPosiciones = Depends(caso("registrar_posiciones")),
) -> dict:
    empresa_id = await autenticar(clave)
    lote = [
        PosicionEntrante(p.numero_lateral, p.lat, p.lng, p.reportada_en, p.velocidad_kmh, p.rumbo) for p in cuerpo.posiciones
    ]
    resultado = await caso_uso(empresa_id, lote)
    return {"aceptadas": resultado.aceptadas, "descartadas": resultado.descartadas, "rechazadas": resultado.rechazadas}
