"""B6: favoritos, alertas de llegada (EvaluadorAlertas, WebSocket de notificaciones) y planificación de viajes directos."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from composicion import Repositorios, construir_contenedor
from modulos.pasajero.dominio.evaluador_alertas import EvaluadorAlertas, distancia_restante_m
from modulos.planificacion.dominio.calculo import calcular_tiempos
from nucleo.configuracion import Configuracion
from nucleo.reloj import RelojSimulado
from pruebas import dobles
from pruebas.dobles import LUNES_MEDIODIA, RelojFijo
from servidor import crear_app

AHORA = LUNES_MEDIODIA
PARADERO = uuid4()
LONGITUD = 10000.0


def alerta(distancia: int = 300, ultima: datetime | None = None) -> dict:
    return {"id": uuid4(), "paradero_id": PARADERO, "distancia_aviso_m": distancia, "ultima_notificacion_en": ultima}


def evaluar(ev: EvaluadorAlertas, alertas: list[dict], progreso_bus: float, desvio: float = 0, ahora: datetime = AHORA):
    return ev.evaluar(alertas, "1544", progreso_bus, desvio, LONGITUD, {PARADERO: 500.0}, ahora)


# ---------- EvaluadorAlertas ----------


def test_dispara_al_entrar_en_la_distancia_de_aviso() -> None:
    ev, a = EvaluadorAlertas(10, 100), alerta(300)
    assert evaluar(ev, [a], 100) == []  # a 400 m
    [n] = evaluar(ev, [a], 300)  # a 200 m
    assert (n.tipo, n.distancia_m, n.mensaje) == ("alerta_llegada", 200, "La buseta 1544 está a 200 m de tu paradero.")


def test_enfriamiento_evita_avisar_dos_veces() -> None:
    ev = EvaluadorAlertas(10, 100)
    reciente = alerta(300, ultima=AHORA - timedelta(minutes=3))
    vencido = alerta(300, ultima=AHORA - timedelta(minutes=11))
    assert evaluar(ev, [reciente], 300) == []
    assert len(evaluar(ev, [vencido], 300)) == 1


def test_buseta_que_ya_paso_no_dispara() -> None:
    ev = EvaluadorAlertas(10, 100)
    assert distancia_restante_m(500, 510, LONGITUD) == 9990
    assert evaluar(ev, [alerta(300)], 510) == []  # acaba de pasar: le falta casi una vuelta


def test_desvio_avisa_una_vez_por_episodio_y_termina_al_volver() -> None:
    ev, a = EvaluadorAlertas(10, 100), alerta(300)
    [n] = evaluar(ev, [a], 300, desvio=150)
    assert (n.tipo, n.mensaje) == ("alerta_desvio", "La buseta 1544 se desvió de su recorrido. Tu llegada puede cambiar.")
    assert evaluar(ev, [a], 320, desvio=160) == []  # mismo episodio: no repite
    assert evaluar(ev, [alerta(300)], 100, desvio=10) == []  # volvió a la ruta (otra alerta, mismo bus: no afecta a `a`)
    assert [x.tipo for x in evaluar(ev, [a], 100, desvio=10)] == []  # `a` vuelve a la ruta y cierra el episodio
    assert [x.tipo for x in evaluar(ev, [a], 100, desvio=150)] == ["alerta_desvio"]  # nuevo episodio


def test_un_desvio_en_curso_no_estima_llegada() -> None:
    ev = EvaluadorAlertas(10, 100)
    assert [n.tipo for n in evaluar(ev, [alerta(300)], 300, desvio=500)] == ["alerta_desvio"]


# ---------- cálculo de planificación ----------


def test_tiempos_de_viaje_directo() -> None:
    t = calcular_tiempos(120, 200, 500, 3000, LONGITUD, 20, 10)
    assert t.caminata_min == 4.0 and t.espera_min == 5.0 and t.bus_min == pytest.approx(7.5)
    assert t.total_min == pytest.approx(16.5)


def test_el_sentido_es_circular_si_el_destino_quedo_atras() -> None:
    adelante = calcular_tiempos(0, 0, 500, 3000, LONGITUD, 20, 10)
    atras = calcular_tiempos(0, 0, 3000, 500, LONGITUD, 20, 10)
    assert atras.bus_min == pytest.approx(22.5) and atras.bus_min > adelante.bus_min


# ---------- API ----------


@pytest.fixture
def repos() -> Repositorios:
    return dobles.repositorios_en_memoria()


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo()


@pytest.fixture
def cliente(repos: Repositorios, reloj: RelojFijo) -> TestClient:
    cont = construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(reloj))
    return TestClient(crear_app(cont), raise_server_exceptions=False)


def _con(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


PAS = _con("tok-pasajera")
RUTA, A, B = str(dobles.RUTA_ENEA), str(dobles.PARADERO_A), str(dobles.PARADERO_B)


def test_favoritos_exigen_sesion_de_pasajero(cliente: TestClient) -> None:
    r = cliente.get("/api/v1/favoritos")
    assert r.status_code == 401 and r.json()["error"]["mensaje"] == "Inicia sesión para guardar."
    assert cliente.get("/api/v1/favoritos", headers=_con("tok-jefe")).status_code == 403
    assert cliente.get("/api/v1/alertas-llegada", headers=_con("tok-admin")).status_code == 403


def test_favorito_de_ruta_y_de_paradero_repetido_devuelve_200(cliente: TestClient) -> None:
    nuevo = cliente.post("/api/v1/favoritos", json={"tipo": "ruta", "rutaId": RUTA}, headers=PAS)
    assert nuevo.status_code == 201 and nuevo.json()["disponible"] is True
    repetido = cliente.post("/api/v1/favoritos", json={"tipo": "ruta", "rutaId": RUTA}, headers=PAS)
    assert repetido.status_code == 200 and repetido.json()["id"] == nuevo.json()["id"]
    assert cliente.post("/api/v1/favoritos", json={"tipo": "paradero", "paraderoId": A}, headers=PAS).status_code == 201
    assert len(cliente.get("/api/v1/favoritos", headers=PAS).json()) == 2


def test_favorito_invalido_o_inexistente(cliente: TestClient) -> None:
    assert cliente.post("/api/v1/favoritos", json={"tipo": "ruta"}, headers=PAS).status_code == 400
    assert cliente.post("/api/v1/favoritos", json={"tipo": "ruta", "rutaId": RUTA, "paraderoId": A}, headers=PAS).status_code == 400
    assert cliente.post("/api/v1/favoritos", json={"tipo": "ruta", "rutaId": str(uuid4())}, headers=PAS).status_code == 404


def test_quitar_favorito_solo_propio(cliente: TestClient, repos: Repositorios) -> None:
    fav = cliente.post("/api/v1/favoritos", json={"tipo": "ruta", "rutaId": RUTA}, headers=PAS).json()["id"]
    ajeno = uuid4()
    repos.favoritos.filas[ajeno] = {"id": ajeno, "usuario_id": uuid4(), "tipo": "ruta"}  # de otro usuario
    assert cliente.delete(f"/api/v1/favoritos/{ajeno}", headers=PAS).status_code == 404
    assert cliente.delete(f"/api/v1/favoritos/{uuid4()}", headers=PAS).status_code == 404
    assert cliente.delete(f"/api/v1/favoritos/{fav}", headers=PAS).status_code == 204
    assert cliente.delete(f"/api/v1/favoritos/{fav}", headers=PAS).status_code == 404


def test_alerta_usa_la_distancia_por_defecto_y_repetida_es_409(cliente: TestClient) -> None:
    cuerpo = {"rutaId": RUTA, "paraderoId": A}
    r = cliente.post("/api/v1/alertas-llegada", json=cuerpo, headers=PAS)
    assert r.status_code == 201 and r.json()["distanciaAvisoM"] == 300 and r.json()["estado"] == "activa"
    dup = cliente.post("/api/v1/alertas-llegada", json=cuerpo, headers=PAS)
    assert dup.status_code == 409 and dup.json()["error"]["codigo"] == "CONFLICTO_NEGOCIO"
    propia = cliente.post("/api/v1/alertas-llegada", json={**cuerpo, "paraderoId": B, "distanciaAvisoM": 500}, headers=PAS)
    assert propia.json()["distanciaAvisoM"] == 500
    assert cliente.post("/api/v1/alertas-llegada", json={**cuerpo, "distanciaAvisoM": 10}, headers=PAS).status_code == 400
    assert cliente.post("/api/v1/alertas-llegada", json={"rutaId": str(uuid4()), "paraderoId": A}, headers=PAS).status_code == 404
    assert len(cliente.get("/api/v1/alertas-llegada", headers=PAS).json()) == 2


def test_eliminar_alerta_la_desactiva(cliente: TestClient) -> None:
    alerta_id = cliente.post("/api/v1/alertas-llegada", json={"rutaId": RUTA, "paraderoId": A}, headers=PAS).json()["id"]
    assert cliente.delete(f"/api/v1/alertas-llegada/{alerta_id}", headers=PAS).status_code == 204
    assert cliente.get("/api/v1/alertas-llegada", headers=PAS).json() == []
    assert cliente.delete(f"/api/v1/alertas-llegada/{alerta_id}", headers=PAS).status_code == 404
    # tras desactivar, se puede crear otra igual
    assert cliente.post("/api/v1/alertas-llegada", json={"rutaId": RUTA, "paraderoId": A}, headers=PAS).status_code == 201


def _posicion() -> dict:
    return {"posiciones": [{"numeroLateral": "1544", "lat": 5.07, "lng": -75.51, "reportadaEn": AHORA.isoformat()}]}


def test_ws_notificaciones_rechaza_sin_token_o_con_token_ajeno(cliente: TestClient) -> None:
    for url in ("/ws/notificaciones", "/ws/notificaciones?token=basura", "/ws/notificaciones?token=tok-jefe"):
        with pytest.raises(WebSocketDisconnect), cliente.websocket_connect(url):
            pass


def test_la_alerta_llega_por_websocket_al_entrar_en_distancia(repos: Repositorios, reloj: RelojFijo) -> None:
    cont = construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(reloj))
    clave = {"X-Clave-Fuente": dobles.CLAVE_SIDERAL}
    with TestClient(crear_app(cont)) as c, c.websocket_connect("/ws/notificaciones?token=tok-pasajera") as ws:
        alerta_id = c.post("/api/v1/alertas-llegada", json={"rutaId": RUTA, "paraderoId": A}, headers=PAS).json()["id"]
        assert c.post("/api/v1/ingesta/posiciones", json=_posicion(), headers=clave).status_code == 202
        msg = ws.receive_json()
        assert msg == {
            "tipo": "alerta_llegada", "alertaId": alerta_id, "rutaId": RUTA, "paraderoId": A, "distanciaM": 200,
            "mensaje": "La buseta 1544 está a 200 m de tu paradero.",
        }
        assert repos.alertas.notificadas[0][0].hex == alerta_id.replace("-", "")
        # enfriamiento: una segunda posición más reciente no repite el aviso
        reloj.fijar(AHORA + timedelta(seconds=5))
        segunda = _posicion()
        segunda["posiciones"][0]["reportadaEn"] = (AHORA + timedelta(seconds=5)).isoformat()
        c.post("/api/v1/ingesta/posiciones", json=segunda, headers=clave)
        ws.send_text("ping")
        assert ws.receive_text() == "pong"  # el siguiente mensaje es el pong, no otra alerta


def test_desvio_llega_como_alerta_desvio(repos: Repositorios, reloj: RelojFijo) -> None:
    repos.alertas.punto["desvio_m"] = 250.0
    cont = construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(reloj))
    with TestClient(crear_app(cont)) as c, c.websocket_connect("/ws/notificaciones?token=tok-pasajera") as ws:
        c.post("/api/v1/alertas-llegada", json={"rutaId": RUTA, "paraderoId": A}, headers=PAS)
        c.post("/api/v1/ingesta/posiciones", json=_posicion(), headers={"X-Clave-Fuente": dobles.CLAVE_SIDERAL})
        msg = ws.receive_json()
        assert msg["tipo"] == "alerta_desvio" and msg["busetaNumero"] == "1544"
        assert msg["mensaje"] == "La buseta 1544 se desvió de su recorrido. Tu llegada puede cambiar."


def test_alerta_de_telegram_sin_bot_no_rompe(repos: Repositorios, reloj: RelojFijo) -> None:
    import asyncio

    from nucleo.notificador import DestinoAlerta

    cont = construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(reloj))
    asyncio.run(cont.servicios.crear_alerta_llegada.para_destino(DestinoAlerta(telegram_chat_id=99), dobles.RUTA_ENEA, dobles.PARADERO_A, None))
    mensajes: list = []

    async def enviar(chat: int, texto: str) -> None:
        mensajes.append((chat, texto))

    asyncio.run(cont.servicios.registrar_posiciones(dobles.EMPRESA_SIDERAL, [_entrante()]))  # sin bot: se omite
    assert mensajes == []
    cont.notificador.enviar_telegram = enviar
    repos.alertas.filas[next(iter(repos.alertas.filas))]["ultima_notificacion_en"] = None
    asyncio.run(cont.servicios.registrar_posiciones(dobles.EMPRESA_SIDERAL, [_entrante(segundos=3)]))
    assert mensajes == [(99, "La buseta 1544 está a 200 m de tu paradero.")]


def _entrante(segundos: int = 0):
    from modulos.seguimiento import PosicionEntrante

    return PosicionEntrante("1544", 5.07, -75.51, AHORA + timedelta(seconds=segundos))


# ---------- planificación ----------


def _plan(origen: dict, destino: dict) -> dict:
    return {"origen": origen, "destino": destino}


ORIGEN = {"lat": 5.07, "lng": -75.51}
DESTINO = {"lat": 5.08, "lng": -75.51}  # lat >= 5.075: el doble devuelve el paradero B a 200 m


def test_planificar_una_opcion_directa(cliente: TestClient) -> None:
    r = cliente.post("/api/v1/viajes/planificar", json=_plan(ORIGEN, DESTINO))
    assert r.status_code == 200
    [op] = r.json()["opciones"]
    assert op["tipo"] == "directa" and op["rutaId"] == RUTA and op["servicioId"] == str(dobles.SERVICIO_SIDERAL_ENEA)
    assert op["paraderoOrigen"]["paraderoId"] == A and op["paraderoDestino"]["paraderoId"] == B
    assert (op["caminataMin"], op["esperaMin"], op["busMin"], op["totalMin"]) == (4.0, 5.0, 7.5, 16.5)
    assert r.json()["motivo"] is None and r.json()["paraderoMasCercano"] is None


def test_planificar_el_sentido_circular_cambia_el_tiempo_de_bus(cliente: TestClient) -> None:
    r = cliente.post("/api/v1/viajes/planificar", json=_plan(DESTINO, ORIGEN))
    [op] = r.json()["opciones"]
    assert op["paraderoOrigen"]["paraderoId"] == B and op["busMin"] == 22.5


def test_planificar_por_hito(cliente: TestClient) -> None:
    r = cliente.post("/api/v1/viajes/planificar", json=_plan({"hitoId": str(dobles.HITO_CABLE)}, {"hitoId": str(dobles.HITO_LEJANO)}))
    assert r.status_code == 200 and len(r.json()["opciones"]) == 1
    assert cliente.post("/api/v1/viajes/planificar", json=_plan({"hitoId": str(uuid4())}, DESTINO)).status_code == 404


def test_planificar_ruta_compartida_da_una_opcion_por_empresa(cliente: TestClient, repos: Repositorios) -> None:
    from datetime import time

    original = repos.horarios.horarios_de

    async def con_serviturismo(ids):
        filas = await original(ids)
        return filas + [{"servicio_id": dobles.SERVICIO_SERVITURISMO_ENEA, "tipo_dia": "lun_vie", "primera_salida": time(4, 40),
                         "ultima_salida": time(22, 0), "cierre": None, "nota": None}]

    async def frecuencias(ids):
        return [{"servicio_id": dobles.SERVICIO_SERVITURISMO_ENEA, "tipo_dia": "lun_vie", "inicio_minuto": 0, "fin_minuto": 1440,
                 "minutos_min": 4, "minutos_max": 4, "nota": None},
                {"servicio_id": dobles.SERVICIO_SIDERAL_ENEA, "tipo_dia": "lun_vie", "inicio_minuto": 0, "fin_minuto": 1440,
                 "minutos_min": 8, "minutos_max": 10, "nota": None}]

    repos.horarios.horarios_de = con_serviturismo
    repos.horarios.frecuencias_de = frecuencias
    ops = cliente.post("/api/v1/viajes/planificar", json=_plan(ORIGEN, DESTINO)).json()["opciones"]
    assert [o["servicioId"] for o in ops] == [str(dobles.SERVICIO_SERVITURISMO_ENEA), str(dobles.SERVICIO_SIDERAL_ENEA)]
    assert ops[0]["totalMin"] < ops[1]["totalMin"]  # ordenadas por tiempo total (espera 2 min vs 5 min)


def test_planificar_corta_en_el_maximo_de_opciones(cliente: TestClient, repos: Repositorios) -> None:
    repos.parametros.valores["max_opciones_viaje"] = 1
    assert len(cliente.post("/api/v1/viajes/planificar", json=_plan(ORIGEN, DESTINO)).json()["opciones"]) == 1


def test_planificar_fuera_de_horario_no_da_opciones(cliente: TestClient, reloj: RelojFijo) -> None:
    reloj.fijar(LUNES_MEDIODIA.replace(hour=23, minute=30))
    r = cliente.post("/api/v1/viajes/planificar", json=_plan(ORIGEN, DESTINO))
    assert r.status_code == 200 and r.json()["opciones"] == []
    assert r.json()["motivo"] == "No hay una ruta directa entre esos paraderos en este horario."


def test_planificar_sin_paraderos_cerca_devuelve_el_mas_cercano(cliente: TestClient) -> None:
    r = cliente.post("/api/v1/viajes/planificar", json=_plan({"lat": 7.0, "lng": -75.51}, DESTINO))
    assert r.json()["opciones"] == [] and r.json()["motivo"].startswith("No hay paraderos a menos de 500 m del origen")
    assert r.json()["paraderoMasCercano"]["nombre"] == "Parada A"
    lejos = cliente.post("/api/v1/viajes/planificar", json=_plan(ORIGEN, {"lat": 7.0, "lng": -75.51}))
    assert lejos.json()["motivo"].endswith("del destino.")


def test_planificar_valida_el_lugar(cliente: TestClient) -> None:
    assert cliente.post("/api/v1/viajes/planificar", json=_plan({"lat": 5.0}, DESTINO)).status_code == 400
    assert cliente.post("/api/v1/viajes/planificar", json=_plan({"lat": 5.0, "lng": -75.5, "hitoId": str(uuid4())}, DESTINO)).status_code == 400
    assert cliente.post("/api/v1/viajes/planificar", json=_plan({}, DESTINO)).status_code == 400


def test_planificar_registra_evento_de_uso(cliente: TestClient, repos: Repositorios) -> None:
    cliente.post("/api/v1/viajes/planificar", json=_plan(ORIGEN, DESTINO))
    assert ("planificacion", None) in repos.eventos_uso.eventos
