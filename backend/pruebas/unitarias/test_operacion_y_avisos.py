"""B4: ValidadorRodamiento, PoliticaDeAvisos, versión optimista, edición de horarios, busetas, conductores, rodamientos
y avisos por rol (con repositorios en memoria)."""

from __future__ import annotations

from datetime import time
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from composicion import Repositorios, construir_contenedor
from modulos.avisos.dominio.politica import definir_aviso, puede_retirar
from modulos.horarios.dominio.validacion import FranjaNueva, HorarioNuevo, validar_frecuencias, validar_horarios
from modulos.operacion.dominio.validador_rodamiento import (
    TurnoDato,
    detectar_reemplazos,
    detectar_solapamientos,
)
from nucleo.autorizacion import Identidad, Rol
from nucleo.configuracion import Configuracion
from nucleo.errores import ErrorConflictoVersion, ErrorNoAutorizado, ErrorValidacion
from nucleo.reloj import RelojSimulado
from nucleo.version_optimista import verificar_version
from pruebas import dobles
from pruebas.dobles import RelojFijo
from servidor import crear_app

SERVICIO = uuid4()
OTRO_SERVICIO = uuid4()
B1, B2 = uuid4(), uuid4()
C1 = uuid4()
LATERALES = {B1: "1520", B2: "1544"}
CONDUCTORES = {C1: "Carlos R."}
DURACIONES = {SERVICIO: 50, OTRO_SERVICIO: 50}


def turno(servicio: UUID, buseta: UUID, salida: str, fin: str | None, conductor: UUID | None = None) -> TurnoDato:
    return TurnoDato(servicio, buseta, conductor, time.fromisoformat(salida), time.fromisoformat(fin) if fin else None, uuid4())


# ---------- ValidadorRodamiento ----------


def test_solapamiento_de_buseta_con_el_mensaje_del_mockup() -> None:
    a, b = turno(SERVICIO, B1, "06:00", "06:50"), turno(OTRO_SERVICIO, B1, "06:40", "07:30")
    [adv] = detectar_solapamientos([a, b], DURACIONES, LATERALES, CONDUCTORES)
    assert adv.codigo == "solapamiento_buseta"
    assert adv.mensaje == "La buseta 1520 sale a las 06:40 y todavía está en el turno de las 06:00 a las 06:50."
    assert {t.id for t in adv.turnos} == {a.id, b.id}


def test_solapamiento_de_conductor() -> None:
    a = turno(SERVICIO, B1, "06:00", "06:50", C1)
    b = turno(OTRO_SERVICIO, B2, "06:30", "07:20", C1)
    [adv] = detectar_solapamientos([a, b], DURACIONES, LATERALES, CONDUCTORES)
    assert adv.codigo == "solapamiento_conductor" and adv.mensaje.startswith("El conductor Carlos R. sale a las 06:30")


def test_turnos_consecutivos_no_se_solapan() -> None:
    a, b = turno(SERVICIO, B1, "06:00", "06:50"), turno(OTRO_SERVICIO, B1, "06:50", "07:40")
    assert detectar_solapamientos([a, b], DURACIONES, LATERALES, CONDUCTORES) == []


def test_sin_hora_de_fin_usa_la_duracion_del_servicio_y_si_no_120_minutos() -> None:
    sin_fin = turno(SERVICIO, B1, "06:00", None)  # 50 min → hasta 06:50
    assert detectar_solapamientos([sin_fin, turno(OTRO_SERVICIO, B1, "06:49", "07:30")], DURACIONES, LATERALES, {})
    assert not detectar_solapamientos([sin_fin, turno(OTRO_SERVICIO, B1, "06:50", "07:30")], DURACIONES, LATERALES, {})
    assert detectar_solapamientos([turno(SERVICIO, B1, "06:00", None), turno(SERVICIO, B1, "07:59", None)], {}, LATERALES, {})


