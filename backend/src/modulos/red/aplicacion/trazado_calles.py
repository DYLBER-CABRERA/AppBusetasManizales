"""Trazado de una ruta circular siguiendo calles reales (OSRM), con recta de respaldo SOLO en el tramo que falle."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from modulos.red.dominio.puertos import Coordenada, EnrutadorCalles
from modulos.red.dominio.trazado import unir_segmentos

registro = logging.getLogger("busetasapp.trazado")

PRESUPUESTO_S = 25.0  # tiempo máximo total pidiendo calles; pasado esto, los tramos que faltan van en recta
FALLOS_SEGUIDOS_MAX = 3  # con 3 fallos seguidos se deja de llamar al servicio (está caído o saturado)


@dataclass
class ResultadoTrazado:
    coordenadas: list[Coordenada]
    tramos_sin_ruta: list[tuple[int, int]] = field(default_factory=list)  # (desde, hasta), numerados desde 1


class ConstructorDeTrazado:
    """Pide a OSRM, EN SECUENCIA, la geometría de cada par consecutivo de paradas incluido el cierre último→primero
    (la ruta es circular). Los paraderos no cambian: solo cómo se dibuja la línea. La creación de la ruta nunca falla por esto."""

    def __init__(
        self, enrutador: EnrutadorCalles | None, monotonico: Callable[[], float] = time.monotonic,
        presupuesto_s: float = PRESUPUESTO_S, fallos_seguidos_max: int = FALLOS_SEGUIDOS_MAX,
    ) -> None:
        self._enrutador = enrutador
        self._monotonico = monotonico
        self._presupuesto = presupuesto_s
        self._fallos_max = fallos_seguidos_max

    async def construir(self, paradas: list[Coordenada]) -> ResultadoTrazado:
        n = len(paradas)
        inicio = self._monotonico()
        fallos_seguidos = 0
        sin_servicio = self._enrutador is None
        segmentos: list[list[Coordenada]] = []
        sin_ruta: list[tuple[int, int]] = []
        for i in range(n):
            j = (i + 1) % n
            geometria = None
            if not sin_servicio and self._enrutador is not None:
                if self._monotonico() - inicio > self._presupuesto:
                    sin_servicio = True
                    registro.warning("Trazado por calles: se agotó el tiempo, los tramos restantes van en línea recta")
                else:
                    geometria = await self._enrutador.trazar(paradas[i], paradas[j])
                    fallos_seguidos = 0 if geometria else fallos_seguidos + 1
                    if fallos_seguidos >= self._fallos_max:
                        sin_servicio = True
                        registro.warning("Trazado por calles: %d fallos seguidos, el resto va en línea recta", fallos_seguidos)
            if geometria is None:
                segmentos.append([paradas[i], paradas[j]])
                sin_ruta.append((i + 1, j + 1))
                registro.info("Tramo %d→%d sin ruta real, se usó línea recta", i + 1, j + 1)
            else:
                segmentos.append(geometria)
        return ResultadoTrazado(unir_segmentos(segmentos), sin_ruta)
