"""EmisorEventos: bus de eventos en proceso (una sola instancia; límite documentado: no escala horizontalmente)."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

Manejador = Callable[[dict[str, Any]], Awaitable[None]]

registro = logging.getLogger("busetasapp.eventos")

POSICION_ACEPTADA = "posicion.aceptada"


class EmisorEventos(Protocol):
    async def emitir(self, tipo: str, carga: dict[str, Any]) -> None: ...

    def suscribir(self, tipo: str, manejador: Manejador) -> None: ...


class EmisorEventosEnMemoria:
    """Un suscriptor que falla no afecta al emisor ni a los demás suscriptores."""

    def __init__(self) -> None:
        self._suscriptores: dict[str, list[Manejador]] = defaultdict(list)

    def suscribir(self, tipo: str, manejador: Manejador) -> None:
        self._suscriptores[tipo].append(manejador)

    async def emitir(self, tipo: str, carga: dict[str, Any]) -> None:
        for manejador in list(self._suscriptores.get(tipo, ())):
            try:
                await manejador(carga)
            except Exception as exc:  # noqa: BLE001 - un suscriptor lento o roto no debe frenar el ciclo de posiciones
                registro.warning("Falló un suscriptor de %s (%s)", tipo, type(exc).__name__)
