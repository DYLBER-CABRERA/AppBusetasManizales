"""PuertoNotificador: avisa a quien creó una alerta (app abierta por WebSocket o chat de Telegram)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True)
class DestinoAlerta:
    """Exactamente uno de los dos (D-P08): `usuario_id` (app) o `telegram_chat_id` (bot)."""

    usuario_id: UUID | None = None
    telegram_chat_id: int | None = None


class PuertoNotificador(Protocol):
    async def notificar_alerta(self, destino: DestinoAlerta, mensaje: str, datos: dict[str, Any]) -> None:
        """`datos` es el mensaje WebSocket completo del contrato (§4); `mensaje` es el texto para el chat."""
        ...
