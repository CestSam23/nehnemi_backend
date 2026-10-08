from typing import Literal
from uuid import UUID

from pydantic import BaseModel, model_validator

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


class CiudadanoActualizar(BaseModel):
    tiene_automovil: bool | None = None

    propulsion: Literal[
        "ELECTRICO",
        "HIBRIDO_ENCHUFABLE",
        "HIBRIDO",
        "COMBUSTION",
        "OTRO",
        "SIN_AUTOMOVIL",
    ] | None = None

    consideraria_ev: Literal[
        "SI",
        "NO",
        "NO_SE",
    ] | None = None

    barrera_principal: Literal[
        "PRECIO",
        "CARGA",
        "AUTONOMIA",
        "INFORMACION_DUDAS",
        "CARACTERISTICAS_VEHICULO",
        "NO_INTERESA",
        "OTRA",
        "NINGUNA",
    ] | None = None

    consentimiento_agregado: bool | None = None

    ubicacion: Ubicacion | None = None
    clave_zona: str | None = None

    @model_validator(mode="after")
    def validar_campos(self):
        campos = self.model_fields_set

        if not campos:
            raise ValueError(
                "Debe proporcionar al menos un campo para actualizar"
            )

        if any(
            getattr(self, campo) is None
            for campo in campos
        ):
            raise ValueError(
                "No se permite asignar null a los campos del perfil"
            )

        return self