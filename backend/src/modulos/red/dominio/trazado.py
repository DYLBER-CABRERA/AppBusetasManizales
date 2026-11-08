"""Armado del trazado de una ruta circular a partir de segmentos (stdlib únicamente)."""

from __future__ import annotations

Coordenada = tuple[float, float]  # (lat, lng)
TOLERANCIA_GRADOS = 1e-6  # ~0,1 m: dos vértices más cerca que esto son el mismo punto de unión


def _iguales(a: Coordenada, b: Coordenada) -> bool:
    return abs(a[0] - b[0]) <= TOLERANCIA_GRADOS and abs(a[1] - b[1]) <= TOLERANCIA_GRADOS


def unir_segmentos(segmentos: list[list[Coordenada]]) -> list[Coordenada]:
    """Concatena los segmentos en orden SIN duplicar el punto de unión, y cierra el circuito (último vértice = primero).

    Si el último segmento termina un poco antes del primer vértice (la calle ajustada por OSRM frente al punto tocado), se
    añade el primer vértice al final para que la línea quede cerrada; no se deforma ningún tramo."""
    linea: list[Coordenada] = []
    for segmento in segmentos:
        for k, punto in enumerate(segmento):
            if k == 0 and linea and _iguales(linea[-1], punto):
                continue
            linea.append(punto)
    if linea and not _iguales(linea[-1], linea[0]):
        linea.append(linea[0])
    elif len(linea) > 1:
        linea[-1] = linea[0]  # idénticos salvo redondeo
    return linea
