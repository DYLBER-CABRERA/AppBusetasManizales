"""Casos de uso del jefe de operaciones (HU-J01, J02, J04). El `empresa_id` siempre sale de la identidad."""

from __future__ import annotations

from datetime import date, time, timedelta
from typing import Any
from uuid import UUID

from modulos.operacion.dominio.puertos import RepositorioOperacion
from modulos.operacion.dominio.validador_rodamiento import (
    TurnoDato,
    detectar_reemplazos,
    detectar_solapamientos,
    hora_texto,
    mensaje_de_reemplazo,
)
from nucleo.autorizacion import Identidad, Rol, exigir_rol
from nucleo.errores import ErrorConflictoNegocio, ErrorNoEncontrado, ErrorValidacion
from nucleo.parametros import PuertoParametros
from nucleo.reloj import PuertoReloj
from nucleo.version_optimista import verificar_version


def _empresa(identidad: Identidad | None) -> tuple[Identidad, UUID]:
    actual = exigir_rol(identidad, Rol.JEFE_OPERACIONES)
    return actual, UUID(actual.empresa_id or "")


class _Base:
    def __init__(self, repositorio: RepositorioOperacion) -> None:
        self._repo = repositorio


class ListarServiciosDeMiEmpresa(_Base):
    async def __call__(self, identidad: Identidad | None) -> list[dict[str, Any]]:
        return await self._repo.servicios_de_empresa(_empresa(identidad)[1])


class ListarBusetas(_Base):
    async def __call__(self, identidad: Identidad | None) -> list[dict[str, Any]]:
        return await self._repo.listar_busetas(_empresa(identidad)[1])


class GuardarBuseta(_Base):
    async def __call__(
        self, identidad: Identidad | None, numero_lateral: str, placa: str | None, buseta_id: UUID | None = None,
        version: int | None = None, estado: str | None = None,
    ) -> dict[str, Any]:
        _, empresa_id = _empresa(identidad)
        numero = numero_lateral.strip() if numero_lateral else numero_lateral
        if buseta_id is None:
            if not numero:
                raise ErrorValidacion("El número lateral es obligatorio.")
            return await self._repo.crear_buseta(empresa_id, numero, placa)
        cambios = {"numero_lateral": numero or None, "placa": placa, "estado": estado}
        return await self._repo.editar_buseta(empresa_id, buseta_id, version or 0, cambios)


class ListarConductores(_Base):
    async def __call__(self, identidad: Identidad | None) -> list[dict[str, Any]]:
        return await self._repo.listar_conductores(_empresa(identidad)[1])


class GuardarConductor(_Base):
    async def __call__(
        self, identidad: Identidad | None, nombre: str | None, codigo: str | None, conductor_id: UUID | None = None,
        version: int | None = None, estado: str | None = None,
    ) -> dict[str, Any]:
        _, empresa_id = _empresa(identidad)
        if conductor_id is None:
            if not nombre or not nombre.strip():
                raise ErrorValidacion("El nombre es obligatorio.")
            return await self._repo.crear_conductor(empresa_id, nombre.strip(), codigo)
        cambios = {"nombre": nombre.strip() if nombre else None, "codigo": codigo, "estado": estado}
        return await self._repo.editar_conductor(empresa_id, conductor_id, version or 0, cambios)


def _turnos_datos(entradas: list[dict[str, Any]]) -> list[TurnoDato]:
    datos = []
    for e in entradas:
        salida = time.fromisoformat(e["hora_salida"])
        fin = time.fromisoformat(e["hora_fin_estimada"]) if e.get("hora_fin_estimada") else None
        if fin is not None and fin <= salida:
            raise ErrorValidacion("La hora de fin debe ser posterior a la hora de salida.")
        datos.append(TurnoDato(e["servicio_id"], e["buseta_id"], e.get("conductor_id"), salida, fin))
    return datos


