"""Bot de Telegram (modo polling). SOLO llama a casos de uso (nunca a SQL). Sin LLM: palabras clave sin tildes.

Dos capas: `LogicaBot` (conversación pura: recibe texto, ubicación o *callback* y devuelve `Respuesta`) y `BotTelegram`
(adaptador con python-telegram-bot). Privacidad: la ubicación vive solo en memoria del chat (≤ 10 min) y nunca se guarda
ni se registra; tampoco se registran los textos ni los identificadores de chat.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from modulos.busqueda import normalizar_consulta
from nucleo.errores import ErrorAplicacion, ErrorConflictoNegocio
from nucleo.notificador import DestinoAlerta
from nucleo.reloj import PuertoReloj

registro = logging.getLogger("busetasapp.bot")

RADIO_M = 500
VIGENCIA_UBICACION = timedelta(minutes=10)
AVISO_EJEMPLO = "Datos de ejemplo · no son rutas oficiales."
PALABRAS_VACIAS = {
    "que", "ruta", "rutas", "va", "voy", "para", "por", "pasa", "pasan", "hacia", "a", "al", "el", "la", "los", "las", "de", "del",
    "en", "un", "una", "me", "sirve", "sirven", "como", "llego", "cual", "cuales", "donde", "hay", "quiero", "ir", "bus", "buseta",
}


@dataclass(frozen=True)
class Boton:
    texto: str
    datos: str  # callback_data (≤ 64 bytes)


@dataclass
class Respuesta:
    texto: str
    botones: list[list[Boton]] = field(default_factory=list)
    pedir_ubicacion: bool = False
    menu: bool = False


@dataclass
class _Chat:
    ubicacion: tuple[float, float] | None = None
    desde: datetime | None = None
    pares: list[tuple[UUID, UUID, str]] = field(default_factory=list)  # (ruta, paradero, nombre de la ruta)


def _minutos(segundos: int) -> str:
    return "menos de 1 min" if segundos < 60 else f"{math.ceil(segundos / 60)} min"


class LogicaBot:
    def __init__(self, servicios: Any, reloj: PuertoReloj) -> None:
        self._s = servicios
        self._reloj = reloj
        self._chats: dict[int, _Chat] = {}

    # ---------- estado en memoria ----------

    def _chat(self, chat_id: int) -> _Chat:
        return self._chats.setdefault(chat_id, _Chat())

    def _ubicacion(self, chat_id: int) -> tuple[float, float] | None:
        chat = self._chat(chat_id)
        if chat.ubicacion is None or chat.desde is None:
            return None
        if self._reloj.ahora() - chat.desde > VIGENCIA_UBICACION:
            chat.ubicacion = chat.desde = None  # vencida: se olvida
            return None
        return chat.ubicacion

    # ---------- entradas ----------

    async def inicio(self, chat_id: int) -> Respuesta:
        return Respuesta(
            "¡Hola! Soy el asistente de BusetasApp.\n"
            "Te ayudo con las rutas de buses de Manizales: qué ruta te sirve, cada cuánto sale y cuándo llega.\n"
            f"{AVISO_EJEMPLO}\n\n"
            "¿Qué quieres hacer?\n"
            "También puedes escribirme tu pregunta, por ejemplo: «¿Qué ruta va a Villamaría?»",
            menu=True,
        )

    def ayuda(self) -> Respuesta:
        return Respuesta(
            "BusetasApp te dice qué rutas pasan cerca, a qué hora salen y cuándo llega la próxima buseta.\n\n"
            "Cómo usarme:\n"
            "• «Rutas cerca de mí»: comparte tu ubicación (no la guardo) y te muestro las rutas a menos de 500 m.\n"
            "• «¿Cuándo llega?»: te digo en cuántos minutos llega la buseta a tu paradero.\n"
            "• «Avisarme cuando esté cerca»: te escribo cuando la buseta esté a 300 m.\n"
            "• «Horarios» y «Avisos»: consulta por ruta o los avisos vigentes.\n"
            "• También entiendo preguntas como «¿Qué ruta va a Villamaría?».\n\n"
            f"{AVISO_EJEMPLO} Las rutas, horarios y posiciones son simulados.\n\n"
            "Los roles de la plataforma: pasajero (consulta, favoritos y alertas), jefe de operaciones (rodamientos y horarios "
            "de su empresa), Secretaría de Movilidad (rutas, paraderos y cambios de ciudad) y administrador (control total).",
            menu=True,
        )

    async def texto(self, chat_id: int, texto: str) -> Respuesta:
        normal = normalizar_consulta(texto)
        if normal in ("/start", "start", "hola", "menu", "inicio"):
            return await self.inicio(chat_id)
        if "ayuda" in normal or "como funciona" in normal:
            return self.ayuda()
        if "rutas cerca" in normal or normal == "cerca de mi":
            return self._pedir_ubicacion()
        if "cuando llega" in normal:
            return await self.cuando_llega(chat_id)
        if "horario" in normal:
            return await self.elegir_ruta("horarios", "¿De qué ruta quieres ver los horarios?")
        if "aviso" in normal:
            return await self.avisos()
        return await self._buscar_en_texto(normal)

    async def ubicacion(self, chat_id: int, lat: float, lng: float) -> Respuesta:
        chat = self._chat(chat_id)
        chat.ubicacion, chat.desde = (lat, lng), self._reloj.ahora()
        return await self._rutas_cerca(chat_id, lat, lng)

    async def callback(self, chat_id: int, datos: str) -> Respuesta:
        accion, _, resto = datos.partition(":")
        try:
            if accion == "ruta":
                return await self._ver_ruta(UUID(resto))
            if accion == "horarios":
                return await self._horarios(UUID(resto))
            if accion == "eta":
                return await self._eta(chat_id, int(resto))
            if accion == "alerta":
                return await self._alerta(chat_id, int(resto))
            if accion == "ver":
                return await self._ver_ruta(self._par(chat_id, int(resto))[0])
        except (ValueError, IndexError):
            return Respuesta("Esa opción ya venció. Vuelve a compartir tu ubicación.", menu=True)
        except ErrorAplicacion as exc:
            return Respuesta(exc.mensaje, menu=True)
        return Respuesta("No entendí esa opción.", menu=True)

    # ---------- flujos ----------

    @staticmethod
    def _pedir_ubicacion() -> Respuesta:
        return Respuesta("Compárteme tu ubicación para buscar. No la guardo.", pedir_ubicacion=True)

    def _par(self, chat_id: int, indice: int) -> tuple[UUID, UUID, str]:
        return self._chat(chat_id).pares[indice]

    async def _rutas_cerca(self, chat_id: int, lat: float, lng: float) -> Respuesta:
        cercanas = await self._s.consultar_rutas_cercanas(lat, lng, RADIO_M)
        rutas = cercanas["rutas"]
        chat = self._chat(chat_id)
        chat.pares = []
        if not rutas:
            texto = f"No encontré rutas a menos de {RADIO_M} m."
            cercano = cercanas["paradero_mas_cercano"]
            if cercano:
                texto += f" El paradero más cercano es «{cercano['nombre']}», a {round(cercano['distancia_m'])} m."
            return Respuesta(texto, menu=True)
        lineas, botones = [f"Encontré {len(rutas)} {'ruta' if len(rutas) == 1 else 'rutas'} a menos de {RADIO_M} m:"], []
        for ruta in rutas:
            paraderos = await self._s.consultar_paraderos_cercanos(lat, lng, RADIO_M, ruta["id"])
            if not paraderos:
                continue
            indice = len(chat.pares)
            chat.pares.append((ruta["id"], paraderos[0]["paradero_id"], ruta["nombre"]))
            lineas.append(f"Ruta {ruta['nombre']} · paradero a {round(paraderos[0]['distancia_m'])} m")
            botones.append([Boton(f"Ver ruta {ruta['nombre']}", f"ver:{indice}"), Boton("¿Cuándo llega?", f"eta:{indice}")])
        return Respuesta("\n".join(lineas), botones)

    async def cuando_llega(self, chat_id: int) -> Respuesta:
        punto = self._ubicacion(chat_id)
        if punto is None:
            return Respuesta("Para saber cuándo llega, primero compárteme tu ubicación. No la guardo.", pedir_ubicacion=True)
        return await self._rutas_cerca(chat_id, *punto)

    async def _ver_ruta(self, ruta_id: UUID) -> Respuesta:
        d = await self._s.obtener_detalle_ruta(ruta_id)
        empresas = ", ".join(f"{s['empresa_nombre']}{' ' + s['codigo_publico'] if s['codigo_publico'] else ''}" for s in d["servicios"])
        paradas = " → ".join(p["nombre"] for p in d["paraderos"][:6])
        mas = " → …" if len(d["paraderos"]) > 6 else ""
        return Respuesta(f"Ruta {d['nombre']} (circular)\nEmpresas: {empresas or 'sin servicio asignado'}\nParadas: {paradas}{mas}\n{AVISO_EJEMPLO}", menu=True)

    async def _eta(self, chat_id: int, indice: int) -> Respuesta:
        ruta_id, paradero_id, nombre = self._par(chat_id, indice)
        eta = await self._s.calcular_eta_paradero(paradero_id, ruta_id)
        lineas = [f"Ruta {nombre}"]
        for r in eta["resultados"]:
            empresa = r["empresa"]
            if r["fuente"] == "gps":
                lineas.append(
                    f"{empresa}: próxima buseta en {_minutos(r['eta_segundos'])} · Según el GPS · actualizado hace {r['ultima_senal_hace_s']} s"
                )
            elif r["fuente"] == "horario":
                cada = math.ceil(r["rango"]["max_segundos"] / 60)
                lineas.append(
                    f"⚠️ {empresa}: Sin señal GPS en este momento. Te doy un estimado por horario: sale cada {cada} min aprox. "
                    "(estimado por horario, no es una posición en vivo)"
                )
            else:
                lineas.append(f"{empresa}: {r['mensaje']}")
        return Respuesta("\n".join(lineas), [[Boton("Avisarme cuando esté cerca", f"alerta:{indice}")]])

    async def _alerta(self, chat_id: int, indice: int) -> Respuesta:
        ruta_id, paradero_id, nombre = self._par(chat_id, indice)
        try:
            alerta = await self._s.crear_alerta_llegada.para_destino(DestinoAlerta(telegram_chat_id=chat_id), ruta_id, paradero_id, None)
        except ErrorConflictoNegocio:
            return Respuesta("Ya tenías una alerta activa para ese paradero. Te aviso cuando la buseta esté cerca.", menu=True)
        return Respuesta(f"Listo, te aviso cuando la {nombre} esté a {alerta['distancia_aviso_m']} m de tu paradero.", menu=True)

    async def elegir_ruta(self, accion: str, pregunta: str) -> Respuesta:
        rutas = await self._s.listar_rutas()
        return Respuesta(pregunta, [[Boton(r["nombre"], f"{accion}:{r['id']}")] for r in rutas])

    async def _horarios(self, ruta_id: UUID) -> Respuesta:
        d = await self._s.consultar_horarios(ruta_id)
        ruta = await self._s.obtener_detalle_ruta(ruta_id)
        lineas = [f"Horarios de la ruta {ruta['nombre']} (hoy):"]
        for s in d["servicios"]:
            hoy = next((h for h in s["horarios"] if h["tipo_dia"] == d["tipo_dia_hoy"]), None)
            etiqueta = f"{s['empresa_nombre']}{' ' + s['codigo_publico'] if s['codigo_publico'] else ''}"
            if hoy is None:
                lineas.append(f"{etiqueta}: Información pendiente de actualización.")
            else:
                cierre = f", cierre {hoy['cierre']}" if hoy["cierre"] else ""
                lineas.append(f"{etiqueta}: primera salida {hoy['primera_salida']}, última {hoy['ultima_salida']}{cierre}")
        return Respuesta("\n".join(lineas), menu=True)

    async def avisos(self) -> Respuesta:
        avisos = await self._s.consultar_avisos_vigentes(None)
        if not avisos:
            return Respuesta("No hay avisos vigentes.", menu=True)
        return Respuesta("Avisos vigentes:\n" + "\n".join(f"• {a['titulo']}: {a['cuerpo']}" for a in avisos[:5]), menu=True)

    async def _buscar_en_texto(self, normal: str) -> Respuesta:
        palabras = [p for p in normal.replace("?", " ").replace("¿", " ").split() if p not in PALABRAS_VACIAS and len(p) >= 3]
        candidatos = [" ".join(palabras), *palabras] if len(palabras) > 1 else palabras
        for consulta in candidatos:
            hitos = await self._s.buscar_hitos(consulta)
            if hitos:
                d = await self._s.consultar_rutas_por_hito(hitos[0]["id"])
                if d["rutas"]:
                    nombres = ", ".join(f"Ruta {r['nombre']}" for r in d["rutas"])
                    return Respuesta(f"Cerca de «{hitos[0]['nombre']}» pasa: {nombres}.", self._botones_ruta(d["rutas"]))
                cercano = d["paradero_mas_cercano"]
                extra = f" El paradero más cercano es «{cercano['nombre']}»." if cercano else ""
                return Respuesta(f"No encontré rutas que pasen por «{hitos[0]['nombre']}».{extra}", menu=True)
            rutas = await self._s.buscar_rutas_por_texto(consulta)
            if rutas:
                return Respuesta("Encontré: " + ", ".join(f"Ruta {r['nombre']}" for r in rutas) + ".", self._botones_ruta(rutas))
        return Respuesta("No te entendí. Elige una opción del menú o escribe, por ejemplo: «¿Qué ruta va a Villamaría?».", menu=True)

    @staticmethod
    def _botones_ruta(rutas: list[dict[str, Any]]) -> list[list[Boton]]:
        return [[Boton(f"Ver ruta {r['nombre']}", f"ruta:{r['id']}")] for r in rutas[:5]]


# ----------------------------------------------------------------------------------------------------------------------
# Adaptador con python-telegram-bot
# ----------------------------------------------------------------------------------------------------------------------

MENU = [["Rutas cerca de mí", "¿Cuándo llega?"], ["Horarios", "Avisos"], ["Ayuda"]]


class BotTelegram:
    def __init__(self, token: str, logica: LogicaBot) -> None:
        from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

        self._logica = logica
        self.aplicacion = Application.builder().token(token).build()
        self.aplicacion.add_handler(CommandHandler("start", self._al_iniciar))
        self.aplicacion.add_handler(CommandHandler("ayuda", self._al_pedir_ayuda))
        self.aplicacion.add_handler(MessageHandler(filters.LOCATION, self._al_recibir_ubicacion))
        self.aplicacion.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._al_recibir_texto))
        self.aplicacion.add_handler(CallbackQueryHandler(self._al_pulsar_boton))

    # --- ciclo de vida ---
    async def iniciar(self) -> None:
        await self.aplicacion.initialize()
        await self.aplicacion.start()
        await self.aplicacion.updater.start_polling()  # type: ignore[union-attr]

    async def detener(self) -> None:
        if self.aplicacion.updater and self.aplicacion.updater.running:
            await self.aplicacion.updater.stop()
        if self.aplicacion.running:
            await self.aplicacion.stop()
        await self.aplicacion.shutdown()

    async def enviar(self, chat_id: int, texto: str) -> None:
        """Usado por el notificador: el bot escribe primero cuando la buseta está cerca o se desvía."""
        await self.aplicacion.bot.send_message(chat_id=chat_id, text=texto)

    # --- traducción Respuesta → Telegram ---
    async def _responder(self, mensaje: Any, r: Respuesta) -> None:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

        teclado: Any = None
        if r.pedir_ubicacion:
            teclado = ReplyKeyboardMarkup(
                [[KeyboardButton("Compartir mi ubicación", request_location=True)]], resize_keyboard=True, one_time_keyboard=True
            )
        elif r.botones:
            teclado = InlineKeyboardMarkup([[InlineKeyboardButton(b.texto, callback_data=b.datos) for b in fila] for fila in r.botones])
        elif r.menu:
            teclado = ReplyKeyboardMarkup(MENU, resize_keyboard=True)
        await mensaje.reply_text(r.texto, reply_markup=teclado)

    async def _ejecutar(self, mensaje: Any, corrutina: Any) -> None:
        try:
            respuesta = await corrutina
        except Exception as exc:  # noqa: BLE001 - el bot no debe caerse por una consulta fallida
            registro.warning("Falló una consulta del bot (%s)", type(exc).__name__)
            respuesta = Respuesta("Ahora no puedo consultar la información. Intenta de nuevo en un momento.", menu=True)
        await self._responder(mensaje, respuesta)

    async def _al_iniciar(self, update: Any, _: Any) -> None:
        await self._ejecutar(update.message, self._logica.inicio(update.effective_chat.id))

    async def _al_pedir_ayuda(self, update: Any, _: Any) -> None:
        await self._responder(update.message, self._logica.ayuda())

    async def _al_recibir_texto(self, update: Any, _: Any) -> None:
        await self._ejecutar(update.message, self._logica.texto(update.effective_chat.id, update.message.text or ""))

    async def _al_recibir_ubicacion(self, update: Any, _: Any) -> None:
        punto = update.message.location
        await self._ejecutar(update.message, self._logica.ubicacion(update.effective_chat.id, punto.latitude, punto.longitude))

    async def _al_pulsar_boton(self, update: Any, _: Any) -> None:
        consulta = update.callback_query
        await consulta.answer()
        await self._ejecutar(consulta.message, self._logica.callback(update.effective_chat.id, consulta.data or ""))
