"""Router del módulo red. Solo traduce HTTP. Consulta pública (B2) y gestión de la Secretaría (B5)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from modulos.red.aplicacion.consultas import (
    ConsultarParaderosCercanos,
    ConsultarRutasCercanas,
    ListarEmpresas,
    ListarRutas,
    ObtenerDetalleRuta,
)
from modulos.red.aplicacion.gestion import (
    AsignarRutaAEmpresa,
    CrearHito,
    CrearParadero,
    EditarParadero,
    EditarRuta,
    EliminarParadero,
    EliminarRuta,
    ListarParaderos,
    RegistrarRuta,
    RegistrarRutaDesdePuntos,
    RetirarRutaDeEmpresa,
)
from modulos.red.aplicacion.importacion import ConfirmarImportacionRutas, VistaPreviaImportacionRutas
from modulos.red.dominio.importacion_rutas import MAX_BYTES, PLANTILLA, error_archivo_muy_grande
from modulos.red.infraestructura.esquemas import (
    Empresa,
    Hito,
    HitoCrear,
    Paradero,
    ParaderoCercano,
    ParaderoCrear,
    ParaderoEditar,
    ResultadoImportacion,
    RutaCrear,
    RutaDesdePuntos,
    RutaDetalle,
    RutaEditar,
    RutaResumen,
    RutasCercanas,
    ServicioAsignar,
    ServicioRuta,
    VistaPreviaImportacion,
)
from nucleo.autorizacion import Identidad, Rol
from nucleo.dependencias import RegistroUso, caso, requiere_rol
from nucleo.esquemas import errores

router = APIRouter(tags=["Red"])

_gestion = Depends(requiere_rol(Rol.SECRETARIA_MOVILIDAD, Rol.ADMINISTRADOR))


@router.get("/rutas/cercanas", response_model=RutasCercanas, responses=errores(400))
async def consultar_rutas_cercanas(
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
    radio_m: int | None = Query(default=None, alias="radioM", ge=50, le=5000),
    caso_uso: ConsultarRutasCercanas = Depends(caso("consultar_rutas_cercanas")),
    uso: RegistroUso = Depends(RegistroUso),
) -> dict:
    resultado = await caso_uso(lat, lng, radio_m)
    uso("mapa")
    return resultado


@router.get("/rutas", response_model=list[RutaResumen])
async def listar_rutas(
    caso_uso: ListarRutas = Depends(caso("listar_rutas")), uso: RegistroUso = Depends(RegistroUso)
) -> list[dict]:
    resultado = await caso_uso()
    uso("mapa")
    return resultado


async def _leer_cuerpo(request: Request) -> bytes:
    """El CSV llega como cuerpo crudo (`Content-Type: text/csv`). Se corta apenas pasa el máximo, sin cargarlo entero."""
    declarado = request.headers.get("content-length", "")
    if declarado.isdigit() and int(declarado) > MAX_BYTES:
        raise error_archivo_muy_grande()
    partes: list[bytes] = []
    total = 0
    async for trozo in request.stream():
        total += len(trozo)
        if total > MAX_BYTES:
            raise error_archivo_muy_grande()
        partes.append(trozo)
    return b"".join(partes)


_CUERPO_CSV = {"requestBody": {"required": True, "content": {"text/csv": {"schema": {"type": "string", "format": "binary"}}}}}


@router.get(
    "/rutas/importacion/plantilla", response_class=Response, responses={200: {"content": {"text/csv": {}}}, **errores(401, 403)},
)
async def descargar_plantilla_importacion(_: Identidad = _gestion) -> Response:
    """Plantilla CSV (UTF-8 con BOM para Excel) con la ruta de ejemplo Fátima → Chipre."""
    return Response(
        content="\ufeff" + PLANTILLA, media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="plantilla_importacion_rutas.csv"'},
    )


@router.post(
    "/rutas/importacion/vista-previa", response_model=VistaPreviaImportacion, openapi_extra=_CUERPO_CSV,
    responses=errores(400, 401, 403),
)
async def vista_previa_importacion_rutas(
    request: Request,
    identidad: Identidad = _gestion,
    caso_uso: VistaPreviaImportacionRutas = Depends(caso("vista_previa_importacion_rutas")),
) -> dict:
    """Valida el CSV y dice qué rutas se crearían. NO escribe nada y NO llama a OSRM."""
    return await caso_uso(identidad, await _leer_cuerpo(request))


@router.post(
    "/rutas/importacion/confirmar", response_model=ResultadoImportacion, status_code=201, openapi_extra=_CUERPO_CSV,
    responses={200: {"model": ResultadoImportacion, "description": "No se creó ninguna ruta"}, **errores(400, 401, 403)},
)
async def confirmar_importacion_rutas(
    request: Request,
    respuesta: Response,
    identidad: Identidad = _gestion,
    caso_uso: ConfirmarImportacionRutas = Depends(caso("confirmar_importacion_rutas")),
) -> dict:
    """Reenvía el mismo CSV: se valida de nuevo y se crean solo las rutas válidas (una por una)."""
    resultado = await caso_uso(identidad, await _leer_cuerpo(request))
    if not resultado["creadas"]:
        respuesta.status_code = 200
    return resultado


@router.get("/rutas/{ruta_id}", response_model=RutaDetalle, responses=errores(404))
async def obtener_detalle_ruta(
    ruta_id: UUID,
    caso_uso: ObtenerDetalleRuta = Depends(caso("obtener_detalle_ruta")),
    uso: RegistroUso = Depends(RegistroUso),
) -> dict:
    resultado = await caso_uso(ruta_id)
    uso("detalle_ruta", ruta_id)
    return resultado


@router.get("/paraderos/cercanos", response_model=list[ParaderoCercano], responses=errores(400))
async def consultar_paraderos_cercanos(
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
    radio_m: int | None = Query(default=None, alias="radioM", ge=50, le=5000),
    ruta_id: UUID | None = Query(default=None, alias="rutaId"),
    caso_uso: ConsultarParaderosCercanos = Depends(caso("consultar_paraderos_cercanos")),
    uso: RegistroUso = Depends(RegistroUso),
) -> list[dict]:
    resultado = await caso_uso(lat, lng, radio_m, ruta_id)
    uso("mapa", ruta_id)
    return resultado


@router.get("/empresas", response_model=list[Empresa])
async def listar_empresas(caso_uso: ListarEmpresas = Depends(caso("listar_empresas"))) -> list[dict]:
    return await caso_uso()


# ---- Secretaría de Movilidad (S) y administrador (A) ----


@router.post("/rutas", response_model=RutaDetalle, status_code=201, responses=errores(400, 401, 403, 404, 409))
async def registrar_ruta(
    cuerpo: RutaCrear,
    identidad: Identidad = _gestion,
    caso_uso: RegistrarRuta = Depends(caso("registrar_ruta")),
) -> dict:
    return await caso_uso(
        identidad, cuerpo.nombre, cuerpo.ruta_principal_id, cuerpo.paradero_ids,
        [sv.model_dump() for sv in cuerpo.servicios], cuerpo.confirmar_compartida,
    )


@router.post("/rutas/desde-puntos", response_model=RutaDetalle, status_code=201, responses=errores(400, 401, 403, 404, 409))
async def registrar_ruta_desde_puntos(
    cuerpo: RutaDesdePuntos,
    identidad: Identidad = _gestion,
    caso_uso: RegistrarRutaDesdePuntos = Depends(caso("registrar_ruta_desde_puntos")),
) -> dict:
    return await caso_uso(
        identidad, cuerpo.nombre, cuerpo.ruta_principal_id, [p.model_dump() for p in cuerpo.puntos],
        [sv.model_dump() for sv in cuerpo.servicios], cuerpo.confirmar_compartida,
    )


@router.put("/rutas/{ruta_id}", response_model=RutaDetalle, responses=errores(400, 401, 403, 404, 409))
async def editar_ruta(
    ruta_id: UUID,
    cuerpo: RutaEditar,
    identidad: Identidad = _gestion,
    caso_uso: EditarRuta = Depends(caso("editar_ruta")),
) -> dict:
    return await caso_uso(identidad, ruta_id, cuerpo.nombre, cuerpo.descripcion, cuerpo.paradero_ids, cuerpo.version)


@router.delete("/rutas/{ruta_id}", status_code=204, responses=errores(401, 403, 404, 409))
async def eliminar_ruta(
    ruta_id: UUID,
    version: int = Query(ge=1),
    confirmar: bool = False,
    identidad: Identidad = _gestion,
    caso_uso: EliminarRuta = Depends(caso("eliminar_ruta")),
) -> Response:
    await caso_uso(identidad, ruta_id, version, confirmar)
    return Response(status_code=204)


@router.post(
    "/rutas/{ruta_id}/servicios", response_model=ServicioRuta, status_code=201, responses=errores(400, 401, 403, 404, 409)
)
async def asignar_ruta_a_empresa(
    ruta_id: UUID,
    cuerpo: ServicioAsignar,
    identidad: Identidad = _gestion,
    caso_uso: AsignarRutaAEmpresa = Depends(caso("asignar_ruta_a_empresa")),
) -> dict:
    return await caso_uso(
        identidad, ruta_id, cuerpo.empresa_id, cuerpo.codigo_publico, cuerpo.codigo_interno, cuerpo.confirmar_compartida
    )


@router.delete("/servicios/{servicio_id}", status_code=204, responses=errores(401, 403, 404, 409))
async def retirar_ruta_de_empresa(
    servicio_id: UUID,
    version: int = Query(ge=1),
    confirmar: bool = False,
    identidad: Identidad = _gestion,
    caso_uso: RetirarRutaDeEmpresa = Depends(caso("retirar_ruta_de_empresa")),
) -> Response:
    await caso_uso(identidad, servicio_id, version, confirmar)
    return Response(status_code=204)


@router.get("/paraderos", response_model=list[Paradero], responses=errores(401, 403))
async def listar_paraderos(
    identidad: Identidad = _gestion, caso_uso: ListarParaderos = Depends(caso("listar_paraderos"))
) -> list[dict]:
    return await caso_uso(identidad)


@router.post("/paraderos", response_model=Paradero, status_code=201, responses=errores(400, 401, 403, 409))
async def crear_paradero(
    cuerpo: ParaderoCrear,
    identidad: Identidad = _gestion,
    caso_uso: CrearParadero = Depends(caso("crear_paradero")),
) -> dict:
    return await caso_uso(identidad, cuerpo.nombre, cuerpo.direccion, cuerpo.lat, cuerpo.lng)


@router.put("/paraderos/{paradero_id}", response_model=Paradero, responses=errores(400, 401, 403, 404, 409))
async def editar_paradero(
    paradero_id: UUID,
    cuerpo: ParaderoEditar,
    identidad: Identidad = _gestion,
    caso_uso: EditarParadero = Depends(caso("editar_paradero")),
) -> dict:
    cambios = cuerpo.model_dump(exclude={"version"})
    return await caso_uso(identidad, paradero_id, cambios, cuerpo.version)


@router.delete("/paraderos/{paradero_id}", status_code=204, responses=errores(401, 403, 404, 409))
async def eliminar_paradero(
    paradero_id: UUID,
    version: int = Query(ge=1),
    confirmar: bool = False,
    identidad: Identidad = _gestion,
    caso_uso: EliminarParadero = Depends(caso("eliminar_paradero")),
) -> Response:
    await caso_uso(identidad, paradero_id, version, confirmar)
    return Response(status_code=204)


@router.post("/hitos", response_model=Hito, status_code=201, responses=errores(400, 401, 403))
async def crear_hito(
    cuerpo: HitoCrear,
    identidad: Identidad = _gestion,
    caso_uso: CrearHito = Depends(caso("crear_hito")),
) -> dict:
    return await caso_uso(identidad, cuerpo.nombre, cuerpo.tipo, cuerpo.alias, cuerpo.lat, cuerpo.lng)
