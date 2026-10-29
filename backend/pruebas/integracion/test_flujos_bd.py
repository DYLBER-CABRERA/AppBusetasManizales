"""Flujos B3 a B6 contra la BD de desarrollo (Supabase). NO corre por defecto.

Ejecutar (PowerShell, desde backend/), con la BD migrada, sembrada y los usuarios demo creados:
    $env:PRUEBAS_INTEGRACION="1"; .venv\\Scripts\\python.exe -m pytest -m integracion -q
ESCRIBE en la BD: arranca el simulador (MODO_DEMO), crea un rodamiento de pasado mañana de Sideral (queda anulado), una ruta de
prueba "zz Prueba integración" (queda en baja) y eventos de uso. Las cuentas se leen de DEMO_PASSWORD_* del `.env`.
"""

from __future__ import annotations

import os
import time
from datetime import date, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from nucleo.configuracion import obtener_configuracion
from servidor import crear_app, fabrica_bucle

pytestmark = [
    pytest.mark.integracion,
    pytest.mark.skipif(os.environ.get("PRUEBAS_INTEGRACION") != "1", reason="Define PRUEBAS_INTEGRACION=1"),
]

CUENTAS = {
    "admin": ("admin@busetasapp.example", "demo_password_admin"),
    "movilidad": ("movilidad@alcaldia.example", "demo_password_movilidad"),
    "jefe": ("jefe@sideral.example", "demo_password_jefe"),
    "jefe_socobuses": ("jefe@socobuses.example", "demo_password_jefe"),
    "pasajera": ("pasajera@correo.example", "demo_password_pasajero"),
}


def _token(clave: str) -> dict[str, str]:
    config = obtener_configuracion()
    correo, atributo = CUENTAS[clave]
    r = httpx.post(
        f"{config.supabase_url.rstrip('/')}/auth/v1/token?grant_type=password",
        headers={"apikey": config.supabase_anon_key.get_secret_value()},
        json={"email": correo, "password": getattr(config, atributo).get_secret_value()},
        timeout=15,
    )
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def cliente():
    with TestClient(crear_app(), backend_options={"loop_factory": fabrica_bucle}) as c:
        yield c


@pytest.fixture(scope="module")
def sesiones() -> dict[str, dict[str, str]]:
    return {clave: _token(clave) for clave in CUENTAS}


def test_401_403_404(cliente: TestClient, sesiones: dict) -> None:
    assert cliente.get("/api/v1/yo").status_code == 401
    assert cliente.get("/api/v1/busetas", headers=sesiones["pasajera"]).status_code == 403
    assert cliente.get("/api/v1/admin/usuarios", headers=sesiones["jefe"]).status_code == 403
    assert cliente.get("/api/v1/rutas/00000000-0000-0000-0000-000000000000").status_code == 404
    assert cliente.get("/api/v1/yo", headers=sesiones["jefe"]).json()["empresaNombre"] == "Sideral"


def test_eta_con_el_simulador_corriendo(cliente: TestClient) -> None:
    rutas = cliente.get("/api/v1/rutas").json()
    ruta = next(r for r in rutas if any(s["empresaNombre"] == "Sideral" for s in r["servicios"]))
    time.sleep(8)  # al menos dos ciclos del simulador (SIM_INTERVALO_S)
    en_vivo = cliente.get(f"/api/v1/rutas/{ruta['id']}/busetas").json()
    detalle = cliente.get(f"/api/v1/rutas/{ruta['id']}").json()
    eta = cliente.get(f"/api/v1/paraderos/{detalle['paraderos'][0]['paraderoId']}/eta", params={"rutaId": ruta["id"]})
    assert eta.status_code == 200 and eta.json()["resultados"]
    assert isinstance(en_vivo["seguimientoDisponible"], bool)


def test_flujo_rodamiento_y_aislamiento_entre_jefes(cliente: TestClient, sesiones: dict) -> None:
    jefe = sesiones["jefe"]
    servicio = cliente.get("/api/v1/mis-servicios", headers=jefe).json()[0]["id"]
    busetas = cliente.get("/api/v1/busetas", headers=jefe).json()
    fecha = (date.today() + timedelta(days=2)).isoformat()
    turnos = [
        {"servicioId": servicio, "busetaId": busetas[0]["id"], "horaSalida": "06:00", "horaFinEstimada": "06:50"},
        {"servicioId": servicio, "busetaId": busetas[0]["id"], "horaSalida": "06:40", "horaFinEstimada": "07:30"},
    ]
    r = cliente.post("/api/v1/rodamientos", json={"fecha": fecha, "turnos": turnos}, headers=jefe)
    assert r.status_code == 201 and r.json()["advertencias"]
    rid = r.json()["rodamientoId"]
    assert cliente.post(f"/api/v1/rodamientos/{rid}/publicar", json={"version": 1}, headers=jefe).status_code == 409
    corregido = [turnos[0], {**turnos[1], "horaSalida": "06:50", "horaFinEstimada": "07:40"}]
    ok = cliente.put(f"/api/v1/rodamientos/{rid}", json={"turnos": corregido, "version": 1}, headers=jefe)
    assert ok.status_code == 200 and ok.json()["advertencias"] == []
    # el jefe de otra empresa no lo ve
    assert cliente.get(f"/api/v1/rodamientos/{rid}", headers=sesiones["jefe_socobuses"]).status_code == 404
    assert cliente.post(f"/api/v1/rodamientos/{rid}/anular", json={"version": ok.json()["version"]}, headers=jefe).status_code == 200


def test_eliminar_ruta_con_confirmacion(cliente: TestClient, sesiones: dict) -> None:
    mov = sesiones["movilidad"]
    paraderos = cliente.get("/api/v1/paraderos", headers=mov).json()[:2]
    empresa = next(e for e in cliente.get("/api/v1/empresas").json() if e["nombre"] == "Sideral")["id"]
    r = cliente.post(
        "/api/v1/rutas",
        json={"nombre": "zz Prueba integración", "paraderoIds": [p["id"] for p in paraderos], "servicios": [{"empresaId": empresa}]},
        headers=mov,
    )
    assert r.status_code == 201
    ruta = r.json()
    assert cliente.delete(f"/api/v1/rutas/{ruta['id']}", params={"version": ruta["version"] + 5}, headers=mov).status_code == 409
    assert cliente.delete(f"/api/v1/rutas/{ruta['id']}", params={"version": ruta["version"], "confirmar": "true"}, headers=mov).status_code == 204
    assert cliente.get(f"/api/v1/rutas/{ruta['id']}").status_code == 404


def test_favoritos_y_planificacion(cliente: TestClient, sesiones: dict) -> None:
    rutas = cliente.get("/api/v1/rutas").json()
    pas = sesiones["pasajera"]
    fav = cliente.post("/api/v1/favoritos", json={"tipo": "ruta", "rutaId": rutas[0]["id"]}, headers=pas)
    assert fav.status_code in (200, 201)
    assert cliente.delete(f"/api/v1/favoritos/{fav.json()['id']}", headers=pas).status_code == 204
    centro = {"lat": 5.0703, "lng": -75.5138}
    assert cliente.post("/api/v1/viajes/planificar", json={"origen": centro, "destino": centro}).status_code == 200
