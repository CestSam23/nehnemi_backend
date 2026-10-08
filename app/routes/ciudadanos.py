import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import obtener_db
from app.models.ciudadano import PerfilCiudadano
from app.models.zona import Zona
from app.schemas.ciudadano import (
    CiudadanoCrear,
    CiudadanoCreado,
)
from app.services.autenticacion_ciudadano import (
    crear_token_ciudadano,
)
from app.services.zonas import obtener_ageb_por_ubicacion

from uuid import UUID

from app.schemas.ciudadano import CiudadanoPerfil
from app.services.autenticacion_ciudadano import obtener_id_ciudadano

router = APIRouter(
    prefix="/ciudadanos",
    tags=["Ciudadanos"],
)


@router.post(
    "",
    response_model=CiudadanoCreado,
    status_code=201,
)
def crear_ciudadano(
    datos: CiudadanoCrear,
    db: Session = Depends(obtener_db),
):
    zona = None

    if datos.clave_zona:
        zona = db.execute(
            select(Zona)
            .where(
                Zona.clave == datos.clave_zona,
                Zona.activa.is_(True),
            )
        ).scalar_one_or_none()

        if zona is None:
            raise HTTPException(
                status_code=422,
                detail="Zona no válida",
            )

    elif datos.ubicacion:
        zona = obtener_ageb_por_ubicacion(
            db,
            datos.ubicacion.latitud,
            datos.ubicacion.longitud,
        )

        if zona is None:
            raise HTTPException(
                status_code=422,
                detail="La ubicación no corresponde a una AGEB disponible",
            )

    perfil = PerfilCiudadano(
        id=uuid.uuid4(),
        zona_id=zona.id if zona else None,
        tiene_automovil=datos.tiene_automovil,
        propulsion=datos.propulsion,
        consideraria_ev=datos.consideraria_ev,
        barrera_principal=datos.barrera_principal,
        consentimiento_agregado=datos.consentimiento_agregado,
    )

    db.add(perfil)
    db.commit()
    db.refresh(perfil)

    return CiudadanoCreado(
        id=perfil.id,
        token=crear_token_ciudadano(perfil.id),
        zona_clave=zona.clave if zona else None,
    )

@router.get(
    "/mi-perfil",
    response_model=CiudadanoPerfil,
)
def obtener_mi_perfil(
    ciudadano_id: UUID = Depends(obtener_id_ciudadano),
    db: Session = Depends(obtener_db),
):
    fila = db.execute(
        select(
            PerfilCiudadano.id,
            PerfilCiudadano.tiene_automovil,
            PerfilCiudadano.propulsion,
            PerfilCiudadano.consideraria_ev,
            PerfilCiudadano.barrera_principal,
            PerfilCiudadano.consentimiento_agregado,
            Zona.clave.label("zona_clave"),
        )
        .outerjoin(
            Zona,
            PerfilCiudadano.zona_id == Zona.id,
        )
        .where(
            PerfilCiudadano.id == ciudadano_id,
        )
    ).one_or_none()

    if fila is None:
        raise HTTPException(
            status_code=401,
            detail="Perfil ciudadano no válido",
        )

    return CiudadanoPerfil(
        id=fila.id,
        zona_clave=fila.zona_clave,
        tiene_automovil=fila.tiene_automovil,
        propulsion=fila.propulsion,
        consideraria_ev=fila.consideraria_ev,
        barrera_principal=fila.barrera_principal,
        consentimiento_agregado=fila.consentimiento_agregado,
    )