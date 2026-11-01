"""B3b: reloj simulado, simulador de GPS, panel de demo, autenticación, perfil y WebSocket (sin base de datos)."""

from __future__ import annotations

import asyncio
import random
from datetime import time, timedelta
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from composicion import Contenedor, Repositorios, construir_contenedor
from herramientas.simulador_gps import Circuito, desplazar, haversine_m, rumbo_grados
from modulos.administracion import AutenticacionSupabase
from nucleo.configuracion import Configuracion
from nucleo.errores import ErrorNoAutenticado, ErrorServicioExterno
from nucleo.reloj import RelojSimulado
from pruebas import dobles
from pruebas.dobles import LUNES_MEDIODIA, RelojFijo
from servidor import crear_app

# ---------- reloj simulado ----------


def test_reloj_simulado_salta_a_la_hora_y_sigue_corriendo() -> None:
    base = RelojFijo()
    reloj = RelojSimulado(base)
    reloj.fijar_hora(time(6, 30))
    assert (reloj.ahora().hour, reloj.ahora().minute) == (6, 30) and reloj.simulado
    base.fijar(LUNES_MEDIODIA + timedelta(seconds=90))
    assert (reloj.ahora().hour, reloj.ahora().minute, reloj.ahora().second) == (6, 31, 30)
    reloj.fijar_hora(None)
    assert reloj.ahora() == base.ahora() and not reloj.simulado


# ---------- geometría ----------


def test_haversine_y_circuito() -> None:
    assert haversine_m(5.0, -75.5, 5.0, -75.5) == 0
    assert 111_000 < haversine_m(5.0, -75.5, 6.0, -75.5) < 111_400  # un grado de latitud
    circuito = Circuito.desde_geojson(dobles.CUADRADO)
    assert 8_000 < circuito.longitud < 9_000
    lat0, lng0, _ = circuito.punto_en(0)
    lat1, lng1, _ = circuito.punto_en(circuito.longitud)  # una vuelta completa vuelve al inicio
    assert (round(lat0, 5), round(lng0, 5)) == (round(lat1, 5), round(lng1, 5))
    lat_m, lng_m, rumbo = circuito.punto_en(500)
    assert 85 < rumbo < 95 and lat_m == pytest.approx(5.06, abs=1e-4)  # primer lado: hacia el este


def test_desplazar_se_aleja_la_distancia_pedida() -> None:
    lat, lng = desplazar(5.07, -75.51, 90, 160)
    assert haversine_m(5.07, -75.51, lat, lng) == pytest.approx(160, abs=1)
    assert rumbo_grados(5.0, -75.5, 5.0, -75.4) == pytest.approx(90, abs=1)


# ---------- simulador ----------


@pytest.fixture
def repos() -> Repositorios:
    return dobles.repositorios_en_memoria()


@pytest.fixture
def base() -> RelojFijo:
    return RelojFijo()


@pytest.fixture
def contenedor(repos: Repositorios, base: RelojFijo) -> Contenedor:
    config = Configuracion(_env_file=None, modo_demo=True)
    return construir_contenedor(config, repos, RelojSimulado(base))


@pytest.fixture
async def simulador(contenedor: Contenedor):
    sim = contenedor.servicios.simulador
    sim._azar = random.Random(1)
    await sim.cargar()
    return sim


async def test_serviturismo_no_emite_por_defecto_y_sideral_si(simulador, repos: Repositorios) -> None:
    await simulador.ciclo()
    guardadas = repos.seguimiento.guardadas
    assert dobles.BUSETA_1544 in guardadas and dobles.BUSETA_2683 not in guardadas
    g = guardadas[dobles.BUSETA_1544]
    assert g["servicio_id"] == dobles.SERVICIO_SIDERAL_ENEA and 5.05 < g["lat"] < 5.09
    assert g["velocidad_kmh"] is not None and g["reportada_en"] == LUNES_MEDIODIA
    estado = {b["numero_lateral"]: b for b in simulador.estado()["busetas"]}
    assert estado["1544"]["emitiendo"] and estado["1544"]["ultima_posicion"] == LUNES_MEDIODIA
    assert not estado["2683"]["emitiendo"] and estado["2683"]["ultima_posicion"] is None


