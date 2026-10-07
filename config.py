"""Configuración del servicio, leída del entorno y de `.env` (nunca escrita en el código)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cada campo se lee de la variable de entorno homónima (DATABASE_URL, SECRETO_FIRMA, ...).

    Prioridad: variable de entorno > `.env` > valor por defecto. Los valores por defecto
    permiten arrancar sin `.env` (p. ej. en el contenedor), pero NO son secretos reales:
    en producción se definen SECRETO_FIRMA y CLAVE_API_REASEGURO en el entorno.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///app.db"
    secreto_firma: str = "solo-para-desarrollo"
    clave_api_reaseguro: str = ""
    ruta_modelo: str = "modelo.pkl"
    umbral_alto_riesgo: float = 0.6


@lru_cache
def get_settings() -> Settings:
    """Una sola instancia por proceso: `.env` se lee una vez, no en cada petición."""
    return Settings()
