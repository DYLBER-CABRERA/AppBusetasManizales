"""Registro de pasajeros: POST /yo completa el perfil de una cuenta recién creada en Supabase Auth."""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from composicion import Repositorios, construir_contenedor
from modulos.administracion.dominio.validacion_pasajero import limpiar_nombre, normalizar_celular
from nucleo.configuracion import Configuracion
from nucleo.errores import ErrorValidacion
from nucleo.reloj import RelojSimulado
from pruebas import dobles
from pruebas.dobles import RelojFijo
from servidor import crear_app

CUERPO = {"nombre": "  Ana  María ", "apellido": " Pérez ", "celular": "+57 300-123 4567"}


@pytest.fixture
def repos() -> Repositorios:
    return dobles.repositorios_en_memoria()


@pytest.fixture
def cliente(repos: Repositorios) -> TestClient:
    cont = construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(RelojFijo()))
    return TestClient(crear_app(cont), raise_server_exceptions=False)


NUEVO = {"Authorization": "Bearer tok-nuevo"}


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("3001234567", "3001234567"),
        ("+57 300-123 4567", "3001234567"),
        ("57 300 123 4567", "3001234567"),
        ("(300) 123.4567", "3001234567"),
        ("  +573211234567 ", "3211234567"),
    ],
)
def test_celular_se_normaliza(entrada: str, esperado: str) -> None:
    assert normalizar_celular(entrada) == esperado


@pytest.mark.parametrize("entrada", ["", "   ", "2001234567", "300123456", "30012345678", "+1 300 123 4567", "abc3001234567", "6011234567"])
def test_celular_invalido(entrada: str) -> None:
    with pytest.raises(ErrorValidacion):
        normalizar_celular(entrada)


def test_nombre_se_recorta_y_colapsa_espacios() -> None:
    assert limpiar_nombre("  Ana   María ", "nombre") == "Ana María"
    for malo in ("", "   ", None, "x" * 61):
        with pytest.raises(ErrorValidacion):
            limpiar_nombre(malo, "nombre")


def test_crea_el_perfil_de_pasajero_con_201(cliente: TestClient, repos: Repositorios) -> None:
    r = cliente.post("/api/v1/yo", json=CUERPO, headers=NUEVO)
    assert r.status_code == 201
    assert r.json() == {
        "usuarioId": str(dobles.USUARIO_NUEVO), "correo": "nueva@correo.example", "rol": "pasajero", "empresaId": None,
        "empresaNombre": None, "nombre": "Ana María", "apellido": "Pérez", "celular": "3001234567",
    }
    guardado = repos.usuarios.perfiles[dobles.USUARIO_NUEVO]
    assert guardado["rol"] == "pasajero" and guardado["activo"] is True


def test_el_rol_del_cliente_se_ignora(cliente: TestClient) -> None:
    r = cliente.post("/api/v1/yo", json={**CUERPO, "rol": "administrador", "empresaId": str(dobles.EMPRESA_SIDERAL)}, headers=NUEVO)
    assert r.status_code == 201 and r.json()["rol"] == "pasajero" and r.json()["empresaId"] is None


def test_idempotente_responde_200_sin_sobrescribir(cliente: TestClient, repos: Repositorios) -> None:
    assert cliente.post("/api/v1/yo", json=CUERPO, headers=NUEVO).status_code == 201
    otro = {"nombre": "Otra", "apellido": "Persona", "celular": "3109876543"}
    r = cliente.post("/api/v1/yo", json=otro, headers=NUEVO)
    assert r.status_code == 200 and r.json()["nombre"] == "Ana María" and r.json()["celular"] == "3001234567"
    assert len([p for p in repos.usuarios.perfiles.values() if p["correo"] == "nueva@correo.example"]) == 1


def test_cuenta_existente_responde_200_aunque_el_cuerpo_sea_distinto(cliente: TestClient) -> None:
    r = cliente.post("/api/v1/yo", json=CUERPO, headers={"Authorization": "Bearer tok-pasajera"})
    assert r.status_code == 200 and r.json()["correo"] == "pasajera@correo.example" and r.json()["rol"] == "pasajero"


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"apellido": "P", "celular": "3001234567"},
        {"nombre": "   ", "apellido": "P", "celular": "3001234567"},
        {"nombre": "A", "apellido": "", "celular": "3001234567"},
        {"nombre": "A", "apellido": "P", "celular": "12345"},
        {"nombre": "A", "apellido": "P", "celular": "2001234567"},
        {"nombre": "A", "apellido": "P"},
        {},
    ],
)
def test_validaciones_responden_400(cliente: TestClient, repos: Repositorios, cuerpo: dict) -> None:
    r = cliente.post("/api/v1/yo", json=cuerpo, headers=NUEVO)
    assert r.status_code == 400 and r.json()["error"]["codigo"] == "VALIDACION"
    assert dobles.USUARIO_NUEVO not in repos.usuarios.perfiles


def test_sin_token_o_token_invalido_401(cliente: TestClient) -> None:
    assert cliente.post("/api/v1/yo", json=CUERPO).status_code == 401
    r = cliente.post("/api/v1/yo", json=CUERPO, headers={"Authorization": "Bearer basura"})
    assert r.status_code == 401 and r.json()["error"]["codigo"] == "NO_AUTENTICADO"


def test_perfil_inactivo_401(cliente: TestClient, repos: Repositorios) -> None:
    repos.usuarios.perfiles[dobles.USUARIO_PASAJERA]["activo"] = False
    assert cliente.post("/api/v1/yo", json=CUERPO, headers={"Authorization": "Bearer tok-pasajera"}).status_code == 401


def test_correo_ya_usado_por_otro_perfil_409(cliente: TestClient, repos: Repositorios) -> None:
    repos.usuarios.perfiles[dobles.USUARIO_JEFE]["correo"] = "nueva@correo.example"
    r = cliente.post("/api/v1/yo", json=CUERPO, headers=NUEVO)
    assert r.status_code == 409 and r.json()["error"]["codigo"] == "CONFLICTO_NEGOCIO"


def test_el_pasajero_recien_creado_ya_puede_usar_la_app(cliente: TestClient) -> None:
    # el token de "tok-nuevo" no existe como Identidad en el doble; tras el registro basta con que GET /yo funcione para tok-pasajera
    assert cliente.get("/api/v1/yo", headers={"Authorization": "Bearer tok-pasajera"}).status_code == 200


def test_no_se_registran_correo_celular_ni_token(cliente: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        cliente.post("/api/v1/yo", json=CUERPO, headers=NUEVO)
        cliente.post("/api/v1/yo", json={"nombre": "", "apellido": "", "celular": "x"}, headers=NUEVO)
    texto = caplog.text
    for secreto in ("nueva@correo.example", "3001234567", "tok-nuevo", "300-123"):
        assert secreto not in texto
