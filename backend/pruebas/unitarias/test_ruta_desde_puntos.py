"""POST /rutas/desde-puntos: rutas creadas tocando puntos en el mapa. Sin BD: repositorios en memoria y semillas reales."""

from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from composicion import Repositorios, construir_contenedor
from herramientas.simulador_gps import Circuito
from modulos.red.dominio.puntos_ruta import DIRECCION_FICTICIA, SEPARACION_MINIMA_M, distancia_m
from nucleo.configuracion import Configuracion
from nucleo.reloj import RelojSimulado
from pruebas import dobles
from pruebas.dobles import RelojFijo
from servidor import crear_app

BARRIOS = {b["nombre"]: b for b in json.loads(
    (Path(__file__).resolve().parents[2] / "supabase" / "semillas" / "barrios.json").read_text(encoding="utf-8"))["barrios"]}
FATIMA, CHIPRE = BARRIOS["Fátima"], BARRIOS["Chipre"]
SEC = {"Authorization": "Bearer tok-secretaria"}
ADM = {"Authorization": "Bearer tok-admin"}
SIDERAL = str(dobles.EMPRESA_SIDERAL)
SERVI = str(dobles.EMPRESA_SERVITURISMO)


def _punto(lat: float, lng: float, nombre: str | None = None) -> dict:
    return {"lat": lat, "lng": lng, **({"nombre": nombre} if nombre else {})}


def _fatima_a_chipre() -> dict:
    # extremos reales de la capa oficial y dos puntos intermedios sobre la recta Fátima → Chipre (dentro de la caja)
    a, b = (FATIMA["lat"], FATIMA["lng"]), (CHIPRE["lat"], CHIPRE["lng"])
    intermedio = lambda t: _punto(a[0] + (b[0] - a[0]) * t + 0.0008, a[1] + (b[1] - a[1]) * t - 0.0008)  # noqa: E731
    return {
        "nombre": "Fátima a Chipre",
        "puntos": [_punto(*a, "Fátima"), intermedio(0.35), intermedio(0.7), _punto(*b, "Chipre")],
        "servicios": [{"empresaId": SIDERAL, "codigoPublico": "77"}],
    }


@pytest.fixture
def repos() -> Repositorios:
    r = dobles.repositorios_en_memoria()
    gestion = r.gestion_red
    original = r.rutas.obtener_detalle

    async def detalle(ruta_id):  # GET /rutas/{id} sobre lo que se guardó
        creada = gestion.creadas.get(ruta_id)
        if creada is None:
            return await original(ruta_id)
        coords = [tuple(map(float, par.split())) for par in re.findall(r"(-?\d+\.\d+ -?\d+\.\d+)", creada["wkt"])]
        return {
            "id": ruta_id, "nombre": creada["nombre"], "tipo_recorrido": "circular", "es_variante": False, "distancia_m": None,
            "servicios": [{"servicio_id": uuid4(), "empresa_id": s["empresa_id"], "empresa_nombre": "Sideral",
                           "codigo_publico": s.get("codigo_publico")} for s in creada["servicios"]],
            "descripcion": None, "ruta_principal_id": None, "longitud_m": Circuito.desde_geojson([list(c) for c in coords]).longitud,
            "version": creada["version"], "trazado": {"type": "LineString", "coordinates": [list(c) for c in coords]},
            "paraderos": [{"orden": i + 1, "paradero_id": pid, "nombre": gestion.paraderos[pid]["nombre"],
                           "lat": gestion.paraderos[pid]["lat"], "lng": gestion.paraderos[pid]["lng"]}
                          for i, pid in enumerate(creada["paradero_ids"])],
        }

    r.rutas.obtener_detalle = detalle
    return r


@pytest.fixture
def cliente(repos: Repositorios) -> TestClient:
    cont = construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(RelojFijo()))
    return TestClient(crear_app(cont), raise_server_exceptions=False)


# ---------- caso real: Fátima → Chipre ----------


