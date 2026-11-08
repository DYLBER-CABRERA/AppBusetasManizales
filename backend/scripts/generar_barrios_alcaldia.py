"""Genera supabase/semillas/barrios.json desde la capa OFICIAL de barrios de la Alcaldía de Manizales (+ las veredas de OSM).

Entradas (versionadas, sin internet):
  - supabase/semillas/fuentes/barrios_alcaldia.geojson  (polígonos, EPSG:4326; ver fuentes/LEEME.md)
  - supabase/semillas/fuentes/barrios_osm.json          (descarga de OSM de scripts/descargar_barrios.py)
  - supabase/semillas/hitos.json                        (los hitos originales, que no se tocan)
Salida: supabase/semillas/barrios.json. Python puro, sin dependencias nuevas. El GeoJSON se trata como dato no confiable:
solo se lee como JSON y se valida; nunca se ejecuta nada de él.

Uso (desde backend/):  python scripts/generar_barrios_alcaldia.py
Reglas:
  - Un barrio por nombre normalizado (sin tildes, minúsculas); los polígonos repetidos se fusionan y se toma el mayor.
  - Punto representativo DENTRO del polígono: el centroide si cae dentro; si no, el punto más interior (búsqueda en rejilla).
  - Los barrios oficiales reemplazan a los barrios urbanos de OSM con el mismo nombre; las veredas de OSM (tipo `sector`) se
    conservan. Si una vereda se llama como un barrio oficial se renombra «Nombre (vereda)» y conserva el alias original.
  - Un barrio oficial con el mismo nombre que uno de los hitos originales (La Enea, Fundadores…) no se incluye.
"""

from __future__ import annotations

import json
import math
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SEMILLAS = RAIZ / "supabase" / "semillas"
FUENTE_ALCALDIA = SEMILLAS / "fuentes" / "barrios_alcaldia.geojson"
FUENTE_OSM = SEMILLAS / "fuentes" / "barrios_osm.json"
DESTINO = SEMILLAS / "barrios.json"
CAJA = {"min_lat": 4.95, "max_lat": 5.20, "min_lng": -75.65, "max_lng": -75.40}  # = parámetro caja_ciudad
DESCARGADO_EN = "2026-11-02"
ATRIBUCION = (
    "Barrios urbanos: Alcaldía de Manizales, «Límite de barrios Municipio de Manizales» (Acuerdos Municipales 589 de 2004 y "
    "1038 de 2019), https://sig.manizales.gov.co/wadmzl/rest/services/20_WEB/2021_consulta_catas_urbano_web/FeatureServer/1. "
    "Veredas y otros lugares: © OpenStreetMap contributors (ODbL), https://www.openstreetmap.org/copyright"
)

# Corrección explícita y pequeña de tildes y ortografía (solo donde la forma correcta es segura); el resto queda como en la fuente.
CORRECCIONES = {
    "SAN SEBASTIAN": "San Sebastián", "FATIMA": "Fátima", "BELEN": "Belén", "COLON": "Colón", "PIO XII": "Pío XII",
    "GALAN": "Galán", "GONZALEZ": "González", "FANNY GONZALEZ": "Fanny González", "MILAN": "Milán",
    "SAN JOAQUIN": "San Joaquín", "SAN JOSE": "San José", "SINAI": "Sinaí", "VELEZ": "Vélez", "EL CAMPIN": "El Campín",
    "EL PARAISO": "El Paraíso", "EL TREBOL": "El Trébol", "LA ASUNCION": "La Asunción", "LAS AMERICAS": "Las Américas",
    "LOS ALCAZARES": "Los Alcázares", "BELLA MONTAÑA": "Bella Montaña", "CASERIO LA ENEA": "Caserío La Enea",
    "BUENA ESPERNZA": "Buena Esperanza",  # errata evidente de la fuente (ESPERNZA); el alias conserva la forma original
    "PUERTA DEL SOL(Corinto)": "Puerta del Sol (Corinto)",
}
MINUSCULAS = {"de", "del"}


