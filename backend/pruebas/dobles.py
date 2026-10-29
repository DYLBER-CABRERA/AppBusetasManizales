"""Repositorios en memoria para pruebas (sin base de datos). Devuelven dicts como los adaptadores SQL."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, time
from typing import Any
from uuid import UUID, uuid4

from composicion import Repositorios

EMPRESA_SIDERAL = uuid4()
EMPRESA_SERVITURISMO = uuid4()
RUTA_ENEA = uuid4()
RUTA_VILLAMARIA = uuid4()
SERVICIO_SIDERAL_ENEA = uuid4()
SERVICIO_SERVITURISMO_ENEA = uuid4()
PARADERO_A = uuid4()
PARADERO_B = uuid4()
HITO_CABLE = uuid4()
HITO_LEJANO = uuid4()
AVISO_OBRA = uuid4()


def _servicio(servicio_id: UUID, empresa_id: UUID, empresa: str, codigo: str | None) -> dict[str, Any]:
    return {"servicio_id": servicio_id, "empresa_id": empresa_id, "empresa_nombre": empresa, "codigo_publico": codigo}


def _resumen(ruta_id: UUID, nombre: str, servicios: list[dict[str, Any]], distancia: float | None = None) -> dict[str, Any]:
    return {
        "id": ruta_id, "nombre": nombre, "tipo_recorrido": "circular", "es_variante": False,
        "distancia_m": distancia, "servicios": servicios,
    }


class RutasEnMemoria:
    def __init__(self) -> None:
        self.rutas = {
            RUTA_ENEA: _resumen(RUTA_ENEA, "La Enea", [
                _servicio(SERVICIO_SIDERAL_ENEA, EMPRESA_SIDERAL, "Sideral", "39"),
                _servicio(SERVICIO_SERVITURISMO_ENEA, EMPRESA_SERVITURISMO, "Serviturismo", None),
            ]),
            RUTA_VILLAMARIA: _resumen(RUTA_VILLAMARIA, "Villamaría", []),
        }
        self.paraderos = [
            {"paradero_id": PARADERO_A, "nombre": "Parada A", "lat": 5.07, "lng": -75.51, "distancia_m": 120.0},
            {"paradero_id": PARADERO_B, "nombre": "Parada B", "lat": 5.071, "lng": -75.512, "distancia_m": 480.0},
        ]
        self.llamadas: list[tuple[Any, ...]] = []

    async def rutas_cercanas(self, lat: float, lng: float, radio_m: int) -> list[dict[str, Any]]:
        self.llamadas.append(("rutas_cercanas", radio_m))
        if lat > 6:  # lejos de todo
            return []
        return [deepcopy(self.rutas[RUTA_ENEA]) | {"distancia_m": 90.0}]

    async def listar_activas(self) -> list[dict[str, Any]]:
        return [deepcopy(r) for r in self.rutas.values()]

    async def resumenes(self, ruta_ids: list[UUID], distancias: dict[UUID, float] | None = None) -> list[dict[str, Any]]:
        return [deepcopy(self.rutas[i]) | {"distancia_m": (distancias or {}).get(i)} for i in ruta_ids if i in self.rutas]

    async def obtener_detalle(self, ruta_id: UUID) -> dict[str, Any] | None:
        if ruta_id not in self.rutas:
            return None
        return deepcopy(self.rutas[ruta_id]) | {
            "descripcion": None, "ruta_principal_id": None, "longitud_m": 9000.0, "version": 1,
            "trazado": {"type": "LineString", "coordinates": [[-75.51, 5.07], [-75.52, 5.08]]},
            "paraderos": [
                {"orden": 1, "paradero_id": PARADERO_A, "nombre": "Parada A", "lat": 5.07, "lng": -75.51},
                {"orden": 2, "paradero_id": PARADERO_B, "nombre": "Parada B", "lat": 5.071, "lng": -75.512},
            ],
        }

    async def paraderos_cercanos(self, lat: float, lng: float, radio_m: int, ruta_id: UUID | None) -> list[dict[str, Any]]:
        self.llamadas.append(("paraderos_cercanos", radio_m, ruta_id))
        return [p for p in self.paraderos if p["distancia_m"] <= radio_m]

    async def paradero_mas_cercano(self, lat: float, lng: float) -> dict[str, Any] | None:
        return deepcopy(self.paraderos[0])

    async def listar_empresas(self) -> list[dict[str, Any]]:
        return [{"id": EMPRESA_SIDERAL, "nombre": "Sideral"}, {"id": EMPRESA_SERVITURISMO, "nombre": "Serviturismo"}]


class HorariosEnMemoria:
    async def ruta_activa_existe(self, ruta_id: UUID) -> bool:
        return ruta_id in (RUTA_ENEA, RUTA_VILLAMARIA)

    async def servicios_de_ruta(self, ruta_id: UUID) -> list[dict[str, Any]]:
        if ruta_id != RUTA_ENEA:
            return []
        return [
            {**_servicio(SERVICIO_SIDERAL_ENEA, EMPRESA_SIDERAL, "Sideral", "39"), "version": 2},
            {**_servicio(SERVICIO_SERVITURISMO_ENEA, EMPRESA_SERVITURISMO, "Serviturismo", None), "version": 1},
        ]

    async def horarios_de(self, servicio_ids: list[UUID]) -> list[dict[str, Any]]:
        filas = [
            ("lun_vie", time(5, 30), time(21, 0), time(22, 0), None),
            ("sabado", time(6, 0), time(20, 0), None, "Sábados"),
        ]
        return [
            {"servicio_id": SERVICIO_SIDERAL_ENEA, "tipo_dia": d, "primera_salida": a, "ultima_salida": b, "cierre": c, "nota": n}
            for d, a, b, c, n in filas
            if SERVICIO_SIDERAL_ENEA in servicio_ids
        ]

    async def frecuencias_de(self, servicio_ids: list[UUID]) -> list[dict[str, Any]]:
        if SERVICIO_SIDERAL_ENEA not in servicio_ids:
            return []
        return [
            {"servicio_id": SERVICIO_SIDERAL_ENEA, "tipo_dia": "lun_vie", "inicio_minuto": 330, "fin_minuto": 540,
             "minutos_min": 4, "minutos_max": 6, "nota": None},
            {"servicio_id": SERVICIO_SIDERAL_ENEA, "tipo_dia": "lun_vie", "inicio_minuto": 540, "fin_minuto": 1440,
             "minutos_min": 8, "minutos_max": 10, "nota": "Resto del día"},
        ]


class BusquedaEnMemoria:
    def __init__(self) -> None:
        self.hitos = {
            HITO_CABLE: {
                "id": HITO_CABLE, "nombre": "Cable Aéreo", "tipo": "terminal", "alias": ["Cable"], "lat": 5.06, "lng": -75.5,
            },
            HITO_LEJANO: {
                "id": HITO_LEJANO, "nombre": "Vereda Lejana", "tipo": "sector", "alias": [], "lat": 5.15, "lng": -75.45,
            },
        }
        self.patrones: list[tuple[str, str]] = []

    async def buscar_rutas(self, patron: str, texto: str) -> list[UUID]:
        self.patrones.append((patron, texto))
        return [RUTA_ENEA] if "enea" in texto or texto == "39" else []

    async def buscar_hitos(self, patron: str, texto: str) -> list[dict[str, Any]]:
        self.patrones.append((patron, texto))
        return [
            h for h in self.hitos.values()
            if texto in h["nombre"].lower().replace("é", "e") or texto in [a.lower() for a in h["alias"]]
        ]

    async def obtener_hito(self, hito_id: UUID) -> dict[str, Any] | None:
        return self.hitos.get(hito_id)

    async def rutas_por_hito(self, hito_id: UUID, radio_m: int) -> dict[UUID, float]:
        return {RUTA_ENEA: 150.0} if hito_id == HITO_CABLE else {}


class AvisosEnMemoria:
    def __init__(self) -> None:
        self.consultas: list[tuple[UUID | None, datetime]] = []

    async def vigentes(self, ruta_id: UUID | None, ahora: datetime) -> list[dict[str, Any]]:
        self.consultas.append((ruta_id, ahora))
        return [{
            "id": AVISO_OBRA, "origen": "movilidad", "empresa_id": None, "empresa_nombre": None, "tipo_cambio": "obra",
            "titulo": "Obra en la Avenida", "cuerpo": "Desvío temporal.", "desde": datetime(2026, 10, 1, tzinfo=UTC),
            "hasta": None, "ruta_ids": [RUTA_ENEA], "paradero_ids": [],
        }]


class EventosEnMemoria:
    def __init__(self, falla: bool = False) -> None:
        self.eventos: list[tuple[str, UUID | None]] = []
        self.falla = falla

    async def registrar(self, tipo: str, ruta_id: UUID | None) -> None:
        if self.falla:
            raise RuntimeError("BD caída")
        self.eventos.append((tipo, ruta_id))


class ParametrosEnMemoria:
    def __init__(self, valores: dict[str, float] | None = None) -> None:
        self.valores = {"radio_busqueda_m": 800, "radio_hito_m": 300} | (valores or {})

    async def numero(self, clave: str) -> float:
        return self.valores[clave]


def repositorios_en_memoria() -> Repositorios:
    return Repositorios(
        rutas=RutasEnMemoria(), horarios=HorariosEnMemoria(), busqueda=BusquedaEnMemoria(),
        avisos=AvisosEnMemoria(), eventos_uso=EventosEnMemoria(), parametros=ParametrosEnMemoria(),
    )
