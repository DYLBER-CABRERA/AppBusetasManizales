"""Casos de uso de la Secretaría de Movilidad sobre la red (SM01 a SM04). Solo secretaría y administrador (BR-04)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from modulos.red.aplicacion.trazado_calles import ConstructorDeTrazado
from modulos.red.dominio.puertos import ProveedorAvisosVigentes, RepositorioGestionRed, RepositorioRutas
from modulos.red.dominio.puntos_ruta import DIRECCION_FICTICIA, nombre_automatico, validar_puntos
from nucleo.autorizacion import Identidad, Rol, exigir_rol
from nucleo.errores import ErrorConflictoNegocio, ErrorNoEncontrado, ErrorValidacion
from nucleo.parametros import PuertoParametros
from nucleo.reloj import PuertoReloj
from nucleo.version_optimista import verificar_version


def _gestion(identidad: Identidad | None) -> Identidad:
    return exigir_rol(identidad, Rol.SECRETARIA_MOVILIDAD, Rol.ADMINISTRADOR)


class _Base:
    def __init__(self, gestion: RepositorioGestionRed) -> None:
        self._g = gestion


# ---------- paraderos y hitos ----------


class ListarParaderos(_Base):
    async def __call__(self, identidad: Identidad | None) -> list[dict[str, Any]]:
        _gestion(identidad)
        return await self._g.listar_paraderos()


class CrearParadero(_Base):
    async def __call__(
        self, identidad: Identidad | None, nombre: str, direccion: str | None, lat: float, lng: float
    ) -> dict[str, Any]:
        _gestion(identidad)
        if await self._g.hay_paradero_duplicado(nombre.strip(), lat, lng, None):
            raise ErrorConflictoNegocio("Ya existe un paradero con ese nombre a menos de 20 m.")
        return await self._g.crear_paradero(nombre.strip(), direccion, lat, lng)


class EditarParadero(_Base):
    async def __call__(
        self, identidad: Identidad | None, paradero_id: UUID, cambios: dict[str, Any], version: int
    ) -> dict[str, Any]:
        _gestion(identidad)
        actual = await self._g.obtener_paradero(paradero_id)
        if actual is None:
            raise ErrorNoEncontrado("El paradero no existe.")
        verificar_version(version, actual["version"])
        nombre = (cambios.get("nombre") or actual["nombre"]).strip()
        lat = actual["lat"] if cambios.get("lat") is None else cambios["lat"]
        lng = actual["lng"] if cambios.get("lng") is None else cambios["lng"]
        if await self._g.hay_paradero_duplicado(nombre, lat, lng, paradero_id):
            raise ErrorConflictoNegocio("Ya existe un paradero con ese nombre a menos de 20 m.")
        return await self._g.editar_paradero(paradero_id, version, nombre, cambios.get("direccion"), lat, lng)


class EliminarParadero(_Base):
    async def __call__(self, identidad: Identidad | None, paradero_id: UUID, version: int, confirmar: bool) -> None:
        _gestion(identidad)
        actual = await self._g.obtener_paradero(paradero_id)
        if actual is None:
            raise ErrorNoEncontrado("El paradero no existe.")
        verificar_version(version, actual["version"])
        usadas = await self._g.rutas_que_usan_paradero(paradero_id)
        if usadas and not confirmar:
            raise ErrorConflictoNegocio(
                "El paradero lo usan estas rutas. Confirma para darlo de baja.", {"rutas": usadas}
            )
        await self._g.dar_de_baja_paradero(paradero_id, version)


class CrearHito(_Base):
    async def __call__(
        self, identidad: Identidad | None, nombre: str, tipo: str, alias: list[str], lat: float, lng: float
    ) -> dict[str, Any]:
        _gestion(identidad)
        return await self._g.crear_hito(nombre.strip(), tipo, [a.strip() for a in alias if a.strip()], lat, lng)


# ---------- rutas ----------


class _CasoRuta(_Base):
    def __init__(
        self, gestion: RepositorioGestionRed, rutas: RepositorioRutas, avisos: ProveedorAvisosVigentes, reloj: PuertoReloj
    ) -> None:
        super().__init__(gestion)
        self._rutas = rutas
        self._avisos = avisos
        self._reloj = reloj

    async def _detalle(self, ruta_id: UUID) -> dict[str, Any]:
        detalle = await self._rutas.obtener_detalle(ruta_id)
        if detalle is None:
            raise ErrorNoEncontrado("La ruta no existe o fue dada de baja.")
        detalle["avisos"] = await self._avisos.vigentes(ruta_id, self._reloj.ahora())
        return detalle

    async def _validar_paraderos(self, paradero_ids: list[UUID]) -> None:
        if len(set(paradero_ids)) != len(paradero_ids):
            raise ErrorValidacion("Un paradero no puede repetirse en la ruta.")
        if len(paradero_ids) < 2:
            raise ErrorValidacion("La ruta necesita al menos dos paraderos.")
        if not await self._g.paraderos_activos_existen(paradero_ids):
            raise ErrorNoEncontrado("Alguno de los paraderos no existe.")


class RegistrarRuta(_CasoRuta):
    async def __call__(
        self, identidad: Identidad | None, nombre: str, ruta_principal_id: UUID | None, paradero_ids: list[UUID],
        servicios: list[dict[str, Any]], confirmar_compartida: bool,
    ) -> dict[str, Any]:
        _gestion(identidad)
        await self._validar_paraderos(paradero_ids)
        empresas = [s["empresa_id"] for s in servicios]
        if len(set(empresas)) != len(empresas):
            raise ErrorValidacion("Una empresa no puede repetirse en la ruta.")
        if len(empresas) > 1 and not confirmar_compartida:
            raise ErrorConflictoNegocio("La ruta quedará compartida por varias empresas. Confirma para continuar.")
        if not await self._g.empresas_activas_existen(empresas):
            raise ErrorNoEncontrado("Alguna de las empresas no existe.")
        if ruta_principal_id is not None and not await self._g.ruta_principal_valida(ruta_principal_id):
            raise ErrorValidacion("La ruta principal no existe o ya es una variante.")
        ruta_id = await self._g.crear_ruta(nombre.strip(), ruta_principal_id, paradero_ids, servicios)
        return await self._detalle(ruta_id)


class RegistrarRutaDesdePuntos(_CasoRuta):
    """Ruta creada tocando puntos en el mapa: cada punto es un paradero de la ruta, en el orden tocado.

    - Un punto a ≤ `radio_reuso_paradero_m` (por omisión 20 m) de un paradero activo REUTILIZA ese paradero (un paradero puede
      estar en varias rutas); el nombre del punto se ignora y se usa el del paradero existente. Un paradero no se repite
      dentro de la misma ruta: si ya se usó, el punto crea uno nuevo.
    - Los demás puntos crean un paradero nuevo marcado «Paradero de ejemplo (ficticio)» en `direccion`, con el nombre dado o,
      si falta, «Paradero <NombreRuta> N» (N cuenta solo los paraderos nuevos sin nombre).
    - El trazado sigue calles reales (OSRM) entre paradas consecutivas, incluido el cierre último→primero (D-P02); en un
      tramo sin ruta real usa una recta y lo avisa en `avisos`. Los paraderos son exactamente los puntos tocados."""

    def __init__(self, gestion, rutas, avisos, reloj, parametros: PuertoParametros, trazado: ConstructorDeTrazado) -> None:  # noqa: ANN001
        super().__init__(gestion, rutas, avisos, reloj)
        self._parametros = parametros
        self._trazado = trazado

    async def __call__(
        self, identidad: Identidad | None, nombre: str, ruta_principal_id: UUID | None, puntos: list[dict[str, Any]],
        servicios: list[dict[str, Any]], confirmar_compartida: bool,
    ) -> dict[str, Any]:
        _gestion(identidad)
        nombre = " ".join(nombre.split())
        if len(nombre) < 2:
            raise ErrorValidacion("El nombre de la ruta es obligatorio.", [{"campo": "nombre", "motivo": "obligatorio"}])
        validar_puntos(puntos, await self._parametros.objeto("caja_ciudad"))
        empresas = [s["empresa_id"] for s in servicios]
        if len(set(empresas)) != len(empresas):
            raise ErrorValidacion("Una empresa no puede repetirse en la ruta.")
        if not await self._g.empresas_activas_existen(empresas):
            raise ErrorNoEncontrado("Alguna de las empresas no existe.")
        if len(empresas) > 1 and not confirmar_compartida:
            raise ErrorConflictoNegocio("La ruta quedará compartida por varias empresas. Confirma para continuar.")
        if ruta_principal_id is not None and not await self._g.ruta_principal_valida(ruta_principal_id):
            raise ErrorValidacion("La ruta principal no existe o ya es una variante.")
        if await self._g.ruta_nombre_existe(nombre):
            raise ErrorConflictoNegocio("Ya existe una ruta con ese nombre.")
        radio = await self._parametros.numero("radio_reuso_paradero_m")
        paraderos: list[dict[str, Any]] = []
        usados: list[UUID] = []
        numero = 0
        for p in puntos:
            cercano = await self._g.paradero_cercano(p["lat"], p["lng"], radio, usados) if radio > 0 else None
            if cercano is not None:
                usados.append(cercano["id"])
                paraderos.append({"id": cercano["id"], "nombre": cercano["nombre"], "lat": cercano["lat"], "lng": cercano["lng"]})
                continue
            propio = " ".join((p.get("nombre") or "").split())
            if not propio:
                numero += 1
            paraderos.append({
                "id": None, "nombre": propio or nombre_automatico(nombre, numero), "direccion": DIRECCION_FICTICIA,
                "lat": p["lat"], "lng": p["lng"],
            })
        trazado = await self._trazado.construir([(p["lat"], p["lng"]) for p in paraderos])
        ruta_id = await self._g.crear_ruta_con_paraderos(nombre, ruta_principal_id, paraderos, servicios, trazado.coordenadas)
        detalle = await self._detalle(ruta_id)
        if trazado.tramos_sin_ruta:  # aviso de la respuesta (no se guarda): qué tramos quedaron en línea recta
            detalle["avisos"] = [*detalle["avisos"], _aviso_tramos_en_recta(trazado.tramos_sin_ruta)]
        return detalle


def _aviso_tramos_en_recta(tramos: list[tuple[int, int]]) -> dict[str, Any]:
    from uuid import uuid4

    lista = ", ".join(f"{a}→{b}" for a, b in tramos)
    cuerpo = (
        f"Tramo {lista} sin ruta real, se usó línea recta." if len(tramos) == 1
        else f"Tramos sin ruta real, se usó línea recta: {lista}."
    )
    return {
        "id": uuid4(), "origen": "aplicativo", "empresa_nombre": None, "titulo": "Trazado parcialmente en línea recta",
        "cuerpo": cuerpo,
    }


class EditarRuta(_CasoRuta):
    async def __call__(
        self, identidad: Identidad | None, ruta_id: UUID, nombre: str | None, descripcion: str | None,
        paradero_ids: list[UUID] | None, version: int,
    ) -> dict[str, Any]:
        _gestion(identidad)
        actual = await self._rutas.obtener_detalle(ruta_id)
        if actual is None:
            raise ErrorNoEncontrado("La ruta no existe o fue dada de baja.")
        verificar_version(version, actual["version"])
        if paradero_ids is not None:
            await self._validar_paraderos(paradero_ids)
        await self._g.editar_ruta(ruta_id, version, nombre.strip() if nombre else None, descripcion, paradero_ids)
        return await self._detalle(ruta_id)


class EliminarRuta(_Base):
    def __init__(self, gestion: RepositorioGestionRed, rutas: RepositorioRutas, reloj: PuertoReloj) -> None:
        super().__init__(gestion)
        self._rutas = rutas
        self._reloj = reloj

    async def __call__(self, identidad: Identidad | None, ruta_id: UUID, version: int, confirmar: bool) -> None:
        _gestion(identidad)
        actual = await self._rutas.obtener_detalle(ruta_id)
        if actual is None:
            raise ErrorNoEncontrado("La ruta no existe o fue dada de baja.")
        verificar_version(version, actual["version"])
        futuros = await self._g.turnos_futuros_de_ruta(ruta_id, self._reloj.ahora().date())
        if futuros and not confirmar:
            raise ErrorConflictoNegocio(
                "La ruta tiene turnos futuros que se cancelarán. Confirma para darla de baja.", {"turnosFuturos": futuros}
            )
        await self._g.dar_de_baja_ruta(ruta_id, version)


class AsignarRutaAEmpresa(_Base):
    async def __call__(
        self, identidad: Identidad | None, ruta_id: UUID, empresa_id: UUID, codigo_publico: str | None,
        codigo_interno: str | None, confirmar_compartida: bool,
    ) -> dict[str, Any]:
        _gestion(identidad)
        if not await self._g.ruta_activa_existe(ruta_id):
            raise ErrorNoEncontrado("La ruta no existe o fue dada de baja.")
        if not await self._g.empresas_activas_existen([empresa_id]):
            raise ErrorNoEncontrado("La empresa no existe.")
        if await self._g.empresa_opera_ruta(ruta_id, empresa_id):
            raise ErrorConflictoNegocio("La empresa ya opera esta ruta.")
        if await self._g.empresas_que_operan_ruta(ruta_id) and not confirmar_compartida:
            raise ErrorConflictoNegocio("La ruta ya está asignada a otra empresa. Confirma para compartirla.")
        return await self._g.asignar_servicio(ruta_id, empresa_id, codigo_publico, codigo_interno)


class RetirarRutaDeEmpresa(_Base):
    def __init__(self, gestion: RepositorioGestionRed, reloj: PuertoReloj) -> None:
        super().__init__(gestion)
        self._reloj = reloj

    async def __call__(self, identidad: Identidad | None, servicio_id: UUID, version: int, confirmar: bool) -> None:
        _gestion(identidad)
        actual = await self._g.obtener_servicio(servicio_id)
        if actual is None:
            raise ErrorNoEncontrado("El servicio no existe.")
        verificar_version(version, actual["version"])
        futuros = await self._g.turnos_futuros_de_servicio(servicio_id, self._reloj.ahora().date())
        if futuros and not confirmar:
            raise ErrorConflictoNegocio(
                "El servicio tiene turnos futuros que se cancelarán. Confirma para retirarlo.", {"turnosFuturos": futuros}
            )
        await self._g.retirar_servicio(servicio_id, version, self._reloj.ahora().date())
