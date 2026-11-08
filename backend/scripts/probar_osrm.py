"""Prueba MANUAL del adaptador OSRM real con la ruta de ejemplo Fátima → Chipre (puntos de barrios.json + 2 intermedios).

Hace 4 llamadas al servidor OSRM configurado (los 3 tramos + el cierre) y una más con los nombres de calle del trayecto
Fátima → Chipre. NO toca ninguna base de datos ni el endpoint. Solo para validar el trazado; no corre en pytest.

Uso (desde backend/):  python scripts/probar_osrm.py
"""

from __future__ import annotations

import asyncio
import json
import sys

import httpx

from _comun import SEMILLAS
from herramientas.simulador_gps import Circuito, haversine_m
from modulos.red.aplicacion.trazado_calles import ConstructorDeTrazado
from modulos.red.infraestructura.enrutador_osrm import USER_AGENT, EnrutadorOsrm
from nucleo.configuracion import obtener_configuracion


def puntos() -> list[tuple[float, float]]:
    barrios = {b["nombre"]: b for b in json.loads((SEMILLAS / "barrios.json").read_text(encoding="utf-8"))["barrios"]}
    a, d = (barrios["Fátima"]["lat"], barrios["Fátima"]["lng"]), (barrios["Chipre"]["lat"], barrios["Chipre"]["lng"])
    intermedio = lambda t: (a[0] + (d[0] - a[0]) * t + 0.0008, a[1] + (d[1] - a[1]) * t - 0.0008)  # noqa: E731
    return [a, intermedio(0.35), intermedio(0.7), d]


def distancia_a_la_linea(p: tuple[float, float], linea: list[tuple[float, float]]) -> float:
    """Distancia mínima (m) del punto a los vértices de la línea (aprox., la línea de OSRM es densa)."""
    return min(haversine_m(*p, *v) for v in linea)


async def main() -> int:
    url = obtener_configuracion().osrm_url or "https://router.project-osrm.org"
    paradas = puntos()
    async with httpx.AsyncClient() as cliente:
        resultado = await ConstructorDeTrazado(EnrutadorOsrm(cliente, url)).construir(paradas)
        r = await cliente.get(
            f"{url.rstrip('/')}/route/v1/driving/{paradas[0][1]:.6f},{paradas[0][0]:.6f};{paradas[-1][1]:.6f},{paradas[-1][0]:.6f}",
            params={"overview": "false", "steps": "true"}, headers={"User-Agent": USER_AGENT}, timeout=5,
        )
    calles: list[str] = []
    if r.status_code == 200:
        for tramo in r.json().get("routes", [{}])[0].get("legs", []):
            for paso in tramo.get("steps", []):
                nombre = paso.get("name")
                if nombre and nombre not in calles:
                    calles.append(nombre)
    linea = resultado.coordenadas
    circuito = Circuito(linea)
    recta = Circuito([*paradas, paradas[0]])
    print(f"Tramos sin ruta real (respaldo en recta): {resultado.tramos_sin_ruta or 'ninguno'}")
    print(f"Vértices del trazado: {len(linea)} (la recta tendría {len(paradas) + 1})")
    print(f"Longitud real del circuito: {circuito.longitud:.0f} m · en recta: {recta.longitud:.0f} m · razón {circuito.longitud / recta.longitud:.2f}")
    print(f"Circuito cerrado: {linea[0] == linea[-1]}")
    for i, p in enumerate(paradas, start=1):
        print(f"Parada {i}: a {distancia_a_la_linea(p, linea):.1f} m del vértice más cercano del trazado")
    print("Calles del trayecto Fátima → Chipre según OSRM:", calles or "(sin nombres)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
