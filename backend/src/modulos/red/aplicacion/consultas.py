"""Casos de uso de consulta pública del módulo red (HU-P01, HU-P02)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from modulos.red.dominio.puertos import ProveedorAvisosVigentes, RepositorioRutas
from nucleo.errores import ErrorNoEncontrado
from nucleo.parametros import PuertoParametros
from nucleo.reloj import PuertoReloj


class ConsultarRutasCercanas:
    def __init__(self, rutas: RepositorioRutas, parametros: PuertoParametros) -> None:
        self._rutas = rutas
        self._parametros = parametros

    async def __call__(self, lat: float, lng: float, radio_m: int | None = None) -> dict[str, Any]:
        radio = radio_m or int(await self._parametros.numero("radio_busqueda_m"))
        rutas = await self._rutas.rutas_cercanas(lat, lng, radio)
        paradero = None if rutas else await self._rutas.paradero_mas_cercano(lat, lng)
        return {"rutas": rutas, "paradero_mas_cercano": paradero}


class ListarRutas:
    def __init__(self, rutas: RepositorioRutas) -> None:
        self._rutas = rutas

    async def __call__(self) -> list[dict[str, Any]]:
        return await self._rutas.listar_activas()


class ObtenerDetalleRuta:
    def __init__(self, rutas: RepositorioRutas, avisos: ProveedorAvisosVigentes, reloj: PuertoReloj) -> None:
        self._rutas = rutas
        self._avisos = avisos
        self._reloj = reloj

    async def __call__(self, ruta_id: UUID) -> dict[str, Any]:
        detalle = await self._rutas.obtener_detalle(ruta_id)
        if detalle is None:
            raise ErrorNoEncontrado("La ruta no existe o fue dada de baja.")
        detalle["avisos"] = await self._avisos.vigentes(ruta_id, self._reloj.ahora())
        return detalle


class ConsultarParaderosCercanos:
    def __init__(self, rutas: RepositorioRutas, parametros: PuertoParametros) -> None:
        self._rutas = rutas
        self._parametros = parametros

    async def __call__(
        self, lat: float, lng: float, radio_m: int | None = None, ruta_id: UUID | None = None
    ) -> list[dict[str, Any]]:
        radio = radio_m or int(await self._parametros.numero("radio_busqueda_m"))
        return await self._rutas.paraderos_cercanos(lat, lng, radio, ruta_id)


class ListarEmpresas:
    def __init__(self, rutas: RepositorioRutas) -> None:
        self._rutas = rutas

    async def __call__(self) -> list[dict[str, Any]]:
        return await self._rutas.listar_empresas()
