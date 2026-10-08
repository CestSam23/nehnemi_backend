from pydantic import BaseModel


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