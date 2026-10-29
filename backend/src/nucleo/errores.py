"""Errores de la aplicación. Solo biblioteca estándar: los traduce a HTTP la capa de infraestructura."""

from __future__ import annotations

from typing import Any


class ErrorAplicacion(Exception):
    codigo = "ERROR_INTERNO"
    estado_http = 500
    reintentable = False

    def __init__(self, mensaje: str, detalles: Any = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalles = detalles


class ErrorValidacion(ErrorAplicacion):
    codigo = "VALIDACION"
    estado_http = 400


class ErrorNoAutenticado(ErrorAplicacion):
    codigo = "NO_AUTENTICADO"
    estado_http = 401


class ErrorNoAutorizado(ErrorAplicacion):
    codigo = "NO_AUTORIZADO"
    estado_http = 403


class ErrorNoEncontrado(ErrorAplicacion):
    codigo = "NO_ENCONTRADO"
    estado_http = 404


class ErrorConflictoVersion(ErrorAplicacion):
    codigo = "CONFLICTO_VERSION"
    estado_http = 409

    def __init__(self, version_actual: int, mensaje: str | None = None) -> None:
        super().__init__(
            mensaje or "El recurso cambió. Recarga para ver la versión más reciente.",
            {"versionActual": version_actual},
        )
        self.version_actual = version_actual


class ErrorConflictoNegocio(ErrorAplicacion):
    codigo = "CONFLICTO_NEGOCIO"
    estado_http = 409


class ErrorServicioExterno(ErrorAplicacion):
    codigo = "SERVICIO_EXTERNO_NO_DISPONIBLE"
    estado_http = 503
    reintentable = True
