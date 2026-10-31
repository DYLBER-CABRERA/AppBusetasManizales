"""Casos de uso del módulo administración (B3b): perfil y panel de demo. La autorización vive aquí."""

from __future__ import annotations

from datetime import time
from typing import Any
from uuid import UUID

from modulos.administracion.dominio.puertos import PuertoSimulador, RepositorioUsuarios
from modulos.administracion.dominio.validacion_pasajero import limpiar_nombre, normalizar_celular
from nucleo.autenticacion import SesionAuth
from nucleo.autorizacion import Identidad, Rol, exigir_identidad, exigir_rol
from nucleo.errores import ErrorNoAutenticado, ErrorNoEncontrado, ErrorValidacion


class ObtenerPerfil:
    def __init__(self, usuarios: RepositorioUsuarios) -> None:
        self._usuarios = usuarios

    async def __call__(self, identidad: Identidad | None) -> dict[str, Any]:
        actual = exigir_identidad(identidad)
        perfil = await self._usuarios.perfil(UUID(actual.usuario_id))
        if perfil is None or not perfil["activo"]:
            raise ErrorNoAutenticado("Usuario inactivo o sin perfil.")
        perfil = dict(perfil)
        if perfil["rol"] != Rol.JEFE_OPERACIONES.value:  # empresa solo para el jefe (docs/03 §2.1.1)
            perfil["empresa_id"] = perfil["empresa_nombre"] = None
        return perfil


class CompletarPerfilPasajero:
    """Crea el perfil de un pasajero recién registrado en Supabase Auth. El rol siempre es `pasajero`.
    Idempotente: si ya hay perfil, lo devuelve sin duplicar ni sobrescribir."""

    def __init__(self, usuarios: RepositorioUsuarios) -> None:
        self._usuarios = usuarios

    async def __call__(
        self, sesion: SesionAuth, nombre: str | None, apellido: str | None, celular: str | None
    ) -> tuple[dict[str, Any], bool]:
        existente = await self._usuarios.perfil_completo(sesion.usuario_id)
        if existente is not None:
            if not existente["activo"]:
                raise ErrorNoAutenticado("Usuario inactivo.")
            if existente["rol"] != Rol.JEFE_OPERACIONES.value:
                existente = {**existente, "empresa_id": None, "empresa_nombre": None}
            return existente, False
        datos = (limpiar_nombre(nombre, "nombre"), limpiar_nombre(apellido, "apellido"), normalizar_celular(celular))
        creado = await self._usuarios.crear_pasajero(sesion.usuario_id, sesion.correo, *datos)
        if creado is None:  # otra petición lo creó entre medias: se devuelve ese
            return await self._usuarios.perfil_completo(sesion.usuario_id), False  # type: ignore[return-value]
        return creado, True


class _PanelDemo:
    def __init__(self, simulador: PuertoSimulador | None, modo_demo: bool) -> None:
        self._simulador = simulador
        self._modo_demo = modo_demo

    def _disponible(self, identidad: Identidad | None) -> PuertoSimulador:
        exigir_rol(identidad, Rol.ADMINISTRADOR)
        if not self._modo_demo:
            raise ErrorNoEncontrado("El panel de demo no está habilitado.")
        if self._simulador is None:
            raise ErrorNoEncontrado("El simulador no está activo (falta la base de datos).")
        return self._simulador


class ConsultarEstadoDemo(_PanelDemo):
    async def __call__(self, identidad: Identidad | None) -> dict[str, Any]:
        return self._disponible(identidad).estado()


class EjecutarEscenarioDemo(_PanelDemo):
    async def __call__(self, identidad: Identidad | None, escenario: dict[str, Any]) -> dict[str, Any]:
        simulador = self._disponible(identidad)
        tipo = escenario["tipo"]
        if tipo in ("perder_senal", "restaurar_senal") and not (escenario.get("numero_lateral") or escenario.get("empresa_id")):
            raise ErrorValidacion("Indica numeroLateral o empresaId.")
        if tipo == "desvio" and not (escenario.get("numero_lateral") and escenario.get("duracion_s")):
            raise ErrorValidacion("El desvío necesita numeroLateral y duracionS.")
        if tipo == "acelerar" and escenario.get("factor") is None:
            raise ErrorValidacion("Indica factor (0.5 a 5).")
        if tipo == "activar_gps_empresa" and not (escenario.get("empresa_id") and escenario.get("activo") is not None):
            raise ErrorValidacion("Indica empresaId y activo.")
        if tipo == "fijar_hora":
            texto = escenario.get("hora")
            escenario = {**escenario, "hora": time.fromisoformat(texto) if texto else None}
        await simulador.aplicar(escenario)
        return simulador.estado()