async def test_la_buseta_avanza_en_cada_ciclo(simulador, repos: Repositorios, base: RelojFijo) -> None:
    await simulador.ciclo()
    primera = dict(repos.seguimiento.guardadas[dobles.BUSETA_1544])
    base.fijar(LUNES_MEDIODIA + timedelta(seconds=3))
    await simulador.ciclo()
    segunda = repos.seguimiento.guardadas[dobles.BUSETA_1544]
    assert segunda["reportada_en"] > primera["reportada_en"]
    assert (segunda["lat"], segunda["lng"]) != (primera["lat"], primera["lng"])


async def test_fuera_de_turno_no_se_mueve(simulador, repos: Repositorios, base: RelojFijo) -> None:
    base.fijar(LUNES_MEDIODIA.replace(hour=3))
    await simulador.ciclo()
    assert repos.seguimiento.guardadas == {}


async def test_perder_y_restaurar_senal(simulador, repos: Repositorios) -> None:
    await simulador.aplicar({"tipo": "perder_senal", "numero_lateral": "1544"})
    await simulador.ciclo()
    assert repos.seguimiento.guardadas == {}
    await simulador.aplicar({"tipo": "restaurar_senal", "empresa_id": dobles.EMPRESA_SIDERAL})
    await simulador.ciclo()
    assert dobles.BUSETA_1544 in repos.seguimiento.guardadas


async def test_activar_gps_de_empresa(simulador, repos: Repositorios) -> None:
    await simulador.aplicar({"tipo": "activar_gps_empresa", "empresa_id": dobles.EMPRESA_SERVITURISMO, "activo": True})
    await simulador.ciclo()
    assert dobles.BUSETA_2683 in repos.seguimiento.guardadas


async def test_desvio_aparta_la_posicion_mas_del_umbral_y_luego_regresa(
    simulador, contenedor: Contenedor, repos: Repositorios, base: RelojFijo
) -> None:
    await simulador.ciclo()
    normal = repos.seguimiento.guardadas[dobles.BUSETA_1544]
    circuito = simulador._circuitos[dobles.RUTA_ENEA]
    avance = simulador._busetas[(dobles.EMPRESA_SIDERAL, "1544")].avance_m
    lat_t, lng_t, _ = circuito.punto_en(avance)
    assert haversine_m(normal["lat"], normal["lng"], lat_t, lng_t) < 1
    await simulador.aplicar({"tipo": "desvio", "numero_lateral": "1544", "duracion_s": 30})
    base.fijar(LUNES_MEDIODIA + timedelta(seconds=3))
    await simulador.ciclo()
    desviada = repos.seguimiento.guardadas[dobles.BUSETA_1544]
    avance = simulador._busetas[(dobles.EMPRESA_SIDERAL, "1544")].avance_m
    lat_t, lng_t, _ = circuito.punto_en(avance)
    assert haversine_m(desviada["lat"], desviada["lng"], lat_t, lng_t) > 100  # umbral_desvio_m por defecto
    base.fijar(LUNES_MEDIODIA + timedelta(seconds=40))
    await simulador.ciclo()
    avance = simulador._busetas[(dobles.EMPRESA_SIDERAL, "1544")].avance_m
    lat_t, lng_t, _ = circuito.punto_en(avance)
    vuelta = repos.seguimiento.guardadas[dobles.BUSETA_1544]
    assert haversine_m(vuelta["lat"], vuelta["lng"], lat_t, lng_t) < 1


async def test_acelerar_aumenta_el_avance(simulador, repos: Repositorios) -> None:
    simulador._intervalo = 10
    await simulador.ciclo()
    a1 = simulador._busetas[(dobles.EMPRESA_SIDERAL, "1544")].avance_m
    await simulador.aplicar({"tipo": "reiniciar_simulacion"})
    await simulador.aplicar({"tipo": "acelerar", "factor": 5})
    simulador._ultimo_ciclo = None
    await simulador.ciclo()
    a5 = simulador._busetas[(dobles.EMPRESA_SIDERAL, "1544")].avance_m
    assert a5 > a1 * 3 and simulador.estado()["factor"] == 5
    assert repos.seguimiento.guardadas[dobles.BUSETA_1544]["velocidad_kmh"] <= 150


