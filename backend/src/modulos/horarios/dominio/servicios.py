"""Servicios de dominio de horarios: tipo de día, estado de completitud y formato de horas (stdlib únicamente)."""

from __future__ import annotations

from datetime import date, datetime, time

TIPOS_DIA = ("lun_vie", "sabado", "dom_festivo")


class CalculadorTipoDia:
    """Festivo (lista `FESTIVOS` de la configuración) → dom_festivo; si no, lun–vie / sábado / domingo (D-P11)."""

    def __init__(self, festivos: frozenset[date] = frozenset()) -> None:
        self._festivos = festivos

    def para_fecha(self, fecha: date) -> str:
        if fecha in self._festivos:
            return "dom_festivo"
        dia = fecha.weekday()
        if dia <= 4:
            return "lun_vie"
        return "sabado" if dia == 5 else "dom_festivo"

    def para_instante(self, instante: datetime) -> str:
        """El instante ya viene en hora de America/Bogota (lo entrega PuertoReloj)."""
        return self.para_fecha(instante.date())


def estado_de_horarios(tipos_dia_con_horario: set[str]) -> tuple[str, list[str]]:
    """(`completo` | `parcial` | `pendiente_actualizacion`, tipos de día pendientes). Nunca se inventa un dato."""
    pendientes = [t for t in TIPOS_DIA if t not in tipos_dia_con_horario]
    if not pendientes:
        return "completo", []
    if len(pendientes) == len(TIPOS_DIA):
        return "pendiente_actualizacion", pendientes
    return "parcial", pendientes


def hora_a_texto(valor: time) -> str:
    return f"{valor.hour:02d}:{valor.minute:02d}"


def minuto_a_texto(minuto: int) -> str:
    """Minutos desde 00:00 → `HH:MM`; 1440 es `24:00` (fin de franja)."""
    return f"{minuto // 60:02d}:{minuto % 60:02d}"
