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


def calcular_tiempos(
    caminata_origen_m: float, caminata_destino_m: float, progreso_origen_m: float, progreso_destino_m: float,
    longitud_m: float, velocidad_kmh: float, frecuencia_max_min: float,
) -> TiemposViaje:
    """Circular: el bus siempre avanza, así que si el destino quedó "atrás" da la vuelta al circuito.

    bus = ((destino − origen) mod L) / velocidad; espera = frecuencia_max / 2; caminata = metros / 80 por minuto
    (suma de la caminata al paradero de origen y desde el de destino).
    """
    recorrido = (progreso_destino_m - progreso_origen_m) % longitud_m
    return TiemposViaje(
        caminata_min=(caminata_origen_m + caminata_destino_m) / METROS_POR_MINUTO_A_PIE,
        espera_min=frecuencia_max_min / 2,
        bus_min=recorrido / (velocidad_kmh / 3.6) / 60,
    )