class _CasoRodamiento(_Base):
    """Utilidades comunes: pertenencia a la empresa, advertencias y forma de respuesta."""

    async def _validar_recursos(self, recursos: dict[str, Any], turnos: list[TurnoDato]) -> None:
        for t in turnos:  # recurso de otra empresa (o inexistente) → 404, nunca revela que existe
            if t.servicio_id not in recursos["servicios"]:
                raise ErrorNoEncontrado("El servicio no existe en tu empresa.")
            if t.buseta_id not in recursos["busetas"]:
                raise ErrorNoEncontrado("La buseta no existe en tu empresa.")
            if t.conductor_id is not None and t.conductor_id not in recursos["conductores"]:
                raise ErrorNoEncontrado("El conductor no existe en tu empresa.")

    @staticmethod
    def _advertencias(turnos: list[TurnoDato], recursos: dict[str, Any]) -> list:
        return detectar_solapamientos(turnos, recursos["servicios"], recursos["busetas"], recursos["conductores"])

    async def _respuesta(self, empresa_id: UUID, rodamiento_id: UUID) -> dict[str, Any]:
        rodamiento = await self._repo.obtener_rodamiento(empresa_id, rodamiento_id)
        if rodamiento is None:
            raise ErrorNoEncontrado("El rodamiento no existe.")
        recursos = await self._repo.recursos_de_empresa(empresa_id)
        return self._forma(rodamiento, recursos)

    def _forma(self, rodamiento: dict[str, Any], recursos: dict[str, Any]) -> dict[str, Any]:
        activos = [t["datos"] for t in rodamiento["turnos"] if t["estado"] == "programado"]
        advertencias = self._advertencias(activos, recursos) if rodamiento["estado"] != "anulado" else []
        return {
            "rodamiento_id": rodamiento["rodamiento_id"],
            "fecha": rodamiento["fecha"].isoformat(),
            "estado": rodamiento["estado"],
            "version": rodamiento["version"],
            "turnos": [
                {
                    "id": t["datos"].id, "servicio_id": t["datos"].servicio_id, "buseta_id": t["datos"].buseta_id,
                    "numero_lateral": recursos["busetas"].get(t["datos"].buseta_id), "conductor_id": t["datos"].conductor_id,
                    "hora_salida": hora_texto(t["datos"].hora_salida),
                    "hora_fin_estimada": hora_texto(t["datos"].hora_fin_estimada) if t["datos"].hora_fin_estimada else None,
                    "estado": t["estado"],
                }
                for t in rodamiento["turnos"]
            ],
            "advertencias": [
                {"codigo": a.codigo, "mensaje": a.mensaje, "turno_ids": [x.id for x in a.turnos if x.id]} for a in advertencias
            ],
        }


class ListarRodamientos(_CasoRodamiento):
    async def __call__(self, identidad: Identidad | None, desde: date | None, hasta: date | None) -> list[dict[str, Any]]:
        _, empresa_id = _empresa(identidad)
        recursos = await self._repo.recursos_de_empresa(empresa_id)
        return [self._forma(r, recursos) for r in await self._repo.listar_rodamientos(empresa_id, desde, hasta)]


class ObtenerRodamiento(_CasoRodamiento):
    async def __call__(self, identidad: Identidad | None, rodamiento_id: UUID) -> dict[str, Any]:
        return await self._respuesta(_empresa(identidad)[1], rodamiento_id)


