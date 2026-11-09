"""El simulador toma rutas, trazados y busetas creados con el servidor ya arrancado (sin reiniciar). Sin BD: dobles en memoria."""

from __future__ import annotations

import random
from datetime import time, timedelta
from uuid import uuid4

import pytest

from composicion import Contenedor, Repositorios, construir_contenedor
from herramientas.simulador_gps import REFRESCO_S
from nucleo.configuracion import Configuracion
from nucleo.reloj import RelojSimulado
from pruebas import dobles
from pruebas.dobles import LUNES_MEDIODIA, RelojFijo

RUTA_NUEVA = uuid4()
SERVICIO_NUEVO = uuid4()
# ruta creada con POST /rutas/desde-puntos: otra zona de la ciudad, lejos del cuadrado de La Enea de los dobles
TRAZADO_NUEVO = [[-75.455, 5.100], [-75.435, 5.100], [-75.435, 5.120], [-75.455, 5.120], [-75.455, 5.100]]  # [lng, lat]
OTRO_TRAZADO = [[-75.600, 5.020], [-75.580, 5.020], [-75.580, 5.040], [-75.600, 5.040], [-75.600, 5.020]]
BUSETA_NUEVA = uuid4()


@pytest.fixture
def repos() -> Repositorios:
    return dobles.repositorios_en_memoria()


@pytest.fixture
def base() -> RelojFijo:
    return RelojFijo()


@pytest.fixture
async def simulador(repos: Repositorios, base: RelojFijo):
    cont: Contenedor = construir_contenedor(Configuracion(_env_file=None, modo_demo=True), repos, RelojSimulado(base))
    sim = cont.servicios.simulador
    sim._azar = random.Random(1)
    await sim.cargar()
    return sim


async def _ciclos(sim, base: RelojFijo, cuantos: int, inicio: int = 0) -> None:
    for k in range(cuantos):
        base.fijar(LUNES_MEDIODIA + timedelta(seconds=3 * (inicio + k)))
        await sim.ciclo()


def _en(lat_lng: tuple[float, float], trazado: list[list[float]]) -> bool:
    lat, lng = lat_lng
    lngs, lats = [p[0] for p in trazado], [p[1] for p in trazado]
    return min(lats) - 1e-4 <= lat <= max(lats) + 1e-4 and min(lngs) - 1e-4 <= lng <= max(lngs) + 1e-4


def _crear_ruta_y_buseta_nuevas(repos: Repositorios) -> None:
    """Lo que ocurre en la BD: la Secretaría crea la ruta y la asigna a Sideral, el jefe crea la buseta y publica un turno."""
    repos.simulacion.trazados_nuevos[RUTA_NUEVA] = TRAZADO_NUEVO
    repos.seguimiento.rutas_de_servicios[SERVICIO_NUEVO] = RUTA_NUEVA
    repos.simulacion.busetas_nuevas.append(
        {"buseta_id": BUSETA_NUEVA, "numero_lateral": "9001", "empresa_id": dobles.EMPRESA_SIDERAL, "empresa_nombre": "Sideral"}
    )
    repos.seguimiento.busetas[(dobles.EMPRESA_SIDERAL, "9001")] = {"id": BUSETA_NUEVA, "numero_lateral": "9001"}
    repos.seguimiento.turnos[(dobles.EMPRESA_SIDERAL, "9001")] = (time(5, 0), time(23, 0), SERVICIO_NUEVO)


async def test_antes_del_cambio_una_buseta_creada_con_el_servidor_arrancado_no_aparecia(simulador, repos, base) -> None:
    """Documenta la limitación que había: sin releer, la buseta nueva no entra a la simulación."""
    _crear_ruta_y_buseta_nuevas(repos)
    await _ciclos(simulador, base, 2)  # menos ciclos que el refresco
    assert BUSETA_NUEVA not in repos.seguimiento.guardadas
    assert "9001" not in [b["numero_lateral"] for b in simulador.estado()["busetas"]]


async def test_una_buseta_nueva_aparece_y_se_mueve_por_el_trazado_de_la_ruta_nueva(simulador, repos, base) -> None:
    _crear_ruta_y_buseta_nuevas(repos)
    cada = max(1, round(REFRESCO_S / simulador._intervalo))
    await _ciclos(simulador, base, cada + 3)
    guardada = repos.seguimiento.guardadas[BUSETA_NUEVA]
    assert guardada["servicio_id"] == SERVICIO_NUEVO  # el turno publicado la deduce en la ruta nueva
    assert _en((guardada["lat"], guardada["lng"]), TRAZADO_NUEVO)
    assert "9001" in [b["numero_lateral"] for b in simulador.estado()["busetas"]]  # el panel de demo también la ve
    antes = (guardada["lat"], guardada["lng"])
    await _ciclos(simulador, base, 1, inicio=cada + 3)
    despues = repos.seguimiento.guardadas[BUSETA_NUEVA]
    assert (despues["lat"], despues["lng"]) != antes and _en((despues["lat"], despues["lng"]), TRAZADO_NUEVO)  # se mueve


