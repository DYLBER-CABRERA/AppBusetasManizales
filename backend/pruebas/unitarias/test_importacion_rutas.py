"""Importación de rutas desde CSV (vista previa y confirmación). Sin BD ni red: dobles en memoria; OSRM nunca se llama."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from composicion import Repositorios, construir_contenedor
from modulos.red.aplicacion.importacion import ConfirmarImportacionRutas
from modulos.red.dominio.importacion_rutas import (
    MAX_BYTES,
    MAX_FILAS,
    MAX_RUTAS,
    PLANTILLA,
    leer,
    validar_ruta,
)
from nucleo.configuracion import Configuracion
from nucleo.errores import ErrorValidacion
from nucleo.reloj import RelojSimulado
from pruebas import dobles
from pruebas.dobles import RelojFijo
from pruebas.unitarias.test_trazado_calles import _con_detalle
from servidor import crear_app

EJEMPLOS = Path(__file__).resolve().parents[2] / "supabase" / "semillas" / "ejemplos"
CAJA = {"minLat": 4.95, "maxLat": 5.20, "minLng": -75.65, "maxLng": -75.40}
SEC = {"Authorization": "Bearer tok-secretaria", "Content-Type": "text/csv"}
ADM = {"Authorization": "Bearer tok-admin", "Content-Type": "text/csv"}
CABECERA = "ruta,orden,latitud,longitud,nombre_punto,empresa,codigo_publico\n"
VALIDA = CABECERA + (
    "Ruta Uno,1,5.060,-75.500,Inicio,Sideral,12\nRuta Uno,2,5.065,-75.505,,Sideral,12\nRuta Uno,3,5.075,-75.515,Fin,Sideral,12\n"
)


def _leer(texto: str | bytes):
    return leer(texto.encode("utf-8") if isinstance(texto, str) else texto)


def _motivos(ruta) -> list[tuple]:
    return [(e.fila, e.columna, e.motivo) for e in ruta.errores]


# ---------- lectura del CSV (parser puro) ----------


def test_csv_valido_agrupa_por_ruta_y_ordena() -> None:
    r = _leer(VALIDA)
    [ruta] = r.rutas
    assert (ruta.nombre, ruta.empresa, ruta.codigo_publico) == ("Ruta Uno", "Sideral", "12") and ruta.errores == []
    assert [(p.orden, p.nombre_punto) for p in ruta.puntos] == [(1, "Inicio"), (2, None), (3, "Fin")]
    assert r.total_filas == 3 and r.errores_generales == []


@pytest.mark.parametrize("separador", [",", ";", "\t"])
def test_acepta_coma_punto_y_coma_o_tabulador(separador: str) -> None:
    texto = VALIDA.replace(",", separador)
    assert len(_leer(texto).rutas[0].puntos) == 3


def test_decimales_con_coma_y_punto_y_celdas_entrecomilladas() -> None:
    texto = "ruta;orden;latitud;longitud;empresa\nR1;1;5,06;-75,50;Sideral\nR1;2;5,07;-75,51;Sideral\n"
    assert [(p.lat, p.lng) for p in _leer(texto).rutas[0].puntos] == [(5.06, -75.5), (5.07, -75.51)]
    texto_coma = 'ruta,orden,latitud,longitud,empresa\nR1,1,"5,06","-75,50",Sideral\nR1,2,5.07,-75.51,Sideral\n'
    assert [(p.lat, p.lng) for p in _leer(texto_coma).rutas[0].puntos] == [(5.06, -75.5), (5.07, -75.51)]


def test_bom_tildes_y_codificacion_de_excel() -> None:
    con_bom = ("﻿" + CABECERA + "Fátima a Chipre,1,5.06,-75.5,Fátima,Sideral,\nFátima a Chipre,2,5.07,-75.51,Chipre,Sideral,\n").encode("utf-8")
    assert _leer(con_bom).rutas[0].nombre == "Fátima a Chipre"
    cp1252 = (CABECERA + "Fátima a Chipre,1,5.06,-75.5,Fátima,Sideral,\nFátima a Chipre,2,5.07,-75.51,Chipre,Sideral,\n").encode("cp1252")
    r = _leer(cp1252)
    assert r.rutas[0].nombre == "Fátima a Chipre" and r.rutas[0].puntos[0].nombre_punto == "Fátima"


def test_filas_vacias_se_ignoran_y_el_numero_de_fila_es_el_del_archivo() -> None:
    texto = CABECERA + "\n,,,,,,\nRuta Uno,1,5.06,-75.5,,Sideral,\n\nRuta Uno,x,5.07,-75.5,,Sideral,\n"
    ruta = _leer(texto).rutas[0]
    assert len(ruta.puntos) == 1 and _motivos(ruta) == [(6, "orden", "orden_invalido")]  # la fila 6 del archivo


def test_encabezados_con_alias_tildes_y_mayusculas_en_cualquier_orden() -> None:
    texto = "Empresa,Longitud,LATITUD,Orden,Nombre del punto,Ruta\nSideral,-75.5,5.06,1,A,R1\nSideral,-75.51,5.07,2,B,R1\n"
    r = _leer(texto.replace("Nombre del punto", "nombre"))
    assert [p.nombre_punto for p in r.rutas[0].puntos] == ["A", "B"]
    extra = _leer(CABECERA.strip() + ",observaciones\nR1,1,5.06,-75.5,,Sideral,,hola\nR1,2,5.07,-75.5,,Sideral,,x\n")
    assert extra.columnas_ignoradas == ["observaciones"]


def test_faltan_columnas_obligatorias_400_con_la_columna() -> None:
    with pytest.raises(ErrorValidacion) as e:
        _leer("ruta,orden,latitud\nR1,1,5.06\n")
    assert [(d["columna"], d["motivo"]) for d in e.value.detalles] == [("longitud", "columna_obligatoria"), ("empresa", "columna_obligatoria")]


@pytest.mark.parametrize(
    ("contenido", "motivo"),
    [
        (b"", "archivo_vacio"), (b"   \n ", "archivo_vacio"),
        (b"PK\x03\x04restoDeUnXlsx", "formato_no_soportado"),
        (b"x" * (MAX_BYTES + 1), "archivo_muy_grande"),
        (CABECERA.encode(), "sin_datos"),
        ((CABECERA + ",,,,,,\n").encode(), "sin_datos"),
    ],
)
def test_errores_generales_del_archivo(contenido: bytes, motivo: str) -> None:
    with pytest.raises(ErrorValidacion) as e:
        _leer(contenido)
    assert e.value.detalles[0]["motivo"] == motivo


def test_limites_de_filas_y_de_rutas() -> None:
    filas = "".join(f"R{i % 2},{i},5.06,-75.5,,Sideral,\n" for i in range(MAX_FILAS + 1))
    with pytest.raises(ErrorValidacion) as e:
        _leer(CABECERA + filas)
    assert e.value.detalles[0]["motivo"] == "demasiadas_filas"
    muchas = "".join(f"Ruta {i},1,5.06,-75.5,,Sideral,\nRuta {i},2,5.07,-75.5,,Sideral,\n" for i in range(MAX_RUTAS + 1))
    with pytest.raises(ErrorValidacion) as e:
        _leer(CABECERA + muchas)
    assert e.value.detalles[0]["motivo"] == "demasiadas_rutas"
    assert len(_leer(CABECERA + muchas.split("Ruta 10")[0]).rutas) == MAX_RUTAS  # justo el máximo: pasa


def test_mas_de_30_puntos_en_una_ruta() -> None:
    filas = "".join(f"Larga,{i + 1},{5.0 + i * 0.002},{-75.5 - i * 0.0005},,Sideral,\n" for i in range(31))
    ruta = _leer(CABECERA + filas).rutas[0]
    validar_ruta(ruta, CAJA)
    assert [e.motivo for e in ruta.errores] == ["demasiados_puntos"] and ruta.errores[0].fila is None
    ok = _leer(CABECERA + filas.split("\n", 1)[1].rsplit("\n", 2)[0] + "\n").rutas[0]  # 29 filas
    validar_ruta(ok, CAJA)
    assert ok.errores == []


@pytest.mark.parametrize(
    ("fila", "columna", "motivo"),
    [
        ("Ruta R,1,norte,-75.5,,Sideral,", "latitud", "numero_invalido"),
        ("Ruta R,1,5.06,1.234.567,,Sideral,", "longitud", "numero_invalido"),
        ("Ruta R,0,5.06,-75.5,,Sideral,", "orden", "orden_invalido"),
        ("Ruta R,1.5,5.06,-75.5,,Sideral,", "orden", "orden_invalido"),
        ("Ruta R,1,5.06,-75.5,,Sideral,abc", "codigo_publico", "codigo_invalido"),
        ("Ruta R,1,5.06,-75.5,=CMD|' /C calc'!A0,Sideral,", "nombre_punto", "formula_no_permitida"),
        ("Ruta R,1,5.06,-75.5,@SUMA(1),Sideral,", "nombre_punto", "formula_no_permitida"),
        ("Ruta R,1,5.06,-75.5,+54,Sideral,", "nombre_punto", "formula_no_permitida"),
        ("Ruta R,1,5.06,-75.5," + "x" * 121 + ",Sideral,", "nombre_punto", "muy_largo"),
    ],
)
def test_errores_por_fila_con_numero_de_fila_y_columna(fila: str, columna: str, motivo: str) -> None:
    ruta = _leer(CABECERA + fila + "\n").rutas[0]
    assert _motivos(ruta) == [(2, columna, motivo)]


def test_una_ruta_con_formula_en_el_nombre_va_a_errores_generales() -> None:
    r = _leer(CABECERA + "=1+1,1,5.06,-75.5,,Sideral,\n,2,5.07,-75.5,,Sideral,\n")
    assert [(e.fila, e.columna, e.motivo) for e in r.errores_generales] == [
        (2, "ruta", "formula_no_permitida"), (3, "ruta", "obligatorio")]
    assert r.rutas == []


def test_orden_duplicado_y_orden_con_saltos() -> None:
    ruta = _leer(CABECERA + "Ruta R,1,5.06,-75.5,,Sideral,\nRuta R,1,5.07,-75.5,,Sideral,\nRuta R,5,5.08,-75.5,,Sideral,\nRuta R,3,5.09,-75.5,,Sideral,\n").rutas[0]
    assert _motivos(ruta) == [(3, "orden", "orden_duplicado")]
    assert [p.orden for p in sorted(ruta.puntos, key=lambda p: p.orden)] == [1, 3, 5]  # los saltos se permiten: se ordena por `orden`


def test_empresa_distinta_en_filas_de_una_misma_ruta() -> None:
    ruta = _leer(CABECERA + "Ruta R,1,5.06,-75.5,,Sideral,\nRuta R,2,5.07,-75.5,,Serviturismo,\n").rutas[0]
    assert _motivos(ruta) == [(3, "empresa", "empresa_distinta")]


def test_el_nombre_de_ruta_se_agrupa_sin_tildes_ni_mayusculas() -> None:
    r = _leer(CABECERA + "Fátima a Chipre,1,5.06,-75.5,,Sideral,\nFATIMA A CHIPRE,2,5.07,-75.5,,Sideral,\n")
    assert len(r.rutas) == 1 and len(r.rutas[0].puntos) == 2


def test_validacion_de_puntos_traduce_el_indice_a_fila_del_archivo() -> None:
    ruta = _leer(CABECERA + "Ruta R,1,5.06,-75.5,,Sideral,\nRuta R,2,4.0,-75.5,,Sideral,\nRuta R,3,5.08,-75.5,,Sideral,\n").rutas[0]
    validar_ruta(ruta, CAJA)
    assert _motivos(ruta) == [(3, "latitud", "fuera_de_zona")]
    cerca = _leer(CABECERA + "Ruta R,1,5.06,-75.5,,Sideral,\nRuta R,2,5.06001,-75.5,,Sideral,\nRuta R,3,5.08,-75.5,,Sideral,\n").rutas[0]
    validar_ruta(cerca, CAJA)
    assert _motivos(cerca) == [(3, "orden", "duplicado_consecutivo")]
    una = _leer(CABECERA + "Ruta R,1,5.06,-75.5,,Sideral,\n").rutas[0]
    validar_ruta(una, CAJA)
    assert _motivos(una) == [(None, None, "pocos_puntos")]
    sin_empresa = _leer(CABECERA + "Ruta R,1,5.06,-75.5,,,\nRuta R,2,5.07,-75.5,,,\n").rutas[0]
    validar_ruta(sin_empresa, CAJA)
    assert _motivos(sin_empresa) == [(None, "empresa", "falta_empresa")]


# ---------- archivos de ejemplo ----------


def test_la_plantilla_y_el_archivo_de_ejemplo_son_validos_y_coinciden() -> None:
    assert (EJEMPLOS / "importacion_rutas_ejemplo.csv").read_text(encoding="utf-8") == PLANTILLA
    ruta = _leer(PLANTILLA).rutas[0]
    validar_ruta(ruta, CAJA)
    assert ruta.errores == [] and len(ruta.puntos) == 4 and "ejemplo" in ruta.nombre.lower()


# ---------- API ----------


@pytest.fixture
def repos() -> Repositorios:
    r = dobles.repositorios_en_memoria()
    _con_detalle(r)  # GET /rutas/{id} sobre lo que se guardó
    return r


@pytest.fixture
def cliente(repos: Repositorios) -> TestClient:
    cont = construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(RelojFijo()))
    return TestClient(crear_app(cont), raise_server_exceptions=False)


def _post(cliente: TestClient, ruta: str, texto: str | bytes, cabeceras: dict = SEC):
    return cliente.post(f"/api/v1/rutas/importacion/{ruta}", content=texto.encode("utf-8") if isinstance(texto, str) else texto, headers=cabeceras)


def test_permisos(cliente: TestClient, repos: Repositorios) -> None:
    for ruta in ("vista-previa", "confirmar"):
        assert cliente.post(f"/api/v1/rutas/importacion/{ruta}", content=VALIDA).status_code == 401
        for token in ("tok-jefe", "tok-pasajera"):
            r = _post(cliente, ruta, VALIDA, {"Authorization": f"Bearer {token}", "Content-Type": "text/csv"})
            assert r.status_code == 403
        assert _post(cliente, ruta, VALIDA, ADM).status_code in (200, 201)
    assert cliente.get("/api/v1/rutas/importacion/plantilla").status_code == 401
    assert cliente.get("/api/v1/rutas/importacion/plantilla", headers={"Authorization": "Bearer tok-jefe"}).status_code == 403


def test_plantilla_descargable(cliente: TestClient) -> None:
    r = cliente.get("/api/v1/rutas/importacion/plantilla", headers=SEC)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"] and r.content.startswith(b"\xef\xbb\xbf")  # BOM para Excel
    assert r.content.decode("utf-8-sig") == PLANTILLA
    assert _post(cliente, "vista-previa", r.content).json()["resumen"] == {"validas": 1, "conErrores": 0, "duplicadas": 0}


def test_vista_previa_no_escribe_ni_llama_a_osrm(cliente: TestClient, repos: Repositorios) -> None:
    r = _post(cliente, "vista-previa", VALIDA)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["seCrearian"] == 1 and cuerpo["totalFilas"] == 3 and cuerpo["erroresGenerales"] == []
    [ruta] = cuerpo["rutas"]
    assert (ruta["nombre"], ruta["estado"], ruta["puntos"], ruta["empresa"], ruta["codigoPublico"]) == ("Ruta Uno", "valida", 3, "Sideral", "12")
    assert ruta["errores"] == [] and ruta["paraderosNuevos"] == 3 and ruta["paraderosReutilizados"] == 0
    assert any("trazado por calles" in a for a in ruta["avisos"])
    assert repos.gestion_red.creadas == {} and repos.enrutador.llamadas == []  # nada escrito, OSRM sin tocar


def test_vista_previa_cuenta_los_paraderos_que_se_reutilizarian(cliente: TestClient, repos: Repositorios) -> None:
    a = repos.gestion_red.paraderos[dobles.PARADERO_A]
    texto = CABECERA + f"Ruta R,1,{a['lat']},{a['lng']},,Sideral,\nRuta R,2,5.09,-75.53,,Sideral,\nRuta R,3,5.095,-75.535,,Sideral,\n"
    ruta = _post(cliente, "vista-previa", texto).json()["rutas"][0]
    assert (ruta["paraderosReutilizados"], ruta["paraderosNuevos"]) == (1, 2) and "reutilizarán" in ruta["avisos"][0]


def test_vista_previa_con_errores_por_ruta(cliente: TestClient, repos: Repositorios) -> None:
    texto = (
        CABECERA + "Buena,1,5.06,-75.5,,Sideral,\nBuena,2,5.07,-75.51,,Sideral,\n"
        "Fuera,1,5.06,-75.5,,Sideral,\nFuera,2,4.0,-75.5,,Sideral,\n"
        "Sin empresa conocida,1,5.06,-75.5,,Marte S.A.,\nSin empresa conocida,2,5.07,-75.5,,Marte S.A.,\n"
        "La Enea,1,5.06,-75.5,,Sideral,\nLa Enea,2,5.07,-75.5,,Sideral,\n"
        "Mala fila,1,abc,-75.5,,Sideral,\nMala fila,2,5.07,-75.5,,Sideral,\n"
    )
    cuerpo = _post(cliente, "vista-previa", texto).json()
    estados = {r["nombre"]: r for r in cuerpo["rutas"]}
    assert estados["Buena"]["estado"] == "valida"
    assert estados["Fuera"]["estado"] == "con_errores"
    assert estados["Fuera"]["errores"] == [{"fila": 5, "columna": "latitud", "motivo": "fuera_de_zona",
                                            "mensaje": "El punto está fuera de la zona de Manizales y Villamaría."}]
    assert [(e["fila"], e["columna"], e["motivo"]) for e in estados["Sin empresa conocida"]["errores"]] == [(6, "empresa", "empresa_desconocida")]
    assert estados["La Enea"]["estado"] == "duplicada" and estados["La Enea"]["errores"][0]["motivo"] == "ruta_duplicada"
    assert [(e["fila"], e["columna"]) for e in estados["Mala fila"]["errores"]] == [(10, "latitud")]
    assert cuerpo["resumen"] == {"validas": 1, "conErrores": 3, "duplicadas": 1} and cuerpo["seCrearian"] == 1
    assert repos.gestion_red.creadas == {}


def test_errores_generales_responden_400_con_formato_estandar(cliente: TestClient) -> None:
    r = _post(cliente, "vista-previa", b"PK\x03\x04xx")
    assert r.status_code == 400 and r.json()["error"]["codigo"] == "VALIDACION"
    assert r.json()["error"]["detalles"] == [{"fila": None, "columna": None, "motivo": "formato_no_soportado"}]
    assert _post(cliente, "vista-previa", b"").status_code == 400
    faltan = _post(cliente, "confirmar", "ruta,orden\nRuta R,1\n")
    assert faltan.status_code == 400 and faltan.json()["error"]["detalles"][0]["motivo"] == "columna_obligatoria"
    grande = _post(cliente, "vista-previa", b"a" * (MAX_BYTES + 10))
    assert grande.status_code == 400 and grande.json()["error"]["detalles"][0]["motivo"] == "archivo_muy_grande"


def test_confirmar_crea_solo_las_rutas_validas_y_lista_las_omitidas(cliente: TestClient, repos: Repositorios) -> None:
    texto = (
        CABECERA + "Buena,1,5.06,-75.5,Inicio,Sideral,31\nBuena,2,5.065,-75.505,,Sideral,31\nBuena,3,5.08,-75.52,Fin,Sideral,31\n"
        "Fuera,1,5.06,-75.5,,Sideral,\nFuera,2,4.0,-75.5,,Sideral,\n"
        "La Enea,1,5.06,-75.5,,Sideral,\nLa Enea,2,5.07,-75.5,,Sideral,\n"
    )
    r = _post(cliente, "confirmar", texto)
    assert r.status_code == 201
    cuerpo = r.json()
    assert [c["nombre"] for c in cuerpo["creadas"]] == ["Buena"] and cuerpo["creadas"][0]["puntos"] == 3
    assert cuerpo["creadas"][0]["avisos"] == []
    assert {o["nombre"]: o["estado"] for o in cuerpo["omitidas"]} == {"Fuera": "con_errores", "La Enea": "duplicada"}
    assert cuerpo["resumen"] == {"creadas": 1, "omitidas": 2}
    [creada] = repos.gestion_red.creadas.values()
    nombres = [repos.gestion_red.paraderos[i]["nombre"] for i in creada["paradero_ids"]]
    assert nombres == ["Inicio", "Paradero Buena 1", "Fin"]  # el orden del archivo y el patrón de nombres de las semillas
    assert creada["servicios"][0]["codigo_publico"] == "31"
    assert len(repos.enrutador.llamadas) == 3  # OSRM solo al confirmar: 3 tramos (incluye el cierre) de la ruta creada


def test_confirmar_el_mismo_archivo_otra_vez_no_pisa_nada(cliente: TestClient, repos: Repositorios) -> None:
    assert _post(cliente, "confirmar", VALIDA).status_code == 201
    segunda = _post(cliente, "confirmar", VALIDA)
    assert segunda.status_code == 200  # nada creado
    cuerpo = segunda.json()
    assert cuerpo["creadas"] == [] and cuerpo["omitidas"][0]["estado"] == "duplicada"
    assert len(repos.gestion_red.creadas) == 1


def test_confirmar_informa_los_tramos_en_linea_recta(repos: Repositorios) -> None:
    class Falla:
        async def trazar(self, origen, destino):
            return None

    repos.enrutador = Falla()
    cont = construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(RelojFijo()))
    cliente = TestClient(crear_app(cont), raise_server_exceptions=False)
    r = _post(cliente, "confirmar", VALIDA)
    assert r.status_code == 201 and len(repos.gestion_red.creadas) == 1  # la creación no falla por OSRM
    assert "sin ruta real" in r.json()["creadas"][0]["avisos"][0]


def test_si_una_ruta_falla_al_crearse_las_demas_siguen(cliente: TestClient, repos: Repositorios) -> None:
    original = repos.gestion_red.crear_ruta_con_paraderos

    async def falla_la_segunda(nombre, *a, **k):
        if nombre == "Segunda":
            raise RuntimeError("no debe filtrarse")
        return await original(nombre, *a, **k)

    repos.gestion_red.crear_ruta_con_paraderos = falla_la_segunda
    texto = CABECERA + "Primera,1,5.06,-75.5,,Sideral,\nPrimera,2,5.07,-75.5,,Sideral,\nSegunda,1,5.08,-75.5,,Sideral,\nSegunda,2,5.09,-75.5,,Sideral,\n"
    r = _post(cliente, "confirmar", texto)
    assert r.status_code == 201 and [c["nombre"] for c in r.json()["creadas"]] == ["Primera"]
    [omitida] = r.json()["omitidas"]
    assert omitida["nombre"] == "Segunda" and omitida["errores"][0]["motivo"] == "error_interno"
    assert "no debe filtrarse" not in r.text  # el detalle del error no sale al cliente
    assert len(repos.gestion_red.creadas) == 1


async def test_el_presupuesto_de_osrm_se_reparte_entre_las_rutas(repos: Repositorios) -> None:
    capturados: list[float | None] = []

    class RegistrarFalso:
        async def __call__(self, identidad, nombre, principal, puntos, servicios, compartida, presupuesto):
            capturados.append(presupuesto)
            return {"id": nombre, "nombre": nombre, "avisos": []}

    reloj = iter([0.0, 0.0, 40.0, 70.0, 70.0])
    caso = ConfirmarImportacionRutas(repos.gestion_red, repos.parametros, RegistrarFalso(), monotonico=lambda: next(reloj))
    texto = "".join(f"Ruta {i},{k},5.0{i + 1}{k},-75.5,,Sideral,\n" for i in range(3) for k in (1, 2))
    from nucleo.autorizacion import Identidad, Rol

    resultado = await caso(Identidad("u", Rol.SECRETARIA_MOVILIDAD), (CABECERA + texto).encode())
    assert len(resultado["creadas"]) == 3
    assert capturados == [25.0, 20.0, 0.0]  # 60 s en total: 25, lo que quedaba, y nada cuando se acabó (el resto va en recta)


def test_no_se_registra_el_contenido_del_archivo(cliente: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    secreto = "NombreMuyEspecificoDeRuta123"
    with caplog.at_level(logging.DEBUG):
        _post(cliente, "vista-previa", CABECERA + f"{secreto},1,5.06,-75.5,PuntoSecreto,Sideral,\n{secreto},2,abc,-75.5,,Sideral,\n")
        _post(cliente, "confirmar", CABECERA + f"{secreto}2,1,5.06,-75.5,PuntoSecreto,Sideral,\n{secreto}2,2,5.07,-75.5,,Sideral,\n")
    assert secreto not in caplog.text and "PuntoSecreto" not in caplog.text and "-75.5" not in caplog.text


def test_el_archivo_de_ejemplo_con_errores_da_los_estados_esperados(cliente: TestClient) -> None:
    contenido = (EJEMPLOS / "importacion_rutas_con_errores_ejemplo.csv").read_bytes()
    estados = {r["nombre"]: r["estado"] for r in _post(cliente, "vista-previa", contenido).json()["rutas"]}
    assert list(estados.values()) == ["valida", "con_errores", "con_errores"]


def test_el_openapi_describe_el_cuerpo_csv(cliente: TestClient) -> None:
    esquema = cliente.app.openapi()
    for ruta in ("vista-previa", "confirmar"):
        cuerpo = esquema["paths"][f"/api/v1/rutas/importacion/{ruta}"]["post"]["requestBody"]
        assert "text/csv" in cuerpo["content"]
    assert "get" in esquema["paths"]["/api/v1/rutas/importacion/plantilla"]
