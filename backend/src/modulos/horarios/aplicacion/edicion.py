"""Casos de uso de edición de horarios y frecuencias del jefe (HU-J02). El servicio debe ser de su empresa."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from modulos.horarios.dominio.puertos import RepositorioHorarios
from modulos.horarios.dominio.servicios import estado_de_horarios, hora_a_texto, minuto_a_texto
from modulos.horarios.dominio.validacion import (
    FranjaNueva,
    HorarioNuevo,
    texto_a_hora,
    texto_a_minuto,
    validar_frecuencias,
    validar_horarios,
)
from nucleo.autorizacion import Identidad, Rol, exigir_rol
from nucleo.errores import ErrorNoEncontrado
from nucleo.version_optimista import verificar_version


async def _servicio_propio(repo: RepositorioHorarios, identidad: Identidad | None, servicio_id: UUID) -> dict[str, Any]:
    actual = exigir_rol(identidad, Rol.JEFE_OPERACIONES)
    servicio = await repo.servicio_de_empresa(servicio_id, UUID(actual.empresa_id or ""))
    if servicio is None:  # inexistente, de baja o de otra empresa: mismo 404
        raise ErrorNoEncontrado("El servicio no existe.")
    return servicio


class ActualizarHorariosServicio:
    def __init__(self, repositorio: RepositorioHorarios) -> None:
        self._repo = repositorio

    async def __call__(
        self, identidad: Identidad | None, servicio_id: UUID, horarios: list[dict[str, Any]], version: int
    ) -> dict[str, Any]:
        servicio = await _servicio_propio(self._repo, identidad, servicio_id)
        nuevos = [
            HorarioNuevo(
                h["tipo_dia"], texto_a_hora(h["primera_salida"]), texto_a_hora(h["ultima_salida"]),
                texto_a_hora(h["cierre"]) if h.get("cierre") else None, h.get("nota"),
            )
            for h in horarios
        ]
        validar_horarios(nuevos)
        verificar_version(version, servicio["version"])
        nueva_version = await self._repo.reemplazar_horarios(servicio_id, version, nuevos)
        estado, pendientes = estado_de_horarios({h.tipo_dia for h in nuevos})
        return {
            **{k: servicio[k] for k in ("servicio_id", "empresa_id", "empresa_nombre", "codigo_publico")},
            "estado": estado, "tipos_dia_pendientes": pendientes, "version": nueva_version,
            "horarios": [
                {
                    "tipo_dia": h.tipo_dia, "primera_salida": hora_a_texto(h.primera_salida),
                    "ultima_salida": hora_a_texto(h.ultima_salida),
                    "cierre": hora_a_texto(h.cierre) if h.cierre else None, "nota": h.nota,
                }
                for h in nuevos
            ],
        }


class ActualizarFrecuenciasServicio:
    def __init__(self, repositorio: RepositorioHorarios) -> None:
        self._repo = repositorio

    async def __call__(
        self, identidad: Identidad | None, servicio_id: UUID, frecuencias: list[dict[str, Any]], version: int
    ) -> dict[str, Any]:
        servicio = await _servicio_propio(self._repo, identidad, servicio_id)
        nuevas = [
            FranjaNueva(
                f["tipo_dia"], texto_a_minuto(f["franja_inicio"]), texto_a_minuto(f["franja_fin"]),
                f["minutos_min"], f["minutos_max"], f.get("nota"),
            )
            for f in frecuencias
        ]
        validar_frecuencias(nuevas)
        verificar_version(version, servicio["version"])
        nueva_version = await self._repo.reemplazar_frecuencias(servicio_id, version, nuevas)
        return {
            "servicio_id": servicio["servicio_id"], "empresa_id": servicio["empresa_id"],
            "empresa_nombre": servicio["empresa_nombre"], "version": nueva_version,
            "frecuencias": [
                {
                    "tipo_dia": f.tipo_dia, "franja_inicio": minuto_a_texto(f.inicio_minuto),
                    "franja_fin": minuto_a_texto(f.fin_minuto), "minutos_min": f.minutos_min,
                    "minutos_max": f.minutos_max, "nota": f.nota,
                }
                for f in nuevas
            ],
        }

