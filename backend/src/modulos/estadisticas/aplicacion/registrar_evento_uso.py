"""Caso de uso `registrar_evento_uso`: nunca propaga errores (no bloquea ni rompe la consulta pública)."""

from __future__ import annotations

import logging
from uuid import UUID

from modulos.estadisticas.dominio.puertos import RepositorioEventosUso

registro = logging.getLogger("busetasapp.estadisticas")


class RegistrarEventoUso:
    def __init__(self, eventos: RepositorioEventosUso) -> None:
        self._eventos = eventos

    async def __call__(self, tipo: str, ruta_id: UUID | None = None) -> None:
        try:
            await self._eventos.registrar(tipo, ruta_id)
        except Exception as exc:  # noqa: BLE001 - el registro de uso es accesorio
            registro.warning("No se pudo registrar el evento de uso (%s)", type(exc).__name__)
