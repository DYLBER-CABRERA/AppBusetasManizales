"""Barrios y sectores de OpenStreetMap como hitos: archivo de semilla, validación y búsqueda (sin base de datos)."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import NAMESPACE_DNS, UUID, uuid5

import pytest
from fastapi.testclient import TestClient

from cargar_semillas import CAJA, normalizar, validar_barrios
from composicion import construir_contenedor
from modulos.busqueda.dominio.servicios import normalizar_consulta
from nucleo.configuracion import Configuracion
from nucleo.reloj import RelojSimulado
from pruebas import dobles
from pruebas.dobles import RelojFijo
from servidor import crear_app

SEMILLAS = Path(__file__).resolve().parents[2] / "supabase" / "semillas"
ARCHIVO = json.loads((SEMILLAS / "barrios.json").read_text(encoding="utf-8"))
BARRIOS = ARCHIVO["barrios"]
HITOS = json.loads((SEMILLAS / "hitos.json").read_text(encoding="utf-8"))

# Barrios que OpenStreetMap NO devolvió y se completan a mano (misma forma que barrios.json). Solo para probar la búsqueda.
A_MANO = [
    {"nombre": "San Sebastián", "tipo": "barrio", "alias": ["san sebastian"], "lat": 5.0687, "lng": -75.5075},
    {"nombre": "Fátima", "tipo": "barrio", "alias": ["fatima"], "lat": 5.0700, "lng": -75.5200},
]


def test_el_archivo_tiene_atribucion_y_marca_validado_false() -> None:
    assert "OpenStreetMap contributors (ODbL)" in ARCHIVO["atribucion"]
    assert ARCHIVO["total"] == len(BARRIOS) > 0
    assert all(b["validado"] is False for b in BARRIOS)
    assert all(b["osm_tipo"] in ("node", "way", "relation") and isinstance(b["osm_id"], int) for b in BARRIOS)


def test_el_archivo_es_valido_sin_duplicados_y_dentro_de_la_caja() -> None:
    assert validar_barrios(BARRIOS) == []
    nombres = [normalizar(b["nombre"]) for b in BARRIOS]
    assert len(nombres) == len(set(nombres))
    for b in BARRIOS:
        assert CAJA["min_lat"] <= b["lat"] <= CAJA["max_lat"] and CAJA["min_lng"] <= b["lng"] <= CAJA["max_lng"]
        assert b["alias"] == sorted({normalizar(b["nombre"])})  # alias sin tildes y en minúsculas


def test_barrios_urbanos_son_barrio_y_las_veredas_son_sector() -> None:
    assert {b["tipo"] for b in BARRIOS if b["place"] == "locality"} == {"sector"}
    assert {b["tipo"] for b in BARRIOS if b["place"] != "locality"} <= {"barrio"}


def test_la_carga_no_pisa_los_hitos_existentes() -> None:
    """El cargador omite por nombre normalizado: ningún barrio debe llamarse como uno de los hitos ya sembrados."""
    existentes = {normalizar(h["nombre"]) for h in HITOS}
    assert existentes.isdisjoint(normalizar(b["nombre"]) for b in BARRIOS)


def test_la_validacion_detecta_duplicados_fuera_de_caja_y_alias_malos() -> None:
    base = {"nombre": "Fátima", "tipo": "barrio", "alias": ["fatima"], "lat": 5.07, "lng": -75.52}
    assert validar_barrios([base]) == []
    assert any("duplicado" in p for p in validar_barrios([base, {**base, "nombre": "FATIMA"}]))
    assert any("fuera de la caja" in p for p in validar_barrios([{**base, "lat": 6.5}]))
    assert any("alias" in p for p in validar_barrios([{**base, "alias": ["Fátima"]}]))
    assert any("tipo" in p for p in validar_barrios([{**base, "tipo": "vereda"}]))
    assert any("sin nombre" in p for p in validar_barrios([{**base, "nombre": " "}]))


# ---------- búsqueda ----------


class BusquedaConHitos:
    """Misma lógica que el SQL de `RepositorioBusquedaSql.buscar_hitos`: contiene (nombre o alias) sobre texto normalizado,
    orden exacto, luego los que EMPIEZAN con el texto, luego alfabético; máximo 20."""

    def __init__(self, hitos: list[dict]) -> None:
        self.hitos = {uuid5(NAMESPACE_DNS, h["nombre"]): {**h, "id": uuid5(NAMESPACE_DNS, h["nombre"])} for h in hitos}

    async def buscar_rutas(self, patron: str, texto: str):
        return []

    async def buscar_hitos(self, patron: str, texto: str):
        def coincide(h: dict) -> bool:
            return texto in normalizar(h["nombre"]) or any(texto in normalizar(a) for a in h.get("alias", []))

        encontrados = [h for h in self.hitos.values() if coincide(h)]
        encontrados.sort(key=lambda h: (normalizar(h["nombre"]) != texto, not normalizar(h["nombre"]).startswith(texto), normalizar(h["nombre"])))
        return encontrados[:20]

    async def obtener_hito(self, hito_id: UUID):
        return self.hitos.get(hito_id)

    async def rutas_por_hito(self, hito_id: UUID, radio_m: int):
        return {}


def _cliente(hitos: list[dict]) -> TestClient:
    repos = dobles.repositorios_en_memoria()
    repos.busqueda = BusquedaConHitos(hitos)
    cont = construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(RelojFijo()))
    return TestClient(crear_app(cont), raise_server_exceptions=False)


@pytest.fixture
def cliente() -> TestClient:
    return _cliente(HITOS + BARRIOS + A_MANO)


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


def test_los_barrios_del_archivo_se_buscan_por_su_nombre_sin_tildes(cliente: TestClient) -> None:
    assert _nombres(cliente, "turin") == ["Turín"]
    assert _nombres(cliente, "monserrate") == ["Monserrate"]
    for b in BARRIOS:
        assert b["nombre"] in _nombres(cliente, normalizar_consulta(b["nombre"]))


def test_busqueda_parcial_ordena_primero_el_que_empieza_con_el_texto() -> None:
    cliente = _cliente([
        {"nombre": "Villa San Sebastián", "tipo": "barrio", "alias": ["villa san sebastian"], "lat": 5.05, "lng": -75.5},
        {"nombre": "San Sebastián", "tipo": "barrio", "alias": ["san sebastian"], "lat": 5.06, "lng": -75.5},
        {"nombre": "Sebastopol", "tipo": "barrio", "alias": ["sebastopol"], "lat": 5.07, "lng": -75.5},
        {"nombre": "Sebastián Belalcázar", "tipo": "barrio", "alias": ["sebastian belalcazar"], "lat": 5.08, "lng": -75.5},
    ])
    # empiezan por «sebas»: Sebastián Belalcázar y Sebastopol (en orden alfabético); luego los que lo contienen
    assert _nombres(cliente, "sebas") == ["Sebastián Belalcázar", "Sebastopol", "San Sebastián", "Villa San Sebastián"]
    # un nombre exacto va primero aunque otros lo contengan
    assert _nombres(cliente, "san sebastian")[0] == "San Sebastián"


def test_busqueda_respeta_el_maximo_de_20_resultados() -> None:
    muchos = [{"nombre": f"Barrio Prueba {i:02d}", "tipo": "barrio", "alias": [f"barrio prueba {i:02d}"], "lat": 5.05, "lng": -75.5}
              for i in range(25)]
    nombres = _nombres(_cliente(muchos), "prueba")
    assert len(nombres) == 20 and nombres == sorted(nombres)


def test_el_sql_de_busqueda_ordena_exacto_luego_prefijo_luego_alfabetico() -> None:
    sql = (Path(__file__).resolve().parents[2] / "src/modulos/busqueda/infraestructura/repositorio_sql.py").read_text(encoding="utf-8")
    cuerpo = sql[sql.index("async def buscar_hitos"):]
    assert "order by (normalizar_texto(h.nombre) = %(texto)s) desc" in cuerpo
    assert "starts_with(normalizar_texto(h.nombre), %(texto)s) desc" in cuerpo and "limit 20" in cuerpo