async def test_la_posicion_de_la_buseta_nueva_llega_con_la_ruta_para_el_websocket(simulador, repos, base, ) -> None:
    from nucleo.emisor_eventos import POSICION_ACEPTADA

    _crear_ruta_y_buseta_nuevas(repos)
    recibidos: list[dict] = []

    async def escuchar(carga: dict) -> None:
        recibidos.append(carga)

    # el simulador usa el mismo caso de uso que el GPS real: el evento lleva la ruta de la buseta (la difusión por WS depende de eso)
    contenedor_emisor = simulador._registrar._emisor
    contenedor_emisor.suscribir(POSICION_ACEPTADA, escuchar)
    cada = max(1, round(REFRESCO_S / simulador._intervalo))
    await _ciclos(simulador, base, cada + 2)
    de_la_nueva = [c for c in recibidos if c["numero_lateral"] == "9001"]
    assert de_la_nueva and all(c["ruta_id"] == RUTA_NUEVA and c["servicio_id"] == SERVICIO_NUEVO for c in de_la_nueva)


async def test_una_buseta_ya_conocida_con_un_turno_en_la_ruta_nueva_se_mueve_sin_esperar_al_refresco(simulador, repos, base) -> None:
    repos.simulacion.trazados_nuevos[RUTA_NUEVA] = TRAZADO_NUEVO
    repos.seguimiento.rutas_de_servicios[SERVICIO_NUEVO] = RUTA_NUEVA
    await _ciclos(simulador, base, 1)
    assert repos.seguimiento.guardadas[dobles.BUSETA_1544]["servicio_id"] == dobles.SERVICIO_SIDERAL_ENEA
    repos.seguimiento.turnos[(dobles.EMPRESA_SIDERAL, "1544")] = (time(5, 0), time(23, 0), SERVICIO_NUEVO)  # el jefe publicó
    await _ciclos(simulador, base, 1, inicio=1)
    g = repos.seguimiento.guardadas[dobles.BUSETA_1544]
    assert g["servicio_id"] == SERVICIO_NUEVO and _en((g["lat"], g["lng"]), TRAZADO_NUEVO)


async def test_las_busetas_conocidas_conservan_su_estado_al_releer(simulador, repos, base) -> None:
    await simulador.aplicar({"tipo": "perder_senal", "numero_lateral": "1544"})
    avance = simulador._busetas[(dobles.EMPRESA_SIDERAL, "1544")].avance_m
    objeto = simulador._busetas[(dobles.EMPRESA_SIDERAL, "1544")]
    await simulador._refrescar()
    assert simulador._busetas[(dobles.EMPRESA_SIDERAL, "1544")] is objeto  # mismo objeto: no se pierde nada
    assert objeto.emitiendo is False and objeto.avance_m == avance


async def test_una_buseta_que_deja_de_estar_activa_deja_de_moverse(simulador, repos, base) -> None:
    cada = max(1, round(REFRESCO_S / simulador._intervalo))
    await _ciclos(simulador, base, 1)
    ultima = repos.seguimiento.guardadas[dobles.BUSETA_1544]["reportada_en"]
    repos.simulacion.inactivas.add("1544")  # el jefe la dio de baja o la pasó a fuera de servicio
    await _ciclos(simulador, base, cada + 2, inicio=1)
    assert "1544" not in [b["numero_lateral"] for b in simulador.estado()["busetas"]]
    assert repos.seguimiento.guardadas[dobles.BUSETA_1544]["reportada_en"] < LUNES_MEDIODIA + timedelta(seconds=3 * (cada + 2))
    assert repos.seguimiento.guardadas[dobles.BUSETA_1544]["reportada_en"] >= ultima  # solo emitió antes del refresco


async def test_un_trazado_editado_se_vuelve_a_leer_en_el_refresco(simulador, repos, base) -> None:
    repos.simulacion.trazados_nuevos[RUTA_NUEVA] = TRAZADO_NUEVO
    repos.seguimiento.rutas_de_servicios[SERVICIO_NUEVO] = RUTA_NUEVA
    repos.seguimiento.turnos[(dobles.EMPRESA_SIDERAL, "1544")] = (time(5, 0), time(23, 0), SERVICIO_NUEVO)
    cada = max(1, round(REFRESCO_S / simulador._intervalo))
    await _ciclos(simulador, base, 1)
    g = repos.seguimiento.guardadas[dobles.BUSETA_1544]
    assert _en((g["lat"], g["lng"]), TRAZADO_NUEVO)
    lecturas = repos.simulacion.lecturas_de_trazado
    repos.simulacion.trazados_nuevos[RUTA_NUEVA] = OTRO_TRAZADO  # PUT /rutas/{id} con otros paraderos
    await _ciclos(simulador, base, cada + 1, inicio=1)
    g = repos.seguimiento.guardadas[dobles.BUSETA_1544]
    assert repos.simulacion.lecturas_de_trazado > lecturas and _en((g["lat"], g["lng"]), OTRO_TRAZADO)


async def test_si_falla_la_relectura_el_simulador_sigue_con_lo_que_conoce(simulador, repos, base) -> None:
    cada = max(1, round(REFRESCO_S / simulador._intervalo))
    original = repos.simulacion.busetas_activas
    llamadas = {"n": 0}

    async def inestable():
        llamadas["n"] += 1
        raise RuntimeError("BD caída")

    repos.simulacion.busetas_activas = inestable
    await _ciclos(simulador, base, cada + 2)
    assert llamadas["n"] >= 1 and dobles.BUSETA_1544 in repos.seguimiento.guardadas  # siguió emitiendo
    repos.simulacion.busetas_activas = original


async def test_el_refresco_es_cada_10_segundos_de_simulacion(simulador) -> None:
    assert REFRESCO_S == 10.0
    simulador._intervalo = 3
    assert max(1, round(REFRESCO_S / simulador._intervalo)) == 3
    simulador._intervalo = 20
    assert max(1, round(REFRESCO_S / simulador._intervalo)) == 1  # con ciclos largos se relee en cada ciclo
