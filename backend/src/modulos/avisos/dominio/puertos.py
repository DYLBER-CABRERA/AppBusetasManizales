"""Puertos de salida del módulo avisos (B2: lectura)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


class RepositorioAvisos(Protocol):
    async def vigentes(self, ruta_id: UUID | None, ahora: datetime) -> list[dict[str, Any]]:
        """Avisos activos con `desde <= ahora` y sin vencer. Con `ruta_id`: los que afectan esa ruta o sus paraderos."""
        ...
