"""B7: bot de Telegram. La conversación (LogicaBot) se prueba sin red; el adaptador solo se construye (sin polling)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from adaptadores_externos.bot_telegram import BotTelegram, LogicaBot, Respuesta
from composicion import Contenedor, Repositorios, construir_contenedor
from nucleo.configuracion import Configuracion
from nucleo.reloj import RelojSimulado
from pruebas import dobles
from pruebas.dobles import LUNES_MEDIODIA, RelojFijo

CHAT = 4242
LAT, LNG = 5.07, -75.51


@pytest.fixture
def repos() -> Repositorios:
    return dobles.repositorios_en_memoria()


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo()


@pytest.fixture
def contenedor(repos: Repositorios, reloj: RelojFijo) -> Contenedor:
    return construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(reloj))


@pytest.fixture
def bot(contenedor: Contenedor, reloj: RelojFijo) -> LogicaBot:
    return LogicaBot(contenedor.servicios, reloj)


def _botones(r: Respuesta) -> list[str]:
    return [b.datos for fila in r.botones for b in fila]


async def test_start_saluda_con_menu_y_aviso_de_datos_de_ejemplo(bot: LogicaBot) -> None:
    r = await bot.inicio(CHAT)
    assert r.menu and "Datos de ejemplo" in r.texto and "¿Qué ruta va a Villamaría?" in r.texto


async def test_ayuda_explica_el_bot_los_datos_de_ejemplo_y_los_4_roles(bot: LogicaBot) -> None:
    r = bot.ayuda()
    for fragmento in ("Datos de ejemplo", "pasajero", "jefe de operaciones", "Secretaría de Movilidad", "administrador", "no la guardo"):
        assert fragmento in r.texto
    assert (await bot.texto(CHAT, "ayuda")).texto == r.texto
    assert (await bot.texto(CHAT, "¿Cómo funciona?")).texto == r.texto


async def test_rutas_cerca_pide_ubicacion_y_luego_lista_las_rutas(bot: LogicaBot) -> None:
    pedir = await bot.texto(CHAT, "Rutas cerca de mí")
    assert pedir.pedir_ubicacion and "No la guardo" in pedir.texto
    r = await bot.ubicacion(CHAT, LAT, LNG)
    assert r.texto == "Encontré 1 ruta a menos de 500 m:\nRuta La Enea · paradero a 120 m"
    assert _botones(r) == ["ver:0", "eta:0"]


async def test_sin_rutas_cerca_ofrece_el_paradero_mas_cercano(bot: LogicaBot) -> None:
    r = await bot.ubicacion(CHAT, 7.0, LNG)
    assert "No encontré rutas a menos de 500 m" in r.texto and "Parada A" in r.texto


async def test_cuando_llega_sin_ubicacion_la_pide(bot: LogicaBot) -> None:
    assert (await bot.texto(CHAT, "¿Cuándo llega?")).pedir_ubicacion


async def test_cuando_llega_con_gps(bot: LogicaBot, contenedor: Contenedor) -> None:
    from modulos.seguimiento import PosicionEntrante

    await bot.ubicacion(CHAT, LAT, LNG)
    await contenedor.servicios.registrar_posiciones(
        dobles.EMPRESA_SIDERAL, [PosicionEntrante("1544", LAT, LNG, LUNES_MEDIODIA, velocidad_kmh=20.0)]
    )
    r = await bot.callback(CHAT, "eta:0")
    assert "Sideral: próxima buseta en 3 min · Según el GPS · actualizado hace 0 s" in r.texto
    assert _botones(r) == ["alerta:0"]


async def test_cuando_llega_sin_gps_da_estimado_por_horario(bot: LogicaBot) -> None:
    await bot.ubicacion(CHAT, LAT, LNG)
    r = await bot.callback(CHAT, "eta:0")
    assert "⚠️ Sideral: Sin señal GPS en este momento. Te doy un estimado por horario: sale cada 10 min aprox." in r.texto
    assert "Serviturismo: Información pendiente de actualización." in r.texto


async def test_avisarme_crea_alerta_con_el_chat_id_y_no_duplica(bot: LogicaBot, repos: Repositorios) -> None:
    await bot.ubicacion(CHAT, LAT, LNG)
    r = await bot.callback(CHAT, "alerta:0")
    assert r.texto == "Listo, te aviso cuando la La Enea esté a 300 m de tu paradero."
    [alerta] = repos.alertas.filas.values()
    assert alerta["telegram_chat_id"] == CHAT and alerta["usuario_id"] is None
    assert "Ya tenías una alerta activa" in (await bot.callback(CHAT, "alerta:0")).texto


async def test_la_ubicacion_vence_a_los_10_minutos(bot: LogicaBot, reloj: RelojFijo) -> None:
    await bot.ubicacion(CHAT, LAT, LNG)
    reloj.fijar(LUNES_MEDIODIA + timedelta(minutes=9))
    assert not (await bot.cuando_llega(CHAT)).pedir_ubicacion
    reloj.fijar(LUNES_MEDIODIA + timedelta(minutes=11))
    assert (await bot.cuando_llega(CHAT)).pedir_ubicacion
    assert bot._chats[CHAT].ubicacion is None  # se olvidó


async def test_boton_vencido_se_explica(bot: LogicaBot) -> None:
    assert "venció" in (await bot.callback(CHAT, "eta:7")).texto
    assert "venció" in (await bot.callback(CHAT, "eta:xx")).texto
    assert "No entendí" in (await bot.callback(CHAT, "otra:1")).texto


async def test_horarios_por_ruta(bot: LogicaBot) -> None:
    r = await bot.texto(CHAT, "Horarios")
    assert _botones(r) == [f"horarios:{dobles.RUTA_ENEA}", f"horarios:{dobles.RUTA_VILLAMARIA}"]
    detalle = await bot.callback(CHAT, r.botones[0][0].datos)
    assert detalle.texto.startswith("Horarios de la ruta La Enea (hoy):")
    assert "Sideral 39: primera salida 05:30, última 21:00, cierre 22:00" in detalle.texto
    assert "Serviturismo: Información pendiente de actualización." in detalle.texto


async def test_avisos_vigentes(bot: LogicaBot) -> None:
    assert (await bot.texto(CHAT, "Avisos")).texto == "Avisos vigentes:\n• Obra en la Avenida: Desvío temporal."


async def test_texto_libre_por_hito_y_por_nombre_sin_tildes(bot: LogicaBot) -> None:
    r = await bot.texto(CHAT, "¿Qué ruta va al Cable?")
    assert r.texto == "Cerca de «Cable Aéreo» pasa: Ruta La Enea." and _botones(r) == [f"ruta:{dobles.RUTA_ENEA}"]
    por_ruta = await bot.texto(CHAT, "enéa")
    assert por_ruta.texto.startswith("Encontré: Ruta La Enea")
    detalle = await bot.callback(CHAT, f"ruta:{dobles.RUTA_ENEA}")
    assert "Ruta La Enea (circular)" in detalle.texto and "Sideral 39, Serviturismo" in detalle.texto


async def test_hito_sin_cobertura_y_texto_sin_coincidencia(bot: LogicaBot) -> None:
    lejos = await bot.texto(CHAT, "¿Qué ruta pasa por Vereda Lejana?")
    assert "No encontré rutas que pasen por «Vereda Lejana»" in lejos.texto and "Parada A" in lejos.texto
    nada = await bot.texto(CHAT, "blablabla")
    assert nada.menu and "No te entendí" in nada.texto


async def test_error_de_negocio_en_un_boton_se_muestra_al_usuario(bot: LogicaBot) -> None:
    r = await bot.callback(CHAT, f"horarios:{dobles.uuid4()}")
    assert "no existe" in r.texto


# ---------- adaptador ----------


async def test_el_adaptador_traduce_respuestas_a_teclados_de_telegram(bot: LogicaBot) -> None:
    from telegram import InlineKeyboardMarkup, ReplyKeyboardMarkup

    enviados: list = []

    class Mensaje:
        async def reply_text(self, texto: str, reply_markup=None) -> None:
            enviados.append((texto, reply_markup))

    adaptador = BotTelegram("123456:token-de-prueba", bot)
    assert len(adaptador.aplicacion.handlers[0]) == 5
    await adaptador._responder(Mensaje(), Respuesta("menu", menu=True))
    await adaptador._responder(Mensaje(), await bot.ubicacion(CHAT, LAT, LNG))
    await adaptador._responder(Mensaje(), Respuesta("ubicación", pedir_ubicacion=True))
    assert isinstance(enviados[0][1], ReplyKeyboardMarkup) and enviados[0][1].keyboard[0][0].text == "Rutas cerca de mí"
    assert isinstance(enviados[1][1], InlineKeyboardMarkup)
    assert enviados[2][1].keyboard[0][0].request_location is True
    callbacks = [b.callback_data for fila in enviados[1][1].inline_keyboard for b in fila]
    assert all(len(c.encode()) <= 64 for c in callbacks)  # límite de Telegram


async def test_una_consulta_fallida_no_tumba_el_bot(bot: LogicaBot, repos: Repositorios) -> None:
    enviados: list = []

    class Mensaje:
        async def reply_text(self, texto: str, reply_markup=None) -> None:
            enviados.append(texto)

    async def falla(*_a, **_k):
        raise RuntimeError("BD caída")

    repos.rutas.rutas_cercanas = falla
    adaptador = BotTelegram("123456:token-de-prueba", bot)
    await adaptador._ejecutar(Mensaje(), bot.ubicacion(CHAT, LAT, LNG))
    assert enviados == ["Ahora no puedo consultar la información. Intenta de nuevo en un momento."]


def test_con_token_la_composicion_arma_el_bot_y_conecta_el_notificador(repos: Repositorios, reloj: RelojFijo) -> None:
    config = Configuracion(_env_file=None, modo_demo=False, telegram_bot_token="123456:token-de-prueba")
    cont = construir_contenedor(config, repos, RelojSimulado(reloj))
    assert cont.bot is not None and cont.notificador.enviar_telegram == cont.bot.enviar
    sin_token = construir_contenedor(Configuracion(_env_file=None, modo_demo=False), repos, RelojSimulado(reloj))
    assert sin_token.bot is None


async def test_el_desvio_por_telegram_lleva_el_aviso_primero(contenedor: Contenedor) -> None:
    from nucleo.notificador import DestinoAlerta

    mensajes: list = []

    async def enviar(chat: int, texto: str) -> None:
        mensajes.append((chat, texto))

    contenedor.notificador.enviar_telegram = enviar
    destino = DestinoAlerta(telegram_chat_id=CHAT)
    await contenedor.notificador.notificar_alerta(destino, "La buseta 1544 se desvió de su recorrido. Tu llegada puede cambiar.", {"tipo": "alerta_desvio"})
    await contenedor.notificador.notificar_alerta(destino, "La buseta 1544 está a 200 m de tu paradero.", {"tipo": "alerta_llegada"})
    assert mensajes[0][1].startswith("⚠️ La buseta 1544 se desvió") and not mensajes[1][1].startswith("⚠️")
