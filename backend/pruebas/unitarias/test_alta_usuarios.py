"""Alta de usuarios del administrador con la API Admin de Supabase (contraseña, sin correo de invitación)."""

from __future__ import annotations

import json
import logging
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from composicion import Repositorios, construir_contenedor
from modulos.administracion import AutenticacionSupabase
from nucleo.configuracion import Configuracion
from nucleo.errores import ErrorConflictoNegocio, ErrorServicioExterno, ErrorValidacion
from nucleo.reloj import RelojSimulado
from pruebas import dobles
from pruebas.dobles import RelojFijo
from servidor import crear_app

ADM = {"Authorization": "Bearer tok-admin"}
CUERPO = {"correo": "Nuevo@Correo.example", "nombre": "Nuevo", "rol": "secretaria_movilidad"}


@pytest.fixture
def repos() -> Repositorios:
    return dobles.repositorios_en_memoria()


@pytest.fixture
def cliente(repos: Repositorios) -> TestClient:
    cont = construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(RelojFijo()))
    return TestClient(crear_app(cont), raise_server_exceptions=False)


def test_sin_contrasena_el_servidor_genera_una_segura_y_la_devuelve_una_vez(cliente: TestClient, repos: Repositorios) -> None:
    r = cliente.post("/api/v1/admin/usuarios", json=CUERPO, headers=ADM)
    assert r.status_code == 201
    cuerpo = r.json()
    assert len(cuerpo["contrasena"]) >= 12 and cuerpo["rol"] == "secretaria_movilidad" and cuerpo["correo"] == "nuevo@correo.example"
    assert repos.autenticacion.creados == [("nuevo@correo.example", cuerpo["contrasena"])]
    otra = cliente.post("/api/v1/admin/usuarios", json={**CUERPO, "correo": "otro@correo.example"}, headers=ADM).json()
    assert otra["contrasena"] != cuerpo["contrasena"]
    for u in cliente.get("/api/v1/admin/usuarios", headers=ADM).json():
        assert "contrasena" not in u  # no vuelve a aparecer


def test_con_contrasena_del_administrador_se_usa_y_se_devuelve(cliente: TestClient, repos: Repositorios) -> None:
    r = cliente.post("/api/v1/admin/usuarios", json={**CUERPO, "contrasena": "Clave-segura-1"}, headers=ADM)
    assert r.status_code == 201 and r.json()["contrasena"] == "Clave-segura-1"
    assert repos.autenticacion.creados[0][1] == "Clave-segura-1"


@pytest.mark.parametrize("clave", ["corta", "1234567", "x" * 73])
def test_contrasena_con_longitud_invalida_400(cliente: TestClient, repos: Repositorios, clave: str) -> None:
    r = cliente.post("/api/v1/admin/usuarios", json={**CUERPO, "contrasena": clave}, headers=ADM)
    assert r.status_code == 400 and r.json()["error"]["codigo"] == "VALIDACION"
    assert repos.autenticacion.creados == []
    assert clave not in r.text  # el error no repite la contraseña


def test_roles_y_empresa_se_validan_como_antes(cliente: TestClient, repos: Repositorios) -> None:
    empresa = str(dobles.EMPRESA_SIDERAL)
    assert cliente.post("/api/v1/admin/usuarios", json={**CUERPO, "rol": "conductor"}, headers=ADM).status_code == 400
    assert cliente.post("/api/v1/admin/usuarios", json={**CUERPO, "rol": "jefe_operaciones"}, headers=ADM).status_code == 400
    assert cliente.post("/api/v1/admin/usuarios", json={**CUERPO, "empresaId": empresa}, headers=ADM).status_code == 400
    assert cliente.post("/api/v1/admin/usuarios", json={**CUERPO, "rol": "pasajero"}, headers=ADM).status_code == 201
    assert len(repos.autenticacion.creados) == 1  # solo el válido llegó a Supabase


