"""Validación de una posición entrante (docs/03 §2.6). Stdlib únicamente."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

TOLERANCIA_FUTURO = timedelta(seconds=60)


@dataclass(frozen=True)
class PosicionEntrante:
    numero_lateral: str
    lat: float
    lng: float
    reportada_en: datetime
    velocidad_kmh: float | None = None
    rumbo: float | None = None


def motivo_de_rechazo(posicion: PosicionEntrante, ahora: datetime, caja: dict[str, Any]) -> str | None:
    """`coordenadas_invalidas` | `fuera_de_zona` | `fecha_invalida` | `fecha_futura` | None si es válida.

    `fecha_invalida`: la hora llega sin zona horaria (no se puede comparar con el reloj del servidor).
    """
    lat, lng = posicion.lat, posicion.lng
    if not (math.isfinite(lat) and math.isfinite(lng)) or not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return "coordenadas_invalidas"
    if not (caja["minLat"] <= lat <= caja["maxLat"] and caja["minLng"] <= lng <= caja["maxLng"]):
        return "fuera_de_zona"
    if posicion.reportada_en.tzinfo is None or posicion.reportada_en.utcoffset() is None:
        return "fecha_invalida"
    if posicion.reportada_en > ahora + TOLERANCIA_FUTURO:
        return "fecha_futura"
    return None
