from pydantic import BaseModel


class ConteoCategoria(BaseModel):
    valor: str
    cantidad: int


class SolicitudesZona(BaseModel):
    zona_clave: str
    total: int
    por_estado: list[ConteoCategoria]
    por_motivo: list[ConteoCategoria]