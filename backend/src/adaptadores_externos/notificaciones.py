"""Notificador de alertas: WebSocket `/ws/notificaciones` (app abierta) y Telegram (bot, B7)."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from adaptadores_externos.websocket_posiciones import GestorConexiones
from nucleo.notificador import DestinoAlerta

registro = logging.getLogger("busetasapp.notificaciones")
EnviarTelegram = Callable[[int, str], Awaitable[None]]


class NotificadorCompuesto:
    """Enruta según el destino. `enviar_telegram` lo asigna el bot al arrancar; sin bot, el aviso por chat se omite."""

    def __init__(self, gestor: GestorConexiones) -> None:
        self._gestor = gestor
        self.enviar_telegram: EnviarTelegram | None = None

    async def notificar_alerta(self, destino: DestinoAlerta, mensaje: str, datos: dict[str, Any]) -> None:
        if destino.usuario_id is not None:
            await self._gestor.difundir_usuario(destino.usuario_id, datos)
        elif destino.telegram_chat_id is not None:
            if self.enviar_telegram is None:
                registro.info("Alerta para un chat de Telegram omitida: el bot no está activo")
                return
            prefijo = "⚠️ " if datos.get("tipo") == "alerta_desvio" else ""
            await self.enviar_telegram(destino.telegram_chat_id, prefijo + mensaje)
