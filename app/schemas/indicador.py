from typing import Literal

from pydantic import BaseModel


DimensionIndicador = Literal[
    "ADOPCION",
    "INFRAESTRUCTURA",
    "PARTICIPACION",
    "ACCESIBILIDAD",
]

NivelIndicador = Literal[
    "MUY_BAJA",
    "BAJA",
    "MEDIA",
    "ALTA",
]

NivelConfianza = Literal[
    "BAJA",
    "MEDIA",
    "ALTA",
]


class IndicadorZona(BaseModel):
    dimension: DimensionIndicador
    disponible: bool

    puntuacion: float | None = None
    nivel: NivelIndicador | None = None
    confianza: NivelConfianza | None = None

    tamano_muestra: int | None = None
    componentes: dict | None = None
    explicacion: str | None = None


class IndicadoresZona(BaseModel):
    zona_clave: str
    indicadores: list[IndicadorZona]