"""B3a: CalculadorEta, DeductorDeRuta, registrar_posiciones, busetas en vivo, ETA e ingesta (sin base de datos)."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from composicion import Contenedor, Repositorios, construir_contenedor
from modulos.seguimiento import DeductorDeRuta, PosicionEntrante
from modulos.seguimiento.dominio.calculador_eta import (
    CalculadorEta,
    EntradaEta,
    FranjaFrecuencia,
    HorarioDia,
    PosicionConProgreso,
    distancia_restante_m,
)
from modulos.seguimiento.dominio.validacion_posicion import motivo_de_rechazo
from nucleo.configuracion import Configuracion
from nucleo.emisor_eventos import POSICION_ACEPTADA
from pruebas import dobles
from pruebas.dobles import LUNES_MEDIODIA, RelojFijo
from servidor import crear_app

AHORA = LUNES_MEDIODIA
CAJA = {"minLat": 4.95, "maxLat": 5.20, "minLng": -75.65, "maxLng": -75.40}


def entrada(**cambios) -> EntradaEta:
    base = {
        "servicio_id": uuid4(), "empresa": "Sideral", "codigo_publico": "39", "suspendido": False,
        "horario": HorarioDia(time(5, 30), time(21, 0), time(22, 0)), "duracion_min": 60,
        "franjas": [FranjaFrecuencia(0, 1440, 8, 10)], "posiciones": [],
    }
    return EntradaEta(**(base | cambios))


def posicion(progreso: float, velocidad: float | None = 20.0, hace_s: int = 5, lateral: str = "1544") -> PosicionConProgreso:
    return PosicionConProgreso(lateral, progreso, AHORA - timedelta(seconds=hace_s), velocidad)


calculador = CalculadorEta(velocidad_default_kmh=20, umbral_obsoleta_s=60)


# ---------- CalculadorEta ----------


def test_mil_metros_a_20_kmh_son_180_segundos() -> None:
    r = calculador.calcular(entrada(posiciones=[posicion(1000)]), AHORA, 2000, 10000)
    assert (r.fuente, r.eta_segundos, r.buseta_numero_lateral, r.ultima_senal_hace_s) == ("gps", 180, "1544", 5)


def test_velocidad_cero_usa_la_velocidad_por_defecto() -> None:
    assert calculador.calcular(entrada(posiciones=[posicion(1000, velocidad=0)]), AHORA, 2000, 10000).eta_segundos == 180
    assert calculador.calcular(entrada(posiciones=[posicion(1000, velocidad=None)]), AHORA, 2000, 10000).eta_segundos == 180


def test_con_dos_busetas_toma_la_mas_cercana() -> None:
    posiciones = [posicion(100, lateral="1111"), posicion(1000, lateral="2222")]
    r = calculador.calcular(entrada(posiciones=posiciones), AHORA, 2000, 10000)
    assert r.buseta_numero_lateral == "2222" and r.eta_segundos == 180


def test_circular_la_buseta_que_ya_paso_da_la_vuelta() -> None:
    # circuito de 10 000 m, buseta en 9 500 m, paradero en 500 m: faltan 1 000 m
    assert distancia_restante_m(500, 9500, 10000) == 1000
    r = calculador.calcular(entrada(posiciones=[posicion(9500)]), AHORA, 500, 10000)
    assert r.eta_segundos == 180


def test_buseta_que_acaba_de_pasar_el_paradero_esta_a_casi_una_vuelta() -> None:
    assert distancia_restante_m(500, 510, 10000) == 9990


def test_posicion_vieja_cae_al_respaldo_por_horario() -> None:
    r = calculador.calcular(entrada(posiciones=[posicion(1000, hace_s=61)]), AHORA, 2000, 10000)
    assert r.fuente == "horario" and r.rango_max_segundos == 600
    assert r.mensaje.startswith("Sin señal GPS en este momento.")
    assert "cada 8 a 10 min" in r.mensaje and "Esté pendiente de la siguiente buseta." in r.mensaje


def test_sin_busetas_el_mensaje_es_el_del_contrato() -> None:
    r = calculador.calcular(entrada(franjas=[FranjaFrecuencia(0, 1440, 4, 4)]), AHORA, 2000, 10000)
    assert r.fuente == "horario" and r.rango_max_segundos == 240
    assert r.mensaje == (
        "Sin ubicación de busetas. Estimación por horario: cada 4 min. Esté pendiente de la siguiente buseta."
    )


def test_sin_frecuencia_en_la_franja_actual() -> None:
    r = calculador.calcular(entrada(franjas=[FranjaFrecuencia(0, 360, 4, 4)]), AHORA, 2000, 10000)
    assert (r.fuente, r.mensaje) == ("no_disponible", "Frecuencia no informada por la empresa.")


def test_con_gps_no_hace_falta_frecuencia() -> None:
    r = calculador.calcular(entrada(franjas=[], posiciones=[posicion(1000)]), AHORA, 2000, 10000)
    assert r.fuente == "gps"


def test_fuera_de_horario() -> None:
    antes = calculador.calcular(entrada(posiciones=[posicion(1000)]), AHORA.replace(hour=4), 2000, 10000)
    despues = calculador.calcular(entrada(posiciones=[posicion(1000)]), AHORA.replace(hour=22, minute=30), 2000, 10000)
    assert (antes.fuente, antes.mensaje) == ("no_disponible", "Aún no inicia el servicio.")
    assert (despues.fuente, despues.mensaje) == ("no_disponible", "El servicio ya cerró.")


def test_sin_cierre_usa_ultima_salida_mas_duracion() -> None:
    horario = HorarioDia(time(5, 30), time(21, 0), None)
    dentro = calculador.calcular(entrada(horario=horario, duracion_min=60), AHORA.replace(hour=21, minute=50), 2000, 10000)
    fuera = calculador.calcular(entrada(horario=horario, duracion_min=60), AHORA.replace(hour=22, minute=10), 2000, 10000)
    assert dentro.fuente == "horario" and fuera.mensaje == "El servicio ya cerró."


def test_servicio_suspendido() -> None:
    r = calculador.calcular(entrada(suspendido=True), AHORA, 2000, 10000)
    assert (r.fuente, r.mensaje) == ("no_disponible", "El servicio está suspendido.")


def test_sabado_sin_horario_es_informacion_pendiente() -> None:
    r = calculador.calcular(entrada(horario=None), AHORA, 2000, 10000)
    assert r.fuente == "no_disponible" and "Información pendiente de actualización" in r.mensaje


# ---------- validación de posiciones ----------


def _entrante(**cambios) -> PosicionEntrante:
    base = {"numero_lateral": "1544", "lat": 5.07, "lng": -75.51, "reportada_en": AHORA}
    return PosicionEntrante(**(base | cambios))


@pytest.mark.parametrize(
    ("cambios", "motivo"),
    [
        ({}, None),
        ({"lat": 95.0}, "coordenadas_invalidas"),
        ({"lng": float("nan")}, "coordenadas_invalidas"),
        ({"lat": 6.5}, "fuera_de_zona"),
        ({"reportada_en": datetime(2026, 10, 26, 12, 0)}, "fecha_invalida"),
        ({"reportada_en": AHORA + timedelta(seconds=61)}, "fecha_futura"),
        ({"reportada_en": AHORA + timedelta(seconds=59)}, None),
    ],
)
def test_motivos_de_rechazo(cambios: dict, motivo: str | None) -> None:
    assert motivo_de_rechazo(_entrante(**cambios), AHORA, CAJA) == motivo


# ---------- DeductorDeRuta ----------


async def test_deductor_turno_vigente_dos_turnos_y_fuera_de_turno() -> None:
    repo = dobles.SeguimientoEnMemoria()
    deductor = DeductorDeRuta(repo)
    assert await deductor(dobles.EMPRESA_SIDERAL, "1544", AHORA) == dobles.SERVICIO_SIDERAL_ENEA
    assert await deductor(dobles.EMPRESA_SIDERAL, "1544", AHORA.replace(hour=3)) is None  # fuera de turno
    assert await deductor(dobles.EMPRESA_SIDERAL, "9999", AHORA) is None  # sin turno
    otra_ruta = uuid4()
    repo.turnos[(dobles.EMPRESA_SIDERAL, "1520")] = (time(5, 0), time(13, 0), dobles.SERVICIO_SIDERAL_ENEA)
    repo.turnos[(dobles.EMPRESA_SIDERAL, "1520")] = (time(5, 0), time(13, 0), dobles.SERVICIO_SIDERAL_ENEA)
    assert await deductor(dobles.EMPRESA_SIDERAL, "1520", AHORA.replace(hour=10)) == dobles.SERVICIO_SIDERAL_ENEA
    repo.turnos[(dobles.EMPRESA_SIDERAL, "1520")] = (time(13, 0), time(22, 0), otra_ruta)  # misma buseta, otro turno
    assert await deductor(dobles.EMPRESA_SIDERAL, "1520", AHORA.replace(hour=15)) == otra_ruta


# ---------- API con dobles ----------


@pytest.fixture
def repos() -> Repositorios:
    return dobles.repositorios_en_memoria()


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo()


@pytest.fixture
def contenedor(repos: Repositorios, reloj: RelojFijo) -> Contenedor:
    return construir_contenedor(Configuracion(_env_file=None), repos, reloj)


@pytest.fixture
def cliente(contenedor: Contenedor) -> TestClient:
    return TestClient(crear_app(contenedor), raise_server_exceptions=False)


def _lote(**cambios) -> dict:
    posicion = {
        "numeroLateral": "1544", "lat": 5.07, "lng": -75.51, "velocidadKmh": 24.5, "rumbo": 130,
        "reportadaEn": AHORA.isoformat(),
    } | cambios
    return {"posiciones": [posicion]}


def _cabecera(clave: str = dobles.CLAVE_SIDERAL) -> dict:
    return {"X-Clave-Fuente": clave}


def test_ingesta_sin_clave_o_con_clave_invalida_401(cliente: TestClient) -> None:
    assert cliente.post("/api/v1/ingesta/posiciones", json=_lote()).status_code == 401
    r = cliente.post("/api/v1/ingesta/posiciones", json=_lote(), headers=_cabecera("otra"))
    assert r.status_code == 401 and r.json()["error"]["codigo"] == "NO_AUTENTICADO"


def test_ingesta_acepta_y_marca_uso_de_la_credencial(cliente: TestClient, repos: Repositorios) -> None:
    r = cliente.post("/api/v1/ingesta/posiciones", json=_lote(), headers=_cabecera())
    assert r.status_code == 202
    assert r.json() == {"aceptadas": 1, "descartadas": 0, "rechazadas": []}
    assert repos.fuentes_gps.usos == [dobles.CREDENCIAL]
    guardada = repos.seguimiento.guardadas[dobles.BUSETA_1544]
    assert guardada["servicio_id"] == dobles.SERVICIO_SIDERAL_ENEA


def test_ingesta_descarta_la_posicion_mas_antigua(cliente: TestClient) -> None:
    cliente.post("/api/v1/ingesta/posiciones", json=_lote(), headers=_cabecera())
    vieja = _lote(reportadaEn=(AHORA - timedelta(seconds=30)).isoformat())
    r = cliente.post("/api/v1/ingesta/posiciones", json=vieja, headers=_cabecera())
    assert r.status_code == 202
    assert (r.json()["aceptadas"], r.json()["descartadas"]) == (0, 1)


def test_ingesta_rechaza_con_indice_y_motivo(cliente: TestClient) -> None:
    cuerpo = {"posiciones": [
        _lote(lat=95)["posiciones"][0],
        _lote(lat=6.5)["posiciones"][0],
        _lote(reportadaEn=(AHORA + timedelta(minutes=5)).isoformat())["posiciones"][0],
        _lote(numeroLateral="0000")["posiciones"][0],
        _lote(reportadaEn="2026-10-26T12:00:00")["posiciones"][0],
        _lote()["posiciones"][0],
    ]}
    r = cliente.post("/api/v1/ingesta/posiciones", json=cuerpo, headers=_cabecera())
    assert r.status_code == 202
    assert [(x["indice"], x["motivo"]) for x in r.json()["rechazadas"]] == [
        (0, "coordenadas_invalidas"), (1, "fuera_de_zona"), (2, "fecha_futura"), (3, "buseta_desconocida"), (4, "fecha_invalida"),
    ]
    assert r.json()["aceptadas"] == 1


def test_ingesta_valida_el_tamano_del_lote(cliente: TestClient) -> None:
    assert cliente.post("/api/v1/ingesta/posiciones", json={"posiciones": []}, headers=_cabecera()).status_code == 400
    grande = {"posiciones": _lote()["posiciones"] * 101}
    assert cliente.post("/api/v1/ingesta/posiciones", json=grande, headers=_cabecera()).status_code == 400


def test_buseta_sin_turno_se_guarda_sin_servicio_y_no_aparece_en_ruta(cliente: TestClient, repos: Repositorios) -> None:
    repos.seguimiento.busetas[(dobles.EMPRESA_SIDERAL, "1388")] = {"id": uuid4(), "numero_lateral": "1388"}
    r = cliente.post("/api/v1/ingesta/posiciones", json=_lote(numeroLateral="1388"), headers=_cabecera())
    assert r.json()["aceptadas"] == 1
    assert [p["servicio_id"] for p in repos.seguimiento.guardadas.values()] == [None]
    assert cliente.get(f"/api/v1/rutas/{dobles.RUTA_ENEA}/busetas").json()["busetas"] == []


async def test_registrar_posiciones_emite_el_evento(contenedor: Contenedor) -> None:
    recibidos: list[dict] = []

    async def escuchar(carga: dict) -> None:
        recibidos.append(carga)

    contenedor.emisor.suscribir(POSICION_ACEPTADA, escuchar)
    resultado = await contenedor.servicios.registrar_posiciones(dobles.EMPRESA_SIDERAL, [_entrante()])
    assert resultado.aceptadas == 1
    assert recibidos[0]["ruta_id"] == dobles.RUTA_ENEA and recibidos[0]["numero_lateral"] == "1544"


async def test_un_suscriptor_roto_no_frena_el_ciclo(contenedor: Contenedor) -> None:
    async def roto(carga: dict) -> None:
        raise RuntimeError("cliente lento")

    contenedor.emisor.suscribir(POSICION_ACEPTADA, roto)
    resultado = await contenedor.servicios.registrar_posiciones(dobles.EMPRESA_SIDERAL, [_entrante()])
    assert resultado.aceptadas == 1


def test_busetas_en_vivo_activa_y_sin_senal(cliente: TestClient, reloj: RelojFijo) -> None:
    cliente.post("/api/v1/ingesta/posiciones", json=_lote(), headers=_cabecera())
    r = cliente.get(f"/api/v1/rutas/{dobles.RUTA_ENEA}/busetas")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["seguimientoDisponible"] is True and cuerpo["unidadesEnServicio"] == 2
    assert cuerpo["busetas"][0]["estado"] == "activa" and cuerpo["busetas"][0]["mensaje"] is None
    reloj.fijar(AHORA + timedelta(seconds=61))
    sin_senal = cliente.get(f"/api/v1/rutas/{dobles.RUTA_ENEA}/busetas").json()["busetas"][0]
    assert sin_senal["estado"] == "sin_senal"
    assert sin_senal["mensaje"] == "Ubicación no disponible. Última señal hace más de 60 s."


def test_busetas_en_vivo_sin_posiciones(cliente: TestClient) -> None:
    cuerpo = cliente.get(f"/api/v1/rutas/{dobles.RUTA_ENEA}/busetas").json()
    assert cuerpo["seguimientoDisponible"] is False and cuerpo["busetas"] == []


def test_busetas_de_ruta_inexistente_404(cliente: TestClient) -> None:
    assert cliente.get(f"/api/v1/rutas/{uuid4()}/busetas").status_code == 404


def test_eta_por_gps_y_por_horario_en_la_misma_respuesta(cliente: TestClient, repos: Repositorios) -> None:
    cliente.post("/api/v1/ingesta/posiciones", json=_lote(velocidadKmh=20), headers=_cabecera())
    r = cliente.get(f"/api/v1/paraderos/{dobles.PARADERO_A}/eta", params={"rutaId": str(dobles.RUTA_ENEA)})
    assert r.status_code == 200
    sideral, servi = r.json()["resultados"]
    assert (sideral["fuente"], sideral["etaSegundos"], sideral["busetaNumeroLateral"]) == ("gps", 180, "1544")
    assert servi["fuente"] == "no_disponible"  # el doble no tiene horario para Serviturismo (información pendiente)
    assert "pendiente de actualización" in servi["mensaje"]


def test_eta_sin_posiciones_usa_horario_y_filtra_por_servicio(cliente: TestClient) -> None:
    r = cliente.get(
        f"/api/v1/paraderos/{dobles.PARADERO_A}/eta",
        params={"rutaId": str(dobles.RUTA_ENEA), "servicioId": str(dobles.SERVICIO_SIDERAL_ENEA)},
    )
    [sideral] = r.json()["resultados"]
    assert sideral["fuente"] == "horario" and sideral["rango"] == {"minSegundos": 0, "maxSegundos": 600}


def test_eta_errores(cliente: TestClient) -> None:
    ruta = str(dobles.RUTA_ENEA)
    assert cliente.get(f"/api/v1/paraderos/{dobles.PARADERO_A}/eta").status_code == 400  # falta rutaId
    assert cliente.get(f"/api/v1/paraderos/{uuid4()}/eta", params={"rutaId": ruta}).status_code == 404
    assert cliente.get(f"/api/v1/paraderos/{dobles.PARADERO_A}/eta", params={"rutaId": str(uuid4())}).status_code == 404
    r = cliente.get(f"/api/v1/paraderos/{dobles.PARADERO_A}/eta", params={"rutaId": ruta, "servicioId": str(uuid4())})
    assert r.status_code == 404


def test_eta_registra_evento_de_uso(cliente: TestClient, repos: Repositorios) -> None:
    cliente.get(f"/api/v1/paraderos/{dobles.PARADERO_A}/eta", params={"rutaId": str(dobles.RUTA_ENEA)})
    assert ("eta", dobles.RUTA_ENEA) in repos.eventos_uso.eventos
