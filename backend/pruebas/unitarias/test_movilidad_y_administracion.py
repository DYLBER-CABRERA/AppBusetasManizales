"""B5: gestión de la red (Secretaría), administración (A01 a A04) y estadísticas, con repositorios en memoria."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from composicion import Repositorios, construir_contenedor
from modulos.seguimiento import hash_de_clave
from nucleo.configuracion import Configuracion
from nucleo.reloj import RelojSimulado
from pruebas import dobles
from pruebas.dobles import RelojFijo
from servidor import crear_app


@pytest.fixture
def repos() -> Repositorios:
    return dobles.repositorios_en_memoria()


@pytest.fixture
def cliente(repos: Repositorios) -> TestClient:
    cont = construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(RelojFijo()))
    return TestClient(crear_app(cont), raise_server_exceptions=False)


def _con(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


SEC, ADM, JEFE = _con("tok-secretaria"), _con("tok-admin"), _con("tok-jefe")
A, B = str(dobles.PARADERO_A), str(dobles.PARADERO_B)
SIDERAL, SERVI = str(dobles.EMPRESA_SIDERAL), str(dobles.EMPRESA_SERVITURISMO)


# ---------- permisos ----------


def test_gestion_de_la_red_solo_secretaria_y_administrador(cliente: TestClient) -> None:
    cuerpo = {"nombre": "Nueva", "lat": 5.07, "lng": -75.5}
    assert cliente.post("/api/v1/paraderos", json=cuerpo).status_code == 401
    assert cliente.post("/api/v1/paraderos", json=cuerpo, headers=JEFE).status_code == 403
    assert cliente.post("/api/v1/paraderos", json=cuerpo, headers=_con("tok-pasajera")).status_code == 403
    assert cliente.post("/api/v1/paraderos", json=cuerpo, headers=SEC).status_code == 201
    assert cliente.post("/api/v1/paraderos", json={**cuerpo, "nombre": "Otra"}, headers=ADM).status_code == 201


def test_administracion_solo_administrador(cliente: TestClient) -> None:
    for ruta in ("/admin/usuarios", "/admin/roles", "/admin/empresas", "/admin/parametros"):
        assert cliente.get(f"/api/v1{ruta}", headers=SEC).status_code == 403
        assert cliente.get(f"/api/v1{ruta}", headers=JEFE).status_code == 403
        assert cliente.get(f"/api/v1{ruta}", headers=ADM).status_code == 200


# ---------- paraderos y hitos ----------


def test_paradero_duplicado_a_menos_de_20_m_409(cliente: TestClient) -> None:
    r = cliente.post("/api/v1/paraderos", json={"nombre": "parada a", "lat": 5.07, "lng": -75.51}, headers=SEC)
    assert r.status_code == 409 and r.json()["error"]["codigo"] == "CONFLICTO_NEGOCIO"


def test_paraderos_listar_editar_con_version(cliente: TestClient) -> None:
    assert len(cliente.get("/api/v1/paraderos", headers=SEC).json()) == 2
    ok = cliente.put(f"/api/v1/paraderos/{B}", json={"nombre": "Parada B2", "version": 1}, headers=SEC)
    assert ok.status_code == 200 and ok.json()["nombre"] == "Parada B2" and ok.json()["version"] == 2
    viejo = cliente.put(f"/api/v1/paraderos/{B}", json={"nombre": "xx", "version": 1}, headers=SEC)
    assert viejo.status_code == 409 and viejo.json()["error"]["codigo"] == "CONFLICTO_VERSION"
    assert cliente.put(f"/api/v1/paraderos/{uuid4()}", json={"version": 1}, headers=SEC).status_code == 404


def test_baja_de_paradero_usado_advierte_con_la_lista(cliente: TestClient, repos: Repositorios) -> None:
    r = cliente.delete(f"/api/v1/paraderos/{A}", params={"version": 1}, headers=SEC)
    assert r.status_code == 409 and r.json()["error"]["detalles"]["rutas"][0]["nombre"] == "La Enea"
    assert cliente.delete(f"/api/v1/paraderos/{A}", params={"version": 1, "confirmar": "true"}, headers=SEC).status_code == 204
    assert cliente.delete(f"/api/v1/paraderos/{B}", params={"version": 1}, headers=SEC).status_code == 204  # sin rutas
    assert [b[0] for b in repos.gestion_red.bajas] == ["paradero", "paradero"]


def test_crear_hito(cliente: TestClient) -> None:
    r = cliente.post("/api/v1/hitos", json={"nombre": "Barrio X", "tipo": "barrio", "alias": ["x"], "lat": 5.06, "lng": -75.5}, headers=SEC)
    assert r.status_code == 201 and r.json()["tipo"] == "barrio"


# ---------- rutas ----------


def _ruta(**cambios) -> dict:
    base = {"nombre": "Nueva ruta", "paraderoIds": [A, B], "servicios": [{"empresaId": SIDERAL, "codigoPublico": "55"}]}
    return base | cambios


def test_registrar_ruta(cliente: TestClient, repos: Repositorios) -> None:
    r = cliente.post("/api/v1/rutas", json=_ruta(), headers=SEC)
    assert r.status_code == 201 and r.json()["tipoRecorrido"] == "circular"
    assert repos.gestion_red.rutas_creadas[0]["servicios"][0]["codigo_publico"] == "55"


def test_registrar_ruta_validaciones(cliente: TestClient) -> None:
    assert cliente.post("/api/v1/rutas", json=_ruta(paraderoIds=[A]), headers=SEC).status_code == 400
    assert cliente.post("/api/v1/rutas", json=_ruta(paraderoIds=[A, A]), headers=SEC).status_code == 400
    assert cliente.post("/api/v1/rutas", json=_ruta(paraderoIds=[A, str(uuid4())]), headers=SEC).status_code == 404
    assert cliente.post("/api/v1/rutas", json=_ruta(servicios=[{"empresaId": str(uuid4())}]), headers=SEC).status_code == 404
    assert cliente.post("/api/v1/rutas", json=_ruta(servicios=[]), headers=SEC).status_code == 400
    assert cliente.post("/api/v1/rutas", json=_ruta(tipoRecorrido="lineal"), headers=SEC).status_code == 400


def test_ruta_compartida_exige_confirmacion(cliente: TestClient) -> None:
    dos = [{"empresaId": SIDERAL}, {"empresaId": SERVI}]
    r = cliente.post("/api/v1/rutas", json=_ruta(servicios=dos), headers=SEC)
    assert r.status_code == 409 and r.json()["error"]["codigo"] == "CONFLICTO_NEGOCIO"
    assert cliente.post("/api/v1/rutas", json=_ruta(servicios=dos, confirmarCompartida=True), headers=SEC).status_code == 201


def test_editar_ruta_con_version(cliente: TestClient) -> None:
    url = f"/api/v1/rutas/{dobles.RUTA_ENEA}"
    assert cliente.put(url, json={"nombre": "La Enea 2", "paraderoIds": [B, A], "version": 1}, headers=SEC).status_code == 200
    assert cliente.put(url, json={"nombre": "xx", "version": 9}, headers=SEC).status_code == 409
    assert cliente.put(url, json={"paraderoIds": [A], "version": 1}, headers=SEC).status_code == 400
    assert cliente.put(f"/api/v1/rutas/{uuid4()}", json={"version": 1}, headers=SEC).status_code == 404


def test_eliminar_ruta_con_turnos_futuros_pide_confirmacion(cliente: TestClient, repos: Repositorios) -> None:
    repos.gestion_red.turnos_futuros = [{"turnoId": str(uuid4()), "fecha": "2026-10-27", "horaSalida": "06:00", "buseta": "1544"}]
    url = f"/api/v1/rutas/{dobles.RUTA_ENEA}"
    r = cliente.delete(url, params={"version": 1}, headers=SEC)
    assert r.status_code == 409 and r.json()["error"]["detalles"]["turnosFuturos"][0]["buseta"] == "1544"
    assert repos.gestion_red.bajas == []
    assert cliente.delete(url, params={"version": 1, "confirmar": "true"}, headers=SEC).status_code == 204
    assert repos.gestion_red.bajas == [("ruta", dobles.RUTA_ENEA)]


def test_eliminar_ruta_sin_turnos_version_y_404(cliente: TestClient) -> None:
    url = f"/api/v1/rutas/{dobles.RUTA_VILLAMARIA}"
    assert cliente.delete(url, params={"version": 7}, headers=SEC).status_code == 409
    assert cliente.delete(url, params={"version": 1}, headers=SEC).status_code == 204
    assert cliente.delete(f"/api/v1/rutas/{uuid4()}", params={"version": 1}, headers=SEC).status_code == 404
    assert cliente.delete(url, headers=SEC).status_code == 400  # falta version


def test_asignar_y_retirar_servicio(cliente: TestClient, repos: Repositorios) -> None:
    url = f"/api/v1/rutas/{dobles.RUTA_ENEA}/servicios"
    assert cliente.post(url, json={"empresaId": SIDERAL}, headers=SEC).status_code == 409  # ya la opera
    sin_confirmar = cliente.post(url, json={"empresaId": SERVI}, headers=SEC)
    assert sin_confirmar.status_code == 409  # ya está asignada a otra empresa
    ok = cliente.post(url, json={"empresaId": SERVI, "confirmarCompartida": True, "codigoPublico": "7"}, headers=SEC)
    assert ok.status_code == 201 and ok.json()["codigoPublico"] == "7"
    libre = cliente.post(f"/api/v1/rutas/{dobles.RUTA_VILLAMARIA}/servicios", json={"empresaId": SERVI}, headers=SEC)
    assert libre.status_code == 201
    assert cliente.post(f"/api/v1/rutas/{uuid4()}/servicios", json={"empresaId": SERVI}, headers=SEC).status_code == 404
    servicio = f"/api/v1/servicios/{dobles.SERVICIO_SIDERAL_ENEA}"
    repos.gestion_red.turnos_futuros = [{"turnoId": "t", "fecha": "2026-10-27", "horaSalida": "06:00", "buseta": "1544"}]
    assert cliente.delete(servicio, params={"version": 2}, headers=SEC).status_code == 409
    assert cliente.delete(servicio, params={"version": 2, "confirmar": "true"}, headers=SEC).status_code == 204
    assert ("servicio", dobles.SERVICIO_SIDERAL_ENEA) in repos.gestion_red.bajas


# ---------- usuarios ----------


def test_crear_usuario_jefe_exige_empresa_y_invita(cliente: TestClient, repos: Repositorios) -> None:
    cuerpo = {"correo": "Nuevo@Sideral.example", "nombre": "Nuevo", "rol": "jefe_operaciones", "empresaId": SIDERAL}
    r = cliente.post("/api/v1/admin/usuarios", json=cuerpo, headers=ADM)
    assert r.status_code == 201 and r.json()["correo"] == "nuevo@sideral.example" and r.json()["empresaId"] == SIDERAL
    assert repos.autenticacion.invitados == ["nuevo@sideral.example"]
    assert cliente.post("/api/v1/admin/usuarios", json=cuerpo, headers=ADM).status_code == 409  # correo repetido
    sin_empresa = {**cuerpo, "correo": "a@b.example", "empresaId": None}
    assert cliente.post("/api/v1/admin/usuarios", json=sin_empresa, headers=ADM).status_code == 400
    con_empresa = {"correo": "c@d.example", "rol": "pasajero", "empresaId": SIDERAL}
    assert cliente.post("/api/v1/admin/usuarios", json=con_empresa, headers=ADM).status_code == 400
    assert cliente.post("/api/v1/admin/usuarios", json={"correo": "sin-arroba", "rol": "pasajero"}, headers=ADM).status_code == 400
    otra = {**cuerpo, "correo": "e@f.example", "empresaId": str(uuid4())}
    assert cliente.post("/api/v1/admin/usuarios", json=otra, headers=ADM).status_code == 404


def test_editar_usuario_y_ultimo_administrador(cliente: TestClient) -> None:
    url = f"/api/v1/admin/usuarios/{dobles.USUARIO_ADMIN}"
    ultimo = cliente.put(url, json={"rol": "pasajero", "version": 1}, headers=ADM)
    assert ultimo.status_code == 409 and ultimo.json()["error"]["codigo"] == "CONFLICTO_NEGOCIO"
    assert cliente.put(url, json={"activo": False, "version": 1}, headers=ADM).status_code == 409
    pasajera = f"/api/v1/admin/usuarios/{dobles.USUARIO_PASAJERA}"
    ok = cliente.put(pasajera, json={"activo": False, "version": 1}, headers=ADM)
    assert ok.status_code == 200 and ok.json()["activo"] is False
    assert cliente.put(pasajera, json={"activo": True, "version": 1}, headers=ADM).status_code == 409  # versión vieja
    assert cliente.put(f"/api/v1/admin/usuarios/{uuid4()}", json={"version": 1}, headers=ADM).status_code == 404


def test_listar_usuarios_por_correo_y_roles(cliente: TestClient) -> None:
    r = cliente.get("/api/v1/admin/usuarios", params={"correo": "SIDERAL"}, headers=ADM)
    assert [u["correo"] for u in r.json()] == ["jefe@sideral.example"]
    roles = cliente.get("/api/v1/admin/roles", headers=ADM).json()
    assert [x["rol"] for x in roles] == ["pasajero", "jefe_operaciones", "secretaria_movilidad", "administrador"]


# ---------- empresas, credenciales, parámetros ----------


def test_empresas(cliente: TestClient) -> None:
    nueva = cliente.post("/api/v1/admin/empresas", json={"nombre": "Nueva Cía"}, headers=ADM)
    assert nueva.status_code == 201 and nueva.json()["estado"] == "activo"
    assert cliente.post("/api/v1/admin/empresas", json={"nombre": "sideral"}, headers=ADM).status_code == 409
    ed = cliente.put(f"/api/v1/admin/empresas/{nueva.json()['id']}", json={"estado": "baja", "version": 1}, headers=ADM)
    assert ed.status_code == 200 and ed.json()["estado"] == "baja"
    assert cliente.put(f"/api/v1/admin/empresas/{SIDERAL}", json={"nombre": "XX", "version": 5}, headers=ADM).status_code == 409


def test_credencial_gps_se_muestra_una_vez_y_se_guarda_el_hash(cliente: TestClient, repos: Repositorios) -> None:
    r = cliente.post(f"/api/v1/admin/empresas/{SIDERAL}/credenciales-gps", json={"nombre": "Flota"}, headers=ADM)
    assert r.status_code == 201 and len(r.json()["clave"]) >= 32
    assert repos.admin.hashes == [hash_de_clave(r.json()["clave"])]
    lista = cliente.get(f"/api/v1/admin/empresas/{SIDERAL}/credenciales-gps", headers=ADM).json()
    assert len(lista) == 1 and "clave" not in lista[0] and lista[0]["activa"] is True
    assert cliente.delete(f"/api/v1/admin/credenciales-gps/{r.json()['id']}", headers=ADM).status_code == 204
    assert cliente.get(f"/api/v1/admin/empresas/{SIDERAL}/credenciales-gps", headers=ADM).json()[0]["activa"] is False
    assert cliente.delete(f"/api/v1/admin/credenciales-gps/{uuid4()}", headers=ADM).status_code == 404
    assert cliente.post(f"/api/v1/admin/empresas/{uuid4()}/credenciales-gps", json={"nombre": "x"}, headers=ADM).status_code == 404


def test_parametros_con_minimo_maximo_y_version(cliente: TestClient) -> None:
    url = "/api/v1/admin/parametros/radio_busqueda_m"
    assert cliente.put(url, json={"valor": 50, "version": 1}, headers=ADM).status_code == 400
    assert cliente.put(url, json={"valor": 6000, "version": 1}, headers=ADM).status_code == 400
    assert cliente.put(url, json={"valor": "mucho", "version": 1}, headers=ADM).status_code == 400
    ok = cliente.put(url, json={"valor": 1000, "version": 1}, headers=ADM)
    assert ok.status_code == 200 and ok.json()["valor"] == 1000 and ok.json()["version"] == 2
    assert cliente.put(url, json={"valor": 900, "version": 1}, headers=ADM).status_code == 409
    assert cliente.put("/api/v1/admin/parametros/no_existe", json={"valor": 1, "version": 1}, headers=ADM).status_code == 404
    caja = cliente.put("/api/v1/admin/parametros/caja_ciudad", json={"valor": {"minLat": 1}, "version": 1}, headers=ADM)
    assert caja.status_code == 400


# ---------- estadísticas ----------


def test_estadisticas_jefe_ve_solo_su_empresa_e_ignora_empresa_id(cliente: TestClient, repos: Repositorios) -> None:
    params = {"desde": "2026-10-20", "hasta": "2026-10-26", "empresaId": SERVI}
    r = cliente.get("/api/v1/estadisticas/uso", params=params, headers=JEFE)
    assert r.status_code == 200 and r.json()["sinDatos"] is False and r.json()["totalesPorTipo"] == [{"tipo": "eta", "total": 5}]
    assert repos.eventos_uso.consultas_estadisticas[-1][0] == dobles.EMPRESA_SIDERAL


def test_estadisticas_administrador_todas_o_una_empresa_y_sin_datos(cliente: TestClient, repos: Repositorios) -> None:
    base = {"desde": "2026-10-20", "hasta": "2026-10-26"}
    cliente.get("/api/v1/estadisticas/uso", params=base, headers=ADM)
    assert repos.eventos_uso.consultas_estadisticas[-1][0] is None
    vacio = cliente.get("/api/v1/estadisticas/uso", params={**base, "empresaId": SERVI}, headers=ADM)
    assert vacio.json() == {"sinDatos": True, "totalesPorTipo": [], "porRuta": [], "porDia": []}


def test_estadisticas_validaciones_y_permisos(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/estadisticas/uso", params={"desde": "2026-10-26", "hasta": "2026-10-20"}, headers=JEFE).status_code == 400
    assert cliente.get("/api/v1/estadisticas/uso", params={"desde": "2024-01-01", "hasta": "2026-10-20"}, headers=JEFE).status_code == 400
    assert cliente.get("/api/v1/estadisticas/uso", params={"desde": "2026-10-20"}, headers=JEFE).status_code == 400
    ok = {"desde": "2026-10-20", "hasta": "2026-10-26"}
    assert cliente.get("/api/v1/estadisticas/uso", params=ok, headers=SEC).status_code == 403
    assert cliente.get("/api/v1/estadisticas/uso", params=ok).status_code == 401