def normalizar(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return " ".join(sin_tildes.lower().split())


def nombre_legible(original: str) -> str:
    original = " ".join(original.split())
    if original in CORRECCIONES:
        return CORRECCIONES[original]
    palabras = re.sub(r"\(", " (", original).split()
    salida: list[str] = []
    for i, p in enumerate(palabras):
        minuscula = p.lower()
        if re.fullmatch(r"[IVXLC]+", p):
            salida.append(p)  # numerales romanos
        elif i > 0 and (minuscula in MINUSCULAS or (minuscula in {"la", "las", "los"} and salida[-1] == "de")):
            salida.append(minuscula)
        else:
            salida.append(p[:1].upper() + p[1:].lower())
    return " ".join(salida)


# ------------------------------------------------------------------ geometría plana (grados escalados por cos(lat))
def _escala(lat: float) -> float:
    return math.cos(math.radians(lat))


def _anillo_xy(anillo: list[list[float]], k: float) -> list[tuple[float, float]]:
    return [(p[0] * k, p[1]) for p in anillo]


def area_anillo(a: list[tuple[float, float]]) -> float:
    return sum(a[i][0] * a[(i + 1) % len(a)][1] - a[(i + 1) % len(a)][0] * a[i][1] for i in range(len(a))) / 2


def punto_en_anillo(x: float, y: float, a: list[tuple[float, float]]) -> bool:
    dentro = False
    j = len(a) - 1
    for i in range(len(a)):
        xi, yi, xj, yj = *a[i], *a[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            dentro = not dentro
        j = i
    return dentro


def punto_en_poligono(lng: float, lat: float, poligono: list[list[list[float]]]) -> bool:
    """`poligono` = [anillo exterior, huecos…] en [lng, lat]. Dentro del exterior y fuera de los huecos."""
    if not punto_en_anillo(lng, lat, [tuple(p[:2]) for p in poligono[0]]):
        return False
    return not any(punto_en_anillo(lng, lat, [tuple(p[:2]) for p in h]) for h in poligono[1:])


def area_poligono(poligono: list[list[list[float]]]) -> float:
    k = _escala(poligono[0][0][1])
    return abs(area_anillo(_anillo_xy(poligono[0], k))) - sum(abs(area_anillo(_anillo_xy(h, k))) for h in poligono[1:])


def centroide(poligono: list[list[list[float]]]) -> tuple[float, float]:
    k = _escala(poligono[0][0][1])
    a = _anillo_xy(poligono[0], k)
    area = area_anillo(a)
    if abs(area) < 1e-18:
        return sum(p[0] for p in poligono[0]) / len(poligono[0]), sum(p[1] for p in poligono[0]) / len(poligono[0])
    cx = cy = 0.0
    for i in range(len(a)):
        x0, y0, x1, y1 = *a[i], *a[(i + 1) % len(a)]
        cruce = x0 * y1 - x1 * y0
        cx += (x0 + x1) * cruce
        cy += (y0 + y1) * cruce
    return cx / (6 * area) / k, cy / (6 * area)


def _distancia_a_bordes(x: float, y: float, anillos: list[list[tuple[float, float]]]) -> float:
    mejor = math.inf
    for a in anillos:
        for i in range(len(a)):
            x0, y0, x1, y1 = *a[i], *a[(i + 1) % len(a)]
            dx, dy = x1 - x0, y1 - y0
            largo = dx * dx + dy * dy
            t = 0.0 if largo == 0 else max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / largo))
            mejor = min(mejor, math.hypot(x - (x0 + t * dx), y - (y0 + t * dy)))
    return mejor


