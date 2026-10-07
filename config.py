"""Configuración del servicio, leída del entorno y de `.env` (nunca escrita en el código)."""
import logging
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


SECRETO_DESARROLLO = "solo-para-desarrollo"


class Settings(BaseSettings):
    """Cada campo se lee de la variable de entorno homónima (DATABASE_URL, SECRETO_FIRMA, ...).

    Prioridad: variable de entorno > `.env` > valor por defecto. Los valores por defecto
    permiten arrancar sin `.env` (p. ej. en el contenedor), pero NO son secretos reales:
    en producción se definen SECRETO_FIRMA y CLAVE_API_REASEGURO en el entorno.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///app.db"
    secreto_firma: str = SECRETO_DESARROLLO
    clave_api_reaseguro: str = ""
    ruta_modelo: str = "modelo.pkl"
    umbral_alto_riesgo: float = 0.6

    @model_validator(mode="after")
    def avisar_secreto_por_defecto(self) -> "Settings":
        # Arrancar sin SECRETO_FIRMA no debe pasar en silencio: las firmas serían predecibles.
        if self.secreto_firma == SECRETO_DESARROLLO:
            logging.getLogger("uvicorn.error").warning(
                "SECRETO_FIRMA no está definido: se usa el valor de desarrollo. "
                "Defínalo en el entorno o en .env antes de usar el servicio en serio.")
        return self


@lru_cache
def get_settings() -> Settings:
    """Una sola instancia por proceso: `.env` se lee una vez, no en cada petición."""
    return Settings()
