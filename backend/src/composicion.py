"""Composición: ÚNICO lugar que crea adaptadores y los inyecta (CLAUDE.md §4).

B0: solo configuración y reloj. B2+ agrega pool de BD, repositorios, casos de uso, emisor de eventos,
autenticación, simulador y bot (PENDIENTE por bloque).
"""

from __future__ import annotations

from dataclasses import dataclass

from nucleo.configuracion import Configuracion, obtener_configuracion
from nucleo.reloj import PuertoReloj, RelojSimulado


@dataclass
class Contenedor:
    configuracion: Configuracion
    reloj: PuertoReloj


def construir_contenedor(configuracion: Configuracion | None = None) -> Contenedor:
    config = configuracion or obtener_configuracion()
    return Contenedor(configuracion=config, reloj=RelojSimulado())