def test_solo_el_administrador_puede_crear_usuarios(cliente: TestClient, repos: Repositorios) -> None:
    assert cliente.post("/api/v1/admin/usuarios", json=CUERPO).status_code == 401
    for token in ("tok-jefe", "tok-secretaria", "tok-pasajera"):
        r = cliente.post("/api/v1/admin/usuarios", json=CUERPO, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403
    assert repos.autenticacion.creados == []


def test_si_falla_el_perfil_se_borra_la_cuenta_de_auth(cliente: TestClient, repos: Repositorios) -> None:
    async def falla(*_a, **_k):
        raise RuntimeError("BD caída")

    repos.admin.crear_perfil = falla
    r = cliente.post("/api/v1/admin/usuarios", json=CUERPO, headers=ADM)
    assert r.status_code == 500 and r.json()["error"]["codigo"] == "ERROR_INTERNO"
    assert len(repos.autenticacion.creados) == 1 and len(repos.autenticacion.eliminados) == 1


def test_no_se_registran_contrasena_correo_ni_token(cliente: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        cliente.post("/api/v1/admin/usuarios", json={**CUERPO, "contrasena": "Clave-secreta-77"}, headers=ADM)
        cliente.post("/api/v1/admin/usuarios", json={**CUERPO, "contrasena": "x"}, headers=ADM)
    for secreto in ("Clave-secreta-77", "nuevo@correo.example", "Nuevo@Correo.example", "tok-admin"):
        assert secreto not in caplog.text


# ---------- adaptador de Supabase (httpx simulado) ----------


def _auth(manejador) -> AutenticacionSupabase:
    return AutenticacionSupabase(
        "https://proyecto.supabase.example/", "anon-falsa", dobles.UsuariosEnMemoria(),
        httpx.AsyncClient(transport=httpx.MockTransport(manejador)), clave_servicio="servicio-falsa",
    )


async def test_crea_con_la_api_admin_con_correo_confirmado() -> None:
    peticiones: list[httpx.Request] = []
    nuevo = uuid4()

    def manejador(req: httpx.Request) -> httpx.Response:
        peticiones.append(req)
        return httpx.Response(200, json={"id": str(nuevo), "email": "a@b.example"})

    assert await _auth(manejador).crear_usuario("a@b.example", "Clave-123456", "Ana") == nuevo
    [req] = peticiones
    assert req.url.path == "/auth/v1/admin/users" and req.method == "POST"
    assert req.headers["authorization"] == "Bearer servicio-falsa"
    cuerpo = json.loads(req.content)
    assert cuerpo["email"] == "a@b.example" and cuerpo["password"] == "Clave-123456" and cuerpo["email_confirm"] is True


@pytest.mark.parametrize(
    ("estado", "cuerpo"),
    [(422, {"error_code": "email_exists"}), (422, {"error_code": "user_already_exists"}), (409, {"msg": "x"})],
)
async def test_correo_ya_registrado_es_conflicto_de_negocio(estado: int, cuerpo: dict) -> None:
    with pytest.raises(ErrorConflictoNegocio):
        await _auth(lambda req: httpx.Response(estado, json=cuerpo)).crear_usuario("a@b.example", "Clave-123456", None)


@pytest.mark.parametrize(
    ("estado", "cuerpo"),
    [(422, {"error_code": "validation_failed", "msg": "Email address is invalid"}), (500, {}), (401, {"msg": "bad key"})],
)
async def test_otros_fallos_de_supabase_son_servicio_externo(estado: int, cuerpo: dict) -> None:
    with pytest.raises(ErrorServicioExterno):
        await _auth(lambda req: httpx.Response(estado, json=cuerpo)).crear_usuario("a@b.example", "Clave-123456", None)


async def test_contrasena_debil_segun_supabase_es_validacion_y_la_red_caida_es_503() -> None:
    debil = _auth(lambda req: httpx.Response(422, json={"error_code": "weak_password"}))
    with pytest.raises(ErrorValidacion):
        await debil.crear_usuario("a@b.example", "12345678", None)

    def caido(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red")

    with pytest.raises(ErrorServicioExterno):
        await _auth(caido).crear_usuario("a@b.example", "Clave-123456", None)


async def test_eliminar_usuario_llama_a_delete_y_nunca_lanza() -> None:
    vistas: list[httpx.Request] = []
    identificador = uuid4()

    def manejador(req: httpx.Request) -> httpx.Response:
        vistas.append(req)
        return httpx.Response(200, json={})

    await _auth(manejador).eliminar_usuario(identificador)
    assert vistas[0].method == "DELETE" and vistas[0].url.path == f"/auth/v1/admin/users/{identificador}"

    def caido(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red")

    await _auth(caido).eliminar_usuario(UUID(int=1))  # no lanza


async def test_sin_clave_de_servicio_no_crea() -> None:
    auth = AutenticacionSupabase("https://p.supabase.example", "anon", dobles.UsuariosEnMemoria(), httpx.AsyncClient())
    with pytest.raises(ErrorServicioExterno):
        await auth.crear_usuario("a@b.example", "Clave-123456", None)
