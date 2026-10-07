"""Esquemas de entrada (validación) y de salida (qué se expone)."""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TipoPoliza = Literal["auto", "hogar", "vida"]
EstadoSiniestro = Literal["abierto", "pagado", "rechazado"]


def _normalizar_nombre(v: str) -> str:
    """Quita espacios sobrantes y pone el nombre con mayúscula inicial."""
    return " ".join(v.split()).title()


# --- Entrada -----------------------------------------------------------------

class SiniestroEntrada(BaseModel):
    fecha: date
    monto: float = Field(gt=0, description="Monto reclamado, en pesos")
    descripcion: str = Field(min_length=3, max_length=200)
    estado: EstadoSiniestro = "abierto"


class PolizaEntrada(BaseModel):
    numero: str = Field(min_length=8, max_length=20, description="Formato POL-AAAA-NNNNN")
    asegurado: str = Field(min_length=3, max_length=80)
    tipo: TipoPoliza = Field(description="auto, hogar o vida")
    prima: float = Field(gt=0, description="Prima anual, en pesos")
    fecha_inicio: date
    fecha_fin: date
    # Submodelo tipado: cada siniestro anidado se valida con las reglas de SiniestroEntrada.
    siniestros: list[SiniestroEntrada] = Field(default_factory=list,
                                               description="Siniestros ya declarados")

    @field_validator("asegurado")
    @classmethod
    def normalizar_asegurado(cls, v: str) -> str:
        return _normalizar_nombre(v)

    @model_validator(mode="after")
    def fechas_coherentes(self) -> "PolizaEntrada":
        if self.fecha_fin <= self.fecha_inicio:
            raise ValueError("fecha_fin debe ser posterior a fecha_inicio")
        return self


class PolizaActualizacion(BaseModel):
    """PUT parcial: solo se aplican los campos que llegan en el cuerpo (exclude_unset)."""

    asegurado: Optional[str] = Field(default=None, min_length=3, max_length=80)
    tipo: Optional[TipoPoliza] = None
    prima: Optional[float] = Field(default=None, gt=0)
    fecha_fin: Optional[date] = None

    @field_validator("asegurado", "tipo", "prima", "fecha_fin", mode="before")
    @classmethod
    def no_nulo(cls, v):
        # Omitir un campo es «no cambiarlo»; mandarlo en null sería borrarlo: se rechaza.
        if v is None:
            raise ValueError("no puede ser null; omita el campo para no cambiarlo")
        return v

    @field_validator("asegurado")
    @classmethod
    def normalizar_asegurado(cls, v: str) -> str:
        return _normalizar_nombre(v)


class PuntuacionEntrada(BaseModel):
    numero: str = Field(min_length=8, max_length=20)


# --- Salida ------------------------------------------------------------------

class _DesdeORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SiniestroSalida(_DesdeORM):
    id: int
    poliza_id: int
    fecha: date
    monto: float
    descripcion: str
    estado: str


class SiniestroConPoliza(SiniestroSalida):
    numero_poliza: str


class PolizaSalida(_DesdeORM):
    """Sin `token_firma`: lo que no está declarado aquí no sale en la respuesta."""

    id: int
    numero: str
    asegurado: str
    tipo: str
    prima: float
    fecha_inicio: date
    fecha_fin: date
    siniestros: list[SiniestroSalida]


class ResumenPoliza(BaseModel):
    numero: str
    n_siniestros: int
    monto_total: float


class PuntuacionSalida(BaseModel):
    numero: str
    puntaje: float = Field(ge=0, le=1)
    alto_riesgo: bool


class PrediccionSalida(_DesdeORM):
    id: int
    poliza_id: int
    numero: str
    puntaje: float
    alto_riesgo: bool
    creado_en: datetime


class Salud(BaseModel):
    estado: str
    base_datos: str
