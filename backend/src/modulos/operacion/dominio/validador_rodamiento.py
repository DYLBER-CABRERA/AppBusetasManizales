"""ValidadorRodamiento: solapamientos y reemplazos (backend/CLAUDE.md §7). Stdlib únicamente, sin I/O."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from itertools import combinations
from typing import Any
from uuid import UUID

DURACION_POR_DEFECTO_MIN = 120


@dataclass(frozen=True)
class TurnoDato:
    servicio_id: UUID
    buseta_id: UUID
    conductor_id: UUID | None
    hora_salida: time
    hora_fin_estimada: time | None = None
    id: UUID | None = None


@dataclass(frozen=True)
class AdvertenciaRodamiento:
    codigo: str  # solapamiento_buseta | solapamiento_conductor
    mensaje: str
    turnos: tuple[TurnoDato, TurnoDato]


def _minutos(hora: time) -> int:
    return hora.hour * 60 + hora.minute


def hora_texto(hora: time) -> str:
    return f"{hora.hour:02d}:{hora.minute:02d}"


def _minutos_a_texto(minutos: int) -> str:
    return f"{minutos // 60 % 24:02d}:{minutos % 60:02d}"


def intervalo(turno: TurnoDato, duraciones: dict[UUID, int | None]) -> tuple[int, int]:
    """[salida, fin): sin hora de fin, salida + duración estándar del servicio (o 120 min)."""
    inicio = _minutos(turno.hora_salida)
    if turno.hora_fin_estimada is not None:
        return inicio, _minutos(turno.hora_fin_estimada)
    return inicio, inicio + (duraciones.get(turno.servicio_id) or DURACION_POR_DEFECTO_MIN)


def _se_solapan(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]  # turnos consecutivos (fin == salida) no se solapan


def detectar_solapamientos(
    turnos: list[TurnoDato],
    duraciones: dict[UUID, int | None],
    laterales: dict[UUID, str],
    conductores: dict[UUID, str],
) -> list[AdvertenciaRodamiento]:
    advertencias: list[AdvertenciaRodamiento] = []
    for a, b in combinations(turnos, 2):
        ia, ib = intervalo(a, duraciones), intervalo(b, duraciones)
        if not _se_solapan(ia, ib):
            continue
        primero, segundo = (a, b) if ia[0] <= ib[0] else (b, a)
        fin_primero = intervalo(primero, duraciones)[1]
        detalle = (
            f"sale a las {hora_texto(segundo.hora_salida)} y todavía está en el turno de las "
            f"{hora_texto(primero.hora_salida)} a las {_minutos_a_texto(fin_primero)}."
        )
        if a.buseta_id == b.buseta_id:
            mensaje = f"La buseta {laterales.get(a.buseta_id, '?')} {detalle}"
            advertencias.append(AdvertenciaRodamiento("solapamiento_buseta", mensaje, (primero, segundo)))
        if a.conductor_id is not None and a.conductor_id == b.conductor_id:
            mensaje = f"El conductor {conductores.get(a.conductor_id, '?')} {detalle}"
            advertencias.append(AdvertenciaRodamiento("solapamiento_conductor", mensaje, (primero, segundo)))
    return advertencias


def detectar_reemplazos(
    guardados: list[TurnoDato], nuevos: list[TurnoDato], laterales: dict[UUID, str], conductores: dict[UUID, str]
) -> list[dict[str, Any]]:
    """Turnos ya guardados (mismo servicio y hora de salida) cuya buseta o conductor cambian (D-P15)."""
    por_clave = {(t.servicio_id, t.hora_salida): t for t in guardados}
    afectados: list[dict[str, Any]] = []
    for nuevo in nuevos:
        actual = por_clave.get((nuevo.servicio_id, nuevo.hora_salida))
        if actual is None or (actual.buseta_id == nuevo.buseta_id and actual.conductor_id == nuevo.conductor_id):
            continue
        afectados.append(
            {
                "turnoId": str(actual.id) if actual.id else None,
                "servicioId": str(nuevo.servicio_id),
                "horaSalida": hora_texto(nuevo.hora_salida),
                "busetaActual": laterales.get(actual.buseta_id),
                "busetaNueva": laterales.get(nuevo.buseta_id),
                "conductorActual": conductores.get(actual.conductor_id) if actual.conductor_id else None,
                "conductorNuevo": conductores.get(nuevo.conductor_id) if nuevo.conductor_id else None,
            }
        )
    return afectados


def mensaje_de_reemplazo(afectados: list[dict[str, Any]]) -> str:
    primero = afectados[0]
    if primero["busetaActual"] != primero["busetaNueva"]:
        return (
            f"La ruta ya tiene asignada la buseta {primero['busetaActual']} a las {primero['horaSalida']}. "
            f"¿Reemplazarla por la {primero['busetaNueva']}?"
        )
    return f"El turno de las {primero['horaSalida']} ya tiene conductor. ¿Reemplazarlo?"
