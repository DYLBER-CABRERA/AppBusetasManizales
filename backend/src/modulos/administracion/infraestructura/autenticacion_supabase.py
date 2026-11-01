"""PuertoAutenticacion con Supabase Auth: el token se valida con `GET /auth/v1/user` (sirve con claves de firma
simétricas o asimétricas) y el rol y la empresa salen de `perfil_usuario`. Nunca se registra el token."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from uuid import UUID

import httpx

from modulos.administracion.dominio.puertos import RepositorioUsuarios
from nucleo.autenticacion import SesionAuth
from nucleo.autorizacion import Identidad, Rol
from nucleo.errores import ErrorConflictoNegocio, ErrorNoAutenticado, ErrorServicioExterno, ErrorValidacion

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

    async def _usuario_supabase(self, jwt: str) -> dict:
        if not self._url or not self._clave:
            raise ErrorServicioExterno("La autenticación no está configurada (SUPABASE_URL y SUPABASE_ANON_KEY).")
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
        return respuesta.json()

    async def verificar_sesion(self, jwt: str) -> SesionAuth:
        datos = await self._usuario_supabase(jwt)
        try:
            return SesionAuth(UUID(str(datos["id"])), str(datos["email"]).strip().lower())
        except (KeyError, ValueError, TypeError) as exc:
            raise ErrorNoAutenticado("Sesión inválida o vencida.") from exc

    async def verificar_token(self, jwt: str) -> Identidad:
        llave = hashlib.sha256(jwt.encode("utf-8")).hexdigest()
        ahora = self._monotonico()
        en_cache = self._cache.get(llave)
        if en_cache and en_cache[0] > ahora:
            return en_cache[1]
        datos = await self._usuario_supabase(jwt)
        try:
            usuario_id = UUID(str(datos["id"]))
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

    def _cabeceras_admin(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._clave_servicio}", "apikey": self._clave_servicio}

    async def crear_usuario(self, correo: str, contrasena: str, nombre: str | None) -> UUID:
        """Crea la cuenta con la API Admin (correo confirmado, sin enviar correos). Usa la clave de servicio, que nunca
        sale del backend. Ni la contraseña, ni el correo, ni la respuesta de Supabase se registran."""
        if not self._url or not self._clave_servicio:
            raise ErrorServicioExterno("Falta SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY para crear usuarios.")
        try:
            respuesta = await self._cliente.post(
                f"{self._url}/auth/v1/admin/users",
                headers=self._cabeceras_admin(),
                json={"email": correo, "password": contrasena, "email_confirm": True,
                      "user_metadata": {"nombre": nombre} if nombre else {}},
            )
        except httpx.HTTPError as exc:
            raise ErrorServicioExterno("No se pudo crear el usuario en el servicio de autenticación.") from exc
        if respuesta.status_code in (200, 201):
            try:
                return UUID(str(respuesta.json()["id"]))
            except (KeyError, ValueError, TypeError) as exc:
                raise ErrorServicioExterno("El servicio de autenticación devolvió una respuesta inesperada.") from exc
        codigo = ""
        try:
            codigo = str(respuesta.json().get("error_code") or "")
        except ValueError:
            pass
        if respuesta.status_code == 409 or codigo in ("email_exists", "user_already_exists"):
            raise ErrorConflictoNegocio("Ya existe una cuenta con ese correo.")
        if codigo == "weak_password":
            raise ErrorValidacion("La contraseña es demasiado débil para el servicio de autenticación.")
        raise ErrorServicioExterno("El servicio de autenticación rechazó la creación del usuario.")

    async def eliminar_usuario(self, usuario_id: UUID) -> None:
        try:
            await self._cliente.delete(f"{self._url}/auth/v1/admin/users/{usuario_id}", headers=self._cabeceras_admin())
        except Exception:  # noqa: BLE001 - limpieza de mejor esfuerzo: no debe tapar el error original
            return
