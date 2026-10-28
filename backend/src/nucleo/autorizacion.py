"""Identidad del usuario y reglas por rol y empresa (stdlib únicamente)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from nucleo.errores import ErrorNoAutenticado, ErrorNoAutorizado


class Rol(StrEnum):
    PASAJERO = "pasajero"
    JEFE_OPERACIONES = "jefe_operaciones"
    SECRETARIA_MOVILIDAD = "secretaria_movilidad"
    ADMINISTRADOR = "administrador"


@dataclass(frozen=True)
class Identidad:
    usuario_id: str
    rol: Rol
    empresa_id: str | None = None


def exigir_identidad(identidad: Identidad | None) -> Identidad:
    if identidad is None:
        raise ErrorNoAutenticado("Inicia sesión para continuar.")
    return identidad


def exigir_rol(identidad: Identidad | None, *roles: Rol) -> Identidad:
    """Quien llama decide si `administrador` va en la lista (es superconjunto de gestión, no de todo)."""
    actual = exigir_identidad(identidad)
    if actual.rol in roles:
        return actual
    raise ErrorNoAutorizado("No tienes permiso para esta acción.")
