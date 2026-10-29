"""Puerto de lectura de parámetros globales (tabla `parametro_global`, docs/03 §6)."""

from __future__ import annotations

from typing import Any, Protocol

# Valores por defecto de docs/03 §6; se usan solo si la fila no existe en la BD.
VALORES_POR_DEFECTO: dict[str, Any] = {
    "radio_busqueda_m": 800,
    "radio_caminata_m": 500,
    "radio_hito_m": 300,
    "velocidad_default_kmh": 20,
    "umbral_posicion_obsoleta_s": 60,
    "intervalo_refresco_cliente_s": 5,
    "distancia_aviso_llegada_m": 300,
    "enfriamiento_alerta_min": 10,
    "umbral_desvio_m": 100,
    "longitud_max_aviso": 500,
    "max_opciones_viaje": 3,
    "dias_max_rodamiento_adelante": 15,
    "rango_max_estadisticas_dias": 365,
    # Provisional (docs/03 §6): el equipo debe validarlo con el mapa.
    "caja_ciudad": {"minLat": 4.95, "maxLat": 5.20, "minLng": -75.65, "maxLng": -75.40},
}


class PuertoParametros(Protocol):
    async def numero(self, clave: str) -> float:
        """Valor numérico del parámetro (caché ≤ 60 s en el adaptador)."""
        ...

    async def objeto(self, clave: str) -> dict[str, Any]:
        """Valor JSON de tipo objeto (p. ej. `caja_ciudad`)."""
        ...