def test_reemplazo_de_buseta_o_conductor_en_un_turno_guardado() -> None:
    guardado = turno(SERVICIO, B1, "06:00", "06:50", C1)
    mismo = turno(SERVICIO, B1, "06:00", "06:50", C1)
    otra_buseta = turno(SERVICIO, B2, "06:00", "06:50", C1)
    otro_conductor = turno(SERVICIO, B1, "06:00", "06:50", None)
    nuevo_horario = turno(SERVICIO, B2, "09:00", "09:50")
    assert detectar_reemplazos([guardado], [mismo, nuevo_horario], LATERALES, CONDUCTORES) == []
    [a] = detectar_reemplazos([guardado], [otra_buseta], LATERALES, CONDUCTORES)
    assert (a["busetaActual"], a["busetaNueva"], a["horaSalida"]) == ("1520", "1544", "06:00")
    assert detectar_reemplazos([guardado], [otro_conductor], LATERALES, CONDUCTORES)[0]["conductorActual"] == "Carlos R."


# ---------- versión optimista ----------


def test_version_distinta_lanza_conflicto_con_la_actual() -> None:
    with pytest.raises(ErrorConflictoVersion) as e:
        verificar_version(1, 4)
    assert e.value.detalles == {"versionActual": 4}


# ---------- PoliticaDeAvisos ----------

JEFE = Identidad("u1", Rol.JEFE_OPERACIONES, str(dobles.EMPRESA_SIDERAL))
SECRETARIA = Identidad("u2", Rol.SECRETARIA_MOVILIDAD)
ADMIN = Identidad("u3", Rol.ADMINISTRADOR)


def test_origen_segun_el_rol() -> None:
    assert definir_aviso(JEFE, "t", "c", "obra", 500, True, False).origen == "empresa"
    assert definir_aviso(JEFE, "t", "c", "obra", 500, True, False).empresa_id == dobles.EMPRESA_SIDERAL
    assert definir_aviso(JEFE, "t", "c", "obra", 500, True, False).tipo_cambio is None  # tipoCambio es solo de movilidad
    movilidad = definir_aviso(SECRETARIA, "t", "c", "obra", 500, True, False)
    assert (movilidad.origen, movilidad.empresa_id, movilidad.tipo_cambio) == ("movilidad", None, "obra")
    assert definir_aviso(ADMIN, "t", "c", None, 500, False, False).origen == "aplicativo"  # sin rutas: prototipo general


def test_aviso_vacio_demasiado_largo_o_sin_destino() -> None:
    for titulo, cuerpo, largo in (("", "c", 500), ("t", "   ", 500), ("t", "x" * 501, 500)):
        with pytest.raises(ErrorValidacion):
            definir_aviso(SECRETARIA, titulo, cuerpo, None, largo, True, False)
    with pytest.raises(ErrorValidacion):
        definir_aviso(JEFE, "t", "c", None, 500, False, False)
    with pytest.raises(ErrorValidacion):
        definir_aviso(JEFE, "t", "c", None, 500, False, True)  # el jefe no asocia paraderos


def test_el_pasajero_no_publica() -> None:
    with pytest.raises(ErrorNoAutorizado):
        definir_aviso(Identidad("u", Rol.PASAJERO), "t", "c", None, 500, True, False)


def test_quien_puede_retirar() -> None:
    empresa = str(dobles.EMPRESA_SIDERAL)
    assert puede_retirar(JEFE, "empresa", empresa) is True
    assert puede_retirar(JEFE, "empresa", str(dobles.EMPRESA_SERVITURISMO)) is None  # de otra empresa: 404
    assert puede_retirar(JEFE, "movilidad", None) is None
    assert puede_retirar(SECRETARIA, "movilidad", None) is True and puede_retirar(SECRETARIA, "empresa", empresa) is False
    assert puede_retirar(ADMIN, "empresa", empresa) is True


# ---------- validación de horarios y frecuencias ----------


