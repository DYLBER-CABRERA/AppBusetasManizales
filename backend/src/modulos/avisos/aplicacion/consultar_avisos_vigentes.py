"""Caso de uso `consultar_avisos_vigentes` (HU-J05, SM05, A05: lectura pública)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from modulos.avisos.dominio.puertos import RepositorioAvisos
from nucleo.reloj import PuertoReloj


class ConsultarAvisosVigentes:
    def __init__(self, avisos: RepositorioAvisos, reloj: PuertoReloj) -> None:
        self._avisos = avisos
        self._reloj = reloj

    async def __call__(self, ruta_id: UUID | None = None) -> list[dict[str, Any]]:
        return await self._avisos.vigentes(ruta_id, self._reloj.ahora())
