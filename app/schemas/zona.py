from typing import Literal

from pydantic import BaseModel


TipoZona = Literal["CDMX", "ALCALDIA", "AGEB"]


class ZonaResumen(BaseModel):
    clave: str
    tipo: TipoZona
    nombre: str
    zona_padre_clave: str | None = None


class ZonaDetalle(ZonaResumen):
    activa: bool