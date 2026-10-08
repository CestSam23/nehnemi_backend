from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import obtener_db


router = APIRouter(
    prefix="/fuentes-datos",
    tags=["Fuentes de datos"],
)


class FuenteRespuesta(BaseModel):
    id: UUID
    clave: str
    nombre: str
    tipo_procedencia: str
    referencia: str | None
    fecha_referencia: date | None
    fecha_descarga: date | None
    notas: str | None


@router.get("", response_model=list[FuenteRespuesta])
def listar_fuentes(
    db: Session = Depends(obtener_db),
):
    filas = db.execute(
        text("""
            SELECT
                id,
                clave,
                nombre,
                tipo_procedencia::text AS tipo_procedencia,
                referencia,
                fecha_referencia,
                fecha_descarga,
                notas
            FROM fuentes_datos
            ORDER BY nombre
        """)
    ).mappings().all()

    return [FuenteRespuesta(**fila) for fila in filas]