"""Geocodifica los hitos UNA vez con Nominatim (OpenStreetMap) y escribe supabase/semillas/hitos.json.

Reglas de uso de Nominatim: máximo 1 petición por segundo y User-Agent propio. El equipo DEBE validar a mano
las coordenadas (campo `validado`); este script no las da por buenas. No toca ninguna base de datos.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "supabase" / "semillas" / "hitos.json"
URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "BusetasApp-prototipo-clase/0.1 (proyecto academico; datos de ejemplo)"

# Caja aproximada de Manizales y Villamaría, para descartar resultados de otras ciudades.
CAJA = {"min_lat": 4.95, "max_lat": 5.20, "min_lng": -75.65, "max_lng": -75.40}

# (nombre, tipo, alias, consultas en orden de preferencia). Nombres de docs/01 §2.3; La Enea y Villamaría se
# agregan como barrio/sector porque son puntos de paso de sus rutas y el ejemplo del bot («¿Qué ruta va a Villamaría?»).
HITOS = [
    ("Catedral", "hito", ["catedral", "la catedral", "catedral basilica"],
     ["Catedral Basílica Nuestra Señora del Rosario, Manizales", "Catedral de Manizales",
      "Catedral Basílica de Manizales", "Catedral, Manizales, Caldas"]),
    ("El Cable", "hito", ["cable", "el cable", "estacion cable"],
     ["Estación Cable Aéreo Manizales", "El Cable, Manizales"]),
    ("Carrera 23", "hito", ["carrera 23", "cra 23", "kr 23", "cra. 23"],
     ["Carrera 23 con Calle 23, Manizales", "Carrera 23, Manizales"]),
    ("Fundadores", "hito", ["fundadores", "monumento a los fundadores", "los fundadores"],
     ["Monumento a los Fundadores, Manizales", "Fundadores, Manizales"]),
    ("Terminal", "terminal", ["terminal", "terminal de transportes", "terminal de manizales"],
     ["Terminal de Transportes de Manizales"]),
    ("Parque de Caldas", "hito", ["parque de caldas", "parque caldas", "plaza de bolivar", "parque"],
     ["Parque Caldas, Manizales", "Parque de Caldas, Manizales"]),
    ("La Enea", "barrio", ["la enea", "enea", "barrio la enea"],
     ["La Enea, Manizales"]),
    ("Villamaría", "sector", ["villamaria", "villa maria", "villamaría"],
     ["Villamaría, Caldas"]),
]


def dentro_de_caja(lat: float, lng: float) -> bool:
    return CAJA["min_lat"] <= lat <= CAJA["max_lat"] and CAJA["min_lng"] <= lng <= CAJA["max_lng"]


def buscar(cliente: httpx.Client, consulta: str) -> dict | None:
    time.sleep(1.1)  # <= 1 petición por segundo
    r = cliente.get(URL, params={"q": consulta, "format": "jsonv2", "limit": 5, "countrycodes": "co"})
    r.raise_for_status()
    for item in r.json():
        lat, lng = float(item["lat"]), float(item["lon"])
        if dentro_de_caja(lat, lng):
            return {"lat": round(lat, 6), "lng": round(lng, 6), "consulta": consulta, "mostrado": item["display_name"]}
    return None


def main() -> int:
    resultado, faltantes = [], []
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30) as cliente:
        for nombre, tipo, alias, consultas in HITOS:
            hallado = None
            for consulta in consultas:
                hallado = buscar(cliente, consulta)
                if hallado:
                    break
            if not hallado:
                faltantes.append(nombre)
                continue
            resultado.append({"nombre": nombre, "tipo": tipo, "alias": alias, "validado": False, **hallado})
            print(f"{nombre}: {hallado['lat']}, {hallado['lng']}")
    if faltantes:
        print("SIN RESULTADO (completar a mano en hitos.json):", ", ".join(faltantes), file=sys.stderr)
        return 1
    DESTINO.write_text(json.dumps(resultado, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Escrito {DESTINO}. Revisa cada punto en un mapa y marca validado=true.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
