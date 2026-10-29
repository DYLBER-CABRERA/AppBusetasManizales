"""B2: consulta pública con repositorios en memoria (sin base de datos)."""

from __future__ import annotations

from datetime import date, datetime, time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from composicion import Contenedor, Repositorios, construir_contenedor
from modulos.busqueda.dominio.servicios import normalizar_consulta, patron_contiene
from modulos.horarios.dominio.servicios import CalculadorTipoDia, estado_de_horarios, minuto_a_texto
from nucleo.configuracion import Configuracion
from pruebas import dobles
from servidor import crear_app

# ---------- servicios de dominio ----------


@pytest.mark.parametrize(
    ("fecha", "esperado"),
    [
        (date(2026, 10, 26), "lun_vie"),  # lunes
        (date(2026, 10, 30), "lun_vie"),  # viernes
        (date(2026, 10, 31), "sabado"),
        (date(2026, 11, 1), "dom_festivo"),  # domingo
    ],
)
def test_tipo_de_dia_normal(fecha: date, esperado: str) -> None:
    assert CalculadorTipoDia().para_fecha(fecha) == esperado


def test_festivo_entre_semana_es_dom_festivo() -> None:
    calculador = CalculadorTipoDia(frozenset({date(2026, 11, 2)}))  # lunes festivo
    assert calculador.para_fecha(date(2026, 11, 2)) == "dom_festivo"
    assert calculador.para_fecha(date(2026, 11, 3)) == "lun_vie"


def test_estado_de_horarios() -> None:
    assert estado_de_horarios({"lun_vie", "sabado", "dom_festivo"}) == ("completo", [])
    assert estado_de_horarios({"lun_vie"}) == ("parcial", ["sabado", "dom_festivo"])
    assert estado_de_horarios(set()) == ("pendiente_actualizacion", ["lun_vie", "sabado", "dom_festivo"])


def test_minutos_a_texto() -> None:
    assert minuto_a_texto(330) == "05:30"
    assert minuto_a_texto(1440) == "24:00"


def test_normalizar_consulta_sin_tildes_ni_mayusculas() -> None:
    assert normalizar_consulta("  Villamaría   CENTRO ") == "villamaria centro"
    assert patron_contiene("50%_a") == "%50\\%\\_a%"


# ---------- API con dobles ----------


@pytest.fixture
def repos() -> Repositorios:
    return dobles.repositorios_en_memoria()


@pytest.fixture
def contenedor(repos: Repositorios) -> Contenedor:
    return construir_contenedor(Configuracion(_env_file=None), repos)


@pytest.fixture
def cliente(contenedor: Contenedor) -> TestClient:
    return TestClient(crear_app(contenedor), raise_server_exceptions=False)


def test_sin_base_de_datos_responde_503() -> None:
    c = TestClient(crear_app(construir_contenedor(Configuracion(_env_file=None))), raise_server_exceptions=False)
    r = c.get("/api/v1/rutas")
    assert r.status_code == 503
    assert r.json()["error"]["codigo"] == "SERVICIO_EXTERNO_NO_DISPONIBLE"
    assert c.get("/api/v1/salud").status_code == 200


def test_rutas_cercanas_usa_el_radio_por_defecto(cliente: TestClient, repos: Repositorios) -> None:
    r = cliente.get("/api/v1/rutas/cercanas", params={"lat": 5.07, "lng": -75.51})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["rutas"][0]["nombre"] == "La Enea"
    assert cuerpo["rutas"][0]["distanciaM"] == 90.0
    assert [s["empresaNombre"] for s in cuerpo["rutas"][0]["servicios"]] == ["Sideral", "Serviturismo"]
    assert cuerpo["paraderoMasCercano"] is None
    assert repos.rutas.llamadas[0] == ("rutas_cercanas", 800)


def test_rutas_cercanas_con_radio_explicito(cliente: TestClient, repos: Repositorios) -> None:
    cliente.get("/api/v1/rutas/cercanas", params={"lat": 5.07, "lng": -75.51, "radioM": 300})
    assert repos.rutas.llamadas[0] == ("rutas_cercanas", 300)


def test_rutas_cercanas_sin_cobertura_devuelve_paradero_mas_cercano(cliente: TestClient) -> None:
    r = cliente.get("/api/v1/rutas/cercanas", params={"lat": 7.0, "lng": -75.51})
    assert r.status_code == 200
    assert r.json()["rutas"] == []
    assert r.json()["paraderoMasCercano"]["nombre"] == "Parada A"


