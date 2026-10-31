"""Planificación sobre los datos de las SEMILLAS (GeoJSON de trazados y hitos.json) en memoria: sin base de datos.

El avance de cada paradero es el `avance_m` que genera `generar_trazados.py` con la misma regla que la función SQL
`progresos_paraderos_ruta` (secuencial por `orden`).
"""

from __future__ import annotations

import json
from datetime import time
from pathlib import Path
from uuid import NAMESPACE_DNS, UUID, uuid5

import pytest

from herramientas.simulador_gps import Circuito, haversine_m
from modulos.horarios import CalculadorTipoDia
from modulos.planificacion import PlanificarViaje
from modulos.planificacion.dominio.calculo import calcular_tiempos, mejor_recorrido_m
from pruebas.dobles import LUNES_MEDIODIA, ParametrosEnMemoria, RelojFijo

SEMILLAS = Path(__file__).resolve().parents[2] / "supabase" / "semillas"
SLUGS = ["la-enea", "villamaria", "el-cable", "centro"]
VELOCIDAD = 20.0  # velocidad_default_kmh


def _id(texto: str) -> UUID:
    return uuid5(NAMESPACE_DNS, texto)


def _cargar(slug: str) -> dict:
    datos = json.loads((SEMILLAS / "trazados" / f"{slug}.geojson").read_text(encoding="utf-8"))
    linea = next(f for f in datos["features"] if f["geometry"]["type"] == "LineString")
    paradas = [f["properties"] | {"coord": f["geometry"]["coordinates"]} for f in datos["features"] if f["geometry"]["type"] == "Point"]
    return {"slug": slug, "nombre": linea["properties"]["ruta"], "longitud": linea["properties"]["longitud_m"],
            "linea": linea["geometry"]["coordinates"], "paradas": sorted(paradas, key=lambda p: p["orden"])}


RUTAS = {s: _cargar(s) for s in SLUGS}


def _bus_min(recorrido_m: float) -> float:
    return calcular_tiempos(0, 0, recorrido_m, VELOCIDAD, 0).bus_min


def _recorrido(slug: str, origen: str, destino: str) -> float:
    paradas = RUTAS[slug]["paradas"]
    avance = lambda nombre: [p["avance_m"] for p in paradas if p["nombre"] == nombre]  # noqa: E731
    r = mejor_recorrido_m(avance(origen), avance(destino), RUTAS[slug]["longitud"])
    assert r is not None
    return r


# ---------- el avance secuencial de las semillas ----------


@pytest.mark.parametrize("slug", SLUGS)
def test_el_avance_secuencial_crece_con_el_orden_y_cabe_en_el_circuito(slug: str) -> None:
    ruta = RUTAS[slug]
    avances = [p["avance_m"] for p in ruta["paradas"]]
    assert avances == sorted(avances) and len(set(avances)) == len(avances)
    assert avances[0] == 0 and avances[-1] < ruta["longitud"]


@pytest.mark.parametrize("slug", SLUGS)
def test_ningun_par_de_paraderos_distintos_da_un_viaje_de_casi_cero(slug: str) -> None:
    paradas = RUTAS[slug]["paradas"]
    for o in paradas:
        for d in paradas:
            if o["nombre"] == d["nombre"]:
                continue
            recorrido = mejor_recorrido_m([o["avance_m"]], [d["avance_m"]], RUTAS[slug]["longitud"])
            assert recorrido is not None and _bus_min(recorrido) > 0.5, (slug, o["nombre"], d["nombre"], recorrido)


def test_la_enea_2_a_la_enea_son_6536_m_y_19_6_min() -> None:
    recorrido = _recorrido("la-enea", "Paradero La Enea 2", "La Enea")
    assert recorrido == pytest.approx(12247.0 - 5710.8, abs=0.5)
    assert _bus_min(recorrido) == pytest.approx(19.6, abs=0.1)  # nunca 2,8 min


def test_el_destino_atras_da_la_vuelta_al_circuito() -> None:
    ida = _recorrido("la-enea", "Paradero La Enea 2", "La Enea")
    vuelta = _recorrido("la-enea", "La Enea", "Paradero La Enea 2")
    assert ida + vuelta == pytest.approx(RUTAS["la-enea"]["longitud"], abs=1)


def _proyeccion_por_cercania(slug: str, nombre: str) -> float:
    """Lo que daría proyectar el paradero sobre el trazado por cercanía (sin la secuencia): el error que se corrigió."""
    circuito = Circuito.desde_geojson(RUTAS[slug]["linea"])
    lng, lat = next(p["coord"] for p in RUTAS[slug]["paradas"] if p["nombre"] == nombre)
    i = min(range(len(circuito.puntos)), key=lambda k: haversine_m(lat, lng, *circuito.puntos[k]))
    return circuito.acumuladas[i]


