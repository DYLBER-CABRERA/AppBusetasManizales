"""Crea la app FastAPI: routers, errores con formato del contrato, X-Id-Peticion y CORS."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from psycopg import OperationalError as ErrorOperacionalBd
from psycopg_pool import PoolTimeout
from starlette.exceptions import HTTPException as ErrorHttpStarlette

from adaptadores_externos.websocket_posiciones import router as router_ws
from composicion import Contenedor, construir_contenedor
from modulos.administracion import router as router_administracion
from modulos.avisos import router as router_avisos
from modulos.busqueda import router as router_busqueda
from modulos.estadisticas import router as router_estadisticas
from modulos.horarios import router as router_horarios
from modulos.operacion import router as router_operacion
from modulos.pasajero import router as router_pasajero
from modulos.planificacion import router as router_planificacion
from modulos.red import router as router_red
from modulos.seguimiento import router as router_seguimiento
from nucleo.errores import ErrorAplicacion
from nucleo.esquemas import EsquemaBase, errores
from nucleo.registro import configurar_registro

PREFIJO_API = "/api/v1"


def fabrica_bucle() -> asyncio.AbstractEventLoop:
    """Bucle de eventos compatible con psycopg asíncrono (en Windows uvicorn usa Proactor, que psycopg no admite).

    Uso: `uvicorn servidor:app --app-dir src --loop servidor:fabrica_bucle`.
    """
    return asyncio.SelectorEventLoop()


registro = logging.getLogger("busetasapp")


class EstadoSalud(EsquemaBase):
    estado: Literal["ok"]


router_sistema = APIRouter(tags=["Sistema"])


@router_sistema.get("/salud", response_model=EstadoSalud)
async def consultar_salud() -> EstadoSalud:
    """Sin consultar la BD."""
    return EstadoSalud(estado="ok")


def _cuerpo_error(codigo: str, mensaje: str, reintentable: bool = False, detalles: object = None) -> dict:
    return {"error": {"codigo": codigo, "mensaje": mensaje, "reintentable": reintentable, "detalles": detalles}}


def _id_operacion(ruta: APIRoute) -> str:
    return ruta.name


def crear_app(contenedor: Contenedor | None = None) -> FastAPI:
    configurar_registro()
    cont = contenedor or construir_contenedor()

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
        if cont.pool is not None:
            await cont.pool.open(wait=False)  # no falla si la BD no responde: las consultas devuelven 503
        simulador = cont.servicios.simulador if cont.servicios is not None else None
        if simulador is not None:
            await simulador.iniciar()  # MODO_DEMO: asegura el rodamiento de hoy y arranca el movimiento
        if cont.bot is not None:
            try:
                await cont.bot.iniciar()
            except Exception as exc:  # noqa: BLE001 - sin red o token inválido: la API sigue funcionando
                registro.error("No se pudo iniciar el bot de Telegram (%s)", type(exc).__name__)
                cont.bot = None
        try:
            yield
        finally:
            if cont.bot is not None:
                await cont.bot.detener()
            if simulador is not None:
                await simulador.detener()
            if cont.cliente_http is not None:
                await cont.cliente_http.aclose()
            if cont.pool is not None:
                await cont.pool.close()

    app = FastAPI(
        title="BusetasApp API (prototipo)",
        version="0.1.0",
        description="Datos de ejemplo · no son rutas oficiales. Contrato: docs/03-contrato-api.md.",
        lifespan=ciclo_de_vida,
        generate_unique_id_function=_id_operacion,
    )
    app.state.contenedor = cont
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cont.configuracion.lista_cors_origenes,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Id-Peticion"],
    )

    @app.middleware("http")
    async def id_peticion(request: Request, siguiente: Callable[[Request], Awaitable[Response]]) -> Response:
        identificador = uuid.uuid4().hex
        request.state.id_peticion = identificador
        respuesta = await siguiente(request)
        respuesta.headers["X-Id-Peticion"] = identificador
        return respuesta

    @app.exception_handler(ErrorAplicacion)
    async def manejar_error_aplicacion(_: Request, exc: ErrorAplicacion) -> JSONResponse:
        return JSONResponse(
            status_code=exc.estado_http,
            content=_cuerpo_error(exc.codigo, exc.mensaje, exc.reintentable, exc.detalles),
        )

    @app.exception_handler(RequestValidationError)
    async def manejar_validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        campos = [
            {"campo": ".".join(str(p) for p in e["loc"] if p != "body"), "motivo": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(status_code=400, content=_cuerpo_error("VALIDACION", "Datos inválidos.", False, campos))

    @app.exception_handler(ErrorHttpStarlette)
    async def manejar_http(_: Request, exc: ErrorHttpStarlette) -> JSONResponse:
        codigo = {401: "NO_AUTENTICADO", 403: "NO_AUTORIZADO", 404: "NO_ENCONTRADO"}.get(exc.status_code, "ERROR_INTERNO")
        return JSONResponse(status_code=exc.status_code, content=_cuerpo_error(codigo, str(exc.detail)))

    @app.exception_handler(PoolTimeout)
    @app.exception_handler(ErrorOperacionalBd)
    async def manejar_bd_no_disponible(request: Request, exc: Exception) -> JSONResponse:
        registro.error("Base de datos no disponible en %s (%s)", request.url.path, type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content=_cuerpo_error("SERVICIO_EXTERNO_NO_DISPONIBLE", "La base de datos no está disponible.", True),
        )

    @app.exception_handler(Exception)
    async def manejar_inesperado(request: Request, exc: Exception) -> JSONResponse:
        registro.error("Error interno en %s (%s)", request.url.path, type(exc).__name__)
        return JSONResponse(status_code=500, content=_cuerpo_error("ERROR_INTERNO", "Ocurrió un error inesperado."))

    # El orden importa: /rutas/cercanas antes que /rutas/{rutaId} (ambos en red).
    for router in (
        router_sistema, router_red, router_busqueda, router_horarios, router_seguimiento,
        router_planificacion, router_avisos, router_pasajero, router_operacion,
        router_estadisticas, router_administracion,
    ):
        app.include_router(router, prefix=PREFIJO_API, responses=errores(500, 501))
    app.include_router(router_ws)
    return app


app = crear_app()
