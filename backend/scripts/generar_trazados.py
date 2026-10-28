"""Genera los trazados circulares UNA vez con OSRM (D-P10) y los paraderos ficticios de cada ruta.

Entrada : supabase/semillas/hitos.json (de geocodificar_hitos.py)
Salida  : supabase/semillas/trazados/<ruta>.geojson  (FeatureCollection: 1 LineString + N Point `paradero`)
El demo NO llama a OSRM. Si OSRM no responde, pide el archivo al equipo: no se inventan coordenadas.
No toca ninguna base de datos. El equipo debe revisar cada GeoJSON en un mapa (p. ej. geojson.io).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[1]
SEMILLAS = RAIZ / "supabase" / "semillas"
OSRM = "https://router.project-osrm.org/route/v1/driving"
ESPACIADO_M = 400
MIN_PARADEROS, MAX_PARADEROS = 6, 12

# Orden de puntos de paso (docs/01 §2.2). El circuito se cierra volviendo al primero.
RUTAS = {
    "el-cable": ("El Cable", ["Terminal", "Carrera 23", "Fundadores", "El Cable"]),
    "centro": ("Centro", ["Terminal", "Catedral", "Parque de Caldas", "Fundadores"]),
    "la-enea": ("La Enea", ["Fundadores", "Carrera 23", "La Enea"]),
    "villamaria": ("Villamaría", ["Terminal", "Villamaría"]),
}


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Puntos como (lng, lat)."""
    r = 6371008.8
    f1, f2 = math.radians(a[1]), math.radians(b[1])
    df, dl = f2 - f1, math.radians(b[0] - a[0])
    h = math.sin(df / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def acumuladas(linea: list[list[float]]) -> list[float]:
    acc = [0.0]
    for i in range(1, len(linea)):
        acc.append(acc[-1] + haversine_m(tuple(linea[i - 1]), tuple(linea[i])))
    return acc


def pedir_trazado(cliente: httpx.Client, puntos: list[tuple[float, float]]) -> list[list[float]]:
    ruta = ";".join(f"{lng},{lat}" for lng, lat in puntos)
    r = cliente.get(f"{OSRM}/{ruta}", params={"overview": "full", "geometries": "geojson", "continue_straight": "false"})
    r.raise_for_status()
    datos = r.json()
    if datos.get("code") != "Ok":
        raise RuntimeError(f"OSRM respondió {datos.get('code')}")
    return [[round(x, 6), round(y, 6)] for x, y in datos["routes"][0]["geometry"]["coordinates"]]


def elegir_paraderos(linea: list[list[float]], hitos: list[dict]) -> list[dict]:
    """Hitos de paso + paraderos intermedios cada ~400 m, entre 6 y 12, ordenados por avance en el circuito."""
    acc = acumuladas(linea)
    largo = acc[-1]

    def avance(lng: float, lat: float) -> float:
        i = min(range(len(linea)), key=lambda k: haversine_m((lng, lat), tuple(linea[k])))
        return acc[i]

    fijos = [{"nombre": h["nombre"], "lat": h["lat"], "lng": h["lng"], "avance": avance(h["lng"], h["lat"]), "hito": True}
             for h in hitos]
    espaciado = float(ESPACIADO_M)
    for _ in range(30):
        extra = []
        d = espaciado
        while d < largo - espaciado / 2:
            if all(abs(d - f["avance"]) >= espaciado / 2 for f in fijos):
                j = min(range(len(acc)), key=lambda k: abs(acc[k] - d))
                extra.append({"nombre": None, "lat": linea[j][1], "lng": linea[j][0], "avance": acc[j], "hito": False})
            d += espaciado
        total = len(fijos) + len(extra)
        if total > MAX_PARADEROS:
            espaciado *= 1.25
        elif total < MIN_PARADEROS:
            espaciado *= 0.8
        else:
            break
    return sorted(fijos + extra, key=lambda p: p["avance"])


def main() -> int:
    ruta_hitos = SEMILLAS / "hitos.json"
    if not ruta_hitos.exists():
        print("Falta hitos.json: ejecuta primero scripts/geocodificar_hitos.py", file=sys.stderr)
        return 1
    hitos = {h["nombre"]: h for h in json.loads(ruta_hitos.read_text(encoding="utf-8"))}
    (SEMILLAS / "trazados").mkdir(exist_ok=True)
    with httpx.Client(headers={"User-Agent": "BusetasApp-prototipo-clase/0.1"}, timeout=60) as cliente:
        for slug, (nombre, paso) in RUTAS.items():
            puntos = [(hitos[n]["lng"], hitos[n]["lat"]) for n in paso]
            try:
                linea = pedir_trazado(cliente, [*puntos, puntos[0]])
            except (httpx.HTTPError, RuntimeError) as e:
                print(f"OSRM no respondió para {nombre} ({type(e).__name__}). Pide el GeoJSON al equipo; "
                      "no se inventan coordenadas.", file=sys.stderr)
                return 1
            paraderos = elegir_paraderos(linea, [hitos[n] for n in paso])
            contador = 0
            features = [{"type": "Feature", "properties": {"tipo": "trazado", "ruta": nombre, "ficticio": True,
                                                            "longitud_m": round(acumuladas(linea)[-1], 1)},
                         "geometry": {"type": "LineString", "coordinates": linea}}]
            for orden, p in enumerate(paraderos, start=1):
                if p["nombre"] is None:
                    contador += 1
                    p["nombre"] = f"Paradero {nombre} {contador}"
                features.append({"type": "Feature",
                                 "properties": {"tipo": "paradero", "orden": orden, "nombre": p["nombre"],
                                                "ficticio": True, "hito": p["hito"]},
                                 "geometry": {"type": "Point", "coordinates": [p["lng"], p["lat"]]}})
            salida = SEMILLAS / "trazados" / f"{slug}.geojson"
            salida.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                                         ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(f"{nombre}: {acumuladas(linea)[-1] / 1000:.1f} km, {len(linea)} puntos, {len(paraderos)} paraderos")
    print("Revisa cada GeoJSON en un mapa (geojson.io) antes de aprobarlo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
