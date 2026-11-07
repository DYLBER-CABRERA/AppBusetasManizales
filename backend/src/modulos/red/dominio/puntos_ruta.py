"""Ruta creada tocando puntos en el mapa: validación y nombres automáticos (stdlib únicamente)."""

from __future__ import annotations

import math
from typing import Any

from nucleo.errores import ErrorValidacion

MIN_PUNTOS = 2
MAX_PUNTOS = 60
SEPARACION_MINIMA_M = 10.0  # dos puntos seguidos a menos de esto se consideran el mismo (se rechazan)
DIRECCION_FICTICIA = "Paradero de ejemplo (ficticio)"  # misma marca que las semillas: no hay columna `ficticio`
RADIO_TIERRA_M = 6_371_000.0


def distancia_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    f1, f2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((f2 - f1) / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    return 2 * RADIO_TIERRA_M * math.asin(math.sqrt(a))


def validar_puntos(puntos: list[dict[str, Any]], caja: dict[str, float]) -> None:
    """400 `VALIDACION` con `detalles` por índice de punto (`puntos[i]`, motivo). No toca la BD."""
    if not MIN_PUNTOS <= len(puntos) <= MAX_PUNTOS:
        raise ErrorValidacion(
            f"La ruta necesita entre {MIN_PUNTOS} y {MAX_PUNTOS} puntos.", [{"campo": "puntos", "motivo": "cantidad"}]
        )
    problemas: list[dict[str, str]] = []
    for i, p in enumerate(puntos):
        lat, lng = p["lat"], p["lng"]
        if not (math.isfinite(lat) and math.isfinite(lng)) or not (-90 <= lat <= 90 and -180 <= lng <= 180):
            problemas.append({"campo": f"puntos[{i}]", "motivo": "coordenadas_invalidas"})
        elif not (caja["minLat"] <= lat <= caja["maxLat"] and caja["minLng"] <= lng <= caja["maxLng"]):
            problemas.append({"campo": f"puntos[{i}]", "motivo": "fuera_de_zona"})
    if not problemas:
        for i in range(1, len(puntos)):
            a, b = puntos[i - 1], puntos[i]
            if distancia_m(a["lat"], a["lng"], b["lat"], b["lng"]) < SEPARACION_MINIMA_M:
                problemas.append({"campo": f"puntos[{i}]", "motivo": "duplicado_consecutivo"})
        a, b = puntos[-1], puntos[0]  # el circuito se cierra solo: el último punto no puede ser el primero
        if len(puntos) > 2 and distancia_m(a["lat"], a["lng"], b["lat"], b["lng"]) < SEPARACION_MINIMA_M:
            problemas.append({"campo": f"puntos[{len(puntos) - 1}]", "motivo": "ultimo_igual_al_primero"})
    if problemas:
        raise ErrorValidacion("Revisa los puntos de la ruta.", problemas)


def nombre_automatico(nombre_ruta: str, numero: int) -> str:
    """Mismo patrón de las semillas: «Paradero <NombreRuta> N» (La Enea → «Paradero La Enea 1», «Paradero La Enea 2»…)."""
    return f"Paradero {nombre_ruta} {numero}"
