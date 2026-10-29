"""Casos de uso de consulta de horarios y frecuencias (HU-P03, HU-P04)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from modulos.horarios.dominio.puertos import RepositorioHorarios
from modulos.horarios.dominio.servicios import CalculadorTipoDia, estado_de_horarios, hora_a_texto, minuto_a_texto
from nucleo.errores import ErrorNoEncontrado
from nucleo.reloj import PuertoReloj

_NO_EXISTE = "La ruta no existe o fue dada de baja."


def _agrupar(filas: list[dict[str, Any]]) -> dict[UUID, list[dict[str, Any]]]:
    por_servicio: dict[UUID, list[dict[str, Any]]] = {}
    for fila in filas:
        por_servicio.setdefault(fila["servicio_id"], []).append(fila)
    return por_servicio


class ConsultarHorarios:
    def __init__(self, repositorio: RepositorioHorarios, reloj: PuertoReloj, calculador: CalculadorTipoDia) -> None:
        self._repo = repositorio
        self._reloj = reloj
        self._calculador = calculador

    async def __call__(self, ruta_id: UUID) -> dict[str, Any]:
        if not await self._repo.ruta_activa_existe(ruta_id):
            raise ErrorNoEncontrado(_NO_EXISTE)
        servicios = await self._repo.servicios_de_ruta(ruta_id)
        filas = _agrupar(await self._repo.horarios_de([s["servicio_id"] for s in servicios]))
        resultado = []
        for s in servicios:
            horarios = [
                {
                    "tipo_dia": h["tipo_dia"],
                    "primera_salida": hora_a_texto(h["primera_salida"]),
                    "ultima_salida": hora_a_texto(h["ultima_salida"]),
                    "cierre": hora_a_texto(h["cierre"]) if h["cierre"] else None,
                    "nota": h["nota"],
                }
                for h in filas.get(s["servicio_id"], [])
            ]
            estado, pendientes = estado_de_horarios({h["tipo_dia"] for h in horarios})
            resultado.append({**s, "estado": estado, "horarios": horarios, "tipos_dia_pendientes": pendientes})
        return {"tipo_dia_hoy": self._calculador.para_instante(self._reloj.ahora()), "servicios": resultado}


class ConsultarFrecuencias:
    def __init__(self, repositorio: RepositorioHorarios) -> None:
        self._repo = repositorio

    async def __call__(self, ruta_id: UUID) -> dict[str, Any]:
        if not await self._repo.ruta_activa_existe(ruta_id):
            raise ErrorNoEncontrado(_NO_EXISTE)
        servicios = await self._repo.servicios_de_ruta(ruta_id)
        filas = _agrupar(await self._repo.frecuencias_de([s["servicio_id"] for s in servicios]))
        resultado = []
        for s in servicios:
            frecuencias = [
                {
                    "tipo_dia": f["tipo_dia"],
                    "franja_inicio": minuto_a_texto(f["inicio_minuto"]),
                    "franja_fin": minuto_a_texto(f["fin_minuto"]),
                    "minutos_min": f["minutos_min"],
                    "minutos_max": f["minutos_max"],
                    "nota": f["nota"],
                }
                for f in filas.get(s["servicio_id"], [])
            ]
            resultado.append(
                {
                    "servicio_id": s["servicio_id"], "empresa_id": s["empresa_id"], "empresa_nombre": s["empresa_nombre"],
                    "frecuencias": frecuencias, "version": s["version"],
                }
            )
        return {"servicios": resultado}
