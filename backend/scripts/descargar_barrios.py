"""Descarga UNA vez los barrios de Manizales y Villamaría desde Overpass API (OpenStreetMap) y escribe
supabase/semillas/barrios.json. Misma idea que D-P10: el demo NO llama a internet; el archivo queda en el repo.

Datos: © OpenStreetMap contributors (ODbL, https://www.openstreetmap.org/copyright).
Uso (desde backend/):  python scripts/descargar_barrios.py
Cortesía con Overpass: una sola consulta, User-Agent identificable, reintentos espaciados y respeto de 429/504.
Nada se marca como validado: el equipo debe revisar los puntos (campo `validado`). No toca ninguna base de datos.
"""

from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "supabase" / "semillas" / "barrios.json"
ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
USER_AGENT = "BusetasApp-prototipo-clase/0.1 (proyecto academico; datos de ejemplo)"
ATRIBUCION = "© OpenStreetMap contributors (ODbL) · https://www.openstreetmap.org/copyright"

# Misma caja provisional que el parámetro `caja_ciudad` (docs/03 §6): descarta puntos fuera de la ciudad.
CAJA = {"min_lat": 4.95, "max_lat": 5.20, "min_lng": -75.65, "max_lng": -75.40}

# Límites administrativos reales de OSM (no se inventan polígonos): municipios de Manizales y Villamaría (en Colombia el
# municipio es admin_level 6; se aceptan 6 a 8). La caja evita homónimos de otros departamentos.
CONSULTA = """
[out:json][timeout:90];
(
  area["boundary"="administrative"]["admin_level"~"^(6|7|8)$"]["name"="Manizales"];
  area["boundary"="administrative"]["admin_level"~"^(6|7|8)$"]["name"="Villamaría"];
)->.zona;
nwr(4.95,-75.65,5.20,-75.40)(area.zona)["place"~"^(suburb|neighbourhood|quarter|city_block|locality)$"]["name"];
out center tags;
"""

PRIORIDAD_TIPO = {"suburb": 0, "neighbourhood": 1, "quarter": 2, "city_block": 3, "locality": 4}
# tipo_hito de la BD: barrios urbanos → `barrio`; place=locality (veredas, lugares rurales) → `sector`.
TIPO_HITO = {"suburb": "barrio", "neighbourhood": "barrio", "quarter": "barrio", "city_block": "barrio", "locality": "sector"}
PRIORIDAD_ELEMENTO = {"node": 0, "relation": 1, "way": 2}


def normalizar(texto: str) -> str:
    """minúsculas, sin tildes y con espacios colapsados (igual que `normalizar_texto` de la BD)."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return " ".join(sin_tildes.lower().split())


def dentro_de_caja(lat: float, lng: float) -> bool:
    return CAJA["min_lat"] <= lat <= CAJA["max_lat"] and CAJA["min_lng"] <= lng <= CAJA["max_lng"]


def consultar() -> dict:
    ultimo: Exception | None = None
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=120) as cliente:
        for intento in range(3):
            for url in ENDPOINTS:
                try:
                    r = cliente.post(url, data={"data": CONSULTA})
                    if r.status_code == 200:
                        return r.json()
                    ultimo = RuntimeError(f"HTTP {r.status_code} en {url}")
                except httpx.HTTPError as exc:
                    ultimo = exc
                time.sleep(5 * (intento + 1))  # espera creciente antes de reintentar (cortesía)
    raise SystemExit(f"Overpass no respondió tras varios intentos: {ultimo}")


def construir(elementos: list[dict]) -> tuple[list[dict], dict[str, list[str]]]:
    candidatos: list[dict] = []
    descartes: dict[str, list[str]] = {"sin_nombre": [], "fuera_de_caja": [], "sin_coordenadas": [], "duplicado": []}
    for e in elementos:
        tags = e.get("tags", {})
        nombre = " ".join((tags.get("name") or "").split())
        centro = e if e["type"] == "node" else e.get("center")
        if not nombre:
            descartes["sin_nombre"].append(f"{e['type']}/{e['id']}")
            continue
        if not centro or "lat" not in centro:
            descartes["sin_coordenadas"].append(nombre)
            continue
        lat, lng = float(centro["lat"]), float(centro["lon"])
        if not dentro_de_caja(lat, lng):
            descartes["fuera_de_caja"].append(nombre)
            continue
        candidatos.append({"nombre": nombre, "place": tags["place"], "lat": round(lat, 6), "lng": round(lng, 6),
                           "osm_tipo": e["type"], "osm_id": e["id"]})
    candidatos.sort(key=lambda c: (normalizar(c["nombre"]), PRIORIDAD_TIPO[c["place"]], PRIORIDAD_ELEMENTO[c["osm_tipo"]], c["osm_id"]))
    vistos: dict[str, dict] = {}
    for c in candidatos:
        clave = normalizar(c["nombre"])
        if clave in vistos:
            descartes["duplicado"].append(c["nombre"])
            continue
        vistos[clave] = c
    barrios = []
    for c in vistos.values():
        motivos = []
        if c["place"] == "locality":
            motivos.append("place=locality (puede ser rural o un lugar, no un barrio)")
        if re.search(r"\d", c["nombre"]) or not re.fullmatch(r"[\w .'\-ÁÉÍÓÚáéíóúÑñÜü]+", c["nombre"]):
            motivos.append("nombre con dígitos o caracteres inusuales")
        if len(c["nombre"]) > 40:
            motivos.append("nombre muy largo")
        barrios.append({
            "nombre": c["nombre"], "tipo": TIPO_HITO[c["place"]], "alias": sorted({normalizar(c["nombre"])}),
            "lat": c["lat"], "lng": c["lng"], "osm_tipo": c["osm_tipo"], "osm_id": c["osm_id"], "place": c["place"],
            "validado": False, **({"dudoso": motivos} if motivos else {}),
        })
    barrios.sort(key=lambda b: normalizar(b["nombre"]))
    return barrios, descartes


def main() -> int:
    respuesta = consultar()
    barrios, descartes = construir(respuesta.get("elements", []))
    salida = {
        "atribucion": ATRIBUCION,
        "fuente": "Overpass API (OpenStreetMap): place=suburb|neighbourhood|quarter|city_block|locality dentro de los "
                  "municipios de Manizales y Villamaría; se toma el centro de relaciones y vías",
        "descargado_en": datetime.now(UTC).date().isoformat(),
        "nota": "Coordenadas de OSM sin validar (validado:false). Revisar a mano antes de tratarlas como oficiales.",
        "total": len(barrios),
        "barrios": barrios,
    }
    DESTINO.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    por_place: dict[str, int] = {}
    for b in barrios:
        por_place[b["place"]] = por_place.get(b["place"], 0) + 1
    print(f"Barrios guardados: {len(barrios)} en {DESTINO.relative_to(RAIZ)}")
    print("Por place:", por_place)
    for motivo, lista in descartes.items():
        print(f"Descartados ({motivo}): {len(lista)}", lista[:10])
    dudosos = [b["nombre"] for b in barrios if "dudoso" in b]
    print(f"Dudosos ({len(dudosos)}):", dudosos)
    return 0


if __name__ == "__main__":
    sys.exit(main())
