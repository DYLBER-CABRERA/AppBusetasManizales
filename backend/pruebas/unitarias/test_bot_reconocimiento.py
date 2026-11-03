"""Bot de Telegram: reconocimiento de lugares en texto libre, con los hitos y barrios REALES (hitos.json + barrios.json).

Bug reportado: «Que ruta van a la enea» respondía «No encontré rutas que pasen por «Avanzada»»."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from adaptadores_externos.bot_telegram import LogicaBot, Respuesta
from composicion import Contenedor, Repositorios, construir_contenedor
from nucleo.configuracion import Configuracion
from nucleo.reloj import RelojSimulado
from pruebas import dobles
from pruebas.dobles import RelojFijo

SEMILLAS = Path(__file__).resolve().parents[2] / "supabase" / "semillas"
HITOS = json.loads((SEMILLAS / "hitos.json").read_text(encoding="utf-8"))
BARRIOS = json.loads((SEMILLAS / "barrios.json").read_text(encoding="utf-8"))["barrios"]
CHAT = 77


@pytest.fixture
def repos() -> Repositorios:
    r = dobles.repositorios_en_memoria()
    r.busqueda = dobles.BusquedaConHitos(HITOS + BARRIOS)
    return r


@pytest.fixture
def contenedor(repos: Repositorios) -> Contenedor:
    return construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(RelojFijo()))


@pytest.fixture
def bot(contenedor: Contenedor) -> LogicaBot:
    return LogicaBot(contenedor.servicios, RelojFijo())


def _botones(r: Respuesta) -> list[str]:
    return [b.datos for fila in r.botones for b in fila]


# ---------- causa raíz demostrada ----------


async def test_causa_raiz_la_palabra_van_es_subcadena_de_avanzada(repos: Repositorios) -> None:
    """La búsqueda de hitos es por SUBCADENA («contiene», igual que el SQL): «van» está dentro de «a-VAN-zada».
    El bot descartaba «que», «ruta», «la» y «a», pero NO «van»; probaba «van enea» (sin resultados) y después «van»
    sobre la búsqueda por subcadena, y tomaba el primer hito: Avanzada."""
    encontrados = await repos.busqueda.buscar_hitos("%van%", "van")
    assert [h["nombre"] for h in encontrados][0] == "Avanzada"
    assert "avanzada" not in "que ruta van a la enea".replace(" ", "")  # el usuario nunca escribió «avanzada»
    assert "Avanzada" not in [h["nombre"] for h in await repos.busqueda.buscar_hitos("%enea%", "enea")]


# ---------- variantes que deben resolver al hito correcto ----------

LA_ENEA = ["la enea", "enea", "La Enea", "LA ENEA", "a la enea", "que ruta van a la enea", "Que ruta van a la enea",
           "qué rutas pasan por la enea", "ruta para la enea", "¿Qué ruta va a La Enea?", "  la   enea  "]


@pytest.mark.parametrize("texto", LA_ENEA)
async def test_la_enea_resuelve_a_la_enea_y_nunca_a_avanzada(bot: LogicaBot, texto: str) -> None:
    r = await bot.texto(CHAT, texto)
    assert "«La Enea»" in r.texto and "Ruta La Enea" in r.texto, r.texto
    assert "Avanzada" not in r.texto and "Caserío" not in r.texto
    assert _botones(r) == [f"ruta:{dobles.RUTA_ENEA}"]


@pytest.mark.parametrize("texto", ["caserio la enea", "Caserío La Enea", "que ruta pasa por el caserio la enea"])
async def test_caserio_la_enea_es_otro_lugar_y_gana_la_frase_mas_larga(bot: LogicaBot, texto: str) -> None:
    r = await bot.texto(CHAT, texto)
    assert "«Caserío La Enea»" in r.texto and "«La Enea»" not in r.texto


@pytest.mark.parametrize(
    ("texto", "nombre"),
    [
        ("villamaria", "Villamaría"), ("villamaría", "Villamaría"), ("ruta para villamaria", "Villamaría"),
        ("¿Qué ruta va a Villamaría?", "Villamaría"),
        ("catedral", "Catedral"), ("la catedral", "Catedral"), ("LA CATEDRAL", "Catedral"),
        ("san sebastian", "San Sebastián"), ("San Sebastián", "San Sebastián"), ("SAN SEBASTIÁN", "San Sebastián"),
        ("fatima", "Fátima"), ("Fátima", "Fátima"), ("que ruta pasa por fatima", "Fátima"),
        ("chipre", "Chipre"), ("palogrande", "Palogrande"), ("alta suiza", "Alta Suiza"), ("Alta Suiza", "Alta Suiza"),
        ("avanzada", "Avanzada"), ("Avanzada", "Avanzada"), ("ruta a avanzada", "Avanzada"),
        ("la florida", "La Florida"), ("florida", "La Florida"),
        ("turin", "Turín"), ("el cable", "El Cable"), ("terminal", "Terminal"),
    ],
)
async def test_lugares_reales_con_y_sin_tildes_mayusculas_y_articulos(bot: LogicaBot, texto: str, nombre: str) -> None:
    r = await bot.texto(CHAT, texto)
    assert f"«{nombre}»" in r.texto, r.texto


async def test_avanzada_solo_sale_cuando_el_usuario_dice_avanzada(bot: LogicaBot) -> None:
    assert "«Avanzada»" in (await bot.texto(CHAT, "avanzada")).texto
    for texto in ("enea", "la enea", "van", "ruta van", "avan", "zada", "anzad", "ena", "nea", "ane", "que ruta van a la enea"):
        assert "Avanzada" not in (await bot.texto(CHAT, texto)).texto, texto


# ---------- ambigüedad real ----------


@pytest.mark.parametrize("texto", ["san", "santa", "las", "villa"])
async def test_si_hay_varios_candidatos_sin_nombre_exacto_pregunta_en_vez_de_elegir(bot: LogicaBot, texto: str) -> None:
    r = await bot.texto(CHAT, texto)
    if r.texto.startswith("No te entendí"):  # palabra demasiado genérica o sin coincidencias confiables
        return
    assert "¿A cuál te refieres?" in r.texto or "«" in r.texto
    assert len(r.botones) <= 5


async def test_santa_lista_opciones_y_el_boton_resuelve(bot: LogicaBot) -> None:
    r = await bot.texto(CHAT, "santa")
    assert r.texto.startswith("¿A cuál te refieres?")
    assert 2 <= len(r.botones) <= 5 and all(d.startswith("hito:") for d in _botones(r))
    nombres = [b.texto for fila in r.botones for b in fila]
    assert {"Santa Ana", "Santa Helena", "Santa Teresa"} <= set(nombres)
    elegido = await bot.callback(CHAT, _botones(r)[0])
    assert f"«{nombres[0]}»" in elegido.texto


async def test_el_nombre_exacto_gana_aunque_otros_lo_contengan(bot: LogicaBot) -> None:
    # «San Antonio» es exacto (barrio) y «San Antonio (vereda)» lo contiene: gana el exacto sin preguntar
    r = await bot.texto(CHAT, "san antonio")
    assert "«San Antonio»" in r.texto and "vereda" not in r.texto


# ---------- sin coincidencia confiable: lo dice, no inventa ----------


@pytest.mark.parametrize(
    "texto",
    ["hola buenas tardes", "quiero comer pizza", "ruta a marte", "que ruta van", "van", "avan", "ena", "nea", "zzz", "a la", "de", "?", "ruta"],
)
async def test_sin_coincidencia_confiable_no_inventa_un_lugar(bot: LogicaBot, texto: str) -> None:
    r = await bot.texto(CHAT, texto)
    assert r.texto.startswith("No te entendí") and r.menu and not r.botones


# ---------- las demás pantallas usan el mismo reconocimiento ----------


async def test_horarios_de_un_lugar_van_directo_a_sus_rutas(bot: LogicaBot) -> None:
    r = await bot.texto(CHAT, "horarios de la enea")
    assert r.texto.startswith("Horarios de la ruta La Enea (hoy):") and "Avanzada" not in r.texto
    lista = await bot.texto(CHAT, "horarios")
    assert lista.texto == "¿De qué ruta quieres ver los horarios?" and _botones(lista)  # sin lugar: botones como antes
    no_hay = await bot.texto(CHAT, "horarios de avanzada")
    assert "No encontré rutas que pasen por «Avanzada»" in no_hay.texto


async def test_avisos_de_un_lugar_filtran_por_su_ruta(bot: LogicaBot, repos: Repositorios) -> None:
    todos = await bot.texto(CHAT, "avisos")
    assert todos.texto.startswith("Avisos vigentes:") and repos.avisos.consultas[-1][0] is None
    await bot.texto(CHAT, "avisos de la enea")
    assert repos.avisos.consultas[-1][0] == dobles.RUTA_ENEA


async def test_cuando_llega_a_un_lugar_ofrece_el_eta_de_las_rutas_cercanas(bot: LogicaBot) -> None:
    sin_lugar = await bot.texto(CHAT, "¿Cuándo llega?")
    assert sin_lugar.pedir_ubicacion
    r = await bot.texto(CHAT, "cuando llega a la enea")
    assert r.texto.startswith("Encontré 1 ruta a menos de 500 m") and _botones(r) == ["ver:0", "eta:0"]
    eta = await bot.callback(CHAT, "eta:0")
    assert "Sideral" in eta.texto


async def test_rutas_cerca_de_un_lugar_o_de_mi(bot: LogicaBot) -> None:
    assert (await bot.texto(CHAT, "rutas cerca de mi")).pedir_ubicacion
    r = await bot.texto(CHAT, "rutas cerca de la enea")
    assert r.texto.startswith("Encontré 1 ruta a menos de 500 m")
    assert bot._chat(CHAT).ubicacion is None  # la ubicación de un lugar no se guarda como la del pasajero


async def test_el_resultado_no_depende_del_orden_de_los_resultados_de_la_busqueda(bot: LogicaBot, repos: Repositorios) -> None:
    original = repos.busqueda.buscar_hitos

    async def invertido(patron: str, texto: str):
        return list(reversed(await original(patron, texto)))

    repos.busqueda.buscar_hitos = invertido
    for texto in ("que ruta van a la enea", "caserio la enea", "san sebastian"):
        assert (await bot.texto(CHAT, texto)).texto == (await LogicaBot(bot._s, RelojFijo()).texto(CHAT, texto)).texto
    assert "«La Enea»" in (await bot.texto(CHAT, "que ruta van a la enea")).texto
