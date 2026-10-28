"""B0: el contrato queda completo (todos los endpoints de docs/03 declarados) y responde 501 sin lógica."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from servidor import crear_app

RAIZ = Path(__file__).resolve().parents[3]

# (método, ruta con parámetros genéricos) tomados de docs/03-contrato-api.md §2
ENDPOINTS_CONTRATO = [
    ("get", "/salud"), ("get", "/rutas/cercanas"), ("get", "/rutas"), ("get", "/rutas/{x}"),
    ("get", "/rutas/{x}/horarios"), ("get", "/rutas/{x}/frecuencias"), ("get", "/rutas/{x}/busetas"),
    ("get", "/paraderos/cercanos"), ("get", "/paraderos/{x}/eta"), ("post", "/viajes/planificar"),
    ("get", "/busqueda/rutas"), ("get", "/busqueda/hitos"), ("get", "/hitos/{x}/rutas"),
    ("get", "/avisos"), ("get", "/empresas"), ("get", "/yo"),
    ("get", "/favoritos"), ("post", "/favoritos"), ("delete", "/favoritos/{x}"),
    ("get", "/alertas-llegada"), ("post", "/alertas-llegada"), ("delete", "/alertas-llegada/{x}"),
    ("get", "/mis-servicios"), ("get", "/busetas"), ("post", "/busetas"), ("put", "/busetas/{x}"),
    ("get", "/conductores"), ("post", "/conductores"), ("put", "/conductores/{x}"),
    ("put", "/servicios/{x}/horarios"), ("put", "/servicios/{x}/frecuencias"),
    ("get", "/rodamientos"), ("post", "/rodamientos"), ("get", "/rodamientos/{x}"),
    ("put", "/rodamientos/{x}"), ("post", "/rodamientos/{x}/publicar"), ("post", "/rodamientos/{x}/anular"),
    ("post", "/avisos"), ("delete", "/avisos/{x}"), ("get", "/estadisticas/uso"),
    ("post", "/rutas"), ("put", "/rutas/{x}"), ("delete", "/rutas/{x}"),
    ("post", "/rutas/{x}/servicios"), ("delete", "/servicios/{x}"),
    ("get", "/paraderos"), ("post", "/paraderos"), ("put", "/paraderos/{x}"), ("delete", "/paraderos/{x}"),
    ("post", "/hitos"),
    ("get", "/admin/usuarios"), ("post", "/admin/usuarios"), ("put", "/admin/usuarios/{x}"),
    ("get", "/admin/roles"), ("get", "/admin/empresas"), ("post", "/admin/empresas"),
    ("put", "/admin/empresas/{x}"), ("get", "/admin/empresas/{x}/credenciales-gps"),
    ("post", "/admin/empresas/{x}/credenciales-gps"), ("delete", "/admin/credenciales-gps/{x}"),
    ("get", "/admin/parametros"), ("put", "/admin/parametros/{x}"),
    ("get", "/demo/estado"), ("post", "/demo/escenarios"), ("post", "/ingesta/posiciones"),
]


@pytest.fixture(scope="module")
def cliente() -> TestClient:
    return TestClient(crear_app(), raise_server_exceptions=False)


@pytest.fixture(scope="module")
def esquema(cliente: TestClient) -> dict:
    return cliente.app.openapi()


def _normalizar(ruta: str) -> str:
    import re

    return re.sub(r"\{[^}]+\}", "{x}", ruta.removeprefix("/api/v1"))


def test_todos_los_endpoints_del_contrato_estan_declarados(esquema: dict) -> None:
    declarados = {(m, _normalizar(p)) for p, ops in esquema["paths"].items() for m in ops}
    assert not set(ENDPOINTS_CONTRATO) - declarados
    assert not declarados - set(ENDPOINTS_CONTRATO), "endpoint fuera del contrato"


def test_salud_no_toca_la_bd(cliente: TestClient) -> None:
    r = cliente.get("/api/v1/salud")
    assert r.status_code == 200
    assert r.json() == {"estado": "ok"}
    assert r.headers["X-Id-Peticion"]


def test_endpoint_publico_sin_logica_responde_501(cliente: TestClient) -> None:
    r = cliente.get("/api/v1/rutas")
    assert r.status_code == 501
    assert r.json()["error"]["codigo"] == "PENDIENTE"


def test_endpoint_protegido_sin_token_responde_401(cliente: TestClient) -> None:
    r = cliente.get("/api/v1/favoritos")
    assert r.status_code == 401
    assert r.json()["error"]["codigo"] == "NO_AUTENTICADO"


def test_ingesta_sin_clave_responde_401(cliente: TestClient) -> None:
    r = cliente.post("/api/v1/ingesta/posiciones", json={"posiciones": []})
    assert r.status_code in (400, 401)


def test_validacion_usa_el_formato_de_error(cliente: TestClient) -> None:
    r = cliente.get("/api/v1/rutas/cercanas")
    assert r.status_code == 400
    cuerpo = r.json()["error"]
    assert cuerpo["codigo"] == "VALIDACION"
    assert cuerpo["reintentable"] is False


def test_cercanas_no_se_confunde_con_detalle(cliente: TestClient) -> None:
    r = cliente.get("/api/v1/rutas/cercanas", params={"lat": 5.07, "lng": -75.51})
    assert r.status_code == 501


def test_ws_responde_pong(cliente: TestClient) -> None:
    with cliente.websocket_connect("/ws/rutas/00000000-0000-0000-0000-000000000000") as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "pong"


def test_openapi_json_publicado_esta_al_dia(esquema: dict) -> None:
    publicado = json.loads((RAIZ / "contrato" / "openapi.json").read_text(encoding="utf-8"))
    generado = json.loads(json.dumps(esquema, sort_keys=True))
    assert publicado == generado, "Ejecuta: python scripts/exportar_openapi.py"
