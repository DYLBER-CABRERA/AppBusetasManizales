"""Barrios de Manizales como hitos: capa oficial de la Alcaldía + veredas de OSM. Archivos, carga y búsqueda, sin base de datos."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cargar_semillas import CAJA, cargar_barrios, normalizar, validar_barrios
from composicion import construir_contenedor
from generar_barrios_alcaldia import (
    barrios_oficiales,
    combinar,
    nombre_legible,
    poligonos_de,
    punto_en_poligono,
    punto_representativo,
)
from modulos.busqueda.dominio.servicios import normalizar_consulta
from nucleo.configuracion import Configuracion
from nucleo.reloj import RelojSimulado
from pruebas import dobles
from pruebas.dobles import RelojFijo
from servidor import crear_app

SEMILLAS = Path(__file__).resolve().parents[2] / "supabase" / "semillas"
ARCHIVO = json.loads((SEMILLAS / "barrios.json").read_text(encoding="utf-8"))
BARRIOS = ARCHIVO["barrios"]
OFICIALES = [b for b in BARRIOS if b["fuente"] == "alcaldia"]
OSM = [b for b in BARRIOS if b["fuente"] == "osm"]
GEOJSON = json.loads((SEMILLAS / "fuentes" / "barrios_alcaldia.geojson").read_text(encoding="utf-8"))
HITOS = json.loads((SEMILLAS / "hitos.json").read_text(encoding="utf-8"))


# ---------- archivos ----------


def test_atribuciones_de_las_dos_fuentes() -> None:
    assert "Alcaldía de Manizales" in ARCHIVO["atribucion"] and "589 de 2004" in ARCHIVO["atribucion"]
    assert "1038 de 2019" in ARCHIVO["atribucion"] and "OpenStreetMap contributors (ODbL)" in ARCHIVO["atribucion"]
    assert "2026-11-02" in ARCHIVO["fuentes"]["alcaldia"]
    leeme = (SEMILLAS / "fuentes" / "LEEME.md").read_text(encoding="utf-8")
    assert "53ddc71c63e9474486a44af3ef334684" in leeme and "2026-11-02" in leeme
    docs = (SEMILLAS.parents[2] / "docs" / "01-alcance-y-datos-simulados.md").read_text(encoding="utf-8")
    assert "Acuerdos Municipales 589 de 2004 y 1038 de 2019" in docs and "OpenStreetMap contributors (ODbL)" in docs


def test_el_archivo_generado_es_valido_sin_duplicados_y_dentro_de_la_caja() -> None:
    assert validar_barrios(BARRIOS) == []
    assert ARCHIVO["total"] == len(BARRIOS) == len(OFICIALES) + len(OSM)
    nombres = [normalizar(b["nombre"]) for b in BARRIOS]
    assert len(nombres) == len(set(nombres))
    assert all(b["validado"] is False for b in BARRIOS)  # son puntos representativos, no hitos exactos
    for b in BARRIOS:
        assert CAJA["min_lat"] <= b["lat"] <= CAJA["max_lat"] and CAJA["min_lng"] <= b["lng"] <= CAJA["max_lng"]
        assert all(a == normalizar(a) for a in b["alias"])  # alias en minúsculas y sin tildes
        assert b["tipo"] in ("barrio", "sector")


def test_114_barrios_oficiales_menos_los_que_ya_son_hitos_originales() -> None:
    assert len({normalizar(f["properties"]["BARRIOS"]) for f in GEOJSON["features"]}) == 114  # 116 polígonos
    assert len(OFICIALES) == 112 and all(b["tipo"] == "barrio" for b in OFICIALES)
    originales = {normalizar(h["nombre"]) for h in HITOS}
    assert originales.isdisjoint(normalizar(b["nombre"]) for b in BARRIOS)  # La Enea y Fundadores no se duplican
    assert {normalizar(b["nombre"]) for b in OFICIALES} >= {"caserio la enea", "san sebastian", "fatima"}


def test_cada_punto_cae_dentro_de_su_poligono() -> None:
    por_nombre: dict[str, list] = {}
    for f in GEOJSON["features"]:
        por_nombre.setdefault(normalizar(f["properties"]["BARRIOS"]), []).extend(poligonos_de(f))
    for b in OFICIALES:
        poligonos = por_nombre[normalizar(b["nombre_original"])]
        assert any(punto_en_poligono(b["lng"], b["lat"], p) for p in poligonos), b["nombre"]


def test_barrios_con_poligonos_repetidos_se_fusionan_en_uno() -> None:
    repetidos = [b for b in OFICIALES if b["poligonos"] > 1]
    assert repetidos and next(b for b in OFICIALES if b["nombre"] == "Puerta del Sol (Corinto)")["poligonos"] == 3
    assert len([b for b in OFICIALES if "puerta del sol" in normalizar(b["nombre"])]) == 1


def test_los_nombres_legibles_y_la_enie_vienen_bien_de_la_fuente() -> None:
    nombres = {b["nombre"] for b in OFICIALES}
    assert {"San Sebastián", "Fátima", "Bella Montaña", "Belén", "Pío XII", "20 de Julio", "Cerros de la Alhambra"} <= nombres
    assert not any("�" in n for n in nombres)  # 'Ñ' es U+00D1 en la fuente: no hay carácter corrupto
    assert "Buena Esperanza" in nombres and "buena espernza" in next(b for b in OFICIALES if b["nombre"] == "Buena Esperanza")["alias"]
    assert nombre_legible("LA ASUNCION") == "La Asunción" and nombre_legible("SAN CANCIO") == "San Cancio"  # sin tilde si no es seguro


def test_el_punto_interior_funciona_en_poligonos_concavos() -> None:
    forma_l = [[[0, 0], [10, 0], [10, 1], [1, 1], [1, 10], [0, 10], [0, 0]]]  # centroide fuera
    lng, lat = punto_representativo(forma_l)
    assert punto_en_poligono(lng, lat, forma_l)
    con_hueco = [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]], [[3, 3], [7, 3], [7, 7], [3, 7], [3, 3]]]
    lng, lat = punto_representativo(con_hueco)
    assert punto_en_poligono(lng, lat, con_hueco) and not (3 < lng < 7 and 3 < lat < 7)


def test_combinar_reglas_de_oficiales_y_osm() -> None:
    oficiales = [{"nombre": "San Antonio", "tipo": "barrio", "alias": ["san antonio"]}, {"nombre": "La Enea", "tipo": "barrio", "alias": ["la enea"]},
                 {"nombre": "Turín", "tipo": "barrio", "alias": ["turin"]}]
    osm = [{"nombre": "San Antonio", "tipo": "sector", "alias": ["san antonio"]}, {"nombre": "Turín", "tipo": "barrio", "alias": ["turin"]},
           {"nombre": "Albania", "tipo": "sector", "alias": ["albania"]}]
    resultado, notas = combinar(oficiales, osm, {"la enea"})
    assert [b["nombre"] for b in resultado] == ["Albania", "San Antonio", "San Antonio (vereda)", "Turín"]
    assert notas["omitidos_hito_original"] == ["La Enea"] and notas["osm_reemplazado"] == ["Turín"]
    assert notas["vereda_renombrada"] == ["San Antonio (vereda)"]
    assert "san antonio" in next(b for b in resultado if b["nombre"] == "San Antonio (vereda)")["alias"]


def test_barrios_oficiales_es_reproducible() -> None:
    assert [(b["nombre"], b["lat"], b["lng"]) for b in barrios_oficiales(GEOJSON) if b["nombre"] in ("Fátima", "San Sebastián")] == [
        (b["nombre"], b["lat"], b["lng"]) for b in OFICIALES if b["nombre"] in ("Fátima", "San Sebastián")]


def test_la_validacion_detecta_duplicados_fuera_de_caja_y_alias_malos() -> None:
    base = {"nombre": "Fátima", "tipo": "barrio", "alias": ["fatima"], "lat": 5.07, "lng": -75.52}
    assert validar_barrios([base]) == []
    assert any("duplicado" in p for p in validar_barrios([base, {**base, "nombre": "FATIMA"}]))
    assert any("fuera de la caja" in p for p in validar_barrios([{**base, "lat": 6.5}]))
    assert any("alias" in p for p in validar_barrios([{**base, "alias": ["Fátima"]}]))
    assert any("tipo" in p for p in validar_barrios([{**base, "tipo": "vereda"}]))
    assert any("sin nombre" in p for p in validar_barrios([{**base, "nombre": " "}]))


# ---------- carga a la BD (conexión simulada) ----------


class _Resultado:
    def __init__(self, fila=None) -> None:
        self._fila = fila

    def fetchone(self):
        return self._fila


class ConexionFalsa:
    """Simula `hito`: busca por nombre normalizado y registra inserciones y actualizaciones."""

    def __init__(self, existentes: dict[str, dict]) -> None:
        self.existentes = existentes  # nombre normalizado → {id, tipo, lat, lng, nombre}
        self.inserts: list[tuple] = []
        self.updates: list[tuple] = []

    def execute(self, sql: str, params: tuple = ()):
        if sql.startswith("select id, tipo"):
            lng, lat, nombre = params
            h = self.existentes.get(normalizar(nombre))
            if h is None:
                return _Resultado(None)
            metros = ((h["lat"] - lat) ** 2 + (h["lng"] - lng) ** 2) ** 0.5 * 111_000
            return _Resultado((h["id"], h["tipo"], metros, h.get("nombre", nombre)))
        if sql.startswith("insert into hito"):
            self.inserts.append(params)
        elif sql.startswith("update hito"):
            self.updates.append(params)
        return _Resultado(None)


def _barrio(nombre: str, fuente: str = "alcaldia", tipo: str = "barrio", lat: float = 5.07, lng: float = -75.51) -> dict:
    return {"nombre": nombre, "tipo": tipo, "alias": [normalizar(nombre)], "lat": lat, "lng": lng, "fuente": fuente}


def test_la_carga_inserta_actualiza_solo_la_capa_oficial_y_no_toca_los_originales() -> None:
    existentes = {
        "turin": {"id": 1, "tipo": "barrio", "lat": 5.0364, "lng": -75.5097},  # cargado desde OSM, coordenada distinta
        "san antonio": {"id": 2, "tipo": "sector", "lat": 5.0015, "lng": -75.4311},  # vereda de OSM con nombre de barrio
        "catedral": {"id": 3, "tipo": "hito", "lat": 5.0674, "lng": -75.5173},  # hito original
        "la enea": {"id": 4, "tipo": "barrio", "lat": 5.0318, "lng": -75.4631},  # hito original (tipo barrio)
        "igual": {"id": 5, "tipo": "barrio", "lat": 5.07, "lng": -75.51},  # ya está igual
        "caserio la enea": {"id": 7, "tipo": "barrio", "lat": 5.07, "lng": -75.51, "nombre": "Caserio La Enea"},  # solo cambia la tilde
        "osm viejo": {"id": 6, "tipo": "sector", "lat": 5.0, "lng": -75.4},  # existe y viene de OSM: no se actualiza
    }
    conexion = ConexionFalsa(existentes)
    barrios = [
        _barrio("Turín", lat=5.0400, lng=-75.5100),  # oficial, difiere → actualiza
        _barrio("San Antonio"),  # oficial: reemplaza la vereda (la vereda vuelve como «San Antonio (vereda)»)
        _barrio("San Antonio (vereda)", fuente="osm", tipo="sector", lat=5.0015, lng=-75.4311),  # nuevo
        _barrio("Catedral"),  # oficial pero es hito original → no se toca
        _barrio("La Enea"),  # protegido por nombre → no se toca
        _barrio("Igual"),  # sin cambios
        _barrio("Osm Viejo", fuente="osm", tipo="sector", lat=5.5, lng=-75.4),  # existente de OSM → se omite
        _barrio("Fátima"),  # nuevo
        _barrio("Caserío La Enea"),  # oficial, mismo punto: solo se corrige el nombre
    ]
    nota = cargar_barrios(conexion, barrios, {"catedral", "la enea"})
    assert [p[0] for p in conexion.inserts] == ["San Antonio (vereda)", "Fátima"]
    assert sorted(p[-1] for p in conexion.updates) == [1, 2, 7]  # Turín, San Antonio y Caserío (nombre), por id
    assert nota == "Barrios: 2 nuevos, 3 actualizados (capa oficial), 4 sin cambios (sin validar)"
    # idempotente: con los mismos datos ya cargados no cambia nada
    repetida = ConexionFalsa({normalizar(b["nombre"]): {"id": i, "tipo": b["tipo"], "lat": b["lat"], "lng": b["lng"]}
                              for i, b in enumerate(barrios)})
    cargar_barrios(repetida, barrios, {"catedral", "la enea"})
    assert repetida.inserts == [] and repetida.updates == []


# ---------- búsqueda con los datos reales del archivo ----------


def _cliente(hitos: list[dict]) -> TestClient:
    repos = dobles.repositorios_en_memoria()
    repos.busqueda = dobles.BusquedaConHitos(hitos)
    cont = construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(RelojFijo()))
    return TestClient(crear_app(cont), raise_server_exceptions=False)


@pytest.fixture
def cliente() -> TestClient:
    return _cliente(HITOS + BARRIOS)  # datos reales del archivo (sin inyectar nada)


def _nombres(cliente: TestClient, q: str) -> list[str]:
    r = cliente.get("/api/v1/busqueda/hitos", params={"q": q})
    assert r.status_code == 200
    return [h["nombre"] for h in r.json()]


@pytest.mark.parametrize("q", ["fatima", "Fátima", "FATIMA", "  fátima "])
def test_fatima_se_encuentra_con_y_sin_tildes(cliente: TestClient, q: str) -> None:
    assert _nombres(cliente, q) == ["Fátima"]


@pytest.mark.parametrize("q", ["san sebastian", "San Sebastián", "SAN SEBASTIÁN"])
def test_san_sebastian_se_encuentra_con_y_sin_tildes(cliente: TestClient, q: str) -> None:
    assert _nombres(cliente, q) == ["San Sebastián"]


def test_todos_los_barrios_del_archivo_se_buscan_por_su_nombre(cliente: TestClient) -> None:
    for b in BARRIOS:
        assert b["nombre"] in _nombres(cliente, normalizar_consulta(b["nombre"])), b["nombre"]


def test_san_antonio_devuelve_el_barrio_y_la_vereda_con_el_barrio_primero(cliente: TestClient) -> None:
    assert _nombres(cliente, "san antonio") == ["San Antonio", "San Antonio (vereda)"]


def test_busqueda_parcial_sebas_ordena_razonable(cliente: TestClient) -> None:
    resultado = _nombres(cliente, "sebas")
    assert resultado == ["San Sebastián"]  # en el archivo real solo hay uno
    # con varios candidatos: primero los que empiezan por el texto, luego los que lo contienen
    c = _cliente([
        {"nombre": "Villa San Sebastián", "tipo": "barrio", "alias": ["villa san sebastian"], "lat": 5.05, "lng": -75.5},
        {"nombre": "San Sebastián", "tipo": "barrio", "alias": ["san sebastian"], "lat": 5.06, "lng": -75.5},
        {"nombre": "Sebastopol", "tipo": "barrio", "alias": ["sebastopol"], "lat": 5.07, "lng": -75.5},
    ])
    assert _nombres(c, "sebas") == ["Sebastopol", "San Sebastián", "Villa San Sebastián"]


def test_busqueda_respeta_el_maximo_de_20_resultados(cliente: TestClient) -> None:
    nombres = _nombres(cliente, "la")  # «la» está en decenas de nombres reales
    assert len(nombres) == 20


def test_el_sql_de_busqueda_ordena_exacto_luego_prefijo_luego_alfabetico() -> None:
    sql = (Path(__file__).resolve().parents[2] / "src/modulos/busqueda/infraestructura/repositorio_sql.py").read_text(encoding="utf-8")
    cuerpo = sql[sql.index("async def buscar_hitos"):]
    assert "order by (normalizar_texto(h.nombre) = %(texto)s" in cuerpo and "unnest(h.alias)" in cuerpo
    assert "starts_with(normalizar_texto(h.nombre), %(texto)s) desc" in cuerpo and "limit 20" in cuerpo
