"""Caso de uso `consultar_estadisticas_uso` (HU-J06): el jefe ve su empresa; el administrador, la que indique o todas."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from modulos.estadisticas.dominio.puertos import RepositorioEventosUso
from nucleo.autorizacion import Identidad, Rol, exigir_rol
from nucleo.errores import ErrorValidacion
from nucleo.parametros import PuertoParametros


class ConsultarEstadisticasUso:
    def __init__(self, eventos: RepositorioEventosUso, parametros: PuertoParametros) -> None:
        self._eventos = eventos
        self._parametros = parametros

    async def __call__(
        self, identidad: Identidad | None, desde: date, hasta: date, empresa_id: UUID | None
    ) -> dict[str, Any]:
        actual = exigir_rol(identidad, Rol.JEFE_OPERACIONES, Rol.ADMINISTRADOR)
        if desde > hasta:
            raise ErrorValidacion("La fecha inicial no puede ser posterior a la final.")
        maximo = int(await self._parametros.numero("rango_max_estadisticas_dias"))
        if (hasta - desde).days + 1 > maximo:
            raise ErrorValidacion(f"El rango máximo es de {maximo} días.")
        # el jefe ignora empresaId: siempre su empresa (BR-03)
        empresa = UUID(actual.empresa_id or "") if actual.rol == Rol.JEFE_OPERACIONES else empresa_id
        datos = await self._eventos.estadisticas(empresa, desde, hasta)
        sin_datos = not any(datos.values())
        return {"sin_datos": sin_datos, **datos}
