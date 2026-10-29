"""Puertos de salida del módulo avisos (B2: lectura)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from modulos.avisos.dominio.politica import DefinicionAviso


class RepositorioAvisos(Protocol):
    async def vigentes(self, ruta_id: UUID | None, ahora: datetime) -> list[dict[str, Any]]:
        """Avisos activos con `desde <= ahora` y sin vencer. Con `ruta_id`: los que afectan esa ruta o sus paraderos."""
        ...

    # ---- publicación y retiro (B4) ----

    async def rutas_de_empresa(self, empresa_id: UUID) -> set[UUID]:
        """Rutas activas que opera la empresa (servicios no dados de baja)."""
        ...

    async def existen_destinos(self, ruta_ids: list[UUID], paradero_ids: list[UUID]) -> bool: ...

    async def crear(
        self, definicion: DefinicionAviso, autor_id: UUID, titulo: str, cuerpo: str, desde: datetime, hasta: datetime | None,
        ruta_ids: list[UUID], paradero_ids: list[UUID],
    ) -> dict[str, Any]: ...

    async def obtener_activo(self, aviso_id: UUID) -> dict[str, Any] | None:
        """origen, empresa_id del aviso con estado `activo`; None si no existe o ya fue retirado."""
        ...

    async def retirar(self, aviso_id: UUID) -> None: ...
