"""Caso de uso `planificar_viaje` (HU-P07): solo rutas directas, origen y destino por punto o por hito (D-P07)."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from modulos.planificacion.dominio.calculo import calcular_tiempos, mejor_recorrido_m
from modulos.planificacion.dominio.puertos import (
    ProveedorHito,
    ProveedorHorarios,
    ProveedorParaderos,
    ProveedorProgreso,
    RepositorioPlanificacion,
)
from modulos.seguimiento import HorarioDia, motivo_fuera_de_horario
from nucleo.errores import ErrorNoEncontrado
from nucleo.parametros import PuertoParametros
from nucleo.reloj import PuertoReloj


class ProveedorTipoDia(Protocol):
    def para_instante(self, instante: Any) -> str: ...


class PlanificarViaje:
    def __init__(
        self, plan: RepositorioPlanificacion, paraderos: ProveedorParaderos, hitos: ProveedorHito, progreso: ProveedorProgreso,
        horarios: ProveedorHorarios, tipo_dia: ProveedorTipoDia, parametros: PuertoParametros, reloj: PuertoReloj,
    ) -> None:
        self._plan = plan
        self._paraderos = paraderos
        self._hitos = hitos
        self._progreso = progreso
        self._horarios = horarios
        self._tipo_dia = tipo_dia
        self._parametros = parametros
        self._reloj = reloj

    async def _punto(self, lugar: dict[str, Any]) -> tuple[float, float]:
        if lugar.get("hito_id") is not None:
            hito = await self._hitos.obtener_hito(lugar["hito_id"])
            if hito is None:
                raise ErrorNoEncontrado("El hito no existe.")
            return hito["lat"], hito["lng"]
        return lugar["lat"], lugar["lng"]

    async def __call__(self, origen: dict[str, Any], destino: dict[str, Any]) -> dict[str, Any]:
        (olat, olng), (dlat, dlng) = await self._punto(origen), await self._punto(destino)
        radio = int(await self._parametros.numero("radio_caminata_m"))
        cerca_o = await self._paraderos.paraderos_cercanos(olat, olng, radio, None)
        cerca_d = await self._paraderos.paraderos_cercanos(dlat, dlng, radio, None)
        if not cerca_o:
            cercano = await self._paraderos.paradero_mas_cercano(olat, olng)
            return self._sin_opciones(f"No hay paraderos a menos de {radio} m del origen.", cercano)
        if not cerca_d:
            cercano = await self._paraderos.paradero_mas_cercano(dlat, dlng)
            return self._sin_opciones(f"No hay paraderos a menos de {radio} m del destino.", cercano)

        rutas_de = await self._plan.rutas_de_paraderos([p["paradero_id"] for p in cerca_o + cerca_d])
        ahora = self._reloj.ahora()
        tipo_dia = self._tipo_dia.para_instante(ahora)
        velocidad = await self._parametros.numero("velocidad_default_kmh")
        maximo = int(await self._parametros.numero("max_opciones_viaje"))
        opciones: list[dict[str, Any]] = []
        comunes = {r for p in cerca_o for r in rutas_de.get(p["paradero_id"], ())} & {
            r for p in cerca_d for r in rutas_de.get(p["paradero_id"], ())
        }
        for ruta_id in sorted(comunes, key=str):
            opciones += await self._opciones_de_ruta(ruta_id, cerca_o, cerca_d, rutas_de, ahora, tipo_dia, velocidad)
        opciones.sort(key=lambda o: o["total_min"])
        if opciones:
            return {"opciones": opciones[:maximo], "motivo": None, "paradero_mas_cercano": None}
        return self._sin_opciones("No hay una ruta directa entre esos paraderos en este horario.", None)

    @staticmethod
    def _sin_opciones(motivo: str, paradero: dict[str, Any] | None) -> dict[str, Any]:
        return {"opciones": [], "motivo": motivo, "paradero_mas_cercano": paradero}

    async def _opciones_de_ruta(
        self, ruta_id: UUID, cerca_o: list[dict], cerca_d: list[dict], rutas_de: dict[UUID, set[UUID]], ahora: Any,
        tipo_dia: str, velocidad: float,
    ) -> list[dict[str, Any]]:
        en_ruta_o = [p for p in cerca_o if ruta_id in rutas_de.get(p["paradero_id"], ())]
        en_ruta_d = [p for p in cerca_d if ruta_id in rutas_de.get(p["paradero_id"], ())]
        progresos = await self._progreso.progresos_de_ruta(ruta_id)
        if not progresos:
            return []
        longitud = progresos[0]["longitud_m"]
        pasos: dict[UUID, list[float]] = {}
        for fila in progresos:
            pasos.setdefault(fila["paradero_id"], []).append(fila["progreso_m"])
        validos = []
        for o in en_ruta_o:
            for d in en_ruta_d:
                if o["paradero_id"] == d["paradero_id"] or o["paradero_id"] not in pasos or d["paradero_id"] not in pasos:
                    continue
                recorrido = mejor_recorrido_m(pasos[o["paradero_id"]], pasos[d["paradero_id"]], longitud)
                if recorrido is not None:
                    validos.append((o, d, recorrido))
        if not validos:
            return []
        po, pd, recorrido = min(validos, key=lambda par: par[0]["distancia_m"] + par[1]["distancia_m"])
        servicios = [s for s in await self._progreso.servicios_para_eta(ruta_id) if s["estado"] == "activo"]
        ids = [s["servicio_id"] for s in servicios]
        horarios = {h["servicio_id"]: h for h in await self._horarios.horarios_de(ids) if h["tipo_dia"] == tipo_dia}
        minuto = ahora.hour * 60 + ahora.minute
        franjas: dict[UUID, dict] = {}
        for f in await self._horarios.frecuencias_de(ids):
            if f["tipo_dia"] == tipo_dia and f["inicio_minuto"] <= minuto < f["fin_minuto"]:
                franjas[f["servicio_id"]] = f
        opciones = []
        for s in servicios:
            h = horarios.get(s["servicio_id"])
            franja = franjas.get(s["servicio_id"])
            if h is None or franja is None:
                continue  # sin horario o sin frecuencia no se inventa el dato
            horario = HorarioDia(h["primera_salida"], h["ultima_salida"], h["cierre"])
            if motivo_fuera_de_horario(horario, s["duracion_estandar_min"], ahora):
                continue
            t = calcular_tiempos(po["distancia_m"], pd["distancia_m"], recorrido, velocidad, franja["minutos_max"])
            opciones.append(
                {
                    "tipo": "directa", "ruta_id": ruta_id, "servicio_id": s["servicio_id"], "paradero_origen": po,
                    "paradero_destino": pd, "caminata_min": round(t.caminata_min, 1), "espera_min": round(t.espera_min, 1),
                    "bus_min": round(t.bus_min, 1), "total_min": round(t.total_min, 1),
                }
            )
        return opciones
