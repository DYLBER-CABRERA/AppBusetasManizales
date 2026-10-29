"""Puertos de salida del módulo horarios (B2: lectura)."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

Registro = dict[str, Any]


class RepositorioHorarios(Protocol):
    async def ruta_activa_existe(self, ruta_id: UUID) -> bool: ...

    async def servicios_de_ruta(self, ruta_id: UUID) -> list[Registro]:
        """Servicios no dados de baja: servicio_id, empresa_id, empresa_nombre, codigo_publico, version."""
        ...

    async def horarios_de(self, servicio_ids: list[UUID]) -> list[Registro]:
        """servicio_id, tipo_dia, primera_salida (time), ultima_salida (time), cierre (time|None), nota."""
        ...

    async def frecuencias_de(self, servicio_ids: list[UUID]) -> list[Registro]:
        """servicio_id, tipo_dia, inicio_minuto, fin_minuto, minutos_min, minutos_max, nota."""
        ...