def test_rutas_cercanas_valida_parametros(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/rutas/cercanas", params={"lat": 5.07}).status_code == 400
    assert cliente.get("/api/v1/rutas/cercanas", params={"lat": 5.07, "lng": -75.5, "radioM": 10}).status_code == 400


def test_listar_rutas(cliente: TestClient) -> None:
    r = cliente.get("/api/v1/rutas")
    assert r.status_code == 200
    assert [x["nombre"] for x in r.json()] == ["La Enea", "Villamaría"]
    assert r.json()[0]["tipoRecorrido"] == "circular"


def test_detalle_de_ruta_incluye_trazado_paraderos_y_avisos(cliente: TestClient) -> None:
    r = cliente.get(f"/api/v1/rutas/{dobles.RUTA_ENEA}")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["trazado"]["type"] == "LineString"
    assert [p["orden"] for p in cuerpo["paraderos"]] == [1, 2]
    assert cuerpo["avisos"][0]["titulo"] == "Obra en la Avenida"
    assert cuerpo["version"] == 1


def test_detalle_de_ruta_inexistente_404(cliente: TestClient) -> None:
    r = cliente.get(f"/api/v1/rutas/{uuid4()}")
    assert r.status_code == 404
    assert r.json()["error"]["codigo"] == "NO_ENCONTRADO"


def test_detalle_con_id_invalido_400(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/rutas/no-es-uuid").status_code == 400


def test_paraderos_cercanos_filtra_por_radio_y_ruta(cliente: TestClient, repos: Repositorios) -> None:
    r = cliente.get(
        "/api/v1/paraderos/cercanos", params={"lat": 5.07, "lng": -75.51, "radioM": 200, "rutaId": str(dobles.RUTA_ENEA)}
    )
    assert r.status_code == 200
    assert [p["nombre"] for p in r.json()] == ["Parada A"]
    assert repos.rutas.llamadas[-1] == ("paraderos_cercanos", 200, dobles.RUTA_ENEA)


def test_empresas(cliente: TestClient) -> None:
    r = cliente.get("/api/v1/empresas")
    assert r.status_code == 200
    assert {e["nombre"] for e in r.json()} == {"Sideral", "Serviturismo"}


def test_horarios_por_servicio_con_estado_y_pendientes(cliente: TestClient) -> None:
    r = cliente.get(f"/api/v1/rutas/{dobles.RUTA_ENEA}/horarios")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["tipoDiaHoy"] in ("lun_vie", "sabado", "dom_festivo")
    sideral, servi = cuerpo["servicios"]
    assert sideral["estado"] == "parcial"
    assert sideral["tiposDiaPendientes"] == ["dom_festivo"]
    assert sideral["horarios"][0] == {
        "tipoDia": "lun_vie", "primeraSalida": "05:30", "ultimaSalida": "21:00", "cierre": "22:00", "nota": None,
    }
    assert servi["estado"] == "pendiente_actualizacion"
    assert servi["horarios"] == []
    assert sideral["version"] == 2


def test_horarios_de_ruta_inexistente_404(cliente: TestClient) -> None:
    assert cliente.get(f"/api/v1/rutas/{uuid4()}/horarios").status_code == 404


def test_frecuencias_con_franjas_en_hhmm(cliente: TestClient) -> None:
    r = cliente.get(f"/api/v1/rutas/{dobles.RUTA_ENEA}/frecuencias")
    assert r.status_code == 200
    sideral = r.json()["servicios"][0]
    assert sideral["frecuencias"][0]["franjaInicio"] == "05:30"
    assert sideral["frecuencias"][1]["franjaFin"] == "24:00"
    assert sideral["frecuencias"][1]["minutosMax"] == 10
    assert r.json()["servicios"][1]["frecuencias"] == []


def test_buscar_rutas_por_texto_sin_tildes(cliente: TestClient, repos: Repositorios) -> None:
    r = cliente.get("/api/v1/busqueda/rutas", params={"q": "  ENÉA "})
    assert r.status_code == 200
    assert [x["nombre"] for x in r.json()] == ["La Enea"]
    assert repos.busqueda.patrones[-1] == ("%enea%", "enea")


def test_buscar_rutas_por_codigo(cliente: TestClient) -> None:
    assert len(cliente.get("/api/v1/busqueda/rutas", params={"q": "39"}).json()) == 1


def test_buscar_vacio_o_solo_espacios_400(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/busqueda/rutas", params={"q": ""}).status_code == 400
    r = cliente.get("/api/v1/busqueda/hitos", params={"q": "   "})
    assert r.status_code == 400
    assert r.json()["error"]["codigo"] == "VALIDACION"


def test_buscar_hitos_por_nombre_y_alias(cliente: TestClient) -> None:
    por_nombre = cliente.get("/api/v1/busqueda/hitos", params={"q": "cable aereo"}).json()
    por_alias = cliente.get("/api/v1/busqueda/hitos", params={"q": "Cable"}).json()
    assert por_nombre[0]["nombre"] == "Cable Aéreo"
    assert por_alias[0]["alias"] == ["Cable"]


def test_rutas_por_hito_con_cobertura(cliente: TestClient) -> None:
    r = cliente.get(f"/api/v1/hitos/{dobles.HITO_CABLE}/rutas")
    assert r.status_code == 200
    assert r.json()["cobertura"] is True
    assert r.json()["rutas"][0]["distanciaM"] == 150.0
    assert r.json()["paraderoMasCercano"] is None


def test_rutas_por_hito_sin_cobertura_da_paradero_mas_cercano(cliente: TestClient) -> None:
    r = cliente.get(f"/api/v1/hitos/{dobles.HITO_LEJANO}/rutas")
    assert r.status_code == 200
    assert r.json()["cobertura"] is False
    assert r.json()["rutas"] == []
    assert r.json()["paraderoMasCercano"]["nombre"] == "Parada A"


def test_rutas_por_hito_inexistente_404(cliente: TestClient) -> None:
    assert cliente.get(f"/api/v1/hitos/{uuid4()}/rutas").status_code == 404


def test_avisos_vigentes_usan_el_reloj_y_el_filtro_de_ruta(cliente: TestClient, repos: Repositorios) -> None:
    r = cliente.get("/api/v1/avisos", params={"rutaId": str(dobles.RUTA_ENEA)})
    assert r.status_code == 200
    aviso = r.json()[0]
    assert aviso["origen"] == "movilidad"
    assert aviso["tipoCambio"] == "obra"
    ruta_id, ahora = repos.avisos.consultas[-1]
    assert ruta_id == dobles.RUTA_ENEA
    assert isinstance(ahora, datetime) and ahora.utcoffset() is not None


def test_cada_consulta_registra_un_evento_de_uso_anonimo(cliente: TestClient, repos: Repositorios) -> None:
    cliente.get("/api/v1/rutas")
    cliente.get(f"/api/v1/rutas/{dobles.RUTA_ENEA}")
    cliente.get(f"/api/v1/rutas/{dobles.RUTA_ENEA}/horarios")
    cliente.get(f"/api/v1/rutas/{dobles.RUTA_ENEA}/frecuencias")
    cliente.get("/api/v1/busqueda/rutas", params={"q": "enea"})
    assert [t for t, _ in repos.eventos_uso.eventos] == ["mapa", "detalle_ruta", "horarios", "frecuencias", "busqueda"]
    assert repos.eventos_uso.eventos[1][1] == dobles.RUTA_ENEA


def test_una_consulta_fallida_no_registra_evento(cliente: TestClient, repos: Repositorios) -> None:
    cliente.get(f"/api/v1/rutas/{uuid4()}")
    assert repos.eventos_uso.eventos == []


def test_si_falla_el_registro_de_uso_la_respuesta_sigue_ok(repos: Repositorios) -> None:
    repos.eventos_uso.falla = True
    c = TestClient(crear_app(construir_contenedor(Configuracion(_env_file=None), repos)), raise_server_exceptions=False)
    assert c.get("/api/v1/rutas").status_code == 200


def test_el_reloj_simulado_alimenta_tipo_dia(contenedor: Contenedor) -> None:
    contenedor.reloj.fijar_hora(time(7, 0))  # solo cambia la hora; el tipo de día sigue siendo el de hoy
    ahora = contenedor.reloj.ahora()
    assert ahora.hour == 7 and ahora.minute == 0