def punto_mas_interior(poligono: list[list[list[float]]]) -> tuple[float, float]:
    """Punto dentro del polígono lo más lejos posible de sus bordes (rejilla refinada; sin dependencias)."""
    k = _escala(poligono[0][0][1])
    anillos = [_anillo_xy(a, k) for a in poligono]
    xs, ys = [p[0] for p in anillos[0]], [p[1] for p in anillos[0]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    mejor, mejor_d = None, -1.0
    for _ in range(4):
        pasos = 40
        for i in range(pasos + 1):
            for j in range(pasos + 1):
                x, y = x0 + (x1 - x0) * i / pasos, y0 + (y1 - y0) * j / pasos
                if punto_en_anillo(x, y, anillos[0]) and not any(punto_en_anillo(x, y, h) for h in anillos[1:]):
                    d = _distancia_a_bordes(x, y, anillos)
                    if d > mejor_d:
                        mejor, mejor_d = (x, y), d
        if mejor is None:
            raise ValueError("el polígono no tiene puntos interiores")
        ancho, alto = (x1 - x0) / 8, (y1 - y0) / 8
        x0, x1, y0, y1 = mejor[0] - ancho, mejor[0] + ancho, mejor[1] - alto, mejor[1] + alto
    return mejor[0] / k, mejor[1]


def punto_representativo(poligono: list[list[list[float]]]) -> tuple[float, float]:
    lng, lat = centroide(poligono)
    if punto_en_poligono(lng, lat, poligono):
        return lng, lat
    return punto_mas_interior(poligono)


def poligonos_de(feature: dict) -> list[list[list[list[float]]]]:
    g = feature["geometry"]
    if g["type"] == "Polygon":
        return [g["coordinates"]]
    if g["type"] == "MultiPolygon":
        return g["coordinates"]
    raise ValueError(f"geometría no soportada: {g['type']}")


# ------------------------------------------------------------------ construcción
def barrios_oficiales(geojson: dict) -> list[dict]:
    por_nombre: dict[str, dict] = {}
    for f in geojson["features"]:
        original = " ".join(str(f["properties"]["BARRIOS"]).split())
        clave = normalizar(original)
        entrada = por_nombre.setdefault(clave, {"original": original, "poligonos": [], "comunas": set()})
        entrada["poligonos"] += poligonos_de(f)
        entrada["comunas"].add(str(f["properties"].get("Id_Comuna") or ""))
    barrios = []
    for entrada in por_nombre.values():
        mayor = max(entrada["poligonos"], key=area_poligono)  # el polígono más grande representa al barrio
        lng, lat = punto_representativo(mayor)
        nombre = nombre_legible(entrada["original"])
        alias = {normalizar(nombre), normalizar(entrada["original"])}
        barrios.append({
            "nombre": nombre, "tipo": "barrio", "alias": sorted(alias), "lat": round(lat, 6), "lng": round(lng, 6),
            "fuente": "alcaldia", "comuna": sorted(c for c in entrada["comunas"] if c)[0] if entrada["comunas"] else None,
            "poligonos": len(entrada["poligonos"]), "nombre_original": entrada["original"], "validado": False,
        })
    return barrios


def combinar(oficiales: list[dict], osm: list[dict], hitos_originales: set[str]) -> tuple[list[dict], dict[str, list[str]]]:
    notas: dict[str, list[str]] = {"omitidos_hito_original": [], "osm_reemplazado": [], "vereda_renombrada": [], "osm_conservado": []}
    resultado = []
    for b in oficiales:
        if normalizar(b["nombre"]) in hitos_originales:
            notas["omitidos_hito_original"].append(b["nombre"])
            continue
        resultado.append(b)
    nombres_oficiales = {normalizar(b["nombre"]) for b in resultado}
    nombres_oficiales |= {a for b in resultado for a in b["alias"]}
    for o in osm:
        clave = normalizar(o["nombre"])
        if o["tipo"] == "barrio" and clave in nombres_oficiales:
            notas["osm_reemplazado"].append(o["nombre"])  # el oficial gana: no se duplica
            continue
        o = {**o, "fuente": "osm"}
        if clave in nombres_oficiales or clave in hitos_originales:  # vereda con el nombre de un barrio: se distingue
            o["nombre"] = f"{o['nombre']} (vereda)"
            o["alias"] = sorted({clave, normalizar(o["nombre"])})
            notas["vereda_renombrada"].append(o["nombre"])
        else:
            notas["osm_conservado"].append(o["nombre"])
        resultado.append(o)
    resultado.sort(key=lambda b: normalizar(b["nombre"]))
    return resultado, notas


def main() -> int:
    geojson = json.loads(FUENTE_ALCALDIA.read_text(encoding="utf-8"))
    osm = json.loads(FUENTE_OSM.read_text(encoding="utf-8"))["barrios"]
    hitos = {normalizar(h["nombre"]) for h in json.loads((SEMILLAS / "hitos.json").read_text(encoding="utf-8"))}
    oficiales = barrios_oficiales(geojson)
    barrios, notas = combinar(oficiales, osm, hitos)
    fuera = [b["nombre"] for b in barrios if not (CAJA["min_lat"] <= b["lat"] <= CAJA["max_lat"] and CAJA["min_lng"] <= b["lng"] <= CAJA["max_lng"])]
    if fuera:
        print("Fuera de la caja de la ciudad:", fuera, file=sys.stderr)
        return 1
    salida = {
        "atribucion": ATRIBUCION,
        "fuentes": {
            "alcaldia": f"fuentes/barrios_alcaldia.geojson (descargado {DESCARGADO_EN} de la API pública del ArcGIS de la Alcaldía)",
            "osm": "fuentes/barrios_osm.json (Overpass API, scripts/descargar_barrios.py)",
        },
        "generado_en": date.today().isoformat(),
        "nota": "Puntos representativos (interiores al polígono) de cada barrio, no hitos exactos: validado:false. "
                "`comuna` y `nombre_original` son informativos y no se cargan a la BD.",
        "total": len(barrios),
        "barrios": barrios,
    }
    DESTINO.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Barrios oficiales: {len(oficiales)} (de {len(geojson['features'])} polígonos) · total en barrios.json: {len(barrios)}")
    for clave, lista in notas.items():
        print(f"{clave} ({len(lista)}): {lista}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
