from pydantic import BaseModel, Field
from typing import Literal
from uuid import UUID
from app.schemas.ubicacion import Ubicacion
from datetime import datetime


class ConteoCategoria(BaseModel):
    valor: str
    cantidad: int


class SolicitudesZona(BaseModel):
    zona_clave: str
    total: int
    por_estado: list[ConteoCategoria]
    por_motivo: list[ConteoCategoria]

class SolicitudCrear(BaseModel):
    ubicacion: Ubicacion

    motivo: Literal[
        "VIVO_CERCA",
        "TRABAJO_CERCA",
        "TRANSITO_FRECUENTE",
        "TENGO_EV",
        "CONSIDERARIA_EV_CON_CARGA",
        "OTRO",
    ]

    comentario: str | None = Field(
        default=None,
        max_length=500,
    )


class SolicitudCreada(BaseModel):
    id: UUID
    zona_clave: str
    motivo: str
    estado: str


class SolicitudCiudadano(BaseModel):
    id: UUID
    zona_clave: str
    motivo: str
    comentario: str | None
    estado: str
    creado_en: datetime
    ubicacion: Ubicacion

class SolicitudAdministrativa(BaseModel):
    id: UUID
    zona_clave: str
    motivo: str
    comentario: str | None
    estado: str
    creado_en: datetime


class ListadoSolicitudes(BaseModel):
    total: int
    pagina: int
    limite: int
    solicitudes: list[SolicitudAdministrativa]


class SolicitudActualizarEstado(BaseModel):
    estado: Literal[
        "REGISTRADA",
        "EN_REVISION",
        "ATENDIDA",
        "DESCARTADA",
    ]