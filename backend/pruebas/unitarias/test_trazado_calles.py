"""Trazado por calles reales (OSRM) en POST /rutas/desde-puntos. Sin red: dobles y httpx.MockTransport; pytest nunca llama a OSRM."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from composicion import construir_contenedor
from herramientas.simulador_gps import Circuito, haversine_m
from modulos.red.aplicacion.trazado_calles import ConstructorDeTrazado
from modulos.red.dominio.trazado import unir_segmentos
from modulos.red.infraestructura.enrutador_osrm import PAUSA_ENTRE_LLAMADAS_S, TIMEOUT_S, USER_AGENT, EnrutadorOsrm
from nucleo.configuracion import Configuracion
from nucleo.reloj import RelojSimulado
from pruebas import dobles
from pruebas.dobles import RelojFijo
from servidor import crear_app

BARRIOS = {b["nombre"]: b for b in json.loads(
    (Path(__file__).resolve().parents[2] / "supabase" / "semillas" / "barrios.json").read_text(encoding="utf-8"))["barrios"]}
A = (BARRIOS["Fátima"]["lat"], BARRIOS["Fátima"]["lng"])
D = (BARRIOS["Chipre"]["lat"], BARRIOS["Chipre"]["lng"])
B = (A[0] + (D[0] - A[0]) * 0.35 + 0.0008, A[1] + (D[1] - A[1]) * 0.35 - 0.0008)
C = (A[0] + (D[0] - A[0]) * 0.7 + 0.0008, A[1] + (D[1] - A[1]) * 0.7 - 0.0008)
PARADAS = [A, B, C, D]


def ajustado(p: tuple[float, float]) -> tuple[float, float]:
    """OSRM ajusta el punto a la calle más cercana: aquí, ~3 m al norte (siempre el mismo para el mismo punto)."""
    return (p[0] + 0.00003, p[1])


class EnrutadorFalso:
    """Geometría con vértices intermedios que se separa de la recta (como una calle); `falla` = pares (i, j) sin ruta."""

    def __init__(self, falla: set[tuple[int, int]] | None = None, reversa: bool = False) -> None:
        self.llamadas: list[tuple[tuple[float, float], tuple[float, float]]] = []
        self.falla = falla or set()
        self.reversa = reversa

    async def trazar(self, origen, destino):
        self.llamadas.append((origen, destino))
        i, j = PARADAS.index(origen) + 1, PARADAS.index(destino) + 1
        if (i, j) in self.falla:
            return None
        lat = (origen[0] + destino[0]) / 2 + 0.002 * (1 if i < j or self.reversa else -1)
        lng = (origen[1] + destino[1]) / 2
        return [ajustado(origen), (lat, lng), (lat + 0.0005, lng + 0.0005), ajustado(destino)]


def _recta(a, b) -> float:
    return haversine_m(*a, *b)


# ---------- unión de segmentos ----------


def test_unir_segmentos_no_duplica_el_punto_de_union_y_cierra() -> None:
    s1 = [(5.0, -75.0), (5.1, -75.1)]
    s2 = [(5.1, -75.1), (5.2, -75.2)]
    s3 = [(5.2, -75.2), (5.05, -75.0)]  # termina cerca, no exactamente en el primer vértice
    linea = unir_segmentos([s1, s2, s3])
    assert linea == [(5.0, -75.0), (5.1, -75.1), (5.2, -75.2), (5.05, -75.0), (5.0, -75.0)]
    assert unir_segmentos([[(5.0, -75.0), (5.1, -75.1)], [(5.1, -75.1), (5.0, -75.0)]]) == [(5.0, -75.0), (5.1, -75.1), (5.0, -75.0)]


# ---------- constructor del trazado ----------


async def test_pide_cada_par_consecutivo_incluido_el_cierre_en_orden() -> None:
    enrutador = EnrutadorFalso()
    r = await ConstructorDeTrazado(enrutador).construir(PARADAS)
    assert enrutador.llamadas == [(A, B), (B, C), (C, D), (D, A)]  # 4 llamadas secuenciales, la última cierra el circuito
    assert r.tramos_sin_ruta == []
    assert r.coordenadas[0] == ajustado(A) and r.coordenadas[-1] == r.coordenadas[0]  # circuito cerrado
    assert len(r.coordenadas) == 4 * 3 + 1  # 4 segmentos de 4 vértices, sin repetir las 4 uniones, +1 de cierre
    assert len(set(r.coordenadas)) == len(r.coordenadas) - 1  # solo se repite el primer vértice al cerrar


async def test_el_trazado_real_es_mas_largo_que_la_recta() -> None:
    real = await ConstructorDeTrazado(EnrutadorFalso()).construir(PARADAS)
    recta = await ConstructorDeTrazado(None).construir(PARADAS)
    assert Circuito(real.coordenadas).longitud > Circuito(recta.coordenadas).longitud > 0
    assert len(real.coordenadas) > len(recta.coordenadas)


async def test_un_tramo_sin_ruta_usa_recta_solo_en_ese_tramo() -> None:
    r = await ConstructorDeTrazado(EnrutadorFalso(falla={(2, 3)})).construir(PARADAS)
    assert r.tramos_sin_ruta == [(2, 3)]
    assert B in r.coordenadas and C in r.coordenadas  # la recta B→C usa los puntos exactos tocados
    indice = r.coordenadas.index(B)
    assert r.coordenadas[indice + 1] == C  # recta pura entre B y C, sin vértices intermedios
    assert len(r.coordenadas) > 2 * 4  # los demás tramos siguen siendo calle real


async def test_tres_fallos_seguidos_cortan_las_llamadas() -> None:
    enrutador = EnrutadorFalso(falla={(1, 2), (2, 3), (3, 4), (4, 1)})
    r = await ConstructorDeTrazado(enrutador, fallos_seguidos_max=3).construir(PARADAS)
    assert len(enrutador.llamadas) == 3 and r.tramos_sin_ruta == [(1, 2), (2, 3), (3, 4), (4, 1)]
    assert r.coordenadas == [A, B, C, D, A]  # todo en recta, la creación no falla


async def test_un_exito_reinicia_la_cuenta_de_fallos() -> None:
    enrutador = EnrutadorFalso(falla={(1, 2), (2, 3)})
    r = await ConstructorDeTrazado(enrutador, fallos_seguidos_max=3).construir(PARADAS)
    assert len(enrutador.llamadas) == 4 and r.tramos_sin_ruta == [(1, 2), (2, 3)]


async def test_el_presupuesto_de_tiempo_corta_las_llamadas() -> None:
    reloj = iter([0.0, 1.0, 100.0, 200.0, 300.0, 400.0])
    enrutador = EnrutadorFalso()
    r = await ConstructorDeTrazado(enrutador, monotonico=lambda: next(reloj), presupuesto_s=25).construir(PARADAS)
    assert len(enrutador.llamadas) == 1 and r.tramos_sin_ruta == [(2, 3), (3, 4), (4, 1)]


async def test_sin_enrutador_todo_va_en_recta_y_se_reporta() -> None:
    r = await ConstructorDeTrazado(None).construir(PARADAS)
    assert r.coordenadas == [A, B, C, D, A] and r.tramos_sin_ruta == [(1, 2), (2, 3), (3, 4), (4, 1)]


async def test_los_tramos_en_recta_quedan_en_los_registros_sin_coordenadas(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        await ConstructorDeTrazado(EnrutadorFalso(falla={(2, 3)})).construir(PARADAS)
    assert "Tramo 2→3 sin ruta real, se usó línea recta" in caplog.text
    assert str(A[0]) not in caplog.text and str(A[1]) not in caplog.text


# ---------- adaptador OSRM (httpx simulado) ----------


def _osrm(manejador, **kwargs) -> EnrutadorOsrm:
    return EnrutadorOsrm(httpx.AsyncClient(transport=httpx.MockTransport(manejador)), "https://osrm.example/", **kwargs)


def _respuesta(coordenadas: list[list[float]], codigo: str = "Ok") -> httpx.Response:
    return httpx.Response(200, json={"code": codigo, "routes": [{"geometry": {"type": "LineString", "coordinates": coordenadas}}]})


async def test_el_adaptador_arma_la_peticion_y_convierte_lng_lat_a_lat_lng() -> None:
    vistas: list[httpx.Request] = []

    def manejador(req: httpx.Request) -> httpx.Response:
        vistas.append(req)
        return _respuesta([[-75.497, 5.0525], [-75.5, 5.055], [-75.5257, 5.0766]])

    linea = await _osrm(manejador).trazar(A, D)
    assert linea == [(5.0525, -75.497), (5.055, -75.5), (5.0766, -75.5257)]
    [req] = vistas
    assert req.url.path == f"/route/v1/driving/{A[1]:.6f},{A[0]:.6f};{D[1]:.6f},{D[0]:.6f}"
    assert dict(req.url.params) == {"overview": "full", "geometries": "geojson"}
    assert req.headers["user-agent"] == USER_AGENT and "BusetasApp" in USER_AGENT
    assert req.extensions["timeout"]["read"] == TIMEOUT_S == 5.0


@pytest.mark.parametrize(
    "respuesta",
    [
        httpx.Response(200, json={"code": "NoRoute", "routes": []}),
        httpx.Response(500, text="error"),
        httpx.Response(429, text="demasiadas peticiones"),
        httpx.Response(200, text="no es json"),
        httpx.Response(200, json={"code": "Ok", "routes": []}),
        httpx.Response(200, json={"code": "Ok", "routes": [{"geometry": {"coordinates": [[-75.5, 5.05]]}}]}),  # 1 solo vértice
        httpx.Response(200, json={"code": "Ok", "routes": [{"geometry": {"coordinates": [["x", "y"], [1, 2]]}}]}),
        httpx.Response(200, json={"code": "Ok", "routes": [{"geometry": {"coordinates": [[-75.5, 5.05], [-75.5, 95.0]]}}]}),
    ],
)
async def test_cualquier_respuesta_mala_devuelve_none(respuesta: httpx.Response) -> None:
    assert await _osrm(lambda req: respuesta).trazar(A, D) is None


@pytest.mark.parametrize("error", [httpx.ReadTimeout("lento"), httpx.ConnectError("sin red")])
async def test_timeout_y_red_caida_devuelven_none(error: Exception) -> None:
    def manejador(req: httpx.Request) -> httpx.Response:
        raise error

    assert await _osrm(manejador).trazar(A, D) is None


async def test_pausa_entre_llamadas_para_no_saturar_el_servidor_demo() -> None:
    reloj = [0.0]
    dormidas: list[float] = []

    async def dormir(segundos: float) -> None:
        dormidas.append(segundos)
        reloj[0] += segundos

    enrutador = _osrm(lambda req: _respuesta([[-75.5, 5.05], [-75.6, 5.06]]), dormir=dormir, monotonico=lambda: reloj[0])
    await enrutador.trazar(A, D)  # la primera no espera
    reloj[0] += 0.05
    await enrutador.trazar(D, A)  # solo pasaron 0,05 s: espera lo que falta
    reloj[0] += 5
    await enrutador.trazar(A, D)  # pasó de sobra: no espera
    assert PAUSA_ENTRE_LLAMADAS_S == 0.2 and len(dormidas) == 1 and dormidas[0] == pytest.approx(0.15)


async def test_el_adaptador_no_registra_coordenadas(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        await _osrm(lambda req: httpx.Response(200, json={"code": "NoRoute"})).trazar(A, D)
    assert str(A[0]) not in caplog.text and str(D[1]) not in caplog.text and "NoRoute" in caplog.text


# ---------- endpoint con el trazado real ----------


def _avisos_de_trazado(ruta: dict) -> list[dict]:
    """Los avisos de tramo en recta (el detalle también trae los avisos vigentes de la ruta, que aquí no interesan)."""
    return [a for a in ruta["avisos"] if a["titulo"] == "Trazado parcialmente en línea recta"]


SEC = {"Authorization": "Bearer tok-secretaria"}


def _cliente(enrutador) -> tuple[TestClient, object]:
    repos = dobles.repositorios_en_memoria()
    repos.enrutador = enrutador
    _con_detalle(repos)
    cont = construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(RelojFijo()))
    return TestClient(crear_app(cont), raise_server_exceptions=False), repos


def _cuerpo() -> dict:
    return {
        "nombre": "Fátima a Chipre", "servicios": [{"empresaId": str(dobles.EMPRESA_SIDERAL)}],
        "puntos": [{"lat": a, "lng": b, **({"nombre": n} if n else {})} for (a, b), n in zip(PARADAS, ["Fátima", None, None, "Chipre"], strict=True)],
    }


def _con_detalle(repos) -> None:
    """GET /rutas/{id} sobre lo guardado (trazado real incluido)."""
    import re
    from uuid import uuid4

    gestion, original = repos.gestion_red, repos.rutas.obtener_detalle

    async def detalle(ruta_id):
        creada = gestion.creadas.get(ruta_id)
        if creada is None:
            return await original(ruta_id)
        coords = [tuple(map(float, par.split())) for par in re.findall(r"(-?\d+\.\d+ -?\d+\.\d+)", creada["wkt"])]
        return {
            "id": ruta_id, "nombre": creada["nombre"], "tipo_recorrido": "circular", "es_variante": False, "distancia_m": None,
            "servicios": [], "descripcion": None, "ruta_principal_id": None, "version": 1,
            "longitud_m": Circuito([(lat, lng) for lng, lat in coords]).longitud,
            "trazado": {"type": "LineString", "coordinates": [list(c) for c in coords]},
            "paraderos": [{"orden": i + 1, "paradero_id": pid, "nombre": gestion.paraderos[pid]["nombre"],
                           "lat": gestion.paraderos[pid]["lat"], "lng": gestion.paraderos[pid]["lng"]}
                          for i, pid in enumerate(creada["paradero_ids"])],
        } | {"_id": uuid4().hex}

    repos.rutas.obtener_detalle = detalle


def _avances_secuenciales(vertices: list[tuple[float, float]], paradas: list[tuple[float, float]]) -> list[int]:
    """Como `progresos_paraderos_ruta`: cada parada se proyecta sobre el trazado desde donde quedó la anterior."""
    indices, previo = [], 0
    for p in paradas:
        candidatos = range(previo, len(vertices) - 1)  # el último vértice repite al primero (cierre)
        elegido = min(candidatos, key=lambda k: haversine_m(*p, *vertices[k]))  # empate → el primero (la ida)
        assert haversine_m(*p, *vertices[elegido]) < 60, "la parada debe quedar sobre el trazado"
        indices.append(elegido)
        previo = elegido
    return indices


@pytest.mark.parametrize("reversa", [False, True])  # True: la vuelta repite el camino de la ida (misma calle)
def test_endpoint_sigue_la_calle_y_los_paraderos_son_los_puntos_tocados(reversa: bool) -> None:
    cliente, repos = _cliente(EnrutadorFalso(reversa=reversa))
    r = cliente.post("/api/v1/rutas/desde-puntos", json=_cuerpo(), headers=SEC)
    assert r.status_code == 201, r.text
    ruta = r.json()
    assert _avisos_de_trazado(ruta) == []  # todo con calle real: ningún aviso de línea recta
    assert [(p["lat"], p["lng"]) for p in ruta["paraderos"]] == PARADAS  # exactamente los puntos tocados, en orden
    vertices = [(lat, lng) for lng, lat in ruta["trazado"]["coordinates"]]
    assert vertices[0] == vertices[-1] and len(vertices) == 13
    recta = Circuito([*PARADAS, A]).longitud
    assert ruta["longitudM"] == pytest.approx(Circuito(vertices).longitud) and ruta["longitudM"] > recta  # la real, no la recta
    indices = _avances_secuenciales(vertices[:-1] + [vertices[0]], PARADAS)
    circuito = Circuito(vertices)
    avances = [circuito.acumuladas[i] for i in indices]
    assert avances[0] == 0 and avances == sorted(avances) and len(set(avances)) == 4 and avances[-1] < circuito.longitud


def test_endpoint_avisa_de_los_tramos_en_recta_y_crea_la_ruta_igual() -> None:
    cliente, repos = _cliente(EnrutadorFalso(falla={(2, 3)}))
    r = cliente.post("/api/v1/rutas/desde-puntos", json=_cuerpo(), headers=SEC)
    assert r.status_code == 201
    [aviso] = _avisos_de_trazado(r.json())
    assert aviso["cuerpo"] == "Tramo 2→3 sin ruta real, se usó línea recta." and aviso["origen"] == "aplicativo"
    assert aviso["titulo"] == "Trazado parcialmente en línea recta" and aviso["id"]
    assert len(repos.gestion_red.creadas) == 1


def test_endpoint_con_varios_tramos_en_recta_los_lista_juntos() -> None:
    cliente, _ = _cliente(EnrutadorFalso(falla={(2, 3), (4, 1)}))
    [aviso] = _avisos_de_trazado(cliente.post("/api/v1/rutas/desde-puntos", json=_cuerpo(), headers=SEC).json())
    assert aviso["cuerpo"] == "Tramos sin ruta real, se usó línea recta: 2→3, 4→1."


def test_endpoint_sin_servidor_osrm_crea_la_ruta_en_recta_y_avisa() -> None:
    cliente, repos = _cliente(None)  # OSRM_URL vacío
    r = cliente.post("/api/v1/rutas/desde-puntos", json=_cuerpo(), headers=SEC)
    assert r.status_code == 201 and len(repos.gestion_red.creadas) == 1
    assert "1→2, 2→3, 3→4, 4→1" in _avisos_de_trazado(r.json())[0]["cuerpo"]


def test_el_limite_de_puntos_es_30() -> None:
    cliente, _ = _cliente(dobles.EnrutadorRectoDoble())
    puntos = [{"lat": 5.0 + i * 0.002, "lng": -75.5 - i * 0.0005} for i in range(31)]
    r = cliente.post("/api/v1/rutas/desde-puntos", json={**_cuerpo(), "puntos": puntos}, headers=SEC)
    assert r.status_code == 400 and r.json()["error"]["codigo"] == "VALIDACION"


def test_configuracion_osrm_por_defecto_y_deshabilitable() -> None:
    assert Configuracion(_env_file=None).osrm_url == "https://router.project-osrm.org"
    assert Configuracion(_env_file=None, osrm_url="").osrm_url == ""