def test_validar_horarios() -> None:
    ok = HorarioNuevo("lun_vie", time(5, 0), time(21, 0), time(22, 0))
    validar_horarios([ok])
    with pytest.raises(ErrorValidacion):
        validar_horarios([HorarioNuevo("lun_vie", time(22, 0), time(21, 0))])
    with pytest.raises(ErrorValidacion):
        validar_horarios([HorarioNuevo("lun_vie", time(5, 0), time(21, 0), time(20, 0))])  # cierre antes de la última salida
    with pytest.raises(ErrorValidacion):
        validar_horarios([ok, ok])


def test_validar_frecuencias_sin_solape() -> None:
    validar_frecuencias([FranjaNueva("lun_vie", 0, 600, 5, 8), FranjaNueva("lun_vie", 600, 1440, 8, 10),
                         FranjaNueva("sabado", 0, 1440, 8, 10)])
    with pytest.raises(ErrorValidacion):
        validar_frecuencias([FranjaNueva("lun_vie", 0, 600, 5, 8), FranjaNueva("lun_vie", 599, 1440, 8, 10)])
    with pytest.raises(ErrorValidacion):
        validar_frecuencias([FranjaNueva("lun_vie", 600, 600, 5, 8)])
    with pytest.raises(ErrorValidacion):
        validar_frecuencias([FranjaNueva("lun_vie", 0, 600, 9, 8)])


# ---------- API ----------


@pytest.fixture
def repos() -> Repositorios:
    return dobles.repositorios_en_memoria()


@pytest.fixture
def cliente(repos: Repositorios) -> TestClient:
    cont = construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(RelojFijo()))
    return TestClient(crear_app(cont), raise_server_exceptions=False)


