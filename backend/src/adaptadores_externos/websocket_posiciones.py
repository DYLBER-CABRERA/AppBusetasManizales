"""WebSockets de posiciones y notificaciones (contrato §4).

`/ws/rutas/{rutaId}` (público): difunde `{"tipo":"posiciones", ...}` cuando el simulador o la ingesta aceptan posiciones.
Una sola instancia (no escala horizontalmente). Un cliente lento o caído no bloquea el ciclo de posiciones: la difusión
corre en su propia tarea, con tiempo de espera por cliente, y las conexiones caídas se limpian.

PENDIENTE(B3b → B4/B6): `senal_perdida` (detector de señal), `aviso_nuevo` (al publicar avisos, B4) y
`/ws/notificaciones` con token (`alerta_llegada` y `alerta_desvio`, B6). Hoy `/ws/notificaciones` solo responde ping/pong.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

registro = logging.getLogger("busetasapp.ws")

TIEMPO_ESPERA_ENVIO_S = 2.0
RETRASO_AGRUPACION_S = 0.2


class GestorConexiones:
    def __init__(self) -> None:
        self._por_ruta: dict[UUID, set[WebSocket]] = defaultdict(set)

    def conectar(self, ruta_id: UUID, ws: WebSocket) -> None:
        self._por_ruta[ruta_id].add(ws)

    def desconectar(self, ruta_id: UUID, ws: WebSocket) -> None:
        self._por_ruta[ruta_id].discard(ws)
        if not self._por_ruta[ruta_id]:
            del self._por_ruta[ruta_id]

    def hay_clientes(self, ruta_id: UUID) -> bool:
        return bool(self._por_ruta.get(ruta_id))

    def total(self) -> int:
        return sum(len(c) for c in self._por_ruta.values())

    async def difundir(self, ruta_id: UUID, mensaje: dict[str, Any]) -> None:
        clientes = list(self._por_ruta.get(ruta_id, ()))

        async def enviar(ws: WebSocket) -> None:
            try:
                await asyncio.wait_for(ws.send_json(mensaje), TIEMPO_ESPERA_ENVIO_S)
            except Exception:  # noqa: BLE001 - cliente caído o lento: se descarta
                self.desconectar(ruta_id, ws)

        await asyncio.gather(*(enviar(ws) for ws in clientes))


class DifusorPosiciones:
    """Suscriptor de `posicion.aceptada`: agrupa las posiciones de un mismo ciclo y difunde un mensaje por ruta."""

    def __init__(
        self,
        gestor: GestorConexiones,
        armar_mensaje: Callable[[UUID], Awaitable[dict[str, Any] | None]],
        retraso_s: float = RETRASO_AGRUPACION_S,
    ) -> None:
        self._gestor = gestor
        self._armar = armar_mensaje
        self._retraso = retraso_s
        self._pendientes: set[UUID] = set()
        self._tarea: asyncio.Task[None] | None = None

    async def al_aceptar_posicion(self, carga: dict[str, Any]) -> None:
        ruta_id = carga.get("ruta_id")
        if ruta_id is None or not self._gestor.hay_clientes(ruta_id):
            return
        self._pendientes.add(ruta_id)
        if self._tarea is None or self._tarea.done():
            self._tarea = asyncio.create_task(self._vaciar())

    async def _vaciar(self) -> None:
        await asyncio.sleep(self._retraso)
        rutas, self._pendientes = self._pendientes, set()
        for ruta_id in rutas:
            try:
                mensaje = await self._armar(ruta_id)
                if mensaje is not None:
                    await self._gestor.difundir(ruta_id, mensaje)
            except Exception as exc:  # noqa: BLE001
                registro.warning("No se pudo difundir la ruta (%s)", type(exc).__name__)


router = APIRouter()


async def _ping_pong(ws: WebSocket) -> None:
    while True:
        if (await ws.receive_text()) == "ping":
            await ws.send_text("pong")


@router.websocket("/ws/rutas/{ruta_id}")
async def ws_rutas(ws: WebSocket, ruta_id: UUID) -> None:
    contenedor = ws.app.state.contenedor
    await ws.accept()
    gestor: GestorConexiones = contenedor.gestor_ws
    gestor.conectar(ruta_id, ws)
    try:
        if contenedor.armar_mensaje_posiciones is not None:  # foto inicial para no esperar al siguiente ciclo
            try:
                inicial = await contenedor.armar_mensaje_posiciones(ruta_id)
                if inicial is not None:
                    await ws.send_json(inicial)
            except Exception as exc:  # noqa: BLE001 - sin BD el socket sigue sirviendo ping/pong
                registro.warning("Sin foto inicial de posiciones (%s)", type(exc).__name__)
        await _ping_pong(ws)
    except WebSocketDisconnect:
        pass
    finally:
        gestor.desconectar(ruta_id, ws)


@router.websocket("/ws/notificaciones")
async def ws_notificaciones(ws: WebSocket) -> None:
    await ws.accept()
    try:
        await _ping_pong(ws)
    except WebSocketDisconnect:
        return