async def test_fijar_hora_cambia_el_reloj_y_limpia_posiciones(simulador, repos: Repositorios) -> None:
    await simulador.ciclo()
    await simulador.aplicar({"tipo": "fijar_hora", "hora": time(7, 15)})
    assert repos.seguimiento.guardadas == {}
    estado = simulador.estado()
    assert estado["reloj_simulado"].hour == 7 and estado["reloj_simulado"].minute == 15
    await simulador.aplicar({"tipo": "fijar_hora", "hora": None})
    assert simulador.estado()["reloj_simulado"] is None


async def test_dos_busetas_de_una_ruta_arrancan_separadas(simulador, repos: Repositorios) -> None:
    repos.seguimiento.busetas[(dobles.EMPRESA_SIDERAL, "9000")] = {"id": uuid4(), "numero_lateral": "9000"}
    repos.seguimiento.turnos[(dobles.EMPRESA_SIDERAL, "9000")] = (time(5, 0), time(23, 0), dobles.SERVICIO_SIDERAL_ENEA)
    simulador._busetas[(dobles.EMPRESA_SIDERAL, "9000")] = type(simulador._busetas[(dobles.EMPRESA_SIDERAL, "1544")])(
        "9000", dobles.EMPRESA_SIDERAL, "Sideral", True
    )
    await simulador.ciclo()
    a = simulador._busetas[(dobles.EMPRESA_SIDERAL, "1544")].avance_m
    b = simulador._busetas[(dobles.EMPRESA_SIDERAL, "9000")].avance_m
    assert abs(a - b) > 1000


async def test_escenario_sobre_buseta_inexistente_404(simulador) -> None:
    from nucleo.errores import ErrorNoEncontrado

    with pytest.raises(ErrorNoEncontrado):
        await simulador.aplicar({"tipo": "perder_senal", "numero_lateral": "0000"})


async def test_iniciar_asegura_rodamientos_y_arranca_la_tarea(simulador, repos: Repositorios) -> None:
    simulador._intervalo = 0.01
    await simulador.iniciar()
    await asyncio.sleep(0.05)
    await simulador.detener()
    assert repos.simulacion.rodamientos_asegurados and dobles.BUSETA_1544 in repos.seguimiento.guardadas


# ---------- panel de demo y perfil (HTTP) ----------


@pytest.fixture
def cliente(contenedor: Contenedor) -> TestClient:
    asyncio.run(contenedor.servicios.simulador.cargar())  # lo que haría el lifespan al iniciar
    return TestClient(crear_app(contenedor), raise_server_exceptions=False)


