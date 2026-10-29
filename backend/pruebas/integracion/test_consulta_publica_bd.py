"""B2 contra la BD de desarrollo (Supabase). NO corre por defecto.

Ejecutar (PowerShell, desde backend/), solo con la BD migrada y sembrada:
    $env:PRUEBAS_INTEGRACION="1"; .venv\Scripts\python.exe -m pytest -m integracion -q
Lee el catálogo y escribe únicamente filas anónimas en `evento_uso` (una por consulta).
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from servidor import crear_app, fabrica_bucle

pytestmark = [
    pytest.mark.integracion,
    pytest.mark.skipif(os.environ.get("PRUEBAS_INTEGRACION") != "1", reason="Define PRUEBAS_INTEGRACION=1"),
]

# Plaza de Bolívar de Manizales (punto de ejemplo dentro de la caja de la ciudad)
CENTRO = {"lat": 5.0703, "lng": -75.5138}


@pytest.fixture(scope="module")
def cliente():
    # psycopg asíncrono no soporta ProactorEventLoop (Windows): mismo bucle que `--loop servidor:fabrica_bucle`
    with TestClient(crear_app(), backend_options={"loop_factory": fabrica_bucle}) as c:  # el lifespan abre el pool
        yield c


def test_salud(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/salud").json() == {"estado": "ok"}


def test_listado_detalle_horarios_y_frecuencias(cliente: TestClient) -> None:
    rutas = cliente.get("/api/v1/rutas").json()
    assert len(rutas) >= 4
    ruta_id = rutas[0]["id"]
    detalle = cliente.get(f"/api/v1/rutas/{ruta_id}").json()
    assert detalle["trazado"]["type"] == "LineString" and detalle["paraderos"]
    assert cliente.get(f"/api/v1/rutas/{ruta_id}/horarios").status_code == 200
    assert cliente.get(f"/api/v1/rutas/{ruta_id}/frecuencias").status_code == 200


def test_cercanas_y_paraderos(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/rutas/cercanas", params=CENTRO).status_code == 200
    assert cliente.get("/api/v1/paraderos/cercanos", params=CENTRO).status_code == 200


def test_busqueda_hitos_y_rutas_por_hito(cliente: TestClient) -> None:
    hitos = cliente.get("/api/v1/busqueda/hitos", params={"q": "villamaria"}).json()
    assert hitos
    assert cliente.get(f"/api/v1/hitos/{hitos[0]['id']}/rutas").status_code == 200
    assert cliente.get("/api/v1/busqueda/rutas", params={"q": "enea"}).status_code == 200


def test_avisos_y_empresas(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/avisos").status_code == 200
    assert {e["nombre"] for e in cliente.get("/api/v1/empresas").json()} >= {"Sideral"}
