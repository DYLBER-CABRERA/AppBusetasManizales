"""EvaluadorAlertas (backend/CLAUDE.md §7, SPEC-009): llegada cercana y desvío, una vez por episodio. Stdlib únicamente."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class Notificacion:
    alerta_id: UUID
    tipo: str  # alerta_llegada | alerta_desvio
    mensaje: str
    distancia_m: int | None = None
    buseta: str = ""


def distancia_restante_m(progreso_paradero_m: float, progreso_buseta_m: float, longitud_m: float) -> float:
    return (progreso_paradero_m - progreso_buseta_m) % longitud_m


class EvaluadorAlertas:
    """Conserva en memoria los episodios de desvío abiertos (alerta, buseta). Una sola instancia del servidor."""

    def __init__(self, enfriamiento_min: float, umbral_desvio_m: float) -> None:
        self.enfriamiento = timedelta(minutes=enfriamiento_min)
        self.umbral = umbral_desvio_m
        self._desvios: set[tuple[UUID, str]] = set()

    def evaluar(
        self, alertas: list[dict[str, Any]], buseta: str, progreso_buseta_m: float, desvio_m: float, longitud_m: float,
        progresos_paraderos: dict[UUID, float], ahora: datetime,
    ) -> list[Notificacion]:
        resultado: list[Notificacion] = []
        for alerta in alertas:
            llave = (alerta["id"], buseta)
            if desvio_m > self.umbral:
                if llave not in self._desvios:  # nuevo episodio: se avisa una sola vez
                    self._desvios.add(llave)
                    resultado.append(Notificacion(
                        alerta["id"], "alerta_desvio", f"La buseta {buseta} se desvió de su recorrido. Tu llegada puede cambiar.",
                        buseta=buseta,
                    ))
                continue  # desviada: no se estima llegada
            self._desvios.discard(llave)  # el episodio termina al volver a la ruta
            ultima = alerta.get("ultima_notificacion_en")
            if ultima is not None and ahora - ultima < self.enfriamiento:
                continue
            progreso_paradero = progresos_paraderos.get(alerta["paradero_id"])
            if progreso_paradero is None:
                continue
            d = distancia_restante_m(progreso_paradero, progreso_buseta_m, longitud_m)
            if d <= alerta["distancia_aviso_m"]:
                resultado.append(Notificacion(
                    alerta["id"], "alerta_llegada", f"La buseta {buseta} está a {round(d)} m de tu paradero.",
                    distancia_m=round(d), buseta=buseta,
                ))
        return resultado