def test_villamaria_recorre_el_mismo_tramo_dos_veces_antes_y_despues() -> None:
    """Villamaría ida y vuelta por la misma vía: «Paradero Villamaría 4» (orden 6) está en la vuelta, pero por cercanía
    se proyecta sobre la IDA (2 200 m en vez de 3 895 m)."""
    sec_ida = _recorrido("villamaria", "Villamaría", "Paradero Villamaría 4")  # secuencial: 847 m
    sec_vuelta = _recorrido("villamaria", "Paradero Villamaría 4", "Villamaría")  # casi toda la vuelta
    longitud = RUTAS["villamaria"]["longitud"]
    plano_v4 = _proyeccion_por_cercania("villamaria", "Paradero Villamaría 4")
    plano_vi = _proyeccion_por_cercania("villamaria", "Villamaría")
    antes_ida = _bus_min((plano_v4 - plano_vi) % longitud)
    antes_vuelta = _bus_min((plano_vi - plano_v4) % longitud)
    # antes: la vuelta daba 2,5 min (subestimado) y la ida 21,3 min
    assert antes_vuelta == pytest.approx(2.5, abs=0.1) and antes_ida == pytest.approx(21.3, abs=0.2)
    # después: ida 2,5 min y vuelta 21,3 min
    assert _bus_min(sec_ida) == pytest.approx(2.5, abs=0.1) and _bus_min(sec_vuelta) == pytest.approx(21.3, abs=0.2)


def test_un_paradero_que_la_ruta_visita_dos_veces_toma_el_pase_mas_corto() -> None:
    longitud = 10000.0
    # origen pasa en 1000 y 6000; destino pasa en 2000 y 7000 → el menor recorrido es 1000 m
    assert mejor_recorrido_m([1000, 6000], [2000, 7000], longitud) == 1000
    # solo con el pase de ida del destino detrás del origen: da la vuelta
    assert mejor_recorrido_m([6000], [2000], longitud) == 6000
    assert mejor_recorrido_m([500], [500], longitud) is None  # mismo punto: no es un viaje


# ---------- planificador de punta a punta con las semillas ----------


class _Mundo:
    """Repositorios en memoria armados con paraderos, rutas y trazados de las semillas."""

    def __init__(self) -> None:
        self.paraderos: dict[UUID, dict] = {}
        self.rutas_de: dict[UUID, set[UUID]] = {}
        for slug, ruta in RUTAS.items():
            for p in ruta["paradas"]:
                pid = _id(p["nombre"])  # Fundadores, Terminal y Carrera 23 se comparten entre rutas
                self.paraderos[pid] = {"paradero_id": pid, "nombre": p["nombre"], "lat": p["coord"][1], "lng": p["coord"][0]}
                self.rutas_de.setdefault(pid, set()).add(_id("ruta-" + slug))
        self.hitos = {_id("hito-" + h["nombre"]): h for h in json.loads((SEMILLAS / "hitos.json").read_text(encoding="utf-8"))}
        self.parametros = ParametrosEnMemoria({"radio_caminata_m": 500, "max_opciones_viaje": 10})

    # RepositorioRutas (lo que el planificador usa)
    async def paraderos_cercanos(self, lat, lng, radio_m, ruta_id):
        cerca = [p | {"distancia_m": haversine_m(lat, lng, p["lat"], p["lng"])} for p in self.paraderos.values()]
        return sorted((p for p in cerca if p["distancia_m"] <= radio_m), key=lambda p: p["distancia_m"])

    async def paradero_mas_cercano(self, lat, lng):
        return min(await self.paraderos_cercanos(lat, lng, 10**9, None), key=lambda p: p["distancia_m"])

    async def resumenes(self, ruta_ids, distancias=None):
        por_id = {_id("ruta-" + s): r["nombre"] for s, r in RUTAS.items()}
        return [{"id": i, "nombre": por_id[i]} for i in ruta_ids]

    async def obtener_hito(self, hito_id):
        return self.hitos.get(hito_id)

    async def rutas_de_paraderos(self, paradero_ids):
        return {p: self.rutas_de[p] for p in paradero_ids if p in self.rutas_de}

    async def progresos_de_ruta(self, ruta_id):
        slug = next(s for s in SLUGS if _id("ruta-" + s) == ruta_id)
        return [{"orden": p["orden"], "paradero_id": _id(p["nombre"]), "progreso_m": p["avance_m"],
                 "longitud_m": RUTAS[slug]["longitud"]} for p in RUTAS[slug]["paradas"]]

    async def servicios_para_eta(self, ruta_id):
        return [{"servicio_id": _id("servicio-" + str(ruta_id)), "empresa_nombre": "Empresa", "codigo_publico": None,
                 "estado": "activo", "duracion_estandar_min": 60}]

    async def horarios_de(self, servicio_ids):
        return [{"servicio_id": s, "tipo_dia": "lun_vie", "primera_salida": time(4, 0), "ultima_salida": time(21, 0),
                 "cierre": time(22, 0), "nota": None} for s in servicio_ids]

    async def frecuencias_de(self, servicio_ids):
        return [{"servicio_id": s, "tipo_dia": "lun_vie", "inicio_minuto": 0, "fin_minuto": 1440, "minutos_min": 8,
                 "minutos_max": 10, "nota": None} for s in servicio_ids]

    def planificador(self) -> PlanificarViaje:
        return PlanificarViaje(
            self, self, self, self, self, CalculadorTipoDia(), self.parametros, RelojFijo(LUNES_MEDIODIA)
        )

    def hito(self, nombre: str) -> UUID:
        return next(i for i, h in self.hitos.items() if h["nombre"] == nombre)


