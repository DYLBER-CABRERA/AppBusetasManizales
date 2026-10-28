"""Configuración por variables de entorno (pydantic-settings). Los valores reales viven en `.env`."""

from __future__ import annotations

from datetime import date
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: SecretStr = SecretStr("")
    supabase_url: str = ""
    supabase_anon_key: SecretStr = SecretStr("")
    supabase_service_role_key: SecretStr = SecretStr("")

    puerto: int = 8000
    cors_origenes: str = "http://localhost:3000"

    modo_demo: bool = True
    sim_velocidad_kmh: float = Field(default=35, gt=0)
    sim_intervalo_s: float = Field(default=3, gt=0)

    festivos: str = ""
    telegram_bot_token: SecretStr = SecretStr("")

    demo_password_admin: SecretStr = SecretStr("")
    demo_password_movilidad: SecretStr = SecretStr("")
    demo_password_jefe: SecretStr = SecretStr("")
    demo_password_pasajero: SecretStr = SecretStr("")

    @field_validator("festivos")
    @classmethod
    def _validar_festivos(cls, valor: str) -> str:
        for texto in _partir(valor):
            date.fromisoformat(texto)
        return valor

    @property
    def lista_cors_origenes(self) -> list[str]:
        return _partir(self.cors_origenes)

    @property
    def lista_festivos(self) -> frozenset[date]:
        return frozenset(date.fromisoformat(t) for t in _partir(self.festivos))

    @property
    def bot_telegram_activo(self) -> bool:
        return bool(self.telegram_bot_token.get_secret_value())


def _partir(valor: str) -> list[str]:
    return [p.strip() for p in valor.split(",") if p.strip()]


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
