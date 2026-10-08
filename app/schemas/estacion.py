from pydantic import BaseModel
from uuid import UUID




class Ubicacion(BaseModel):
    latitud: float
    longitud: float


class ConectorCargaRespuesta(BaseModel):
    cantidad: int
    tipo_conector: str | None = None
    potencia_kw: float | None = None
    estado_operativo: str | None = None


class EstacionCargaRespuesta(BaseModel):
    identificador: str | None
    nombre: str
    direccion: str | None
    ubicacion: Ubicacion
    estado_demostracion: str | None
    conectores: list[ConectorCargaRespuesta]
    id: UUID


class ConectorDetalle(BaseModel):
    tipo_conector: str | None
    cantidad: int
    potencia_kw: float | None
    estado_operativo: str | None


class EstacionDetalle(BaseModel):
    id: UUID
    nombre: str | None
    direccion: str | None
    latitud: float
    longitud: float
    zona_clave: str | None
    conectores: list[ConectorDetalle]