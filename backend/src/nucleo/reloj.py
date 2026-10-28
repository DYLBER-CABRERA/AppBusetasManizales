"""PuertoReloj: única fuente de la hora actual. Prohibido `datetime.now()` fuera de este archivo."""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import Protocol
from zoneinfo import ZoneInfo

ZONA_BOGOTA = ZoneInfo("America/Bogota")


class PuertoReloj(Protocol):
    def ahora(self) -> datetime:
        """Instante actual con zona horaria (America/Bogota)."""
        ...


class RelojReal:
    def ahora(self) -> datetime:
        return datetime.now(UTC).astimezone(ZONA_BOGOTA)


class RelojSimulado:
    """Reloj del panel de demo: `fijar_hora("HH:MM")` o `None` para volver al real (B3 lo conecta)."""

    def __init__(self, base: PuertoReloj | None = None) -> None:
        self._base = base or RelojReal()
        self._hora_fija: time | None = None

    def fijar_hora(self, hora: time | None) -> None:
        self._hora_fija = hora

    def ahora(self) -> datetime:
        real = self._base.ahora()
        if self._hora_fija is None:
            return real
        return real.replace(
            hour=self._hora_fija.hour, minute=self._hora_fija.minute, second=0, microsecond=0
        )
