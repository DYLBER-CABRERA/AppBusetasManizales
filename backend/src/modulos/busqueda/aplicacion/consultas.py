"""Casos de uso de búsqueda (HU-P08, HU-P09)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from modulos.busqueda.dominio.puertos import (
    ProveedorParaderoCercano,
    ProveedorResumenesRuta,
    RepositorioBusqueda,
)
from modulos.busqueda.dominio.servicios import normalizar_consulta, patron_contiene
from nucleo.errores import ErrorNoEncontrado, ErrorValidacion
from nucleo.parametros import PuertoParametros


def _consulta(texto: str) -> tuple[str, str]:
    normalizado = normalizar_consulta(texto)
    if not normalizado:
        raise ErrorValidacion("Escribe qué quieres buscar.")
    return patron_contiene(normalizado), normalizado


class BuscarRutasPorTexto:
    def __init__(self, busqueda: RepositorioBusqueda, rutas: ProveedorResumenesRuta) -> None:
        self._busqueda = busqueda
        self._rutas = rutas

    async def __call__(self, texto: str) -> list[dict[str, Any]]:
        patron, normalizado = _consulta(texto)
        return await self._rutas.resumenes(await self._busqueda.buscar_rutas(patron, normalizado))


class BuscarHitos:
    def __init__(self, busqueda: RepositorioBusqueda) -> None:
        self._busqueda = busqueda

    async def __call__(self, texto: str) -> list[dict[str, Any]]:
        patron, normalizado = _consulta(texto)
        return await self._busqueda.buscar_hitos(patron, normalizado)


class ConsultarRutasPorHito:
    def __init__(
        self,
        busqueda: RepositorioBusqueda,
        rutas: ProveedorResumenesRuta,
        paraderos: ProveedorParaderoCercano,
        parametros: PuertoParametros,
    ) -> None:
        self._busqueda = busqueda
        self._rutas = rutas
        self._paraderos = paraderos
        self._parametros = parametros

    async def __call__(self, hito_id: UUID) -> dict[str, Any]:
        hito = await self._busqueda.obtener_hito(hito_id)
        if hito is None:
            raise ErrorNoEncontrado("El hito no existe.")
        radio = int(await self._parametros.numero("radio_hito_m"))
        distancias = await self._busqueda.rutas_por_hito(hito_id, radio)
        rutas = await self._rutas.resumenes(list(distancias), distancias)
        if rutas:
            return {"cobertura": True, "rutas": rutas, "paradero_mas_cercano": None}
        paradero = await self._paraderos.paradero_mas_cercano(hito["lat"], hito["lng"])
        return {"cobertura": False, "rutas": [], "paradero_mas_cercano": paradero}
