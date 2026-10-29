"""Casos de uso `publicar_aviso` y `retirar_aviso` (HU-J05, SM05, A05)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from modulos.avisos.dominio.politica import definir_aviso, puede_retirar
from modulos.avisos.dominio.puertos import RepositorioAvisos
from nucleo.autorizacion import Identidad, exigir_identidad
from nucleo.emisor_eventos import AVISO_PUBLICADO, EmisorEventos
from nucleo.errores import ErrorNoAutorizado, ErrorNoEncontrado, ErrorValidacion
from nucleo.parametros import PuertoParametros
from nucleo.reloj import PuertoReloj


class PublicarAviso:
    def __init__(
        self, avisos: RepositorioAvisos, parametros: PuertoParametros, reloj: PuertoReloj, emisor: EmisorEventos
    ) -> None:
        self._avisos = avisos
        self._parametros = parametros
        self._reloj = reloj
        self._emisor = emisor

    async def __call__(
        self, identidad: Identidad | None, titulo: str, cuerpo: str, tipo_cambio: str | None, ruta_ids: list[UUID],
        paradero_ids: list[UUID], desde: datetime | None, hasta: datetime | None,
    ) -> dict[str, Any]:
        actual = exigir_identidad(identidad)
        maximo = int(await self._parametros.numero("longitud_max_aviso"))
        definicion = definir_aviso(actual, titulo, cuerpo, tipo_cambio, maximo, bool(ruta_ids), bool(paradero_ids))
        ahora = self._reloj.ahora()
        inicio = desde or ahora
        if hasta is not None and hasta <= inicio:
            raise ErrorValidacion("La fecha de fin debe ser posterior a la de inicio.")
        if definicion.empresa_id is not None:  # el jefe solo publica sobre rutas que su empresa opera
            propias = await self._avisos.rutas_de_empresa(definicion.empresa_id)
            if any(r not in propias for r in ruta_ids):
                raise ErrorNoEncontrado("Una de las rutas no existe en tu empresa.")
        elif not await self._avisos.existen_destinos(ruta_ids, paradero_ids):
            raise ErrorNoEncontrado("Una de las rutas o paraderos no existe.")
        aviso = await self._avisos.crear(
            definicion, UUID(actual.usuario_id), titulo.strip(), cuerpo.strip(), inicio, hasta, ruta_ids, paradero_ids
        )
        await self._emisor.emitir(AVISO_PUBLICADO, {"aviso_id": aviso["id"], "ruta_ids": list(aviso["ruta_ids"])})
        return aviso


class RetirarAviso:
    def __init__(self, avisos: RepositorioAvisos) -> None:
        self._avisos = avisos

    async def __call__(self, identidad: Identidad | None, aviso_id: UUID) -> None:
        actual = exigir_identidad(identidad)
        aviso = await self._avisos.obtener_activo(aviso_id)
        if aviso is None:
            raise ErrorNoEncontrado("El aviso no existe.")
        permiso = puede_retirar(actual, aviso["origen"], str(aviso["empresa_id"]) if aviso["empresa_id"] else None)
        if permiso is None:
            raise ErrorNoEncontrado("El aviso no existe.")
        if not permiso:
            raise ErrorNoAutorizado("No puedes retirar este aviso.")
        await self._avisos.retirar(aviso_id)