def test_fatima_a_chipre_trazado_y_paraderos_coherentes(cliente: TestClient, repos: Repositorios) -> None:
    r = cliente.post("/api/v1/rutas/desde-puntos", json=_fatima_a_chipre(), headers=SEC)
    assert r.status_code == 201, r.text
    ruta = r.json()
    assert ruta["nombre"] == "Fátima a Chipre" and ruta["tipoRecorrido"] == "circular" and ruta["version"] == 1
    assert [s["codigoPublico"] for s in ruta["servicios"]] == ["77"]

    # paraderos en el orden tocado; los extremos con el nombre dado y los intermedios con el patrón de las semillas
    nombres = [p["nombre"] for p in ruta["paraderos"]]
    assert nombres == ["Fátima", "Paradero Fátima a Chipre 1", "Paradero Fátima a Chipre 2", "Chipre"]
    assert [p["orden"] for p in ruta["paraderos"]] == [1, 2, 3, 4]
    assert (ruta["paraderos"][0]["lat"], ruta["paraderos"][0]["lng"]) == (FATIMA["lat"], FATIMA["lng"])
    assert (ruta["paraderos"][3]["lat"], ruta["paraderos"][3]["lng"]) == (CHIPRE["lat"], CHIPRE["lng"])
    assert all(repos.gestion_red.paraderos[UUID(p["paraderoId"])]["direccion"] == DIRECCION_FICTICIA for p in ruta["paraderos"])

    # trazado: parte del primer punto, pasa por todos en orden y el circuito cierra volviendo al primero
    coords = ruta["trazado"]["coordinates"]
    assert coords[0] == pytest.approx([FATIMA["lng"], FATIMA["lat"]], abs=1e-6) and coords[-1] == coords[0]
    assert coords[-2] == pytest.approx([CHIPRE["lng"], CHIPRE["lat"]], abs=1e-6)  # el último paradero va antes del cierre
    assert len(coords) == 5  # 4 paraderos + cierre

    # longitud plausible: ida con desvíos pequeños + vuelta recta al inicio
    directa = distancia_m(FATIMA["lat"], FATIMA["lng"], CHIPRE["lat"], CHIPRE["lng"])
    assert 4000 < directa < 5000
    assert 2 * directa <= ruta["longitudM"] <= 2.2 * directa

    # avance secuencial creciente módulo la longitud (lo que usan el ETA y el planificador)
    circuito = Circuito.desde_geojson(coords)
    avances = circuito.acumuladas[:4]
    assert avances[0] == 0 and avances == sorted(avances) and len(set(avances)) == 4 and avances[-1] < circuito.longitud
    assert circuito.longitud == pytest.approx(ruta["longitudM"])


def test_todo_queda_en_la_caja_de_la_ciudad(cliente: TestClient) -> None:
    caja = {"minLat": 4.95, "maxLat": 5.20, "minLng": -75.65, "maxLng": -75.40}
    for p in _fatima_a_chipre()["puntos"]:
        assert caja["minLat"] <= p["lat"] <= caja["maxLat"] and caja["minLng"] <= p["lng"] <= caja["maxLng"]


# ---------- paraderos nuevos, reutilizados y nombres ----------


def test_nombres_automaticos_cuentan_solo_los_paraderos_nuevos_sin_nombre(cliente: TestClient, repos: Repositorios) -> None:
    cuerpo = {
        "nombre": "Ruta Prueba", "servicios": [{"empresaId": SIDERAL}],
        "puntos": [_punto(5.060, -75.500), _punto(5.062, -75.503, "Esquina X"), _punto(5.064, -75.506), _punto(5.066, -75.509)],
    }
    r = cliente.post("/api/v1/rutas/desde-puntos", json=cuerpo, headers=ADM)
    assert [p["nombre"] for p in r.json()["paraderos"]] == [
        "Paradero Ruta Prueba 1", "Esquina X", "Paradero Ruta Prueba 2", "Paradero Ruta Prueba 3"]


def test_un_punto_a_menos_de_20_m_reutiliza_el_paradero_existente(cliente: TestClient, repos: Repositorios) -> None:
    cantes = len(repos.gestion_red.paraderos)
    a = repos.gestion_red.paraderos[dobles.PARADERO_A]
    cuerpo = {
        "nombre": "Con reuso", "servicios": [{"empresaId": SIDERAL}],
        "puntos": [_punto(a["lat"] + 0.00008, a["lng"], "Nombre ignorado"), _punto(5.080, -75.520), _punto(5.085, -75.525)],
    }
    r = cliente.post("/api/v1/rutas/desde-puntos", json=cuerpo, headers=SEC)
    paraderos = r.json()["paraderos"]
    assert paraderos[0]["paraderoId"] == str(dobles.PARADERO_A) and paraderos[0]["nombre"] == "Parada A"  # nombre del existente
    assert (paraderos[0]["lat"], paraderos[0]["lng"]) == (a["lat"], a["lng"])  # el trazado pasa por el paradero real
    assert len(repos.gestion_red.paraderos) == cantes + 2  # solo se crearon los otros dos
    assert [p["nombre"] for p in paraderos[1:]] == ["Paradero Con reuso 1", "Paradero Con reuso 2"]


