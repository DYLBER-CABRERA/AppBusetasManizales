"""WebSockets de posiciones y notificaciones (contrato §4). B0: aceptan la conexión y responden ping/pong.

PENDIENTE(B3): gestor de conexiones por ruta y por usuario, difusión de `posiciones`, `senal_perdida`,
`aviso_nuevo`, `alerta_llegada` y `alerta_desvio`. El token de /ws/notificaciones nunca se registra en logs.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


async def _ping_pong(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            if (await ws.receive_text()) == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        return


@router.websocket("/ws/rutas/{ruta_id}")
async def ws_rutas(ws: WebSocket, ruta_id: UUID) -> None:
    await _ping_pong(ws)


@router.websocket("/ws/notificaciones")
async def ws_notificaciones(ws: WebSocket) -> None:
    await _ping_pong(ws)