class CrearRodamiento(_CasoRodamiento):
    def __init__(self, repositorio: RepositorioOperacion, parametros: PuertoParametros, reloj: PuertoReloj) -> None:
        super().__init__(repositorio)
        self._parametros = parametros
        self._reloj = reloj

    async def __call__(self, identidad: Identidad | None, fecha: date, turnos: list[dict[str, Any]]) -> dict[str, Any]:
        _, empresa_id = _empresa(identidad)
        hoy = self._reloj.ahora().date()
        maximo = int(await self._parametros.numero("dias_max_rodamiento_adelante"))
        if not hoy <= fecha <= hoy + timedelta(days=maximo):
            raise ErrorValidacion(f"La fecha debe estar entre hoy y {maximo} días adelante.")
        datos = _turnos_datos(turnos)
        await self._validar_recursos(await self._repo.recursos_de_empresa(empresa_id), datos)
        if await self._repo.rodamiento_de_fecha(empresa_id, fecha):
            raise ErrorConflictoNegocio("Tu empresa ya tiene un rodamiento para esa fecha.")
        return await self._respuesta(empresa_id, await self._repo.crear_rodamiento(empresa_id, fecha, datos))


class ActualizarRodamiento(_CasoRodamiento):
    async def __call__(
        self, identidad: Identidad | None, rodamiento_id: UUID, turnos: list[dict[str, Any]], version: int,
        confirmar_reemplazo: bool,
    ) -> dict[str, Any]:
        _, empresa_id = _empresa(identidad)
        actual = await self._repo.obtener_rodamiento(empresa_id, rodamiento_id)
        if actual is None:
            raise ErrorNoEncontrado("El rodamiento no existe.")
        verificar_version(version, actual["version"])
        if actual["estado"] != "borrador":
            raise ErrorConflictoNegocio("Solo se puede editar un rodamiento en borrador.")
        datos = _turnos_datos(turnos)
        recursos = await self._repo.recursos_de_empresa(empresa_id)
        await self._validar_recursos(recursos, datos)
        guardados = [t["datos"] for t in actual["turnos"] if t["estado"] == "programado"]
        afectados = detectar_reemplazos(guardados, datos, recursos["busetas"], recursos["conductores"])
        if afectados and not confirmar_reemplazo:
            raise ErrorConflictoNegocio(mensaje_de_reemplazo(afectados), {"turnosAfectados": afectados})
        await self._repo.reemplazar_turnos(rodamiento_id, version, datos)
        return await self._respuesta(empresa_id, rodamiento_id)


class PublicarRodamiento(_CasoRodamiento):
    async def __call__(self, identidad: Identidad | None, rodamiento_id: UUID, version: int) -> dict[str, Any]:
        actual_id, empresa_id = _empresa(identidad)
        actual = await self._repo.obtener_rodamiento(empresa_id, rodamiento_id)
        if actual is None:
            raise ErrorNoEncontrado("El rodamiento no existe.")
        verificar_version(version, actual["version"])
        if actual["estado"] != "borrador":
            raise ErrorConflictoNegocio("Solo se puede publicar un rodamiento en borrador.")
        forma = self._forma(actual, await self._repo.recursos_de_empresa(empresa_id))
        if forma["advertencias"]:
            raise ErrorConflictoNegocio(
                "No se puede publicar: hay solapamientos. Corrígelos y vuelve a intentar.",
                {"advertencias": [
                    {"codigo": a["codigo"], "mensaje": a["mensaje"], "turnoIds": [str(i) for i in a["turno_ids"]]}
                    for a in forma["advertencias"]
                ]},
            )
        await self._repo.cambiar_estado(rodamiento_id, version, "publicado", UUID(actual_id.usuario_id))
        return await self._respuesta(empresa_id, rodamiento_id)


class AnularRodamiento(_CasoRodamiento):
    async def __call__(self, identidad: Identidad | None, rodamiento_id: UUID, version: int) -> dict[str, Any]:
        actual_id, empresa_id = _empresa(identidad)
        actual = await self._repo.obtener_rodamiento(empresa_id, rodamiento_id)
        if actual is None:
            raise ErrorNoEncontrado("El rodamiento no existe.")
        verificar_version(version, actual["version"])
        if actual["estado"] == "anulado":
            raise ErrorConflictoNegocio("El rodamiento ya está anulado.")
        await self._repo.cambiar_estado(rodamiento_id, version, "anulado", UUID(actual_id.usuario_id))
        return await self._respuesta(empresa_id, rodamiento_id)