def test_un_paradero_no_se_repite_dentro_de_la_misma_ruta(cliente: TestClient, repos: Repositorios) -> None:
    a = repos.gestion_red.paraderos[dobles.PARADERO_A]
    cuerpo = {
        "nombre": "Vuelve a pasar", "servicios": [{"empresaId": SIDERAL}],
        "puntos": [_punto(a["lat"], a["lng"]), _punto(5.09, -75.53), _punto(5.095, -75.535), _punto(a["lat"] + 0.00014, a["lng"])],
    }
    ids = [p["paraderoId"] for p in cliente.post("/api/v1/rutas/desde-puntos", json=cuerpo, headers=SEC).json()["paraderos"]]
    assert len(set(ids)) == 4 and ids[0] == str(dobles.PARADERO_A)  # el último punto (a 15 m de A) crea uno nuevo


def test_el_radio_de_reuso_es_un_parametro_y_cero_significa_nunca(cliente: TestClient, repos: Repositorios) -> None:
    repos.parametros.valores["radio_reuso_paradero_m"] = 0
    a = repos.gestion_red.paraderos[dobles.PARADERO_A]
    cuerpo = {"nombre": "Sin reuso", "servicios": [{"empresaId": SIDERAL}],
              "puntos": [_punto(a["lat"], a["lng"]), _punto(5.09, -75.53)]}
    r = cliente.post("/api/v1/rutas/desde-puntos", json=cuerpo, headers=SEC)
    assert r.json()["paraderos"][0]["paraderoId"] != str(dobles.PARADERO_A)


# ---------- validaciones ----------


def _validar(cliente: TestClient, puntos: list[dict], **extra) -> dict:
    r = cliente.post("/api/v1/rutas/desde-puntos", json={"nombre": "Prueba", "servicios": [{"empresaId": SIDERAL}],
                                                        "puntos": puntos, **extra}, headers=SEC)
    return {"estado": r.status_code, **r.json()}


def test_menos_de_2_o_mas_de_30_puntos(cliente: TestClient, repos: Repositorios) -> None:
    assert _validar(cliente, [_punto(5.07, -75.51)])["estado"] == 400
    muchos = [_punto(5.0 + i * 0.002, -75.5) for i in range(31)]
    assert _validar(cliente, muchos)["estado"] == 400
    treinta = [_punto(5.0 + i * 0.002, -75.5 - i * 0.0005) for i in range(30)]
    assert _validar(cliente, treinta)["estado"] == 201 and len(repos.gestion_red.creadas) == 1


def test_fuera_de_la_caja_da_400_con_el_indice_del_punto(cliente: TestClient, repos: Repositorios) -> None:
    r = _validar(cliente, [_punto(5.07, -75.51), _punto(4.0, -75.51), _punto(5.08, -75.52), _punto(5.5, -76.0)])
    assert r["estado"] == 400 and r["error"]["codigo"] == "VALIDACION"
    assert r["error"]["detalles"] == [{"campo": "puntos[1]", "motivo": "fuera_de_zona"}, {"campo": "puntos[3]", "motivo": "fuera_de_zona"}]
    assert repos.gestion_red.creadas == {}  # no se creó nada


def test_coordenadas_invalidas(cliente: TestClient) -> None:
    r = _validar(cliente, [_punto(5.07, -75.51), _punto(95.0, -75.51)])
    assert r["estado"] == 400 and r["error"]["detalles"] == [{"campo": "puntos[1]", "motivo": "coordenadas_invalidas"}]
    assert _validar(cliente, [{"lat": "norte", "lng": -75.5}, _punto(5.07, -75.51)])["estado"] == 400
    assert _validar(cliente, [{"lng": -75.5}, _punto(5.07, -75.51)])["estado"] == 400


