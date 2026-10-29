"""Casos de uso del pasajero: favoritos (P10), alertas de llegada (P11) y evaluación por posición."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any
from uuid import UUID

from modulos.pasajero.dominio.evaluador_alertas import EvaluadorAlertas
from modulos.pasajero.dominio.puertos import RepositorioAlertas, RepositorioFavoritos, RepositorioProgreso
from nucleo.autorizacion import Identidad, Rol, exigir_rol
from nucleo.errores import ErrorNoEncontrado, ErrorValidacion
from nucleo.notificador import DestinoAlerta, PuertoNotificador
from nucleo.parametros import PuertoParametros
from nucleo.reloj import PuertoReloj

registro = logging.getLogger("busetasapp.alertas")
MENSAJE_SESION = "Inicia sesión para guardar."


def _usuario(identidad: Identidad | None) -> UUID:
    return UUID(exigir_rol(identidad, Rol.PASAJERO).usuario_id)


class ListarFavoritos:
    def __init__(self, favoritos: RepositorioFavoritos) -> None:
        self._f = favoritos

    async def __call__(self, identidad: Identidad | None) -> list[dict[str, Any]]:
        return await self._f.listar(_usuario(identidad))


class AgregarFavorito:
    def __init__(self, favoritos: RepositorioFavoritos) -> None:
        self._f = favoritos

    async def __call__(
        self, identidad: Identidad | None, tipo: str, ruta_id: UUID | None, paradero_id: UUID | None
    ) -> tuple[dict[str, Any], bool]:
        """(favorito, creado). Repetido → el existente con creado=False (el router responde 200)."""
        usuario = _usuario(identidad)
        objetivo = ruta_id if tipo == "ruta" else paradero_id
        otro = paradero_id if tipo == "ruta" else ruta_id
        if objetivo is None or otro is not None:
            raise ErrorValidacion("Un favorito es una ruta o un paradero, no ambos.")
        if not await self._f.destino_existe(tipo, objetivo):
            raise ErrorNoEncontrado("La ruta o el paradero no existe.")
        existente = await self._f.buscar(usuario, tipo, objetivo)
        if existente is not None:
            return existente, False
        return await self._f.crear(usuario, tipo, objetivo), True


class QuitarFavorito:
    def __init__(self, favoritos: RepositorioFavoritos) -> None:
        self._f = favoritos

    async def __call__(self, identidad: Identidad | None, favorito_id: UUID) -> None:
        if not await self._f.eliminar(_usuario(identidad), favorito_id):
            raise ErrorNoEncontrado("El favorito no existe.")


class ListarAlertas:
    def __init__(self, alertas: RepositorioAlertas) -> None:
        self._a = alertas

    async def __call__(self, identidad: Identidad | None) -> list[dict[str, Any]]:
        return await self._a.listar(_usuario(identidad))


class CrearAlertaLlegada:
    """La usan la app (usuario) y el bot (chat de Telegram, D-P08)."""

    def __init__(self, alertas: RepositorioAlertas, parametros: PuertoParametros) -> None:
        self._a = alertas
        self._parametros = parametros

    async def para_destino(
        self, destino: DestinoAlerta, ruta_id: UUID, paradero_id: UUID, distancia_aviso_m: int | None
    ) -> dict[str, Any]:
        if not await self._a.paradero_en_ruta_activa(ruta_id, paradero_id):
            raise ErrorNoEncontrado("El paradero no pertenece a esa ruta.")
        distancia = distancia_aviso_m or int(await self._parametros.numero("distancia_aviso_llegada_m"))
        return await self._a.crear(destino.usuario_id, destino.telegram_chat_id, ruta_id, paradero_id, distancia)

    async def __call__(
        self, identidad: Identidad | None, ruta_id: UUID, paradero_id: UUID, distancia_aviso_m: int | None
    ) -> dict[str, Any]:
        return await self.para_destino(DestinoAlerta(usuario_id=_usuario(identidad)), ruta_id, paradero_id, distancia_aviso_m)


class EliminarAlerta:
    def __init__(self, alertas: RepositorioAlertas) -> None:
        self._a = alertas

    async def __call__(self, identidad: Identidad | None, alerta_id: UUID) -> None:
        if not await self._a.desactivar(_usuario(identidad), alerta_id):
            raise ErrorNoEncontrado("La alerta no existe.")


class EvaluarAlertasPorPosicion:
    """Suscriptor de `posicion.aceptada`: avisa llegada y desvío por el notificador. Nunca propaga errores."""

    def __init__(
        self, alertas: RepositorioAlertas, progreso: RepositorioProgreso, notificador: PuertoNotificador,
        parametros: PuertoParametros, reloj: PuertoReloj,
    ) -> None:
        self._alertas = alertas
        self._progreso = progreso
        self._notificador = notificador
        self._parametros = parametros
        self._reloj = reloj
        self._evaluador = EvaluadorAlertas(10, 100)  # los parámetros se refrescan en cada evaluación

    async def _evaluador_actual(self) -> EvaluadorAlertas:
        self._evaluador.enfriamiento = timedelta(minutes=await self._parametros.numero("enfriamiento_alerta_min"))
        self._evaluador.umbral = await self._parametros.numero("umbral_desvio_m")
        return self._evaluador

    async def __call__(self, carga: dict[str, Any]) -> None:
        try:
            await self._evaluar(carga)
        except Exception as exc:  # noqa: BLE001 - las alertas nunca frenan el ciclo de posiciones
            registro.warning("Falló la evaluación de alertas (%s)", type(exc).__name__)

    async def _evaluar(self, carga: dict[str, Any]) -> None:
        ruta_id = carga.get("ruta_id")
        if ruta_id is None:
            return
        alertas = await self._alertas.activas_de_ruta(ruta_id)
        if not alertas:
            return
        punto = await self._progreso.progreso_de_punto(ruta_id, carga["lat"], carga["lng"])
        if punto is None:
            return
        progresos: dict[UUID, float] = {}
        for paradero_id in {a["paradero_id"] for a in alertas}:
            p = await self._progreso.progreso_paradero(ruta_id, paradero_id)
            if p is not None:
                progresos[paradero_id] = p["progreso_m"]
        ahora = self._reloj.ahora()
        evaluador = await self._evaluador_actual()
        por_id = {a["id"]: a for a in alertas}
        for n in evaluador.evaluar(
            alertas, carga["numero_lateral"], punto["progreso_m"], punto["desvio_m"], punto["longitud_m"], progresos, ahora
        ):
            alerta = por_id[n.alerta_id]
            datos: dict[str, Any] = {
                "tipo": n.tipo, "alertaId": str(alerta["id"]), "rutaId": str(ruta_id),
                "paraderoId": str(alerta["paradero_id"]), "mensaje": n.mensaje,
            }
            if n.tipo == "alerta_llegada":
                datos["distanciaM"] = n.distancia_m
                await self._alertas.marcar_notificada(alerta["id"], ahora)
            else:
                datos["busetaNumero"] = n.buseta
            destino = DestinoAlerta(alerta["usuario_id"], alerta["telegram_chat_id"])
            await self._notificador.notificar_alerta(destino, n.mensaje, datos)
