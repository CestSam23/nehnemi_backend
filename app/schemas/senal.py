from typing import Literal

from pydantic import BaseModel


class SenalDiagnostica(BaseModel):
    codigo: str
    categoria: Literal[
        "INFRAESTRUCTURA",
        "ACCESIBILIDAD",
        "EVIDENCIA",
    ]
    valor: float | int | str | None = None
    unidad: str | None = None
    descripcion: str


class SenalesZona(BaseModel):
    zona_clave: str
    senales: list[SenalDiagnostica]