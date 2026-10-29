"""PuertoReloj: única fuente de la hora actual. Prohibido `datetime.now()` fuera de este archivo."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
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
    """Reloj del panel de demo. `fijar_hora("HH:MM")` salta a esa hora de HOY y desde ahí el tiempo sigue corriendo
    (así las posiciones nuevas siempre son más recientes que las guardadas); `None` vuelve al reloj real."""

    def __init__(self, base: PuertoReloj | None = None) -> None:
        self._base = base or RelojReal()
        self._desfase = timedelta(0)

    def fijar_hora(self, hora: time | None) -> None:
        if hora is None:
            self._desfase = timedelta(0)
            return
        real = self._base.ahora()
        self._desfase = real.replace(hour=hora.hour, minute=hora.minute, second=0, microsecond=0) - real

    @property
    def simulado(self) -> bool:
        return self._desfase != timedelta(0)

    def ahora(self) -> datetime:
        return self._base.ahora() + self._desfase
