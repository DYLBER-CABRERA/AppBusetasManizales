"""Router del módulo administración (A) y perfil `GET /yo`. B0: 501 PENDIENTE (lógica en B3/B5).

Formas tomadas de docs/03 y, donde 03 no las define, de docs/referencia/openapi.yaml.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import Field

from nucleo.autorizacion import Rol
from nucleo.dependencias import pendiente, requiere_rol
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


@router.get(
    "/yo", response_model=Perfil, responses=errores(401),
    dependencies=[Depends(requiere_rol(*Rol))],
)
async def obtener_perfil() -> Perfil:
    pendiente()


@router.get("/admin/usuarios", response_model=list[Usuario], dependencies=[_admin], responses=errores(401, 403))
async def listar_usuarios(correo: str | None = Query(default=None, max_length=80)) -> list[Usuario]:
    pendiente()


@router.post(
    "/admin/usuarios", response_model=Usuario, status_code=201, dependencies=[_admin],
    responses=errores(400, 401, 403, 409),
)
async def crear_usuario(cuerpo: UsuarioCrear) -> Usuario:
    pendiente()


@router.put(
    "/admin/usuarios/{usuario_id}", response_model=Usuario, dependencies=[_admin],
    responses=errores(400, 401, 403, 404, 409),
)
async def editar_usuario(usuario_id: UUID, cuerpo: UsuarioEditar) -> Usuario:
    pendiente()


@router.get("/admin/roles", response_model=list[RolConPermisos], dependencies=[_admin], responses=errores(401, 403))
async def listar_roles() -> list[RolConPermisos]:
    pendiente()


@router.get("/admin/empresas", response_model=list[EmpresaAdmin], dependencies=[_admin], responses=errores(401, 403))
async def listar_empresas_admin() -> list[EmpresaAdmin]:
    pendiente()


@router.post(
    "/admin/empresas", response_model=EmpresaAdmin, status_code=201, dependencies=[_admin],
    responses=errores(400, 401, 403, 409),
)
async def crear_empresa(cuerpo: EmpresaCrear) -> EmpresaAdmin:
    pendiente()


@router.put(
    "/admin/empresas/{empresa_id}", response_model=EmpresaAdmin, dependencies=[_admin],
    responses=errores(400, 401, 403, 404, 409),
)
async def editar_empresa(empresa_id: UUID, cuerpo: EmpresaEditar) -> EmpresaAdmin:
    pendiente()


@router.get(
    "/admin/empresas/{empresa_id}/credenciales-gps", response_model=list[CredencialGps],
    dependencies=[_admin], responses=errores(401, 403, 404),
)
async def listar_credenciales_gps(empresa_id: UUID) -> list[CredencialGps]:
    pendiente()


@router.post(
    "/admin/empresas/{empresa_id}/credenciales-gps", response_model=CredencialGpsCreada, status_code=201,
    dependencies=[_admin], responses=errores(400, 401, 403, 404),
)
async def crear_credencial_gps(empresa_id: UUID, cuerpo: CredencialGpsCrear) -> CredencialGpsCreada:
    pendiente()


@router.delete(
    "/admin/credenciales-gps/{credencial_id}", status_code=204, dependencies=[_admin],
    responses=errores(401, 403, 404),
)
async def revocar_credencial_gps(credencial_id: UUID) -> Response:
    pendiente()


@router.get("/admin/parametros", response_model=list[Parametro], dependencies=[_admin], responses=errores(401, 403))
async def listar_parametros() -> list[Parametro]:
    pendiente()


@router.put(
    "/admin/parametros/{clave}", response_model=Parametro, dependencies=[_admin],
    responses=errores(400, 401, 403, 404, 409),
)
async def configurar_parametro(clave: str, cuerpo: ParametroActualizar) -> Parametro:
    pendiente()


@router.get(
    "/demo/estado", response_model=EstadoDemo, dependencies=[_admin], responses=errores(401, 403, 404),
)
async def consultar_estado_demo() -> EstadoDemo:
    pendiente()


@router.post(
    "/demo/escenarios", response_model=EstadoDemo, dependencies=[_admin],
    responses=errores(400, 401, 403, 404),
)
async def ejecutar_escenario_demo(cuerpo: EscenarioDemo) -> EstadoDemo:
    pendiente()
