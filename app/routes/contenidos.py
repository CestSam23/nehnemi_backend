from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import obtener_db


router = APIRouter(
    prefix="/contenidos",
    tags=["Contenidos informativos"],
)


class ContenidoResumen(BaseModel):
    id: UUID
    slug: str
    titulo: str
    resumen: str | None
    categoria: str | None
    orden: int


class ContenidoDetalle(ContenidoResumen):
    contenido: str
    creado_en: datetime


@router.get("", response_model=list[ContenidoResumen])
def listar_contenidos(
    db: Session = Depends(obtener_db),
):
    filas = db.execute(
        text("""
            SELECT
                id,
                slug,
                titulo,
                resumen,
                categoria,
                orden
            FROM contenidos_informativos
            WHERE publicado = TRUE
            ORDER BY orden, titulo
        """)
    ).mappings().all()

    return [ContenidoResumen(**fila) for fila in filas]


@router.get("/{slug}", response_model=ContenidoDetalle)
def obtener_contenido(
    slug: str,
    db: Session = Depends(obtener_db),
):
    fila = db.execute(
        text("""
            SELECT
                id,
                slug,
                titulo,
                resumen,
                contenido,
                categoria,
                orden,
                creado_en
            FROM contenidos_informativos
            WHERE slug = :slug
              AND publicado = TRUE
        """),
        {"slug": slug},
    ).mappings().first()

    if fila is None:
        raise HTTPException(
            status_code=404,
            detail="Contenido no encontrado",
        )

    return ContenidoDetalle(**fila)