def _con(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_demo_exige_sesion_y_rol_administrador(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/demo/estado").status_code == 401
    assert cliente.get("/api/v1/demo/estado", headers=_con("basura")).status_code == 401
    assert cliente.get("/api/v1/demo/estado", headers=_con("tok-jefe")).status_code == 403
    r = cliente.post("/api/v1/demo/escenarios", json={"tipo": "reiniciar_simulacion"}, headers=_con("tok-pasajera"))
    assert r.status_code == 403


def test_demo_estado_y_escenarios(cliente: TestClient) -> None:
    r = cliente.get("/api/v1/demo/estado", headers=_con("tok-admin"))
    assert r.status_code == 200
    assert r.json()["factor"] == 1 and r.json()["relojSimulado"] is None
    assert [b["numeroLateral"] for b in r.json()["busetas"]] == ["2683", "1544"]  # por empresa y luego número
    r = cliente.post("/api/v1/demo/escenarios", json={"tipo": "acelerar", "factor": 2.5}, headers=_con("tok-admin"))
    assert r.status_code == 200 and r.json()["factor"] == 2.5
    r = cliente.post("/api/v1/demo/escenarios", json={"tipo": "fijar_hora", "hora": "07:30"}, headers=_con("tok-admin"))
    assert r.json()["relojSimulado"] is not None
    r = cliente.post("/api/v1/demo/escenarios", json={"tipo": "fijar_hora", "hora": None}, headers=_con("tok-admin"))
    assert r.json()["relojSimulado"] is None


def test_demo_valida_parametros_del_escenario(cliente: TestClient) -> None:
    cab = _con("tok-admin")
    assert cliente.post("/api/v1/demo/escenarios", json={"tipo": "perder_senal"}, headers=cab).status_code == 400
    sin_duracion = {"tipo": "desvio", "numeroLateral": "1544"}
    assert cliente.post("/api/v1/demo/escenarios", json=sin_duracion, headers=cab).status_code == 400
    assert cliente.post("/api/v1/demo/escenarios", json={"tipo": "acelerar", "factor": 9}, headers=cab).status_code == 400
    assert cliente.post("/api/v1/demo/escenarios", json={"tipo": "acelerar"}, headers=cab).status_code == 400
    r = cliente.post("/api/v1/demo/escenarios", json={"tipo": "perder_senal", "numeroLateral": "0000"}, headers=cab)
    assert r.status_code == 404


def test_demo_apagado_responde_404(repos: Repositorios, base: RelojFijo) -> None:
    cont = construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(base))
    c = TestClient(crear_app(cont), raise_server_exceptions=False)
    r = c.get("/api/v1/demo/estado", headers=_con("tok-admin"))
    assert r.status_code == 404 and r.json()["error"]["codigo"] == "NO_ENCONTRADO"


def test_yo_devuelve_el_perfil_y_la_empresa_solo_del_jefe(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/yo").status_code == 401
    jefe = cliente.get("/api/v1/yo", headers=_con("tok-jefe")).json()
    assert jefe["rol"] == "jefe_operaciones" and jefe["empresaNombre"] == "Sideral" and jefe["correo"].startswith("jefe@")
    pasajera = cliente.get("/api/v1/yo", headers=_con("tok-pasajera")).json()
    assert pasajera["rol"] == "pasajero" and pasajera["empresaId"] is None and pasajera["empresaNombre"] is None


def test_usuario_inactivo_en_yo_responde_401(cliente: TestClient, repos: Repositorios) -> None:
    repos.usuarios.perfiles[dobles.USUARIO_JEFE]["activo"] = False
    assert cliente.get("/api/v1/yo", headers=_con("tok-jefe")).status_code == 401


def test_endpoint_de_gestion_con_rol_equivocado_403(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/admin/usuarios", headers=_con("tok-jefe")).status_code == 403


# ---------- AutenticacionSupabase (httpx simulado) ----------


def _autenticacion(manejador, usuarios=None, reloj=None) -> AutenticacionSupabase:
    cliente = httpx.AsyncClient(transport=httpx.MockTransport(manejador))
    return AutenticacionSupabase(
        "https://proyecto.supabase.example/", "anon-falsa", usuarios or dobles.UsuariosEnMemoria(), cliente,
        monotonico=reloj or (lambda: 0.0),
    )


async def test_token_valido_da_identidad_y_se_cachea() -> None:
    llamadas: list[httpx.Request] = []

    def manejador(req: httpx.Request) -> httpx.Response:
        llamadas.append(req)
        return httpx.Response(200, json={"id": str(dobles.USUARIO_JEFE)})

    auth = _autenticacion(manejador)
    identidad = await auth.verificar_token("jwt-x")
    assert (identidad.rol.value, identidad.empresa_id) == ("jefe_operaciones", str(dobles.EMPRESA_SIDERAL))
    await auth.verificar_token("jwt-x")
    assert len(llamadas) == 1  # segunda llamada desde caché
    assert llamadas[0].url.path == "/auth/v1/user" and llamadas[0].headers["apikey"] == "anon-falsa"


async def test_token_rechazado_por_supabase_es_401() -> None:
    auth = _autenticacion(lambda req: httpx.Response(401, json={"msg": "invalid"}))
    with pytest.raises(ErrorNoAutenticado):
        await auth.verificar_token("jwt-malo")


async def test_usuario_sin_perfil_o_inactivo_es_401() -> None:
    usuarios = dobles.UsuariosEnMemoria()
    usuarios.perfiles[dobles.USUARIO_JEFE]["activo"] = False
    auth = _autenticacion(lambda req: httpx.Response(200, json={"id": str(dobles.USUARIO_JEFE)}), usuarios)
    with pytest.raises(ErrorNoAutenticado):
        await auth.verificar_token("a")
    sin_perfil = _autenticacion(lambda req: httpx.Response(200, json={"id": str(uuid4())}))
    with pytest.raises(ErrorNoAutenticado):
        await sin_perfil.verificar_token("b")


async def test_supabase_caido_es_503_y_el_cache_expira() -> None:
    def caido(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red")

    with pytest.raises(ErrorServicioExterno):
        await _autenticacion(caido).verificar_token("a")
    ahora = [0.0]
    conteo = [0]

    def manejador(req: httpx.Request) -> httpx.Response:
        conteo[0] += 1
        return httpx.Response(200, json={"id": str(dobles.USUARIO_ADMIN)})

    auth = _autenticacion(manejador, reloj=lambda: ahora[0])
    await auth.verificar_token("a")
    ahora[0] = 31.0
    await auth.verificar_token("a")
    assert conteo[0] == 2


# ---------- WebSocket ----------


def test_ws_ruta_entrega_foto_inicial_y_difunde_posiciones(repos: Repositorios, base: RelojFijo) -> None:
    # sin simulador (modo_demo=False) y con TestClient como contexto: todo corre en un único bucle de eventos
    contenedor = construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(base))
    cab = {"X-Clave-Fuente": dobles.CLAVE_SIDERAL}
    with TestClient(crear_app(contenedor)) as cliente, cliente.websocket_connect(f"/ws/rutas/{dobles.RUTA_ENEA}") as ws:
        inicial = ws.receive_json()
        assert inicial["tipo"] == "posiciones" and inicial["rutaId"] == str(dobles.RUTA_ENEA) and inicial["busetas"] == []
        cuerpo = {"posiciones": [{
            "numeroLateral": "1544", "lat": 5.07, "lng": -75.51, "velocidadKmh": 30, "rumbo": 10,
            "reportadaEn": LUNES_MEDIODIA.isoformat(),
        }]}
        assert cliente.post("/api/v1/ingesta/posiciones", json=cuerpo, headers=cab).status_code == 202
        mensaje = ws.receive_json()
        assert mensaje["tipo"] == "posiciones" and mensaje["busetas"][0]["numeroLateral"] == "1544"
        assert mensaje["busetas"][0]["estado"] == "activa" and "calculadoEn" in mensaje
        ws.send_text("ping")
        assert ws.receive_text() == "pong"
    assert contenedor.gestor_ws.total() == 0  # conexión limpiada al cerrar


async def test_cliente_roto_se_limpia_y_no_frena_la_difusion() -> None:
    from adaptadores_externos.websocket_posiciones import GestorConexiones

    class Roto:
        async def send_json(self, _):
            raise RuntimeError("socket cerrado")

    class Bueno:
        recibidos: list = []

        async def send_json(self, mensaje):
            self.recibidos.append(mensaje)

    ruta, gestor, bueno = uuid4(), GestorConexiones(), Bueno()
    gestor.conectar(ruta, Roto())
    gestor.conectar(ruta, bueno)
    await gestor.difundir(ruta, {"tipo": "posiciones"})
    assert bueno.recibidos == [{"tipo": "posiciones"}] and gestor.total() == 1


async def test_difusor_agrupa_posiciones_del_mismo_ciclo() -> None:
    from adaptadores_externos.websocket_posiciones import DifusorPosiciones, GestorConexiones

    ruta, gestor, enviados = uuid4(), GestorConexiones(), []

    class Cliente:
        async def send_json(self, mensaje):
            enviados.append(mensaje)

    gestor.conectar(ruta, Cliente())

    async def armar(r):
        return {"tipo": "posiciones", "rutaId": str(r)}

    difusor = DifusorPosiciones(gestor, armar, retraso_s=0.01)
    for _ in range(5):
        await difusor.al_aceptar_posicion({"ruta_id": ruta})
    await difusor.al_aceptar_posicion({"ruta_id": None})  # sin ruta: se ignora
    await asyncio.sleep(0.1)
    assert len(enviados) == 1


def test_yo_incluye_nombre_apellido_y_celular(cliente: TestClient, repos: Repositorios) -> None:
    demo = cliente.get("/api/v1/yo", headers=_con("tok-pasajera")).json()
    assert (demo["nombre"], demo["apellido"], demo["celular"]) == (None, None, None)  # cuenta demo
    repos.usuarios.perfiles[dobles.USUARIO_PASAJERA].update(nombre="Ana", apellido="Pérez", celular="3001234567")
    completo = cliente.get("/api/v1/yo", headers=_con("tok-pasajera")).json()
    assert (completo["nombre"], completo["apellido"], completo["celular"]) == ("Ana", "Pérez", "3001234567")
    assert completo["rol"] == "pasajero" and completo["empresaId"] is None
