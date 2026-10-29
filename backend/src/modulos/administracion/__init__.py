"""API pública del módulo administración."""

from modulos.administracion.infraestructura.repositorio_parametros_sql import ParametrosSql
from modulos.administracion.infraestructura.router import router

__all__ = ["ParametrosSql", "router"]
