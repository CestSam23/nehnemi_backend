import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query
from sqlalchemy import func, select
from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import obtener_db
from app.models.ciudadano import PerfilCiudadano
from app.models.solicitud import SolicitudInfraestructura
from app.schemas.solicitud import SolicitudCrear, SolicitudCreada
from app.services.autenticacion_ciudadano import obtener_id_ciudadano
from app.services.zonas import obtener_ageb_por_ubicacion


from app.models.zona import Zona
from app.models.usuario_gobierno import UsuarioGobierno


from app.routes.autenticacion import (
    obtener_usuario_gobierno,
    requerir_administrador,
)

from app.schemas.solicitud import (
    SolicitudAdministrativa,
    ListadoSolicitudes,
    SolicitudActualizarEstado,
)

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

def convertir_solicitud(fila):
    return SolicitudAdministrativa(
        id=fila.id,
        zona_clave=fila.zona_clave,
        motivo=fila.motivo,
        comentario=fila.comentario,
        estado=fila.estado,
        creado_en=fila.creado_en,
    )


@router.get("", response_model=ListadoSolicitudes)
def listar_solicitudes(
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    estado: str | None = None,
    clave_zona: str | None = None,
    usuario: UsuarioGobierno = Depends(obtener_usuario_gobierno),
    db: Session = Depends(obtener_db),
):
    filtros = []

    if estado:
        if estado not in {
            "REGISTRADA",
            "EN_REVISION",
            "ATENDIDA",
            "DESCARTADA",
        }:
            raise HTTPException(422, "Estado no válido")

        filtros.append(
            SolicitudInfraestructura.estado == estado
        )

    if clave_zona:
        filtros.append(Zona.clave == clave_zona)

    total = db.scalar(
        select(func.count())
        .select_from(SolicitudInfraestructura)
        .join(Zona, SolicitudInfraestructura.zona_id == Zona.id)
        .where(*filtros)
    ) or 0

    filas = db.execute(
        select(
            SolicitudInfraestructura.id,
            SolicitudInfraestructura.motivo,
            SolicitudInfraestructura.comentario,
            SolicitudInfraestructura.estado,
            SolicitudInfraestructura.creado_en,
            Zona.clave.label("zona_clave"),
        )
        .join(Zona, SolicitudInfraestructura.zona_id == Zona.id)
        .where(*filtros)
        .order_by(SolicitudInfraestructura.creado_en.desc())
        .offset((pagina - 1) * limite)
        .limit(limite)
    ).all()

    return ListadoSolicitudes(
        total=total,
        pagina=pagina,
        limite=limite,
        solicitudes=[convertir_solicitud(fila) for fila in filas],
    )


@router.get(
    "/{solicitud_id}",
    response_model=SolicitudAdministrativa,
)
def consultar_solicitud(
    solicitud_id: UUID,
    usuario: UsuarioGobierno = Depends(obtener_usuario_gobierno),
    db: Session = Depends(obtener_db),
):
    fila = db.execute(
        select(
            SolicitudInfraestructura.id,
            SolicitudInfraestructura.motivo,
            SolicitudInfraestructura.comentario,
            SolicitudInfraestructura.estado,
            SolicitudInfraestructura.creado_en,
            Zona.clave.label("zona_clave"),
        )
        .join(Zona, SolicitudInfraestructura.zona_id == Zona.id)
        .where(SolicitudInfraestructura.id == solicitud_id)
    ).one_or_none()

    if fila is None:
        raise HTTPException(404, "Solicitud no encontrada")

    return convertir_solicitud(fila)


@router.patch(
    "/{solicitud_id}",
    response_model=SolicitudAdministrativa,
)
def actualizar_estado_solicitud(
    solicitud_id: UUID,
    datos: SolicitudActualizarEstado,
    usuario: UsuarioGobierno = Depends(requerir_administrador),
    db: Session = Depends(obtener_db),
):
    solicitud = db.get(SolicitudInfraestructura, solicitud_id)

    if solicitud is None:
        raise HTTPException(404, "Solicitud no encontrada")

    solicitud.estado = datos.estado
    db.commit()

    fila = db.execute(
        select(
            SolicitudInfraestructura.id,
            SolicitudInfraestructura.motivo,
            SolicitudInfraestructura.comentario,
            SolicitudInfraestructura.estado,
            SolicitudInfraestructura.creado_en,
            Zona.clave.label("zona_clave"),
        )
        .join(Zona, SolicitudInfraestructura.zona_id == Zona.id)
        .where(SolicitudInfraestructura.id == solicitud_id)
    ).one()

    return convertir_solicitud(fila)