@pytest.fixture
def mundo() -> _Mundo:
    return _Mundo()


async def test_caso_av_santander_a_la_enea_500_m_contra_1000_m(mundo: _Mundo) -> None:
    origen = {"lat": 5.0638, "lng": -75.4949}  # Av. Santander
    destino = {"hito_id": mundo.hito("La Enea")}
    cerca = await mundo.paraderos_cercanos(origen["lat"], origen["lng"], 1000, None)
    # antes (500 m): solo «Paradero El Cable 2», que no llega a La Enea; ahora (1000 m) aparece «Paradero La Enea 1» (652 m)
    assert [(p["nombre"], round(p["distancia_m"])) for p in cerca][:2] == [("Paradero El Cable 2", 205), ("Paradero La Enea 1", 652)]
    assert [p["nombre"] for p in await mundo.paraderos_cercanos(origen["lat"], origen["lng"], 500, None)] == ["Paradero El Cable 2"]

    mundo.parametros.valores["radio_caminata_m"] = 500
    antes = await mundo.planificador()(origen, destino)
    assert antes["opciones"] == []

    mundo.parametros.valores["radio_caminata_m"] = 1000
    despues = await mundo.planificador()(origen, destino)
    nombres = {(o["paradero_origen"]["nombre"], o["paradero_destino"]["nombre"]) for o in despues["opciones"]}
    assert ("Paradero La Enea 1", "La Enea") in nombres
    la_enea = next(o for o in despues["opciones"] if o["paradero_origen"]["nombre"] == "Paradero La Enea 1")
    assert la_enea["ruta_id"] == _id("ruta-la-enea")
    esperado = (12247.0 - 3836.4) / (VELOCIDAD / 3.6) / 60
    assert la_enea["bus_min"] == pytest.approx(esperado, abs=0.1) and la_enea["bus_min"] > 20  # ~25 min, no ~3


async def test_la_enea_2_a_la_enea_de_punta_a_punta(mundo: _Mundo) -> None:
    paradas = {p["nombre"]: p["coord"] for p in RUTAS["la-enea"]["paradas"]}
    o, d = paradas["Paradero La Enea 2"], paradas["La Enea"]
    r = await mundo.planificador()({"lat": o[1], "lng": o[0]}, {"lat": d[1], "lng": d[0]})
    [opcion] = [x for x in r["opciones"] if x["ruta_id"] == _id("ruta-la-enea")]
    assert opcion["paradero_origen"]["nombre"] == "Paradero La Enea 2" and opcion["paradero_destino"]["nombre"] == "La Enea"
    assert opcion["bus_min"] == pytest.approx(19.6, abs=0.1)


async def test_av_santander_a_villamaria_sugiere_la_ruta_del_cable_y_la_de_villamaria(mundo: _Mundo) -> None:
    """Hay paraderos cerca de ambos puntos pero de rutas que no se conectan: se devuelven las rutas junto a cada punto."""
    mundo.parametros.valores["radio_caminata_m"] = 500
    r = await mundo.planificador()({"lat": 5.0638, "lng": -75.4949}, {"hito_id": mundo.hito("Villamaría")})
    assert r["opciones"] == [] and r["motivo_codigo"] == "sin_ruta_directa"
    por_lado = {}
    for a in r["alternativas"]:
        por_lado.setdefault(a["lado"], []).append((a["ruta_nombre"], a["paradero"]["nombre"]))
    assert por_lado["origen"] == [("El Cable", "Paradero El Cable 2")]
    assert ("Villamaría", "Villamaría") in por_lado["destino"]
    assert r["paradero_mas_cercano"]["nombre"] == "Paradero El Cable 2"
