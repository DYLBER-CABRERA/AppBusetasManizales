"""Simulador de GPS (docs/01 §4, backend/CLAUDE.md §8).

Mueve cada buseta a lo largo del trazado de su turno vigente y llama al MISMO caso de uso `registrar_posiciones`
que usaría un GPS real (D-P03). Toda la hora sale de `PuertoReloj` (así funciona `fijar_hora`). Geometría en Python
puro con *haversine* (sin Shapely).
"""

from __future__ import annotations

import asyncio
import bisect
import logging
import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

from modulos.seguimiento import PosicionEntrante
from nucleo.errores import ErrorNoEncontrado
from nucleo.parametros import PuertoParametros
from nucleo.reloj import RelojSimulado

registro = logging.getLogger("busetasapp.simulador")

RADIO_TIERRA_M = 6_371_000.0
VARIACION_KMH = 5.0
MAX_VELOCIDAD_REPORTADA_KMH = 150.0  # límite del CHECK de posicion_buseta
EXTRA_DESVIO_M = 60.0  # el desvío se aparta umbral_desvio_m + este margen
# docs/01 §4: Serviturismo no emite salvo que el administrador active su GPS.
EMPRESAS_SIN_GPS_POR_DEFECTO = frozenset({"serviturismo"})


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    f1, f2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((f2 - f1) / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    return 2 * RADIO_TIERRA_M * math.asin(math.sqrt(a))


def rumbo_grados(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    f1, f2, dl = math.radians(lat1), math.radians(lat2), math.radians(lng2 - lng1)
    y = math.sin(dl) * math.cos(f2)
    x = math.cos(f1) * math.sin(f2) - math.sin(f1) * math.cos(f2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def desplazar(lat: float, lng: float, rumbo: float, metros: float) -> tuple[float, float]:
    """Punto a `metros` de distancia siguiendo `rumbo` (grados)."""
    d, br, f1, l1 = metros / RADIO_TIERRA_M, math.radians(rumbo), math.radians(lat), math.radians(lng)
    f2 = math.asin(math.sin(f1) * math.cos(d) + math.cos(f1) * math.sin(d) * math.cos(br))
    l2 = l1 + math.atan2(math.sin(br) * math.sin(d) * math.cos(f1), math.cos(d) - math.sin(f1) * math.sin(f2))
    return math.degrees(f2), (math.degrees(l2) + 540) % 360 - 180


class Circuito:
    """Trazado como lista de puntos con distancias acumuladas; el avance se toma módulo la longitud."""

    def __init__(self, puntos: list[tuple[float, float]]) -> None:
        if len(puntos) < 2:
            raise ValueError("Un circuito necesita al menos dos puntos")
        self.puntos = puntos
        self.acumuladas = [0.0]
        for (la1, ln1), (la2, ln2) in zip(puntos, puntos[1:], strict=False):
            self.acumuladas.append(self.acumuladas[-1] + haversine_m(la1, ln1, la2, ln2))
        self.longitud = self.acumuladas[-1]

    @classmethod
    def desde_geojson(cls, coordenadas: list[list[float]]) -> Circuito:
        """GeoJSON usa [lng, lat]."""
        return cls([(c[1], c[0]) for c in coordenadas])

    def punto_en(self, distancia_m: float) -> tuple[float, float, float]:
        """(lat, lng, rumbo) a `distancia_m` desde el inicio, dando vueltas al circuito."""
        d = distancia_m % self.longitud
        i = min(bisect.bisect_right(self.acumuladas, d) - 1, len(self.puntos) - 2)
        (la1, ln1), (la2, ln2) = self.puntos[i], self.puntos[i + 1]
        tramo = self.acumuladas[i + 1] - self.acumuladas[i]
        t = 0.0 if tramo == 0 else (d - self.acumuladas[i]) / tramo
        return la1 + (la2 - la1) * t, ln1 + (ln2 - ln1) * t, rumbo_grados(la1, ln1, la2, ln2)


class RepositorioSimulacion(Protocol):
    async def busetas_activas(self) -> list[dict[str, Any]]:
        """buseta_id, numero_lateral, empresa_id, empresa_nombre de las busetas activas."""
        ...

    async def trazado_de_ruta(self, ruta_id: UUID) -> list[list[float]] | None:
        """Coordenadas GeoJSON [lng, lat] del trazado circular, o None."""
        ...

    async def asegurar_rodamientos_demo(self, hoy: Any) -> list[str]: ...

    async def limpiar_posiciones(self) -> None: ...


@dataclass
class BusetaSim:
    numero_lateral: str
    empresa_id: UUID
    empresa: str
    emitiendo: bool
    ruta_id: UUID | None = None
    avance_m: float = 0.0
    ultima_posicion: datetime | None = None
    desvio_hasta: datetime | None = None


class SimuladorGps:
    def __init__(
        self,
        repo: RepositorioSimulacion,
        registrar_posiciones: Any,
        deductor: Any,
        rodamientos: Any,
        parametros: PuertoParametros,
        reloj: RelojSimulado,
        velocidad_base_kmh: float,
        intervalo_s: float,
        azar: random.Random | None = None,
    ) -> None:
        self._repo = repo
        self._registrar = registrar_posiciones
        self._deductor = deductor
        self._rodamientos = rodamientos
        self._parametros = parametros
        self._reloj = reloj
        self._velocidad_base = velocidad_base_kmh
        self._intervalo = intervalo_s
        self._azar = azar or random.Random()
        self._busetas: dict[tuple[UUID, str], BusetaSim] = {}
        self._factor = 1.0
        self._circuitos: dict[UUID, Circuito] = {}
        self._ruta_de_servicio: dict[UUID, UUID | None] = {}
        self._colocadas: dict[UUID, int] = {}
        self._tarea: asyncio.Task[None] | None = None
        self._ultimo_ciclo: datetime | None = None

    # ---------- ciclo de vida ----------

    async def iniciar(self) -> None:
        try:
            for nota in await self._repo.asegurar_rodamientos_demo(self._reloj.ahora().date()):
                registro.info("Demo: %s", nota)
            await self.cargar()
        except Exception as exc:  # noqa: BLE001 - la API debe arrancar aunque la BD no responda
            registro.error("No se pudo preparar el simulador (%s)", type(exc).__name__)
            return
        self._tarea = asyncio.create_task(self._bucle(), name="simulador-gps")

    async def detener(self) -> None:
        if self._tarea is not None:
            self._tarea.cancel()
            await asyncio.gather(self._tarea, return_exceptions=True)
            self._tarea = None

    async def cargar(self) -> None:
        for fila in await self._repo.busetas_activas():
            llave = (fila["empresa_id"], fila["numero_lateral"])
            self._busetas.setdefault(
                llave,
                BusetaSim(
                    fila["numero_lateral"], fila["empresa_id"], fila["empresa_nombre"],
                    emitiendo=fila["empresa_nombre"].lower() not in EMPRESAS_SIN_GPS_POR_DEFECTO,
                ),
            )

    async def _bucle(self) -> None:
        while True:
            try:
                await self.ciclo()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - un ciclo fallido no debe matar el simulador
                registro.warning("Ciclo del simulador fallido (%s)", type(exc).__name__)
            await asyncio.sleep(self._intervalo)

    # ---------- un ciclo ----------

    async def _circuito(self, ruta_id: UUID) -> Circuito | None:
        if ruta_id not in self._circuitos:
            coordenadas = await self._repo.trazado_de_ruta(ruta_id)
            if coordenadas is None:
                return None
            self._circuitos[ruta_id] = Circuito.desde_geojson(coordenadas)
        return self._circuitos[ruta_id]

    async def _ruta_del_servicio(self, servicio_id: UUID) -> UUID | None:
        if servicio_id not in self._ruta_de_servicio:
            self._ruta_de_servicio[servicio_id] = await self._rodamientos.ruta_de_servicio(servicio_id)
        return self._ruta_de_servicio[servicio_id]

    async def ciclo(self) -> None:
        ahora = self._reloj.ahora()
        transcurrido = self._intervalo
        if self._ultimo_ciclo is not None:  # tiempo del PuertoReloj (respeta fijar_hora); acotado tras saltos del reloj
            transcurrido = min(max((ahora - self._ultimo_ciclo).total_seconds(), 0.0), self._intervalo * 5)
        self._ultimo_ciclo = ahora
        umbral_desvio = await self._parametros.numero("umbral_desvio_m")
        lotes: dict[UUID, list[tuple[BusetaSim, PosicionEntrante]]] = {}
        for buseta in self._busetas.values():
            servicio = await self._deductor(buseta.empresa_id, buseta.numero_lateral, ahora)
            ruta_id = await self._ruta_del_servicio(servicio) if servicio else None
            circuito = await self._circuito(ruta_id) if ruta_id else None
            if circuito is None or ruta_id is None:
                buseta.ruta_id = None  # fuera de turno: no se mueve
                continue
            if buseta.ruta_id != ruta_id:
                buseta.ruta_id = ruta_id
                ordinal = self._colocadas.get(ruta_id, 0)
                self._colocadas[ruta_id] = ordinal + 1
                buseta.avance_m = circuito.longitud * ((ordinal * 0.37) % 1)  # repartidas, no salen pegadas
            velocidad = max(5.0, self._velocidad_base + self._azar.uniform(-VARIACION_KMH, VARIACION_KMH)) * self._factor
            buseta.avance_m = (buseta.avance_m + velocidad / 3.6 * transcurrido) % circuito.longitud
            if not buseta.emitiendo:
                continue  # sigue su camino pero sin reportar
            lat, lng, rumbo = circuito.punto_en(buseta.avance_m)
            if buseta.desvio_hasta is not None:
                if ahora < buseta.desvio_hasta:
                    lat, lng = desplazar(lat, lng, (rumbo + 90) % 360, umbral_desvio + EXTRA_DESVIO_M)
                else:
                    buseta.desvio_hasta = None
            posicion = PosicionEntrante(
                buseta.numero_lateral, lat, lng, ahora, round(min(velocidad, MAX_VELOCIDAD_REPORTADA_KMH), 1), round(rumbo, 1)
            )
            lotes.setdefault(buseta.empresa_id, []).append((buseta, posicion))
        for empresa_id, lote in lotes.items():
            resultado = await self._registrar(empresa_id, [p for _, p in lote])
            rechazados = {r["indice"] for r in resultado.rechazadas}
            for indice, (buseta, _) in enumerate(lote):
                if indice not in rechazados:
                    buseta.ultima_posicion = ahora

    # ---------- escenarios del panel de demo ----------

    def _objetivo(self, escenario: dict[str, Any]) -> list[BusetaSim]:
        numero, empresa_id = escenario.get("numero_lateral"), escenario.get("empresa_id")
        elegidas = [
            b for b in self._busetas.values()
            if (numero is None or b.numero_lateral == numero) and (empresa_id is None or b.empresa_id == empresa_id)
        ]
        if not elegidas:
            raise ErrorNoEncontrado("No hay busetas que coincidan con el escenario.")
        return elegidas

    async def aplicar(self, escenario: dict[str, Any]) -> None:
        tipo = escenario["tipo"]
        if tipo in ("perder_senal", "restaurar_senal"):
            for b in self._objetivo(escenario):
                b.emitiendo = tipo == "restaurar_senal"
        elif tipo == "activar_gps_empresa":
            for b in self._objetivo({"empresa_id": escenario["empresa_id"]}):
                b.emitiendo = bool(escenario["activo"])
        elif tipo == "desvio":
            hasta = self._reloj.ahora() + timedelta(seconds=escenario["duracion_s"])
            for b in self._objetivo({"numero_lateral": escenario["numero_lateral"]}):
                b.desvio_hasta = hasta
        elif tipo == "acelerar":
            self._factor = float(escenario["factor"])
        elif tipo == "fijar_hora":
            self._reloj.fijar_hora(escenario["hora"])
            self._ultimo_ciclo = None
            await self._reiniciar_posiciones()  # las posiciones guardadas quedan en otro "tiempo"
        elif tipo == "reiniciar_simulacion":
            self._colocadas.clear()
            for b in self._busetas.values():
                b.ruta_id = None
            await self._reiniciar_posiciones()

    async def _reiniciar_posiciones(self) -> None:
        await self._repo.limpiar_posiciones()
        for b in self._busetas.values():
            b.ultima_posicion = None

    def estado(self) -> dict[str, Any]:
        return {
            "reloj_simulado": self._reloj.ahora() if self._reloj.simulado else None,
            "factor": self._factor,
            "busetas": [
                {
                    "numero_lateral": b.numero_lateral, "empresa": b.empresa, "emitiendo": b.emitiendo,
                    "ultima_posicion": b.ultima_posicion,
                }
                for b in sorted(self._busetas.values(), key=lambda x: (x.empresa, x.numero_lateral))
            ],
        }
