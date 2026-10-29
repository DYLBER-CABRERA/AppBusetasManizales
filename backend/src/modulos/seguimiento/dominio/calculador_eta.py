"""CalculadorEta para rutas circulares (backend/CLAUDE.md §7). Stdlib únicamente, sin I/O.

Distancia restante = (progreso_paradero - progreso_buseta) mod longitud_circuito (docs/03 §3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from uuid import UUID

VELOCIDAD_MINIMA_VALIDA_KMH = 5.0
DURACION_POR_DEFECTO_MIN = 120


@dataclass(frozen=True)
class HorarioDia:
    primera_salida: time
    ultima_salida: time
    cierre: time | None = None


@dataclass(frozen=True)
class FranjaFrecuencia:
    inicio_minuto: int
    fin_minuto: int
    minutos_min: int
    minutos_max: int


@dataclass(frozen=True)
class PosicionConProgreso:
    numero_lateral: str
    progreso_m: float
    reportada_en: datetime
    velocidad_kmh: float | None = None


@dataclass
class EntradaEta:
    servicio_id: UUID
    empresa: str
    codigo_publico: str | None
    suspendido: bool
    horario: HorarioDia | None
    duracion_min: int | None
    franjas: list[FranjaFrecuencia]
    posiciones: list[PosicionConProgreso] = field(default_factory=list)


@dataclass(frozen=True)
class ResultadoEtaServicio:
    servicio_id: UUID
    empresa: str
    codigo_publico: str | None
    fuente: str  # gps | horario | no_disponible
    eta_segundos: int | None = None
    rango_max_segundos: int | None = None
    buseta_numero_lateral: str | None = None
    ultima_senal_hace_s: int | None = None
    mensaje: str | None = None


def distancia_restante_m(progreso_paradero_m: float, progreso_buseta_m: float, longitud_m: float) -> float:
    """Metros que le faltan a la buseta para llegar al paradero, dando la vuelta al circuito si hace falta."""
    return (progreso_paradero_m - progreso_buseta_m) % longitud_m


def _texto_frecuencia(franja: FranjaFrecuencia) -> str:
    if franja.minutos_min == franja.minutos_max:
        return f"cada {franja.minutos_max} min"
    return f"cada {franja.minutos_min} a {franja.minutos_max} min"


class CalculadorEta:
    def __init__(self, velocidad_default_kmh: float, umbral_obsoleta_s: float) -> None:
        self._velocidad_default = velocidad_default_kmh
        self._umbral = umbral_obsoleta_s

    def calcular(
        self, entrada: EntradaEta, ahora: datetime, progreso_paradero_m: float, longitud_m: float
    ) -> ResultadoEtaServicio:
        def sin_dato(mensaje: str) -> ResultadoEtaServicio:
            return ResultadoEtaServicio(
                entrada.servicio_id, entrada.empresa, entrada.codigo_publico, "no_disponible", mensaje=mensaje
            )

        if entrada.suspendido:
            return sin_dato("El servicio está suspendido.")
        if entrada.horario is None:
            return sin_dato("Información pendiente de actualización.")
        motivo = self._fuera_de_horario(entrada, ahora)
        if motivo:
            return sin_dato(motivo)

        frescas = [p for p in entrada.posiciones if (ahora - p.reportada_en).total_seconds() <= self._umbral]
        if frescas:
            mejor = min(
                ((self._segundos(p, progreso_paradero_m, longitud_m), p) for p in frescas), key=lambda par: par[0]
            )
            segundos, posicion = mejor
            return ResultadoEtaServicio(
                entrada.servicio_id, entrada.empresa, entrada.codigo_publico, "gps",
                eta_segundos=round(segundos), buseta_numero_lateral=posicion.numero_lateral,
                ultima_senal_hace_s=max(0, round((ahora - posicion.reportada_en).total_seconds())),
            )

        minuto = ahora.hour * 60 + ahora.minute
        franja = next((f for f in entrada.franjas if f.inicio_minuto <= minuto < f.fin_minuto), None)
        if franja is None:
            return sin_dato("Frecuencia no informada por la empresa.")
        inicio = "Sin señal GPS en este momento." if entrada.posiciones else "Sin ubicación de busetas."
        return ResultadoEtaServicio(
            entrada.servicio_id, entrada.empresa, entrada.codigo_publico, "horario",
            rango_max_segundos=franja.minutos_max * 60,
            mensaje=f"{inicio} Estimación por horario: {_texto_frecuencia(franja)}. Esté pendiente de la siguiente buseta.",
        )

    def _segundos(self, posicion: PosicionConProgreso, progreso_paradero_m: float, longitud_m: float) -> float:
        distancia = distancia_restante_m(progreso_paradero_m, posicion.progreso_m, longitud_m)
        velocidad = posicion.velocidad_kmh
        if velocidad is None or velocidad < VELOCIDAD_MINIMA_VALIDA_KMH:
            velocidad = self._velocidad_default
        return distancia / (velocidad / 3.6)

    @staticmethod
    def _fuera_de_horario(entrada: EntradaEta, ahora: datetime) -> str | None:
        horario = entrada.horario
        assert horario is not None
        hora = ahora.time().replace(tzinfo=None)
        if hora < horario.primera_salida:
            return "Aún no inicia el servicio."
        if horario.cierre is not None:
            limite = horario.cierre
        else:
            duracion = timedelta(minutes=entrada.duracion_min or DURACION_POR_DEFECTO_MIN)
            fin = datetime.combine(ahora.date(), horario.ultima_salida) + duracion
            limite = time(23, 59, 59) if fin.date() > ahora.date() else fin.time()
        if hora > limite:
            return "El servicio ya cerró."
        return None
