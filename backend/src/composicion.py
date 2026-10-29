"""Composición: ÚNICO lugar que crea adaptadores y los inyecta (CLAUDE.md §4).

B2: pool de BD, repositorios de consulta pública y sus casos de uso. B3+ agrega emisor de eventos, autenticación,
simulador y bot. Las pruebas arman `Repositorios` con dobles en memoria y reutilizan `construir_servicios`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from psycopg_pool import AsyncConnectionPool

from adaptadores_externos.base_datos import crear_pool
from modulos.administracion import ParametrosSql
from modulos.avisos import ConsultarAvisosVigentes, RepositorioAvisosSql
from modulos.busqueda import BuscarHitos, BuscarRutasPorTexto, ConsultarRutasPorHito, RepositorioBusquedaSql
from modulos.estadisticas import RegistrarEventoUso, RepositorioEventosUsoSql
from modulos.horarios import CalculadorTipoDia, ConsultarFrecuencias, ConsultarHorarios, RepositorioHorariosSql
from modulos.red import (
    ConsultarParaderosCercanos,
    ConsultarRutasCercanas,
    ListarEmpresas,
    ListarRutas,
    ObtenerDetalleRuta,
    RepositorioRutasSql,
)
from nucleo.configuracion import Configuracion, obtener_configuracion
from nucleo.reloj import PuertoReloj, RelojSimulado


@dataclass
class Repositorios:
    """Puertos de salida. Los tipos son estructurales (Protocol): SQL en producción, memoria en pruebas."""

    rutas: Any
    horarios: Any
    busqueda: Any
    avisos: Any
    eventos_uso: Any
    parametros: Any


@dataclass
class Servicios:
    """Casos de uso listos para los routers (cada uno es invocable)."""

    consultar_rutas_cercanas: ConsultarRutasCercanas
    listar_rutas: ListarRutas
    obtener_detalle_ruta: ObtenerDetalleRuta
    consultar_paraderos_cercanos: ConsultarParaderosCercanos
    listar_empresas: ListarEmpresas
    consultar_horarios: ConsultarHorarios
    consultar_frecuencias: ConsultarFrecuencias
    buscar_rutas_por_texto: BuscarRutasPorTexto
    buscar_hitos: BuscarHitos
    consultar_rutas_por_hito: ConsultarRutasPorHito
    consultar_avisos_vigentes: ConsultarAvisosVigentes
    registrar_evento_uso: RegistrarEventoUso


@dataclass
class Contenedor:
    configuracion: Configuracion
    reloj: PuertoReloj
    servicios: Servicios | None = None
    pool: AsyncConnectionPool | None = None


def construir_servicios(repos: Repositorios, configuracion: Configuracion, reloj: PuertoReloj) -> Servicios:
    calculador_tipo_dia = CalculadorTipoDia(configuracion.lista_festivos)
    return Servicios(
        consultar_rutas_cercanas=ConsultarRutasCercanas(repos.rutas, repos.parametros),
        listar_rutas=ListarRutas(repos.rutas),
        obtener_detalle_ruta=ObtenerDetalleRuta(repos.rutas, repos.avisos, reloj),
        consultar_paraderos_cercanos=ConsultarParaderosCercanos(repos.rutas, repos.parametros),
        listar_empresas=ListarEmpresas(repos.rutas),
        consultar_horarios=ConsultarHorarios(repos.horarios, reloj, calculador_tipo_dia),
        consultar_frecuencias=ConsultarFrecuencias(repos.horarios),
        buscar_rutas_por_texto=BuscarRutasPorTexto(repos.busqueda, repos.rutas),
        buscar_hitos=BuscarHitos(repos.busqueda),
        consultar_rutas_por_hito=ConsultarRutasPorHito(repos.busqueda, repos.rutas, repos.rutas, repos.parametros),
        consultar_avisos_vigentes=ConsultarAvisosVigentes(repos.avisos, reloj),
        registrar_evento_uso=RegistrarEventoUso(repos.eventos_uso),
    )


def _repositorios_sql(pool: AsyncConnectionPool) -> Repositorios:
    return Repositorios(
        rutas=RepositorioRutasSql(pool),
        horarios=RepositorioHorariosSql(pool),
        busqueda=RepositorioBusquedaSql(pool),
        avisos=RepositorioAvisosSql(pool),
        eventos_uso=RepositorioEventosUsoSql(pool),
        parametros=ParametrosSql(pool),
    )


def construir_contenedor(
    configuracion: Configuracion | None = None, repositorios: Repositorios | None = None
) -> Contenedor:
    config = configuracion or obtener_configuracion()
    reloj = RelojSimulado()
    pool: AsyncConnectionPool | None = None
    if repositorios is None:
        cadena = config.database_url.get_secret_value()
        if cadena:
            pool = crear_pool(cadena)  # sin abrir: el lifespan lo abre
            repositorios = _repositorios_sql(pool)
    servicios = construir_servicios(repositorios, config, reloj) if repositorios is not None else None
    return Contenedor(configuracion=config, reloj=reloj, servicios=servicios, pool=pool)