def _con(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


JEFE_H = _con("tok-jefe")
OTRA_H = _con("tok-jefe-otra")


def test_operacion_exige_el_rol_de_jefe(cliente: TestClient) -> None:
    for ruta in ("/mis-servicios", "/busetas", "/conductores", "/rodamientos"):
        assert cliente.get(f"/api/v1{ruta}").status_code == 401
        assert cliente.get(f"/api/v1{ruta}", headers=_con("tok-pasajera")).status_code == 403
        assert cliente.get(f"/api/v1{ruta}", headers=_con("tok-secretaria")).status_code == 403


def test_mis_servicios_y_listas_son_de_mi_empresa(cliente: TestClient) -> None:
    assert [s["rutaNombre"] for s in cliente.get("/api/v1/mis-servicios", headers=JEFE_H).json()] == ["La Enea"]
    assert cliente.get("/api/v1/mis-servicios", headers=OTRA_H).json() == []
    assert {b["numeroLateral"] for b in cliente.get("/api/v1/busetas", headers=JEFE_H).json()} == {"1544", "1520"}
    assert {b["numeroLateral"] for b in cliente.get("/api/v1/busetas", headers=OTRA_H).json()} == {"2683"}
    assert [c["nombre"] for c in cliente.get("/api/v1/conductores", headers=OTRA_H).json()] == ["Jorge T."]


def test_crear_buseta_numero_repetido_409_y_editar_con_version(cliente: TestClient) -> None:
    r = cliente.post("/api/v1/busetas", json={"numeroLateral": "9001", "placa": "ABC123"}, headers=JEFE_H)
    assert r.status_code == 201 and r.json()["version"] == 1 and r.json()["estado"] == "activa"
    dup = cliente.post("/api/v1/busetas", json={"numeroLateral": "1544"}, headers=JEFE_H)
    assert dup.status_code == 409 and dup.json()["error"]["codigo"] == "CONFLICTO_NEGOCIO"
    # el mismo número en otra empresa sí se permite
    assert cliente.post("/api/v1/busetas", json={"numeroLateral": "1544"}, headers=OTRA_H).status_code == 201
    nueva = r.json()["id"]
    ok = cliente.put(f"/api/v1/busetas/{nueva}", json={"estado": "fuera_servicio", "version": 1}, headers=JEFE_H)
    assert ok.status_code == 200 and ok.json()["version"] == 2 and ok.json()["estado"] == "fuera_servicio"
    viejo = cliente.put(f"/api/v1/busetas/{nueva}", json={"placa": "ZZZ999", "version": 1}, headers=JEFE_H)
    assert viejo.status_code == 409 and viejo.json()["error"]["codigo"] == "CONFLICTO_VERSION"
    assert viejo.json()["error"]["detalles"] == {"versionActual": 2}
    assert cliente.put(f"/api/v1/busetas/{dobles.BUSETA_OTRA_EMPRESA}", json={"version": 1}, headers=JEFE_H).status_code == 404


def test_conductores_crear_y_editar(cliente: TestClient) -> None:
    r = cliente.post("/api/v1/conductores", json={"nombre": "Julián P.", "codigo": "S03"}, headers=JEFE_H)
    assert r.status_code == 201 and r.json()["estado"] == "activo"
    assert cliente.post("/api/v1/conductores", json={"nombre": "x"}, headers=JEFE_H).status_code == 400
    ed = cliente.put(f"/api/v1/conductores/{r.json()['id']}", json={"nombre": "Julián Pérez", "version": 1}, headers=JEFE_H)
    assert ed.status_code == 200 and ed.json()["nombre"] == "Julián Pérez"
    assert cliente.put(f"/api/v1/conductores/{dobles.CONDUCTOR_OTRA_EMPRESA}", json={"version": 1}, headers=JEFE_H).status_code == 404


def _turno(salida: str, fin: str, servicio: UUID = dobles.SERVICIO_SIDERAL_ENEA, buseta: UUID = dobles.BUSETA_1544,
           conductor: UUID | None = dobles.CONDUCTOR_CARLOS) -> dict:
    return {"servicioId": str(servicio), "busetaId": str(buseta), "conductorId": str(conductor) if conductor else None,
            "horaSalida": salida, "horaFinEstimada": fin}


def _fecha_manana() -> str:
    return "2026-10-27"  # RelojFijo: lunes 2026-10-26 12:00


def test_flujo_borrador_con_advertencia_corregir_y_publicar(cliente: TestClient, repos: Repositorios) -> None:
    solapados = [_turno("06:00", "06:50"), _turno("06:40", "07:30", conductor=dobles.CONDUCTOR_MARTA)]
    r = cliente.post("/api/v1/rodamientos", json={"fecha": _fecha_manana(), "turnos": solapados}, headers=JEFE_H)
    assert r.status_code == 201
    borrador = r.json()
    assert borrador["estado"] == "borrador" and borrador["version"] == 1 and len(borrador["turnos"]) == 2
    [adv] = borrador["advertencias"]
    assert adv["codigo"] == "solapamiento_buseta" and "1544 sale a las 06:40" in adv["mensaje"] and len(adv["turnoIds"]) == 2
    assert borrador["turnos"][0]["numeroLateral"] == "1544"

    rid = borrador["rodamientoId"]
    bloqueado = cliente.post(f"/api/v1/rodamientos/{rid}/publicar", json={"version": 1}, headers=JEFE_H)
    assert bloqueado.status_code == 409 and bloqueado.json()["error"]["codigo"] == "CONFLICTO_NEGOCIO"
    assert bloqueado.json()["error"]["detalles"]["advertencias"][0]["codigo"] == "solapamiento_buseta"

    corregido = [_turno("06:00", "06:50"), _turno("06:50", "07:40")]
    con_reemplazo = cliente.put(f"/api/v1/rodamientos/{rid}", json={"turnos": corregido, "version": 1}, headers=JEFE_H)
    assert con_reemplazo.status_code == 200 and con_reemplazo.json()["advertencias"] == []
    assert con_reemplazo.json()["version"] == 2

    publicado = cliente.post(f"/api/v1/rodamientos/{rid}/publicar", json={"version": 2}, headers=JEFE_H)
    assert publicado.status_code == 200 and publicado.json()["estado"] == "publicado"
    assert repos.operacion.estados_cambiados[-1][1] == "publicado"
    otra_vez = cliente.post(f"/api/v1/rodamientos/{rid}/publicar", json={"version": 3}, headers=JEFE_H)
    assert otra_vez.status_code == 409
    editar_publicado = cliente.put(f"/api/v1/rodamientos/{rid}", json={"turnos": corregido, "version": 3}, headers=JEFE_H)
    assert editar_publicado.status_code == 409


def test_reemplazar_buseta_de_un_turno_guardado_exige_confirmacion(cliente: TestClient) -> None:
    creado = cliente.post("/api/v1/rodamientos", json={"fecha": _fecha_manana(), "turnos": [_turno("06:00", "06:50")]}, headers=JEFE_H)
    rid = creado.json()["rodamientoId"]
    cambio = [_turno("06:00", "06:50", buseta=dobles.BUSETA_1520)]
    sin_confirmar = cliente.put(f"/api/v1/rodamientos/{rid}", json={"turnos": cambio, "version": 1}, headers=JEFE_H)
    assert sin_confirmar.status_code == 409
    cuerpo = sin_confirmar.json()["error"]
    assert cuerpo["codigo"] == "CONFLICTO_NEGOCIO"
    assert cuerpo["mensaje"] == "La ruta ya tiene asignada la buseta 1544 a las 06:00. ¿Reemplazarla por la 1520?"
    assert cuerpo["detalles"]["turnosAfectados"][0]["busetaNueva"] == "1520"
    confirmado = cliente.put(
        f"/api/v1/rodamientos/{rid}", json={"turnos": cambio, "version": 1, "confirmarReemplazo": True}, headers=JEFE_H
    )
    assert confirmado.status_code == 200 and confirmado.json()["turnos"][0]["numeroLateral"] == "1520"


def test_version_vieja_en_el_rodamiento_409(cliente: TestClient) -> None:
    rid = cliente.post("/api/v1/rodamientos", json={"fecha": _fecha_manana(), "turnos": [_turno("06:00", "06:50")]},
                       headers=JEFE_H).json()["rodamientoId"]
    r = cliente.put(f"/api/v1/rodamientos/{rid}", json={"turnos": [_turno("07:00", "07:50")], "version": 7}, headers=JEFE_H)
    assert r.status_code == 409 and r.json()["error"]["codigo"] == "CONFLICTO_VERSION"


def test_rodamiento_validaciones_de_fecha_y_unicidad(cliente: TestClient) -> None:
    turnos = [_turno("06:00", "06:50")]
    assert cliente.post("/api/v1/rodamientos", json={"fecha": "2026-10-25", "turnos": turnos}, headers=JEFE_H).status_code == 400
    assert cliente.post("/api/v1/rodamientos", json={"fecha": "2026-11-12", "turnos": turnos}, headers=JEFE_H).status_code == 400
    assert cliente.post("/api/v1/rodamientos", json={"fecha": "2026-13-45", "turnos": turnos}, headers=JEFE_H).status_code == 400
    assert cliente.post("/api/v1/rodamientos", json={"fecha": "2026-10-26", "turnos": turnos}, headers=JEFE_H).status_code == 201  # hoy
    assert cliente.post("/api/v1/rodamientos", json={"fecha": "2026-11-10", "turnos": turnos}, headers=JEFE_H).status_code == 201
    repetido = cliente.post("/api/v1/rodamientos", json={"fecha": "2026-11-10", "turnos": turnos}, headers=JEFE_H)
    assert repetido.status_code == 409 and repetido.json()["error"]["codigo"] == "CONFLICTO_NEGOCIO"
    fin_antes = [_turno("07:00", "06:00")]
    assert cliente.post("/api/v1/rodamientos", json={"fecha": _fecha_manana(), "turnos": fin_antes}, headers=JEFE_H).status_code == 400


def test_recursos_de_otra_empresa_en_un_turno_dan_404(cliente: TestClient) -> None:
    for turno_ajeno in (
        _turno("06:00", "06:50", buseta=dobles.BUSETA_OTRA_EMPRESA),
        _turno("06:00", "06:50", conductor=dobles.CONDUCTOR_OTRA_EMPRESA),
        _turno("06:00", "06:50", servicio=dobles.SERVICIO_SERVITURISMO_ENEA),
    ):
        r = cliente.post("/api/v1/rodamientos", json={"fecha": _fecha_manana(), "turnos": [turno_ajeno]}, headers=JEFE_H)
        assert r.status_code == 404


def test_un_jefe_no_ve_ni_toca_el_rodamiento_de_otro(cliente: TestClient) -> None:
    rid = cliente.post("/api/v1/rodamientos", json={"fecha": _fecha_manana(), "turnos": [_turno("06:00", "06:50")]},
                       headers=JEFE_H).json()["rodamientoId"]
    assert cliente.get(f"/api/v1/rodamientos/{rid}", headers=OTRA_H).status_code == 404
    assert cliente.post(f"/api/v1/rodamientos/{rid}/publicar", json={"version": 1}, headers=OTRA_H).status_code == 404
    assert cliente.post(f"/api/v1/rodamientos/{rid}/anular", json={"version": 1}, headers=OTRA_H).status_code == 404
    assert cliente.get("/api/v1/rodamientos", headers=OTRA_H).json() == []
    assert len(cliente.get("/api/v1/rodamientos", headers=JEFE_H).json()) == 1


def test_listar_con_rango_y_anular(cliente: TestClient) -> None:
    rid = cliente.post("/api/v1/rodamientos", json={"fecha": _fecha_manana(), "turnos": [_turno("06:00", "06:50")]},
                       headers=JEFE_H).json()["rodamientoId"]
    assert len(cliente.get("/api/v1/rodamientos", params={"desde": "2026-10-27", "hasta": "2026-10-27"}, headers=JEFE_H).json()) == 1
    assert cliente.get("/api/v1/rodamientos", params={"desde": "2026-10-28"}, headers=JEFE_H).json() == []
    assert cliente.get("/api/v1/rodamientos", params={"desde": "ayer"}, headers=JEFE_H).status_code == 400
    anulado = cliente.post(f"/api/v1/rodamientos/{rid}/anular", json={"version": 1}, headers=JEFE_H)
    assert anulado.status_code == 200 and anulado.json()["estado"] == "anulado" and anulado.json()["advertencias"] == []
    assert cliente.post(f"/api/v1/rodamientos/{rid}/anular", json={"version": 2}, headers=JEFE_H).status_code == 409
    # una fecha anulada se puede volver a crear
    assert cliente.post("/api/v1/rodamientos", json={"fecha": _fecha_manana(), "turnos": [_turno("06:00", "06:50")]},
                        headers=JEFE_H).status_code == 201


# ---------- horarios y frecuencias del jefe ----------

HORARIO = {"tipoDia": "lun_vie", "primeraSalida": "05:30", "ultimaSalida": "21:00", "cierre": "22:00", "nota": None}


def test_el_jefe_edita_horarios_de_su_servicio(cliente: TestClient, repos: Repositorios) -> None:
    url = f"/api/v1/servicios/{dobles.SERVICIO_SIDERAL_ENEA}/horarios"
    r = cliente.put(url, json={"horarios": [HORARIO], "version": 2}, headers=JEFE_H)
    assert r.status_code == 200
    assert (r.json()["version"], r.json()["estado"], r.json()["tiposDiaPendientes"]) == (3, "parcial", ["sabado", "dom_festivo"])
    assert repos.horarios.horarios_guardados[0].cierre == time(22, 0)
    vieja = cliente.put(url, json={"horarios": [HORARIO], "version": 2}, headers=JEFE_H)
    assert vieja.status_code == 409 and vieja.json()["error"]["detalles"] == {"versionActual": 3}


def test_horarios_invalidos_y_servicio_ajeno(cliente: TestClient) -> None:
    url = f"/api/v1/servicios/{dobles.SERVICIO_SIDERAL_ENEA}/horarios"
    malo = {**HORARIO, "cierre": "20:00"}
    assert cliente.put(url, json={"horarios": [malo], "version": 2}, headers=JEFE_H).status_code == 400
    assert cliente.put(url, json={"horarios": [HORARIO], "version": 2}, headers=OTRA_H).status_code == 404
    assert cliente.put(url, json={"horarios": [HORARIO], "version": 2}).status_code == 401
    assert cliente.put(url, json={"horarios": [HORARIO], "version": 2}, headers=_con("tok-secretaria")).status_code == 403


def test_el_jefe_edita_frecuencias(cliente: TestClient, repos: Repositorios) -> None:
    url = f"/api/v1/servicios/{dobles.SERVICIO_SIDERAL_ENEA}/frecuencias"
    franjas = [
        {"tipoDia": "lun_vie", "franjaInicio": "05:00", "franjaFin": "09:00", "minutosMin": 4, "minutosMax": 6},
        {"tipoDia": "lun_vie", "franjaInicio": "09:00", "franjaFin": "24:00", "minutosMin": 8, "minutosMax": 10},
    ]
    r = cliente.put(url, json={"frecuencias": franjas, "version": 2}, headers=JEFE_H)
    assert r.status_code == 200 and r.json()["version"] == 3 and r.json()["frecuencias"][1]["franjaFin"] == "24:00"
    assert (repos.horarios.franjas_guardadas[0].inicio_minuto, repos.horarios.franjas_guardadas[1].fin_minuto) == (300, 1440)
    solapadas = [franjas[0], {**franjas[1], "franjaInicio": "08:59"}]
    assert cliente.put(url, json={"frecuencias": solapadas, "version": 3}, headers=JEFE_H).status_code == 400


# ---------- avisos por rol ----------


def test_publicar_aviso_segun_el_rol(cliente: TestClient, repos: Repositorios) -> None:
    ruta = str(dobles.RUTA_ENEA)
    jefe = cliente.post("/api/v1/avisos", json={"titulo": "Horario de festivo", "cuerpo": "Opera 06:00-21:00", "rutaIds": [ruta]},
                        headers=JEFE_H)
    assert jefe.status_code == 201 and jefe.json()["origen"] == "empresa" and jefe.json()["empresaNombre"] == "Sideral"
    mov = cliente.post("/api/v1/avisos", json={"tipoCambio": "cierre", "titulo": "Cierre", "cuerpo": "Obra", "rutaIds": [ruta]},
                       headers=_con("tok-secretaria"))
    assert mov.status_code == 201 and mov.json()["origen"] == "movilidad" and mov.json()["tipoCambio"] == "cierre"
    adm = cliente.post("/api/v1/avisos", json={"titulo": "Prototipo", "cuerpo": "Datos de ejemplo"}, headers=_con("tok-admin"))
    assert adm.status_code == 201 and adm.json()["origen"] == "aplicativo"
    assert cliente.post("/api/v1/avisos", json={"titulo": "x", "cuerpo": "y"}, headers=_con("tok-pasajera")).status_code == 403
    assert cliente.post("/api/v1/avisos", json={"titulo": "x", "cuerpo": "y"}).status_code == 401
    assert len(repos.avisos.creados) == 3


def test_el_jefe_no_publica_sobre_rutas_de_otra_empresa(cliente: TestClient) -> None:
    r = cliente.post("/api/v1/avisos", json={"titulo": "x", "cuerpo": "y", "rutaIds": [str(dobles.RUTA_VILLAMARIA)]}, headers=JEFE_H)
    assert r.status_code == 404
    assert cliente.post("/api/v1/avisos", json={"titulo": "x", "cuerpo": "y", "rutaIds": [str(uuid4())]},
                        headers=_con("tok-secretaria")).status_code == 404


def test_aviso_validaciones(cliente: TestClient) -> None:
    ruta = [str(dobles.RUTA_ENEA)]
    assert cliente.post("/api/v1/avisos", json={"titulo": "x", "cuerpo": "z" * 501, "rutaIds": ruta}, headers=JEFE_H).status_code == 400
    assert cliente.post("/api/v1/avisos", json={"titulo": "x", "cuerpo": "y"}, headers=JEFE_H).status_code == 400  # sin ruta
    fechas = {"titulo": "x", "cuerpo": "y", "rutaIds": ruta, "desde": "2026-10-28T10:00:00-05:00", "hasta": "2026-10-28T09:00:00-05:00"}
    assert cliente.post("/api/v1/avisos", json=fechas, headers=JEFE_H).status_code == 400


def test_retirar_avisos(cliente: TestClient, repos: Repositorios) -> None:
    ruta = [str(dobles.RUTA_ENEA)]
    propio = cliente.post("/api/v1/avisos", json={"titulo": "a", "cuerpo": "b", "rutaIds": ruta}, headers=JEFE_H).json()["id"]
    movilidad = cliente.post("/api/v1/avisos", json={"titulo": "a", "cuerpo": "b", "rutaIds": ruta},
                             headers=_con("tok-secretaria")).json()["id"]
    assert cliente.delete(f"/api/v1/avisos/{movilidad}", headers=JEFE_H).status_code == 404  # no es de su empresa
    assert cliente.delete(f"/api/v1/avisos/{propio}", headers=OTRA_H).status_code == 404  # jefe de otra empresa
    assert cliente.delete(f"/api/v1/avisos/{propio}", headers=_con("tok-secretaria")).status_code == 403
    assert cliente.delete(f"/api/v1/avisos/{propio}", headers=JEFE_H).status_code == 204
    assert cliente.delete(f"/api/v1/avisos/{propio}", headers=JEFE_H).status_code == 404  # ya retirado
    assert cliente.delete(f"/api/v1/avisos/{movilidad}", headers=_con("tok-secretaria")).status_code == 204
    assert str(repos.avisos.retirados[0]) == propio


def test_publicar_aviso_avisa_por_websocket_a_los_clientes_de_la_ruta(repos: Repositorios) -> None:
    cont = construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(RelojFijo()))
    with TestClient(crear_app(cont)) as cliente, cliente.websocket_connect(f"/ws/rutas/{dobles.RUTA_ENEA}") as ws:
        ws.receive_json()  # foto inicial
        r = cliente.post("/api/v1/avisos", json={"titulo": "a", "cuerpo": "b", "rutaIds": [str(dobles.RUTA_ENEA)]}, headers=JEFE_H)
        assert ws.receive_json() == {"tipo": "aviso_nuevo", "avisoId": r.json()["id"]}


