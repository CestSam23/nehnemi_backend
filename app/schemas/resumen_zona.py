from pydantic import BaseModel

from app.schemas.indicador import IndicadorZona


class InfraestructuraResumen(BaseModel):
    estaciones: int
    conectores: int
    potencia_total_kw: float
    distancia_estacion_m: float | None = None


class ResumenZona(BaseModel):
    clave: str
    tipo: str
    nombre: str
    zona_padre_clave: str | None = None

    indicadores: list[IndicadorZona]

    infraestructura: InfraestructuraResumen | None = None