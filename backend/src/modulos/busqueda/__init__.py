"""API pública del módulo búsqueda."""

from modulos.busqueda.aplicacion.consultas import BuscarHitos, BuscarRutasPorTexto, ConsultarRutasPorHito
from modulos.busqueda.dominio.servicios import normalizar_consulta
from modulos.busqueda.infraestructura.repositorio_sql import RepositorioBusquedaSql
from modulos.busqueda.infraestructura.router import router

__all__ = [
    "normalizar_consulta","BuscarHitos", "BuscarRutasPorTexto", "ConsultarRutasPorHito", "RepositorioBusquedaSql", "router"]
