from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.ubicacion import Ubicacion


class CiudadanoCrear(BaseModel):
    tiene_automovil: bool

    propulsion: Literal[
        "ELECTRICO",
        "HIBRIDO_ENCHUFABLE",
        "HIBRIDO",
        "COMBUSTION",
        "OTRO",
        "SIN_AUTOMOVIL",
    ]

    consideraria_ev: Literal[
        "SI",
        "NO",
        "NO_SE",
    ]

    barrera_principal: Literal[
        "PRECIO",
        "CARGA",
        "AUTONOMIA",
        "INFORMACION_DUDAS",
        "CARACTERISTICAS_VEHICULO",
        "NO_INTERESA",
        "OTRA",
        "NINGUNA",
    ]

    consentimiento_agregado: bool

    ubicacion: Ubicacion | None = None
    clave_zona: str | None = None


class CiudadanoCreado(BaseModel):
    id: UUID
    token: str
    zona_clave: str | None = None

class CiudadanoPerfil(BaseModel):
    id: UUID
    zona_clave: str | None = None

    tiene_automovil: bool
    propulsion: str
    consideraria_ev: str
    barrera_principal: str
    consentimiento_agregado: bool