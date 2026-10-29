"""Lectura de `parametro_global` con caché de 60 s (docs/03 §2.5, A04). La escritura llega en B5."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from psycopg_pool import AsyncConnectionPool

from nucleo.parametros import VALORES_POR_DEFECTO

TTL_SEGUNDOS = 60.0


class ParametrosSql:
    def __init__(self, pool: AsyncConnectionPool, monotonico: Callable[[], float] = time.monotonic) -> None:
        self._pool = pool
        self._monotonico = monotonico
        self._cache: dict[str, Any] = {}
        self._vence = 0.0

    async def _valor(self, clave: str) -> Any:
        if self._monotonico() >= self._vence:
            async with self._pool.connection() as conexion:
                cursor = await conexion.execute("select clave, valor from parametro_global")
                filas = await cursor.fetchall()
            self._cache = {f["clave"]: f["valor"] for f in filas}
            self._vence = self._monotonico() + TTL_SEGUNDOS
        if clave in self._cache:
            return self._cache[clave]
        if clave in VALORES_POR_DEFECTO:
            return VALORES_POR_DEFECTO[clave]
        raise KeyError(clave)

    async def numero(self, clave: str) -> float:
        return float(await self._valor(clave))

    async def objeto(self, clave: str) -> dict[str, Any]:
        valor = await self._valor(clave)
        if not isinstance(valor, dict):
            raise TypeError(f"El parámetro {clave} no es un objeto")
        return valor
