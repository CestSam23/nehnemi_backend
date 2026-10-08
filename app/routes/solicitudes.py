import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import obtener_db
from app.models.ciudadano import PerfilCiudadano
from app.models.solicitud import SolicitudInfraestructura
from app.schemas.solicitud import SolicitudCrear, SolicitudCreada
from app.services.autenticacion_ciudadano import obtener_id_ciudadano
from app.services.zonas import obtener_ageb_por_ubicacion


router = APIRouter(
    prefix="/solicitudes-infraestructura",
    tags=["Solicitudes de infraestructura"],
)


@router.post(
    "",
    response_model=SolicitudCreada,
    status_code=201,
)
def crear_solicitud(
    datos: SolicitudCrear,
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

    zona = obtener_ageb_por_ubicacion(
        db,
        datos.ubicacion.latitud,
        datos.ubicacion.longitud,
    )

    if zona is None:
        raise HTTPException(
            status_code=422,
            detail="La ubicación no corresponde a una AGEB disponible de CDMX",
        )

    punto = WKTElement(
        (
            f"POINT("
            f"{datos.ubicacion.longitud} "
            f"{datos.ubicacion.latitud}"
            f")"
        ),
        srid=4326,
    )

    solicitud = SolicitudInfraestructura(
        id=uuid.uuid4(),
        perfil_ciudadano_id=perfil.id,
        zona_id=zona.id,
        ubicacion=punto,
        motivo=datos.motivo,
        comentario=datos.comentario,
        estado="REGISTRADA",
    )

    db.add(solicitud)
    db.commit()

    return SolicitudCreada(
        id=solicitud.id,
        zona_clave=zona.clave,
        motivo=solicitud.motivo,
        estado=solicitud.estado,
    )