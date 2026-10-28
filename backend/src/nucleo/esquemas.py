"""Base común de los esquemas HTTP: JSON en camelCase, BD y código en snake_case (D-P12)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class EsquemaBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class DetalleError(EsquemaBase):
    codigo: str
    mensaje: str
    reintentable: bool = False
    detalles: Any | None = None


class RespuestaError(EsquemaBase):
    error: DetalleError


_DESCRIPCIONES = {
    400: "VALIDACION",
    401: "NO_AUTENTICADO",
    403: "NO_AUTORIZADO",
    404: "NO_ENCONTRADO",
    409: "CONFLICTO_VERSION o CONFLICTO_NEGOCIO",
    500: "ERROR_INTERNO",
    501: "PENDIENTE: endpoint declarado en el contrato, lógica aún no implementada",
    503: "SERVICIO_EXTERNO_NO_DISPONIBLE",
}


def errores(*estados: int) -> dict[int | str, dict[str, Any]]:
    """Documenta respuestas de error con el formato del contrato (CLAUDE.md §6)."""
    return {e: {"model": RespuestaError, "description": _DESCRIPCIONES[e]} for e in estados}
