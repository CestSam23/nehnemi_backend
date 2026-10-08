from pydantic import BaseModel, Field


class Ubicacion(BaseModel):
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)