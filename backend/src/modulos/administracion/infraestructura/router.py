"""Router del módulo administración (A), perfil `GET /yo` y panel de demo. `/yo` y `/demo/*` implementados (B3b);
el resto de A01 a A04 (B5).

Formas tomadas de docs/03 y, donde 03 no las define, de docs/referencia/openapi.yaml.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import Field

from modulos.administracion.aplicacion.casos_de_uso import ConsultarEstadoDemo, EjecutarEscenarioDemo, ObtenerPerfil
from modulos.administracion.aplicacion.gestion import (
    ConfigurarParametro,
    CrearCredencialGps,
    CrearEmpresa,
    CrearUsuario,
    EditarEmpresa,
    EditarUsuario,
    ListarCredencialesGps,
    ListarEmpresasAdmin,
    ListarParametros,
    ListarRoles,
    ListarUsuarios,
    RevocarCredencialGps,
)
from nucleo.autorizacion import Identidad, Rol
from nucleo.dependencias import caso, requiere_rol
from nucleo.esquemas import EsquemaBase, errores

router = APIRouter(tags=["Administración"])

_admin = Depends(requiere_rol(Rol.ADMINISTRADOR))
RolTexto = Literal["pasajero", "jefe_operaciones", "secretaria_movilidad", "administrador"]


class Perfil(EsquemaBase):
    usuario_id: UUID
    correo: str
    rol: RolTexto
    empresa_id: UUID | None = None
    empresa_nombre: str | None = None


class Usuario(EsquemaBase):
    id: UUID
    correo: str
    nombre: str | None = None
    rol: RolTexto
    empresa_id: UUID | None = None
    activo: bool
    version: int


class UsuarioCrear(EsquemaBase):
    correo: str = Field(max_length=254)
    nombre: str | None = Field(default=None, max_length=120)
    rol: RolTexto
    empresa_id: UUID | None = Field(default=None, description="Obligatoria si el rol es jefe_operaciones")


class UsuarioEditar(EsquemaBase):
    nombre: str | None = Field(default=None, max_length=120)
    rol: RolTexto | None = None
    empresa_id: UUID | None = None
    activo: bool | None = None
    version: int = Field(ge=1)


class RolConPermisos(EsquemaBase):
    rol: RolTexto
    permisos: list[str]


class EmpresaAdmin(EsquemaBase):
    id: UUID
    nombre: str
    estado: Literal["activo", "baja"]
    version: int


class EmpresaCrear(EsquemaBase):
    nombre: str = Field(min_length=2, max_length=120)


class EmpresaEditar(EsquemaBase):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    estado: Literal["activo", "baja"] | None = None
    version: int = Field(ge=1)


class CredencialGps(EsquemaBase):
    id: UUID
    nombre: str
    activa: bool
    creada_en: datetime
    ultimo_uso: datetime | None = None


class CredencialGpsCrear(EsquemaBase):
    nombre: str = Field(min_length=1, max_length=80)


class CredencialGpsCreada(CredencialGps):
    clave: str = Field(description="Se muestra una sola vez; en BD solo queda el hash")


class Parametro(EsquemaBase):
    clave: str
    valor: Any
    descripcion: str
    minimo: float | None = None
    maximo: float | None = None
    version: int


class ParametroActualizar(EsquemaBase):
    valor: Any
    version: int = Field(ge=1)


class EscenarioDemo(EsquemaBase):
    tipo: Literal[
        "perder_senal", "restaurar_senal", "desvio", "fijar_hora", "acelerar",
        "activar_gps_empresa", "reiniciar_simulacion",
    ]
    numero_lateral: str | None = None
    empresa_id: UUID | None = None
    duracion_s: int | None = Field(default=None, ge=1)
    hora: str | None = Field(default=None, pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$", description="null vuelve al reloj real")
    factor: float | None = Field(default=None, ge=0.5, le=5)
    activo: bool | None = None


class BusetaDemo(EsquemaBase):
    numero_lateral: str
    empresa: str
    emitiendo: bool
    ultima_posicion: datetime | None = None


class EstadoDemo(EsquemaBase):
    reloj_simulado: datetime | None = None
    factor: float
    busetas: list[BusetaDemo]


@router.get("/yo", response_model=Perfil, responses=errores(401))
async def obtener_perfil(
    identidad: Identidad = Depends(requiere_rol(*Rol)),
    caso_uso: ObtenerPerfil = Depends(caso("obtener_perfil")),
) -> dict:
    return await caso_uso(identidad)


@router.get("/admin/usuarios", response_model=list[Usuario], responses=errores(401, 403))
async def listar_usuarios(
    correo: str | None = Query(default=None, max_length=80),
    identidad: Identidad = _admin,
    caso_uso: ListarUsuarios = Depends(caso("listar_usuarios")),
) -> list[dict]:
    return await caso_uso(identidad, correo)


@router.post("/admin/usuarios", response_model=Usuario, status_code=201, responses=errores(400, 401, 403, 404, 409))
async def crear_usuario(
    cuerpo: UsuarioCrear, identidad: Identidad = _admin, caso_uso: CrearUsuario = Depends(caso("crear_usuario"))
) -> dict:
    return await caso_uso(identidad, cuerpo.correo, cuerpo.nombre, cuerpo.rol, cuerpo.empresa_id)


@router.put("/admin/usuarios/{usuario_id}", response_model=Usuario, responses=errores(400, 401, 403, 404, 409))
async def editar_usuario(
    usuario_id: UUID,
    cuerpo: UsuarioEditar,
    identidad: Identidad = _admin,
    caso_uso: EditarUsuario = Depends(caso("editar_usuario")),
) -> dict:
    return await caso_uso(identidad, usuario_id, cuerpo.model_dump(exclude={"version"}), cuerpo.version)


@router.get("/admin/roles", response_model=list[RolConPermisos], responses=errores(401, 403))
async def listar_roles(identidad: Identidad = _admin, caso_uso: ListarRoles = Depends(caso("listar_roles"))) -> list[dict]:
    return await caso_uso(identidad)


@router.get("/admin/empresas", response_model=list[EmpresaAdmin], responses=errores(401, 403))
async def listar_empresas_admin(
    identidad: Identidad = _admin, caso_uso: ListarEmpresasAdmin = Depends(caso("listar_empresas_admin"))
) -> list[dict]:
    return await caso_uso(identidad)


@router.post("/admin/empresas", response_model=EmpresaAdmin, status_code=201, responses=errores(400, 401, 403, 409))
async def crear_empresa(
    cuerpo: EmpresaCrear, identidad: Identidad = _admin, caso_uso: CrearEmpresa = Depends(caso("crear_empresa"))
) -> dict:
    return await caso_uso(identidad, cuerpo.nombre)


@router.put("/admin/empresas/{empresa_id}", response_model=EmpresaAdmin, responses=errores(400, 401, 403, 404, 409))
async def editar_empresa(
    empresa_id: UUID,
    cuerpo: EmpresaEditar,
    identidad: Identidad = _admin,
    caso_uso: EditarEmpresa = Depends(caso("editar_empresa")),
) -> dict:
    return await caso_uso(identidad, empresa_id, cuerpo.nombre, cuerpo.estado, cuerpo.version)


@router.get(
    "/admin/empresas/{empresa_id}/credenciales-gps", response_model=list[CredencialGps], responses=errores(401, 403, 404)
)
async def listar_credenciales_gps(
    empresa_id: UUID,
    identidad: Identidad = _admin,
    caso_uso: ListarCredencialesGps = Depends(caso("listar_credenciales_gps")),
) -> list[dict]:
    return await caso_uso(identidad, empresa_id)


@router.post(
    "/admin/empresas/{empresa_id}/credenciales-gps", response_model=CredencialGpsCreada, status_code=201,
    responses=errores(400, 401, 403, 404),
)
async def crear_credencial_gps(
    empresa_id: UUID,
    cuerpo: CredencialGpsCrear,
    identidad: Identidad = _admin,
    caso_uso: CrearCredencialGps = Depends(caso("crear_credencial_gps")),
) -> dict:
    return await caso_uso(identidad, empresa_id, cuerpo.nombre)


@router.delete("/admin/credenciales-gps/{credencial_id}", status_code=204, responses=errores(401, 403, 404))
async def revocar_credencial_gps(
    credencial_id: UUID,
    identidad: Identidad = _admin,
    caso_uso: RevocarCredencialGps = Depends(caso("revocar_credencial_gps")),
) -> Response:
    await caso_uso(identidad, credencial_id)
    return Response(status_code=204)


@router.get("/admin/parametros", response_model=list[Parametro], responses=errores(401, 403))
async def listar_parametros(
    identidad: Identidad = _admin, caso_uso: ListarParametros = Depends(caso("listar_parametros"))
) -> list[dict]:
    return await caso_uso(identidad)


@router.put("/admin/parametros/{clave}", response_model=Parametro, responses=errores(400, 401, 403, 404, 409))
async def configurar_parametro(
    clave: str,
    cuerpo: ParametroActualizar,
    identidad: Identidad = _admin,
    caso_uso: ConfigurarParametro = Depends(caso("configurar_parametro")),
) -> dict:
    return await caso_uso(identidad, clave, cuerpo.valor, cuerpo.version)


@router.get("/demo/estado", response_model=EstadoDemo, responses=errores(401, 403, 404))
async def consultar_estado_demo(
    identidad: Identidad = Depends(requiere_rol(Rol.ADMINISTRADOR)),
    caso_uso: ConsultarEstadoDemo = Depends(caso("consultar_estado_demo")),
) -> dict:
    return await caso_uso(identidad)


@router.post("/demo/escenarios", response_model=EstadoDemo, responses=errores(400, 401, 403, 404))
async def ejecutar_escenario_demo(
    cuerpo: EscenarioDemo,
    identidad: Identidad = Depends(requiere_rol(Rol.ADMINISTRADOR)),
    caso_uso: EjecutarEscenarioDemo = Depends(caso("ejecutar_escenario_demo")),
) -> dict:
    return await caso_uso(identidad, cuerpo.model_dump())
