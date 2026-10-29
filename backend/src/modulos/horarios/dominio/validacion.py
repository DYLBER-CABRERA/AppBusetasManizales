"""Validación de la edición de horarios y frecuencias (stdlib únicamente). Mensajes para el panel del jefe."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from modulos.horarios.dominio.servicios import TIPOS_DIA
from nucleo.errores import ErrorValidacion


@dataclass(frozen=True)
class HorarioNuevo:
    tipo_dia: str
    primera_salida: time
    ultima_salida: time
    cierre: time | None = None
    nota: str | None = None


@dataclass(frozen=True)
class FranjaNueva:
    tipo_dia: str
    inicio_minuto: int
    fin_minuto: int
    minutos_min: int
    minutos_max: int
    nota: str | None = None


def validar_horarios(horarios: list[HorarioNuevo]) -> None:
    vistos: set[str] = set()
    for h in horarios:
        if h.tipo_dia not in TIPOS_DIA:
            raise ErrorValidacion(f"Tipo de día desconocido: {h.tipo_dia}.")
        if h.tipo_dia in vistos:
            raise ErrorValidacion(f"El tipo de día {h.tipo_dia} está repetido.")
        vistos.add(h.tipo_dia)
        if h.primera_salida > h.ultima_salida:
            raise ErrorValidacion("La primera salida no puede ser después de la última salida.")
        if h.cierre is not None and h.cierre < h.ultima_salida:
            raise ErrorValidacion("El cierre no puede ser antes de la última salida.")


def validar_frecuencias(franjas: list[FranjaNueva]) -> None:
    por_dia: dict[str, list[FranjaNueva]] = {}
    for f in franjas:
        if f.tipo_dia not in TIPOS_DIA:
            raise ErrorValidacion(f"Tipo de día desconocido: {f.tipo_dia}.")
        if not (0 <= f.inicio_minuto < f.fin_minuto <= 1440):
            raise ErrorValidacion("Cada franja debe terminar después de empezar (entre 00:00 y 24:00).")
        if f.minutos_min < 1 or f.minutos_max < f.minutos_min:
            raise ErrorValidacion("El máximo de minutos no puede ser menor que el mínimo.")
        por_dia.setdefault(f.tipo_dia, []).append(f)
    for franjas_dia in por_dia.values():
        ordenadas = sorted(franjas_dia, key=lambda x: x.inicio_minuto)
        for anterior, siguiente in zip(ordenadas, ordenadas[1:], strict=False):
            if siguiente.inicio_minuto < anterior.fin_minuto:
                raise ErrorValidacion("Las franjas de frecuencia de un mismo tipo de día no pueden solaparse.")


def texto_a_hora(texto: str) -> time:
    return time.fromisoformat(texto)


def texto_a_minuto(texto: str) -> int:
    """`HH:MM` (incluye `24:00`) → minutos desde 00:00."""
    horas, minutos = texto.split(":")
    return int(horas) * 60 + int(minutos)
