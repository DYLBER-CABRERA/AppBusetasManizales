"""Composición: ÚNICO lugar que crea adaptadores y los inyecta (CLAUDE.md §4).

B2/B3: pool de BD, repositorios, casos de uso y emisor de eventos. B3b+ agrega autenticación, simulador y bot.
Las pruebas arman `Repositorios` con dobles en memoria y reutilizan `construir_servicios`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from psycopg_pool import AsyncConnectionPool

from adaptadores_externos.base_datos import crear_pool
from adaptadores_externos.websocket_posiciones import DifusorPosiciones, GestorConexiones
from herramientas.repositorio_simulacion_sql import RepositorioSimulacionSql
from herramientas.simulador_gps import SimuladorGps
from modulos.administracion import (
    AutenticacionSupabase,
    ConsultarEstadoDemo,
    EjecutarEscenarioDemo,
    ObtenerPerfil,
    ParametrosSql,
    RepositorioFuentesGpsSql,
    RepositorioUsuariosSql,
)
from modulos.avisos import ConsultarAvisosVigentes, PublicarAviso, RepositorioAvisosSql, RetirarAviso
from modulos.busqueda import BuscarHitos, BuscarRutasPorTexto, ConsultarRutasPorHito, RepositorioBusquedaSql
from modulos.estadisticas import RegistrarEventoUso, RepositorioEventosUsoSql
from modulos.horarios import (
    ActualizarFrecuenciasServicio,
    ActualizarHorariosServicio,
    CalculadorTipoDia,
    ConsultarFrecuencias,
    ConsultarHorarios,
    RepositorioHorariosSql,
)
from modulos.operacion import (
    ActualizarRodamiento,
    AnularRodamiento,
    CrearRodamiento,
    GuardarBuseta,
    GuardarConductor,
    ListarBusetas,
    ListarConductores,
    ListarRodamientos,
    ListarServiciosDeMiEmpresa,
    ObtenerRodamiento,
    PublicarRodamiento,
    RepositorioOperacionSql,
)
from modulos.red import (
    ConsultarParaderosCercanos,
    ConsultarRutasCercanas,
    ListarEmpresas,
    ListarRutas,
    ObtenerDetalleRuta,
    RepositorioRutasSql,
)
from modulos.seguimiento import (
    AutenticarFuenteGps,
    BusetaEnVivo,
    CalcularEtaParadero,
    ConsultarBusetasEnVivo,
    DeductorDeRuta,
    RegistrarPosiciones,
    RepositorioSeguimientoSql,
)
from nucleo.autenticacion import PuertoAutenticacion
from nucleo.configuracion import Configuracion, obtener_configuracion
from nucleo.emisor_eventos import AVISO_PUBLICADO, POSICION_ACEPTADA, EmisorEventos, EmisorEventosEnMemoria
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
    seguimiento: Any  # RepositorioPosiciones + RepositorioRodamientos + RepositorioEta
    fuentes_gps: Any
    usuarios: Any = None
    autenticacion: Any = None  # PuertoAutenticacion
    simulacion: Any = None  # RepositorioSimulacion (solo MODO_DEMO)
    operacion: Any = None


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
    registrar_posiciones: RegistrarPosiciones
    autenticar_fuente_gps: AutenticarFuenteGps
    consultar_busetas_en_vivo: ConsultarBusetasEnVivo
    calcular_eta_paradero: CalcularEtaParadero
    autenticacion: PuertoAutenticacion
    obtener_perfil: ObtenerPerfil
    consultar_estado_demo: ConsultarEstadoDemo
    ejecutar_escenario_demo: EjecutarEscenarioDemo
    actualizar_horarios_servicio: ActualizarHorariosServicio
    actualizar_frecuencias_servicio: ActualizarFrecuenciasServicio
    listar_servicios_de_mi_empresa: ListarServiciosDeMiEmpresa
    listar_busetas: ListarBusetas
    guardar_buseta: GuardarBuseta
    listar_conductores: ListarConductores
    guardar_conductor: GuardarConductor
    listar_rodamientos: ListarRodamientos
    obtener_rodamiento: ObtenerRodamiento
    crear_rodamiento: CrearRodamiento
    actualizar_rodamiento: ActualizarRodamiento
    publicar_rodamiento: PublicarRodamiento
    anular_rodamiento: AnularRodamiento
    publicar_aviso: PublicarAviso
    retirar_aviso: RetirarAviso
    simulador: SimuladorGps | None = None


@dataclass
class Contenedor:
    configuracion: Configuracion
    reloj: PuertoReloj
    servicios: Servicios | None = None
    emisor: EmisorEventos | None = None
    pool: AsyncConnectionPool | None = None
    cliente_http: httpx.AsyncClient | None = None
    gestor_ws: GestorConexiones | None = None
    armar_mensaje_posiciones: Any = None


def construir_servicios(
    repos: Repositorios, configuracion: Configuracion, reloj: PuertoReloj, emisor: EmisorEventos
) -> Servicios:
    calculador_tipo_dia = CalculadorTipoDia(configuracion.lista_festivos)
    deductor = DeductorDeRuta(repos.seguimiento)
    registrar_posiciones = RegistrarPosiciones(
        repos.seguimiento, deductor, repos.seguimiento, repos.parametros, reloj, emisor
    )
    simulador = None
    if configuracion.modo_demo and repos.simulacion is not None and isinstance(reloj, RelojSimulado):
        simulador = SimuladorGps(
            repos.simulacion, registrar_posiciones, deductor, repos.seguimiento, repos.parametros, reloj,
            configuracion.sim_velocidad_kmh, configuracion.sim_intervalo_s,
        )
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
        registrar_posiciones=registrar_posiciones,
        autenticar_fuente_gps=AutenticarFuenteGps(repos.fuentes_gps, reloj),
        consultar_busetas_en_vivo=ConsultarBusetasEnVivo(repos.seguimiento, repos.seguimiento, repos.parametros, reloj),
        calcular_eta_paradero=CalcularEtaParadero(
            repos.seguimiento, repos.seguimiento, repos.horarios, calculador_tipo_dia, repos.parametros, reloj
        ),
        autenticacion=repos.autenticacion,
        obtener_perfil=ObtenerPerfil(repos.usuarios),
        consultar_estado_demo=ConsultarEstadoDemo(simulador, configuracion.modo_demo),
        ejecutar_escenario_demo=EjecutarEscenarioDemo(simulador, configuracion.modo_demo),
        actualizar_horarios_servicio=ActualizarHorariosServicio(repos.horarios),
        actualizar_frecuencias_servicio=ActualizarFrecuenciasServicio(repos.horarios),
        listar_servicios_de_mi_empresa=ListarServiciosDeMiEmpresa(repos.operacion),
        listar_busetas=ListarBusetas(repos.operacion),
        guardar_buseta=GuardarBuseta(repos.operacion),
        listar_conductores=ListarConductores(repos.operacion),
        guardar_conductor=GuardarConductor(repos.operacion),
        listar_rodamientos=ListarRodamientos(repos.operacion),
        obtener_rodamiento=ObtenerRodamiento(repos.operacion),
        crear_rodamiento=CrearRodamiento(repos.operacion, repos.parametros, reloj),
        actualizar_rodamiento=ActualizarRodamiento(repos.operacion),
        publicar_rodamiento=PublicarRodamiento(repos.operacion),
        anular_rodamiento=AnularRodamiento(repos.operacion),
        publicar_aviso=PublicarAviso(repos.avisos, repos.parametros, reloj, emisor),
        retirar_aviso=RetirarAviso(repos.avisos),
        simulador=simulador,
    )


def _repositorios_sql(pool: AsyncConnectionPool, config: Configuracion, cliente_http: httpx.AsyncClient) -> Repositorios:
    usuarios = RepositorioUsuariosSql(pool)
    return Repositorios(
        rutas=RepositorioRutasSql(pool),
        horarios=RepositorioHorariosSql(pool),
        busqueda=RepositorioBusquedaSql(pool),
        avisos=RepositorioAvisosSql(pool),
        eventos_uso=RepositorioEventosUsoSql(pool),
        parametros=ParametrosSql(pool),
        seguimiento=RepositorioSeguimientoSql(pool),
        fuentes_gps=RepositorioFuentesGpsSql(pool),
        usuarios=usuarios,
        autenticacion=AutenticacionSupabase(
            config.supabase_url, config.supabase_anon_key.get_secret_value(), usuarios, cliente_http
        ),
        simulacion=RepositorioSimulacionSql(pool),
        operacion=RepositorioOperacionSql(pool),
    )


def construir_contenedor(
    configuracion: Configuracion | None = None,
    repositorios: Repositorios | None = None,
    reloj: PuertoReloj | None = None,
) -> Contenedor:
    config = configuracion or obtener_configuracion()
    reloj = reloj or RelojSimulado()
    pool: AsyncConnectionPool | None = None
    cliente_http: httpx.AsyncClient | None = None
    if repositorios is None:
        cadena = config.database_url.get_secret_value()
        if cadena:
            pool = crear_pool(cadena)  # sin abrir: el lifespan lo abre
            cliente_http = httpx.AsyncClient(timeout=5.0)
            repositorios = _repositorios_sql(pool, config, cliente_http)
    emisor = EmisorEventosEnMemoria()
    gestor = GestorConexiones()
    contenedor = Contenedor(
        configuracion=config, reloj=reloj, emisor=emisor, pool=pool, cliente_http=cliente_http, gestor_ws=gestor
    )
    if repositorios is None:
        return contenedor
    servicios = construir_servicios(repositorios, config, reloj, emisor)
    contenedor.servicios = servicios

    async def armar_mensaje_posiciones(ruta_id: UUID) -> dict[str, Any] | None:
        datos = await servicios.consultar_busetas_en_vivo(ruta_id)
        return {
            "tipo": "posiciones",
            "rutaId": str(ruta_id),
            "calculadoEn": datos["calculado_en"].isoformat(),
            "busetas": [BusetaEnVivo.model_validate(b).model_dump(by_alias=True, mode="json") for b in datos["busetas"]],
        }

    contenedor.armar_mensaje_posiciones = armar_mensaje_posiciones
    emisor.suscribir(POSICION_ACEPTADA, DifusorPosiciones(gestor, armar_mensaje_posiciones).al_aceptar_posicion)

    async def difundir_aviso_nuevo(carga: dict[str, Any]) -> None:
        for ruta_id in carga["ruta_ids"]:
            await gestor.difundir(ruta_id, {"tipo": "aviso_nuevo", "avisoId": str(carga["aviso_id"])})

    emisor.suscribir(AVISO_PUBLICADO, difundir_aviso_nuevo)
    return contenedor
