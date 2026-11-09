"""Importación de rutas desde un CSV: vista previa (solo valida, no escribe ni llama a OSRM) y confirmación (crea las rutas
válidas reutilizando el caso de uso de `POST /rutas/desde-puntos`). Solo secretaría y administrador."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any
from uuid import UUID

from modulos.red.aplicacion.gestion import TITULO_AVISO_TRAZADO, RegistrarRutaDesdePuntos
from modulos.red.dominio.importacion_rutas import (
    ErrorImportacion,
    RutaImportada,
    leer,
    normalizar,
    puntos_ordenados,
    validar_ruta,
)
from modulos.red.dominio.puertos import RepositorioGestionRed
from nucleo.autorizacion import Identidad, Rol, exigir_rol
from nucleo.errores import ErrorAplicacion, ErrorConflictoNegocio
from nucleo.parametros import PuertoParametros

registro = logging.getLogger("busetasapp.importacion")

PRESUPUESTO_TOTAL_S = 60.0  # tiempo total pidiendo calles a OSRM en una importación (se reparte entre las rutas)
PRESUPUESTO_POR_RUTA_S = 25.0


def _error(e: ErrorImportacion) -> dict[str, Any]:
    return {"fila": e.fila, "columna": e.columna, "motivo": e.motivo, "mensaje": e.mensaje}


class _Analisis:
    def __init__(self, ruta: RutaImportada, estado: str, empresa_id: UUID | None) -> None:
        self.ruta = ruta
        self.estado = estado
        self.empresa_id = empresa_id
        self.nuevos: int | None = None
        self.reutilizados: int | None = None
        self.avisos: list[str] = []

    def como_dict(self) -> dict[str, Any]:
        r = self.ruta
        return {
            "nombre": r.nombre, "estado": self.estado, "puntos": len(r.puntos), "empresa": r.empresa,
            "codigo_publico": r.codigo_publico, "paraderos_nuevos": self.nuevos, "paraderos_reutilizados": self.reutilizados,
            "errores": [_error(e) for e in r.errores], "avisos": self.avisos,
        }


class _Base:
    def __init__(self, gestion: RepositorioGestionRed, parametros: PuertoParametros) -> None:
        self._g = gestion
        self._parametros = parametros

    async def _analizar(self, identidad: Identidad | None, contenido: bytes) -> tuple[list[_Analisis], list[ErrorImportacion], int, list[str]]:
        exigir_rol(identidad, Rol.SECRETARIA_MOVILIDAD, Rol.ADMINISTRADOR)
        lectura = leer(contenido)  # errores generales de formato: ErrorValidacion (400)
        caja = await self._parametros.objeto("caja_ciudad")
        radio = await self._parametros.numero("radio_reuso_paradero_m")
        empresas = {normalizar(e["nombre"]): e["id"] for e in await self._g.listar_empresas_activas()}
        analisis: list[_Analisis] = []
        for ruta in lectura.rutas:
            validar_ruta(ruta, caja)
            empresa_id = empresas.get(normalizar(ruta.empresa)) if ruta.empresa else None
            if ruta.empresa and empresa_id is None:
                ruta.errores.append(ErrorImportacion(ruta.fila_empresa, "empresa", "empresa_desconocida", "La empresa no existe o está inactiva."))
            duplicada = await self._g.ruta_nombre_existe(ruta.nombre)
            if duplicada:
                ruta.errores.append(ErrorImportacion(None, "ruta", "ruta_duplicada", "Ya existe una ruta con ese nombre; no se modifica."))
            estado = "duplicada" if duplicada else "con_errores" if ruta.errores else "valida"
            a = _Analisis(ruta, estado, empresa_id)
            if estado == "valida":
                await self._estimar_paraderos(a, radio)
            analisis.append(a)
        return analisis, lectura.errores_generales, lectura.total_filas, lectura.columnas_ignoradas

    async def _estimar_paraderos(self, a: _Analisis, radio: float) -> None:
        """Cuántos paraderos se reutilizarían y cuántos se crearían (solo lectura, mismas reglas que desde-puntos)."""
        usados: list[UUID] = []
        reutilizados = 0
        for p in puntos_ordenados(a.ruta):
            cercano = await self._g.paradero_cercano(p["lat"], p["lng"], radio, usados) if radio > 0 else None
            if cercano is not None:
                usados.append(cercano["id"])
                reutilizados += 1
        a.reutilizados, a.nuevos = reutilizados, len(a.ruta.puntos) - reutilizados
        if reutilizados:
            a.avisos.append(f"{reutilizados} punto(s) reutilizarán un paradero existente a {radio:g} m o menos.")
        a.avisos.append("El trazado por calles se calcula al confirmar; si un tramo no tiene ruta real quedará en línea recta.")


def _resumen(analisis: list[_Analisis]) -> dict[str, int]:
    return {
        "validas": sum(a.estado == "valida" for a in analisis), "con_errores": sum(a.estado == "con_errores" for a in analisis),
        "duplicadas": sum(a.estado == "duplicada" for a in analisis),
    }


class VistaPreviaImportacionRutas(_Base):
    async def __call__(self, identidad: Identidad | None, contenido: bytes) -> dict[str, Any]:
        analisis, generales, total, ignoradas = await self._analizar(identidad, contenido)
        return {
            "total_filas": total, "rutas": [a.como_dict() for a in analisis], "errores_generales": [_error(e) for e in generales],
            "columnas_ignoradas": ignoradas, "resumen": _resumen(analisis),
            "se_crearian": sum(a.estado == "valida" for a in analisis),
        }


class ConfirmarImportacionRutas(_Base):
    """Vuelve a leer y validar el archivo (no se confía en la vista previa) y crea solo las rutas válidas, de a una y en
    secuencia. Una ruta que falla al crearse queda en `omitidas`; las demás siguen."""

    def __init__(
        self, gestion: RepositorioGestionRed, parametros: PuertoParametros, registrar: RegistrarRutaDesdePuntos,
        monotonico: Callable[[], float] = time.monotonic, presupuesto_total_s: float = PRESUPUESTO_TOTAL_S,
    ) -> None:
        super().__init__(gestion, parametros)
        self._registrar = registrar
        self._monotonico = monotonico
        self._total = presupuesto_total_s

    async def __call__(self, identidad: Identidad | None, contenido: bytes) -> dict[str, Any]:
        analisis, generales, total, ignoradas = await self._analizar(identidad, contenido)
        inicio = self._monotonico()
        creadas: list[dict[str, Any]] = []
        omitidas: list[dict[str, Any]] = []
        for a in analisis:
            if a.estado != "valida":
                omitidas.append(a.como_dict())
                continue
            restante = max(0.0, self._total - (self._monotonico() - inicio))
            try:
                detalle = await self._registrar(
                    identidad, a.ruta.nombre, None, puntos_ordenados(a.ruta),
                    [{"empresa_id": a.empresa_id, "codigo_publico": a.ruta.codigo_publico, "codigo_interno": None}], False,
                    min(PRESUPUESTO_POR_RUTA_S, restante),
                )
            except Exception as exc:  # noqa: BLE001 - esta ruta no se creó; las demás siguen
                if isinstance(exc, ErrorAplicacion):
                    a.estado = "duplicada" if isinstance(exc, ErrorConflictoNegocio) and "nombre" in exc.mensaje.lower() else "con_errores"
                    a.ruta.errores.append(ErrorImportacion(None, None, exc.codigo.lower(), exc.mensaje))
                else:  # no se filtra el detalle del error ni se registra contenido del archivo
                    registro.warning("Falló la creación de una ruta importada (%s)", type(exc).__name__)
                    a.estado = "con_errores"
                    a.ruta.errores.append(ErrorImportacion(None, None, "error_interno", "No se pudo crear la ruta por un error interno; puedes reintentar."))
                omitidas.append(a.como_dict())
                continue
            creadas.append({
                "nombre": detalle["nombre"], "ruta_id": detalle["id"], "puntos": len(a.ruta.puntos),
                "avisos": [x["cuerpo"] for x in detalle["avisos"] if x["titulo"] == TITULO_AVISO_TRAZADO],
            })
        return {
            "creadas": creadas, "omitidas": omitidas, "errores_generales": [_error(e) for e in generales],
            "columnas_ignoradas": ignoradas, "total_filas": total,
            "resumen": {"creadas": len(creadas), "omitidas": len(omitidas)},
        }
