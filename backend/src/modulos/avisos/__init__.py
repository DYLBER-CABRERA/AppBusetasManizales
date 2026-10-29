"""API pública del módulo avisos."""

from modulos.avisos.aplicacion.consultar_avisos_vigentes import ConsultarAvisosVigentes
from modulos.avisos.infraestructura.repositorio_sql import RepositorioAvisosSql
from modulos.avisos.infraestructura.router import router

__all__ = ["ConsultarAvisosVigentes", "RepositorioAvisosSql", "router"]
