"""Puerto para registrar eventos de uso anónimos sin bloquear la respuesta (RD-17)."""

from __future__ import annotations

from typing import Literal, Protocol
from uuid import UUID

TipoEventoUso = Literal["mapa", "detalle_ruta", "horarios", "frecuencias", "busetas_vivo", "eta", "busqueda", "planificacion"]


class RegistradorEventosUso(Protocol):
    async def __call__(self, tipo: TipoEventoUso, ruta_id: UUID | None = None) -> None:
        """Nunca lanza: un fallo al registrar no debe afectar la consulta."""
        ...
