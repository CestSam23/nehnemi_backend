from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import obtener_db
from app.models.ciudadano import PerfilCiudadano
from app.models.interaccion import Interaccion
from app.schemas.interaccion import (
    InteraccionCrear,
    InteraccionCreada,
)
from app.services.autenticacion_ciudadano import (
    obtener_id_ciudadano,
)


router = APIRouter(
    prefix="/interacciones",
    tags=["Interacciones ciudadanas"],
)


@router.post(
    "",
    response_model=InteraccionCreada,
    status_code=201,
)
def registrar_interaccion(
    datos: InteraccionCrear,
    ciudadano_id: UUID = Depends(obtener_id_ciudadano),
    db: Session = Depends(obtener_db),
):
    perfil = db.execute(
        select(PerfilCiudadano)
        .where(PerfilCiudadano.id == ciudadano_id)
    ).scalar_one_or_none()

    if perfil is None:
        raise HTTPException(
            status_code=401,
            detail="Perfil ciudadano no válido",
        )

    interaccion = Interaccion(
        perfil_ciudadano_id=perfil.id,
        zona_id=perfil.zona_id,
        tipo=datos.tipo,
        metadatos=datos.metadatos,
    )

    db.add(interaccion)
    db.commit()
    db.refresh(interaccion)

    return InteraccionCreada(
        id=interaccion.id,
        tipo=interaccion.tipo,
    )