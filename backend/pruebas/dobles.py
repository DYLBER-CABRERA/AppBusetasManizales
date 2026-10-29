"""Repositorios en memoria para pruebas (sin base de datos). Devuelven dicts como los adaptadores SQL."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, time
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from composicion import Repositorios
from modulos.seguimiento import hash_de_clave
from nucleo.autorizacion import Identidad, Rol
from nucleo.errores import ErrorNoAutenticado

ZONA = ZoneInfo("America/Bogota")
LUNES_MEDIODIA = datetime(2026, 10, 26, 12, 0, tzinfo=ZONA)


class RelojFijo:
    """PuertoReloj de pruebas: avanza solo cuando la prueba lo pide."""

    def __init__(self, ahora: datetime = LUNES_MEDIODIA) -> None:
        self._ahora = ahora

    def ahora(self) -> datetime:
        return self._ahora

    def fijar(self, ahora: datetime) -> None:
        self._ahora = ahora


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
    def __init__(self, valores: dict[str, Any] | None = None) -> None:
        self.valores: dict[str, Any] = {
            "radio_busqueda_m": 800, "radio_hito_m": 300, "velocidad_default_kmh": 20,
            "umbral_posicion_obsoleta_s": 60, "umbral_desvio_m": 100,
            "caja_ciudad": {"minLat": 4.95, "maxLat": 5.20, "minLng": -75.65, "maxLng": -75.40},
        } | (valores or {})

    async def numero(self, clave: str) -> float:
        return float(self.valores[clave])

    async def objeto(self, clave: str) -> dict[str, Any]:
        return self.valores[clave]


BUSETA_1544 = uuid4()
BUSETA_2683 = uuid4()
CLAVE_SIDERAL = "clave-de-prueba-sideral"
CREDENCIAL = uuid4()


class SeguimientoEnMemoria:
    """Implementa RepositorioPosiciones, RepositorioRodamientos y RepositorioEta con turnos fijos 05:00-23:00 de hoy."""

    def __init__(self) -> None:
        self.busetas = {
            (EMPRESA_SIDERAL, "1544"): {"id": BUSETA_1544, "numero_lateral": "1544"},
            (EMPRESA_SERVITURISMO, "2683"): {"id": BUSETA_2683, "numero_lateral": "2683"},
        }
        self.turnos = {
            (EMPRESA_SIDERAL, "1544"): (time(5, 0), time(23, 0), SERVICIO_SIDERAL_ENEA),
            (EMPRESA_SERVITURISMO, "2683"): (time(5, 0), time(23, 0), SERVICIO_SERVITURISMO_ENEA),
        }
        self.guardadas: dict[UUID, dict[str, Any]] = {}
        self.progreso_buseta = 9500.0
        self.longitud = 10000.0
        self.progreso_paradero_m = 500.0

    async def buscar_buseta(self, empresa_id: UUID, numero_lateral: str) -> dict[str, Any] | None:
        return self.busetas.get((empresa_id, numero_lateral))

    async def guardar_posicion(self, buseta_id, servicio_id, lat, lng, velocidad_kmh, rumbo, reportada_en) -> bool:
        previa = self.guardadas.get(buseta_id)
        if previa and previa["reportada_en"] >= reportada_en:
            return False
        self.guardadas[buseta_id] = {
            "buseta_id": buseta_id, "numero_lateral": "1544", "empresa": "Sideral", "servicio_id": servicio_id,
            "lat": lat, "lng": lng, "velocidad_kmh": velocidad_kmh, "rumbo": rumbo, "reportada_en": reportada_en,
        }
        return True

    async def posiciones_de_ruta(self, ruta_id: UUID, ahora: datetime) -> list[dict[str, Any]]:
        return [p for p in self.guardadas.values() if p["servicio_id"] == SERVICIO_SIDERAL_ENEA]

    async def unidades_en_servicio(self, ruta_id: UUID, ahora: datetime) -> int:
        return 2 if ruta_id == RUTA_ENEA else 0

    async def posiciones_para_eta(self, servicio_ids, ruta_id, ahora) -> list[dict[str, Any]]:
        return [
            {"servicio_id": p["servicio_id"], "numero_lateral": p["numero_lateral"], "velocidad_kmh": p["velocidad_kmh"],
             "reportada_en": p["reportada_en"], "progreso_m": self.progreso_buseta}
            for p in self.guardadas.values() if p["servicio_id"] in servicio_ids
        ]

    async def limpiar_posiciones(self) -> None:
        self.guardadas.clear()

    async def turno_vigente(self, empresa_id: UUID, numero_lateral: str, instante: datetime) -> UUID | None:
        turno = self.turnos.get((empresa_id, numero_lateral))
        if turno and turno[0] <= instante.time().replace(tzinfo=None) <= turno[1]:
            return turno[2]
        return None

    async def ruta_de_servicio(self, servicio_id: UUID) -> UUID | None:
        return RUTA_ENEA

    async def ruta_activa_existe(self, ruta_id: UUID) -> bool:
        return ruta_id in (RUTA_ENEA, RUTA_VILLAMARIA)

    async def progreso_paradero(self, ruta_id: UUID, paradero_id: UUID) -> dict[str, Any] | None:
        if ruta_id != RUTA_ENEA or paradero_id != PARADERO_A:
            return None
        return {"progreso_m": self.progreso_paradero_m, "longitud_m": self.longitud}

    async def servicios_para_eta(self, ruta_id: UUID) -> list[dict[str, Any]]:
        return [
            {"servicio_id": SERVICIO_SIDERAL_ENEA, "empresa_nombre": "Sideral", "codigo_publico": "39", "estado": "activo",
             "duracion_estandar_min": 60},
            {"servicio_id": SERVICIO_SERVITURISMO_ENEA, "empresa_nombre": "Serviturismo", "codigo_publico": None,
             "estado": "activo", "duracion_estandar_min": 60},
        ]


class FuentesGpsEnMemoria:
    def __init__(self) -> None:
        self.usos: list[UUID] = []

    async def empresa_por_hash(self, hash_clave: str) -> dict[str, Any] | None:
        if hash_clave == hash_de_clave(CLAVE_SIDERAL):
            return {"credencial_id": CREDENCIAL, "empresa_id": EMPRESA_SIDERAL}
        return None

    async def marcar_uso(self, credencial_id: UUID, ahora: datetime) -> None:
        self.usos.append(credencial_id)


USUARIO_ADMIN = uuid4()
USUARIO_JEFE = uuid4()
USUARIO_PASAJERA = uuid4()
TOKENS = {
    "tok-admin": Identidad(str(USUARIO_ADMIN), Rol.ADMINISTRADOR),
    "tok-jefe": Identidad(str(USUARIO_JEFE), Rol.JEFE_OPERACIONES, str(EMPRESA_SIDERAL)),
    "tok-pasajera": Identidad(str(USUARIO_PASAJERA), Rol.PASAJERO),
}


class AutenticacionFalsa:
    async def verificar_token(self, jwt: str) -> Identidad:
        if jwt not in TOKENS:
            raise ErrorNoAutenticado("Sesión inválida o vencida.")
        return TOKENS[jwt]


class UsuariosEnMemoria:
    def __init__(self) -> None:
        self.perfiles = {
            USUARIO_ADMIN: {"usuario_id": USUARIO_ADMIN, "correo": "admin@busetasapp.example", "rol": "administrador",
                            "empresa_id": None, "empresa_nombre": None, "activo": True},
            USUARIO_JEFE: {"usuario_id": USUARIO_JEFE, "correo": "jefe@sideral.example", "rol": "jefe_operaciones",
                           "empresa_id": EMPRESA_SIDERAL, "empresa_nombre": "Sideral", "activo": True},
            USUARIO_PASAJERA: {"usuario_id": USUARIO_PASAJERA, "correo": "pasajera@correo.example", "rol": "pasajero",
                               "empresa_id": EMPRESA_SIDERAL, "empresa_nombre": "Sideral", "activo": True},
        }

    async def perfil(self, usuario_id: UUID) -> dict[str, Any] | None:
        return self.perfiles.get(usuario_id)


CUADRADO = [[-75.52, 5.06], [-75.50, 5.06], [-75.50, 5.08], [-75.52, 5.08], [-75.52, 5.06]]  # [lng, lat]


class SimulacionEnMemoria:
    def __init__(self, seguimiento: SeguimientoEnMemoria) -> None:
        self._seguimiento = seguimiento
        self.rodamientos_asegurados: list[Any] = []

    async def busetas_activas(self) -> list[dict[str, Any]]:
        return [
            {"buseta_id": BUSETA_1544, "numero_lateral": "1544", "empresa_id": EMPRESA_SIDERAL, "empresa_nombre": "Sideral"},
            {"buseta_id": BUSETA_2683, "numero_lateral": "2683", "empresa_id": EMPRESA_SERVITURISMO,
             "empresa_nombre": "Serviturismo"},
        ]

    async def trazado_de_ruta(self, ruta_id: UUID) -> list[list[float]] | None:
        return CUADRADO if ruta_id == RUTA_ENEA else None

    async def asegurar_rodamientos_demo(self, hoy: Any) -> list[str]:
        self.rodamientos_asegurados.append(hoy)
        return ["Rodamiento publicado de Sideral: ya existía"]

    async def limpiar_posiciones(self) -> None:
        await self._seguimiento.limpiar_posiciones()



def repositorios_en_memoria() -> Repositorios:
    seguimiento = SeguimientoEnMemoria()
    return Repositorios(
        rutas=RutasEnMemoria(), horarios=HorariosEnMemoria(), busqueda=BusquedaEnMemoria(),
        avisos=AvisosEnMemoria(), eventos_uso=EventosEnMemoria(), parametros=ParametrosEnMemoria(),
        seguimiento=seguimiento, fuentes_gps=FuentesGpsEnMemoria(), usuarios=UsuariosEnMemoria(),
        autenticacion=AutenticacionFalsa(), simulacion=SimulacionEnMemoria(seguimiento),
    )