def test_el_administrador_actua_sobre_la_empresa_que_indica(cliente: TestClient) -> None:
    admin = _con("tok-admin")
    assert cliente.get("/api/v1/busetas", headers=admin).status_code == 400  # falta empresaId
    r = cliente.get("/api/v1/busetas", params={"empresaId": str(dobles.EMPRESA_SERVITURISMO)}, headers=admin)
    assert [b["numeroLateral"] for b in r.json()] == ["2683"]
    r = cliente.get("/api/v1/mis-servicios", params={"empresaId": str(dobles.EMPRESA_SIDERAL)}, headers=admin)
    assert r.status_code == 200 and len(r.json()) == 1
    url = f"/api/v1/servicios/{dobles.SERVICIO_SIDERAL_ENEA}/horarios"
    ok = cliente.put(url, params={"empresaId": str(dobles.EMPRESA_SIDERAL)}, json={"horarios": [HORARIO], "version": 2}, headers=admin)
    assert ok.status_code == 200
    ajeno = cliente.put(url, params={"empresaId": str(dobles.EMPRESA_SERVITURISMO)}, json={"horarios": [HORARIO], "version": 3}, headers=admin)
    assert ajeno.status_code == 404


def test_el_jefe_ignora_empresa_id(cliente: TestClient) -> None:
    r = cliente.get("/api/v1/busetas", params={"empresaId": str(dobles.EMPRESA_SERVITURISMO)}, headers=JEFE_H)
    assert {b["numeroLateral"] for b in r.json()} == {"1544", "1520"}