def test_puntos_duplicados_consecutivos_se_rechazan(cliente: TestClient) -> None:
    cerca = _punto(5.07 + (SEPARACION_MINIMA_M - 2) / 111_000, -75.51)  # a menos de 10 m
    r = _validar(cliente, [_punto(5.07, -75.51), cerca, _punto(5.09, -75.53)])
    assert r["estado"] == 400 and r["error"]["detalles"] == [{"campo": "puntos[1]", "motivo": "duplicado_consecutivo"}]
    lejos = _punto(5.07 + (SEPARACION_MINIMA_M + 5) / 111_000, -75.51)  # a más de 10 m: válido
    assert _validar(cliente, [_punto(5.07, -75.51), lejos, _punto(5.09, -75.53)])["estado"] == 201


def test_el_ultimo_punto_no_puede_ser_el_primero_porque_el_circuito_cierra_solo(cliente: TestClient) -> None:
    r = _validar(cliente, [_punto(5.07, -75.51), _punto(5.08, -75.52), _punto(5.07, -75.51)])
    assert r["estado"] == 400 and r["error"]["detalles"] == [{"campo": "puntos[2]", "motivo": "ultimo_igual_al_primero"}]


def test_nombre_de_ruta_repetido_409_sin_tildes_ni_mayusculas(cliente: TestClient, repos: Repositorios) -> None:
    puntos = [_punto(5.07, -75.51), _punto(5.08, -75.52)]
    assert _validar(cliente, puntos, nombre="Ruta Única")["estado"] == 201
    r = _validar(cliente, puntos, nombre="  ruta   UNICA ")
    assert r["estado"] == 409 and r["error"]["codigo"] == "CONFLICTO_NEGOCIO"
    assert _validar(cliente, puntos, nombre="La Enea")["estado"] == 409  # ya existe una ruta con ese nombre
    assert _validar(cliente, puntos, nombre="x")["estado"] == 400
    assert len(repos.gestion_red.creadas) == 1


def test_empresas(cliente: TestClient) -> None:
    puntos = [_punto(5.07, -75.51), _punto(5.08, -75.52)]
    assert _validar(cliente, puntos, servicios=[{"empresaId": str(uuid4())}])["estado"] == 404
    assert _validar(cliente, puntos, servicios=[])["estado"] == 400
    repetida = [{"empresaId": SIDERAL}, {"empresaId": SIDERAL}]
    assert _validar(cliente, puntos, servicios=repetida)["estado"] == 400
    dos = [{"empresaId": SIDERAL}, {"empresaId": SERVI}]
    assert _validar(cliente, puntos, servicios=dos)["estado"] == 409  # compartida sin confirmar
    assert _validar(cliente, puntos, servicios=dos, confirmarCompartida=True)["estado"] == 201


def test_solo_secretaria_y_administrador(cliente: TestClient, repos: Repositorios) -> None:
    cuerpo = _fatima_a_chipre()
    assert cliente.post("/api/v1/rutas/desde-puntos", json=cuerpo).status_code == 401
    assert cliente.post("/api/v1/rutas/desde-puntos", json=cuerpo, headers={"Authorization": "Bearer tok-jefe"}).status_code == 403
    assert cliente.post("/api/v1/rutas/desde-puntos", json=cuerpo, headers={"Authorization": "Bearer tok-pasajera"}).status_code == 403
    assert repos.gestion_red.creadas == {}
    assert cliente.post("/api/v1/rutas/desde-puntos", json=cuerpo, headers=SEC).status_code == 201


def test_post_rutas_con_paraderoids_sigue_igual(cliente: TestClient) -> None:
    cuerpo = {"nombre": "Nueva ruta", "paraderoIds": [str(dobles.PARADERO_A), str(dobles.PARADERO_B)],
              "servicios": [{"empresaId": SIDERAL}]}
    assert cliente.post("/api/v1/rutas", json=cuerpo, headers=SEC).status_code == 201


def test_la_creacion_usa_una_sola_transaccion() -> None:
    fuente = (Path(__file__).resolve().parents[2] / "src/modulos/red/infraestructura/repositorio_gestion_sql.py").read_text(encoding="utf-8")
    cuerpo = fuente[fuente.index("async def crear_ruta_con_paraderos"):fuente.index("async def editar_ruta")]
    assert cuerpo.count("self._pool.connection()") == 1  # paraderos, ruta, trazado, secuencia y servicios en la misma conexión
