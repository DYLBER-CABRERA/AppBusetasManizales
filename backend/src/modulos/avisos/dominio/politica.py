"""PoliticaDeAvisos (BR-05): quién publica con qué origen. Stdlib únicamente."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from nucleo.autorizacion import Identidad, Rol
from nucleo.errores import ErrorNoAutorizado, ErrorValidacion

ORIGEN_POR_ROL = {
    Rol.JEFE_OPERACIONES: "empresa",
    Rol.SECRETARIA_MOVILIDAD: "movilidad",
    Rol.ADMINISTRADOR: "aplicativo",
}


@dataclass(frozen=True)
class DefinicionAviso:
    origen: str
    empresa_id: UUID | None
    tipo_cambio: str | None


def definir_aviso(
    identidad: Identidad, titulo: str, cuerpo: str, tipo_cambio: str | None, longitud_maxima: int,
    hay_rutas: bool, hay_paraderos: bool,
) -> DefinicionAviso:
    """Origen y alcance según el rol; valida título y cuerpo."""
    origen = ORIGEN_POR_ROL.get(identidad.rol)
    if origen is None:
        raise ErrorNoAutorizado("Tu rol no puede publicar avisos.")
    if not titulo.strip():
        raise ErrorValidacion("El título no puede estar vacío.")
    if not cuerpo.strip():
        raise ErrorValidacion("El aviso no puede estar vacío.")
    if len(cuerpo) > longitud_maxima:
        raise ErrorValidacion(f"El aviso supera el máximo de {longitud_maxima} caracteres.")
    if origen != "aplicativo" and not (hay_rutas or hay_paraderos):
        raise ErrorValidacion("Indica al menos una ruta afectada.")
    if origen == "empresa" and hay_paraderos:
        raise ErrorValidacion("Los avisos de empresa se asocian solo a rutas de tu empresa.")
    empresa = UUID(identidad.empresa_id) if origen == "empresa" and identidad.empresa_id else None
    # tipoCambio es de los cambios de movilidad (SM05); en los demás orígenes se ignora.
    return DefinicionAviso(origen, empresa, tipo_cambio if origen == "movilidad" else None)


def puede_retirar(identidad: Identidad, origen: str, empresa_id: str | None) -> bool | None:
    """True: puede. False: existe pero no es suyo (403). None: de otra empresa → 404 (el jefe no ve lo ajeno)."""
    if identidad.rol == Rol.ADMINISTRADOR:
        return True
    if identidad.rol == Rol.SECRETARIA_MOVILIDAD:
        return origen == "movilidad"
    if identidad.rol == Rol.JEFE_OPERACIONES:
        return True if origen == "empresa" and empresa_id == identidad.empresa_id else None
    return False
