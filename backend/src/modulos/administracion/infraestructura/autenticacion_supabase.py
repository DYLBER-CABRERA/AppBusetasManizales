"""PuertoAutenticacion con Supabase Auth: el token se valida con `GET /auth/v1/user` (sirve con claves de firma
simétricas o asimétricas) y el rol y la empresa salen de `perfil_usuario`. Nunca se registra el token."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from uuid import UUID

import httpx

from modulos.administracion.dominio.puertos import RepositorioUsuarios
from nucleo.autorizacion import Identidad, Rol
from nucleo.errores import ErrorConflictoNegocio, ErrorNoAutenticado, ErrorServicioExterno

TTL_CACHE_S = 30.0


class AutenticacionSupabase:
    def __init__(
        self,
        url_supabase: str,
        clave_anonima: str,
        usuarios: RepositorioUsuarios,
        cliente: httpx.AsyncClient,
        monotonico: Callable[[], float] = time.monotonic,
        clave_servicio: str = "",
    ) -> None:
        self._clave_servicio = clave_servicio
        self._url = url_supabase.rstrip("/")
        self._clave = clave_anonima
        self._usuarios = usuarios
        self._cliente = cliente
        self._monotonico = monotonico
        self._cache: dict[str, tuple[float, Identidad]] = {}

    async def verificar_token(self, jwt: str) -> Identidad:
        if not self._url or not self._clave:
            raise ErrorServicioExterno("La autenticación no está configurada (SUPABASE_URL y SUPABASE_ANON_KEY).")
        llave = hashlib.sha256(jwt.encode("utf-8")).hexdigest()
        ahora = self._monotonico()
        en_cache = self._cache.get(llave)
        if en_cache and en_cache[0] > ahora:
            return en_cache[1]
        try:
            respuesta = await self._cliente.get(
                f"{self._url}/auth/v1/user", headers={"Authorization": f"Bearer {jwt}", "apikey": self._clave}
            )
        except httpx.HTTPError as exc:
            raise ErrorServicioExterno("No se pudo validar la sesión con el servicio de autenticación.") from exc
        if respuesta.status_code in (400, 401, 403):
            raise ErrorNoAutenticado("Sesión inválida o vencida.")
        if respuesta.status_code != 200:
            raise ErrorServicioExterno("El servicio de autenticación no está disponible.")
        try:
            usuario_id = UUID(str(respuesta.json()["id"]))
        except (KeyError, ValueError) as exc:
            raise ErrorNoAutenticado("Sesión inválida o vencida.") from exc
        perfil = await self._usuarios.perfil(usuario_id)
        if perfil is None or not perfil["activo"]:
            raise ErrorNoAutenticado("Usuario inactivo o sin perfil.")
        empresa = perfil["empresa_id"]
        identidad = Identidad(str(usuario_id), Rol(perfil["rol"]), str(empresa) if empresa else None)
        self._cache = {k: v for k, v in self._cache.items() if v[0] > ahora}
        self._cache[llave] = (ahora + TTL_CACHE_S, identidad)
        return identidad

    async def crear_usuario(self, correo: str, nombre: str | None) -> UUID:
        """Invita al usuario (Supabase le envía el correo para fijar su contraseña). Usa la clave de servicio, que
        nunca sale del backend ni se registra."""
        if not self._url or not self._clave_servicio:
            raise ErrorServicioExterno("Falta SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY para crear usuarios.")
        try:
            respuesta = await self._cliente.post(
                f"{self._url}/auth/v1/invite",
                headers={"Authorization": f"Bearer {self._clave_servicio}", "apikey": self._clave_servicio},
                json={"email": correo, "data": {"nombre": nombre} if nombre else {}},
            )
        except httpx.HTTPError as exc:
            raise ErrorServicioExterno("No se pudo crear el usuario en el servicio de autenticación.") from exc
        if respuesta.status_code in (409, 422):
            raise ErrorConflictoNegocio("Ya existe una cuenta con ese correo.")
        if respuesta.status_code >= 300:
            raise ErrorServicioExterno("El servicio de autenticación rechazó la creación del usuario.")
        return UUID(str(respuesta.json()["id"]))
