"""API pública del módulo administración."""

from modulos.administracion.aplicacion.casos_de_uso import ConsultarEstadoDemo, EjecutarEscenarioDemo, ObtenerPerfil
from modulos.administracion.aplicacion.gestion import (
    ConfigurarParametro,
    CrearCredencialGps,
    CrearEmpresa,
    CrearUsuario,
    EditarEmpresa,
    EditarUsuario,
    ListarCredencialesGps,
    ListarEmpresasAdmin,
    ListarParametros,
    ListarRoles,
    ListarUsuarios,
    RevocarCredencialGps,
)
from modulos.administracion.infraestructura.autenticacion_supabase import AutenticacionSupabase
from modulos.administracion.infraestructura.repositorio_admin_sql import RepositorioAdminSql
from modulos.administracion.infraestructura.repositorio_fuentes_gps_sql import RepositorioFuentesGpsSql
from modulos.administracion.infraestructura.repositorio_parametros_sql import ParametrosSql
from modulos.administracion.infraestructura.repositorio_usuarios_sql import RepositorioUsuariosSql
from modulos.administracion.infraestructura.router import router

__all__ = [
    "AutenticacionSupabase", "ConfigurarParametro", "ConsultarEstadoDemo", "CrearCredencialGps", "CrearEmpresa", "CrearUsuario",
    "EditarEmpresa", "EditarUsuario", "EjecutarEscenarioDemo", "ListarCredencialesGps", "ListarEmpresasAdmin",
    "ListarParametros", "ListarRoles", "ListarUsuarios", "ObtenerPerfil", "ParametrosSql", "RepositorioAdminSql",
    "RepositorioFuentesGpsSql", "RepositorioUsuariosSql", "RevocarCredencialGps", "router",
]
