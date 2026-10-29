"""Casos de uso de seguimiento: registrar_posiciones, consultar_busetas_en_vivo, calcular_eta_paradero (HU-P05, HU-P06)."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from modulos.seguimiento.dominio.calculador_eta import (
    CalculadorEta,
    EntradaEta,
    FranjaFrecuencia,
    HorarioDia,
    PosicionConProgreso,
)
from modulos.seguimiento.dominio.puertos import (
    ProveedorHorarios,
    ProveedorTipoDia,
    RepositorioEta,
    RepositorioFuentesGps,
    RepositorioPosiciones,
    RepositorioRodamientos,
)
from modulos.seguimiento.dominio.validacion_posicion import PosicionEntrante, motivo_de_rechazo
from nucleo.emisor_eventos import POSICION_ACEPTADA, EmisorEventos
from nucleo.errores import ErrorNoAutenticado, ErrorNoEncontrado
from nucleo.parametros import PuertoParametros
from nucleo.reloj import PuertoReloj

registro = logging.getLogger("busetasapp.seguimiento")


def hash_de_clave(clave: str) -> str:
    return hashlib.sha256(clave.encode("utf-8")).hexdigest()


class DeductorDeRuta:
    """`servicio_ruta_id` del turno PUBLICADO de la buseta que contiene el instante; `None` si está fuera de turno."""

    def __init__(self, rodamientos: RepositorioRodamientos) -> None:
        self._rodamientos = rodamientos

    async def __call__(self, empresa_id: UUID, numero_lateral: str, instante: datetime) -> UUID | None:
        return await self._rodamientos.turno_vigente(empresa_id, numero_lateral, instante)


@dataclass
class ResultadoRegistro:
    aceptadas: int = 0
    descartadas: int = 0
    rechazadas: list[dict[str, Any]] = field(default_factory=list)


class RegistrarPosiciones:
    """Mismo caso de uso para el GPS real (HTTP) y para el simulador (D-P03)."""

    def __init__(
        self,
        posiciones: RepositorioPosiciones,
        deductor: DeductorDeRuta,
        rodamientos: RepositorioRodamientos,
        parametros: PuertoParametros,
        reloj: PuertoReloj,
        emisor: EmisorEventos,
    ) -> None:
        self._posiciones = posiciones
        self._deductor = deductor
        self._rodamientos = rodamientos
        self._parametros = parametros
        self._reloj = reloj
        self._emisor = emisor

    async def __call__(self, empresa_id: UUID, lote: list[PosicionEntrante]) -> ResultadoRegistro:
        resultado = ResultadoRegistro()
        ahora = self._reloj.ahora()
        caja = await self._parametros.objeto("caja_ciudad")
        for indice, posicion in enumerate(lote):
            motivo = motivo_de_rechazo(posicion, ahora, caja)
            buseta = None
            if motivo is None:
                buseta = await self._posiciones.buscar_buseta(empresa_id, posicion.numero_lateral)
                if buseta is None:
                    motivo = "buseta_desconocida"
            if motivo is not None or buseta is None:
                resultado.rechazadas.append({"indice": indice, "motivo": motivo})
                continue
            servicio_id = await self._deductor(empresa_id, posicion.numero_lateral, posicion.reportada_en)
            guardada = await self._posiciones.guardar_posicion(
                buseta["id"], servicio_id, posicion.lat, posicion.lng, posicion.velocidad_kmh, posicion.rumbo,
                posicion.reportada_en,
            )
            if not guardada:
                resultado.descartadas += 1
                continue
            resultado.aceptadas += 1
            ruta_id = await self._rodamientos.ruta_de_servicio(servicio_id) if servicio_id else None
            await self._emisor.emitir(
                POSICION_ACEPTADA,
                {
                    "buseta_id": buseta["id"], "numero_lateral": posicion.numero_lateral, "empresa_id": empresa_id,
                    "servicio_id": servicio_id, "ruta_id": ruta_id, "lat": posicion.lat, "lng": posicion.lng,
                    "velocidad_kmh": posicion.velocidad_kmh, "rumbo": posicion.rumbo, "reportada_en": posicion.reportada_en,
                },
            )
        return resultado


class AutenticarFuenteGps:
    """`X-Clave-Fuente` → empresa. Solo se compara el hash SHA-256; la clave nunca se registra."""

    def __init__(self, fuentes: RepositorioFuentesGps, reloj: PuertoReloj) -> None:
        self._fuentes = fuentes
        self._reloj = reloj

    async def __call__(self, clave: str) -> UUID:
        credencial = await self._fuentes.empresa_por_hash(hash_de_clave(clave))
        if credencial is None:
            raise ErrorNoAutenticado("Clave de fuente inválida o revocada.")
        await self._fuentes.marcar_uso(credencial["credencial_id"], self._reloj.ahora())
        return credencial["empresa_id"]


class ConsultarBusetasEnVivo:
    def __init__(
        self, posiciones: RepositorioPosiciones, eta: RepositorioEta, parametros: PuertoParametros, reloj: PuertoReloj
    ) -> None:
        self._posiciones = posiciones
        self._eta = eta
        self._parametros = parametros
        self._reloj = reloj

    async def __call__(self, ruta_id: UUID) -> dict[str, Any]:
        if not await self._eta.ruta_activa_existe(ruta_id):
            raise ErrorNoEncontrado("La ruta no existe o fue dada de baja.")
        ahora = self._reloj.ahora()
        umbral = int(await self._parametros.numero("umbral_posicion_obsoleta_s"))
        busetas = []
        for fila in await self._posiciones.posiciones_de_ruta(ruta_id, ahora):
            sin_senal = (ahora - fila["reportada_en"]).total_seconds() > umbral
            busetas.append(
                {
                    **fila, "estado": "sin_senal" if sin_senal else "activa",
                    "mensaje": f"Ubicación no disponible. Última señal hace más de {umbral} s." if sin_senal else None,
                }
            )
        busetas.sort(key=lambda b: b["numero_lateral"])
        return {
            "seguimiento_disponible": bool(busetas),
            "unidades_en_servicio": await self._posiciones.unidades_en_servicio(ruta_id, ahora),
            "calculado_en": ahora,
            "busetas": busetas,
        }


class CalcularEtaParadero:
    def __init__(
        self,
        eta: RepositorioEta,
        posiciones: RepositorioPosiciones,
        horarios: ProveedorHorarios,
        tipo_dia: ProveedorTipoDia,
        parametros: PuertoParametros,
        reloj: PuertoReloj,
    ) -> None:
        self._eta = eta
        self._posiciones = posiciones
        self._horarios = horarios
        self._tipo_dia = tipo_dia
        self._parametros = parametros
        self._reloj = reloj

    async def __call__(self, paradero_id: UUID, ruta_id: UUID, servicio_id: UUID | None = None) -> dict[str, Any]:
        if not await self._eta.ruta_activa_existe(ruta_id):
            raise ErrorNoEncontrado("La ruta no existe o fue dada de baja.")
        progreso = await self._eta.progreso_paradero(ruta_id, paradero_id)
        if progreso is None:
            raise ErrorNoEncontrado("El paradero no pertenece a esa ruta.")
        servicios = await self._eta.servicios_para_eta(ruta_id)
        if servicio_id is not None:
            servicios = [s for s in servicios if s["servicio_id"] == servicio_id]
            if not servicios:
                raise ErrorNoEncontrado("El servicio no pertenece a esa ruta.")
        ids = [s["servicio_id"] for s in servicios]
        ahora = self._reloj.ahora()
        tipo_dia = self._tipo_dia.para_instante(ahora)
        horarios = {h["servicio_id"]: h for h in await self._horarios.horarios_de(ids) if h["tipo_dia"] == tipo_dia}
        franjas: dict[UUID, list[FranjaFrecuencia]] = {i: [] for i in ids}
        for f in await self._horarios.frecuencias_de(ids):
            if f["tipo_dia"] == tipo_dia:
                franjas[f["servicio_id"]].append(
                    FranjaFrecuencia(f["inicio_minuto"], f["fin_minuto"], f["minutos_min"], f["minutos_max"])
                )
        posiciones: dict[UUID, list[PosicionConProgreso]] = {i: [] for i in ids}
        for p in await self._posiciones.posiciones_para_eta(ids, ruta_id, ahora):
            posiciones[p["servicio_id"]].append(
                PosicionConProgreso(p["numero_lateral"], p["progreso_m"], p["reportada_en"], p["velocidad_kmh"])
            )
        calculador = CalculadorEta(
            await self._parametros.numero("velocidad_default_kmh"),
            await self._parametros.numero("umbral_posicion_obsoleta_s"),
        )
        resultados = []
        for s in servicios:
            h = horarios.get(s["servicio_id"])
            entrada = EntradaEta(
                servicio_id=s["servicio_id"], empresa=s["empresa_nombre"], codigo_publico=s["codigo_publico"],
                suspendido=s["estado"] == "suspendido",
                horario=HorarioDia(h["primera_salida"], h["ultima_salida"], h["cierre"]) if h else None,
                duracion_min=s["duracion_estandar_min"], franjas=franjas[s["servicio_id"]],
                posiciones=posiciones[s["servicio_id"]],
            )
            r = calculador.calcular(entrada, ahora, progreso["progreso_m"], progreso["longitud_m"])
            resultados.append(
                {
                    "servicio_id": r.servicio_id, "empresa": r.empresa, "codigo_publico": r.codigo_publico, "fuente": r.fuente,
                    "eta_segundos": r.eta_segundos,
                    "rango": None if r.rango_max_segundos is None else {"min_segundos": 0, "max_segundos": r.rango_max_segundos},
                    "buseta_numero_lateral": r.buseta_numero_lateral, "ultima_senal_hace_s": r.ultima_senal_hace_s,
                    "mensaje": r.mensaje,
                }
            )
        return {"paradero_id": paradero_id, "ruta_id": ruta_id, "calculado_en": ahora, "resultados": resultados}
