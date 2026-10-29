"""Puertos de salida del módulo operación (B4). Todos los métodos reciben el `empresa_id` del jefe (sale del token)."""

from __future__ import annotations

from datetime import date
from typing import Any, Protocol
from uuid import UUID

from modulos.operacion.dominio.validador_rodamiento import TurnoDato

Registro = dict[str, Any]


class RepositorioOperacion(Protocol):
    async def servicios_de_empresa(self, empresa_id: UUID) -> list[Registro]: ...

    # busetas
    async def listar_busetas(self, empresa_id: UUID) -> list[Registro]: ...

    async def crear_buseta(self, empresa_id: UUID, numero_lateral: str, placa: str | None) -> Registro:
        """ErrorConflictoNegocio si el número lateral ya existe en la empresa."""
        ...

    async def editar_buseta(self, empresa_id: UUID, buseta_id: UUID, version: int, cambios: Registro) -> Registro:
        """ErrorNoEncontrado / ErrorConflictoVersion / ErrorConflictoNegocio."""
        ...

    # conductores
    async def listar_conductores(self, empresa_id: UUID) -> list[Registro]: ...

    async def crear_conductor(self, empresa_id: UUID, nombre: str, codigo: str | None) -> Registro: ...

    async def editar_conductor(self, empresa_id: UUID, conductor_id: UUID, version: int, cambios: Registro) -> Registro: ...

    # rodamientos
    async def recursos_de_empresa(self, empresa_id: UUID) -> Registro:
        """{servicios: {id: duracion_min|None}, busetas: {id: numero_lateral}, conductores: {id: nombre}}."""
        ...

    async def listar_rodamientos(self, empresa_id: UUID, desde: date | None, hasta: date | None) -> list[Registro]: ...

    async def obtener_rodamiento(self, empresa_id: UUID, rodamiento_id: UUID) -> Registro | None:
        """Cabecera (rodamiento_id, fecha, estado, version) y `turnos` (TurnoDato en `datos` + estado)."""
        ...

    async def rodamiento_de_fecha(self, empresa_id: UUID, fecha: date) -> Registro | None: ...

    async def crear_rodamiento(self, empresa_id: UUID, fecha: date, turnos: list[TurnoDato]) -> UUID: ...

    async def reemplazar_turnos(self, rodamiento_id: UUID, version: int, turnos: list[TurnoDato]) -> int: ...

    async def cambiar_estado(self, rodamiento_id: UUID, version: int, estado: str, usuario_id: UUID) -> int: ...
