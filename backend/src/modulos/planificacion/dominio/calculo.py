"""Cálculo de una opción de viaje directo (backend/CLAUDE.md §7, D-P07). Stdlib únicamente."""

from __future__ import annotations

from dataclasses import dataclass

METROS_POR_MINUTO_A_PIE = 80.0


@dataclass(frozen=True)
class TiemposViaje:
    caminata_min: float
    espera_min: float
    bus_min: float

    @property
    def total_min(self) -> float:
        return self.caminata_min + self.espera_min + self.bus_min


UMBRAL_RECORRIDO_M = 1.0  # dos paraderos distintos nunca están a ~0 m a lo largo del circuito


def mejor_recorrido_m(
    progresos_origen: list[float], progresos_destino: list[float], longitud_m: float
) -> float | None:
    """Metros que el bus recorre de un paradero al otro, siempre hacia adelante y dando la vuelta si hace falta.

    Cada lista trae el avance SECUENCIAL (el de `progresos_paraderos_ruta`) de TODAS las veces que la ruta pasa por ese
    paradero: un circuito que recorre dos veces la misma vía pasa dos veces por el mismo paradero y el pasajero toma el
    pase que le da el menor recorrido. `None` si no hay un recorrido válido (p. ej. es el mismo punto).
    """
    candidatos = [
        recorrido
        for o in progresos_origen
        for d in progresos_destino
        if (recorrido := (d - o) % longitud_m) >= UMBRAL_RECORRIDO_M
    ]
    return min(candidatos) if candidatos else None


def calcular_tiempos(
    caminata_origen_m: float, caminata_destino_m: float, recorrido_m: float, velocidad_kmh: float, frecuencia_max_min: float,
) -> TiemposViaje:
    """bus = recorrido / velocidad; espera = frecuencia_max / 2; caminata = metros / 80 por minuto (suma de la caminata
    al paradero de origen y desde el de destino). `recorrido_m` sale de `mejor_recorrido_m`."""
    return TiemposViaje(
        caminata_min=(caminata_origen_m + caminata_destino_m) / METROS_POR_MINUTO_A_PIE,
        espera_min=frecuencia_max_min / 2,
        bus_min=recorrido_m / (velocidad_kmh / 3.6) / 60,
    )
