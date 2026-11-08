"""Adaptador del puerto EnrutadorCalles con el servidor OSRM (demo público por defecto, sin API key).

Servidor demo COMPARTIDO: las llamadas son secuenciales, con una pausa mínima entre ellas, timeout corto y User-Agent
identificable. Cualquier fallo (timeout, red, HTTP ≠ 200, `NoRoute`, geometría rara) devuelve `None`. Los datos externos se tratan
como no confiables: solo se leen números. Nunca se registran coordenadas."""

from __future__ import annotations

import asyncio
import logging
import math
import time
from collections.abc import Awaitable, Callable

import httpx

from modulos.red.dominio.puertos import Coordenada

registro = logging.getLogger("busetasapp.osrm")
logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx registra cada URL en INFO (llevaría las coordenadas)

USER_AGENT = "BusetasApp-prototipo-clase/0.1 (proyecto academico; datos de ejemplo)"
TIMEOUT_S = 5.0
PAUSA_ENTRE_LLAMADAS_S = 0.2
MAX_VERTICES = 20_000


class EnrutadorOsrm:
    def __init__(
        self, cliente: httpx.AsyncClient, url_base: str, pausa_s: float = PAUSA_ENTRE_LLAMADAS_S,
        dormir: Callable[[float], Awaitable[None]] = asyncio.sleep, monotonico: Callable[[], float] = time.monotonic,
    ) -> None:
        self._cliente = cliente
        self._url = url_base.rstrip("/")
        self._pausa = pausa_s
        self._dormir = dormir
        self._monotonico = monotonico
        self._ultima: float | None = None

    async def trazar(self, origen: Coordenada, destino: Coordenada) -> list[Coordenada] | None:
        if self._ultima is not None:
            falta = self._pausa - (self._monotonico() - self._ultima)
            if falta > 0:
                await self._dormir(falta)
        try:
            respuesta = await self._cliente.get(
                f"{self._url}/route/v1/driving/{origen[1]:.6f},{origen[0]:.6f};{destino[1]:.6f},{destino[0]:.6f}",
                params={"overview": "full", "geometries": "geojson"},
                headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_S,
            )
        except httpx.HTTPError as exc:
            registro.warning("OSRM sin respuesta (%s)", type(exc).__name__)
            return None
        finally:
            self._ultima = self._monotonico()
        if respuesta.status_code != 200:
            registro.warning("OSRM respondió HTTP %d", respuesta.status_code)
            return None
        try:
            datos = respuesta.json()
            if datos.get("code") != "Ok":
                registro.warning("OSRM devolvió %s", str(datos.get("code"))[:30])
                return None
            coordenadas = datos["routes"][0]["geometry"]["coordinates"]
            if not 2 <= len(coordenadas) <= MAX_VERTICES:
                return None
            linea = [(float(c[1]), float(c[0])) for c in coordenadas]
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            registro.warning("OSRM devolvió una respuesta inesperada")
            return None
        if not all(math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180 for lat, lng in linea):
            return None
        return linea
