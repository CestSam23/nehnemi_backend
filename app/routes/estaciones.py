from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2 import Geography
from sqlalchemy import cast, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import obtener_db
from app.models.estacion import ConectorCarga, EstacionCarga
from app.models.zona import Zona
from app.schemas.estacion import (
    ConectorCargaRespuesta,
    ConectorDetalle,
    EstacionCargaRespuesta,
    EstacionDetalle,
    Ubicacion,
)


router = APIRouter(
    prefix="/estaciones-carga",
    tags=["Infraestructura"],
)


@router.get(
    "",
    response_model=list[EstacionCargaRespuesta],
)
def listar_estaciones(
    clave_zona: str | None = None,
    buscar: str | None = None,
    latitud: float | None = Query(None, ge=-90, le=90),
    longitud: float | None = Query(None, ge=-180, le=180),
    radio_km: float | None = Query(None, gt=0, le=100),
    db: Session = Depends(obtener_db),
):
    consulta = (
        select(
            EstacionCarga,
            func.ST_Y(EstacionCarga.ubicacion).label("latitud"),
            func.ST_X(EstacionCarga.ubicacion).label("longitud"),
        )
        .options(
            selectinload(EstacionCarga.conectores)
        )
        .order_by(EstacionCarga.nombre)
    )

    # Filtrar por zona
    if clave_zona is not None:
        zona_id = db.execute(
            select(Zona.id).where(
                Zona.clave == clave_zona,
                Zona.activa.is_(True),
            )
        ).scalar_one_or_none()

        if zona_id is None:
            raise HTTPException(
                status_code=404,
                detail="Zona no encontrada",
            )

        consulta = consulta.where(
            EstacionCarga.zona_id == zona_id
        )

    # Buscar por nombre o dirección
    if buscar:
        patron = f"%{buscar.strip()}%"

        consulta = consulta.where(
            or_(
                EstacionCarga.nombre.ilike(patron),
                EstacionCarga.direccion.ilike(patron),
            )
        )

    # Filtrar por radio geográfico
    if radio_km is not None:
        if latitud is None or longitud is None:
            raise HTTPException(
                status_code=422,
                detail="radio_km requiere latitud y longitud",
            )

        punto = func.ST_SetSRID(
            func.ST_MakePoint(longitud, latitud),
            4326,
        )

        consulta = consulta.where(
            func.ST_DWithin(
                cast(EstacionCarga.ubicacion, Geography),
                cast(punto, Geography),
                radio_km * 1000,
            )
        )

    filas = db.execute(consulta).all()

    return [
        EstacionCargaRespuesta(
            id=estacion.id,
            identificador=estacion.identificador_fuente,
            nombre=estacion.nombre,
            direccion=estacion.direccion,
            ubicacion=Ubicacion(
                latitud=float(latitud),
                longitud=float(longitud),
            ),
            estado_demostracion=estacion.estado_demostracion,
            conectores=[
                ConectorCargaRespuesta(
                    cantidad=conector.cantidad,
                    tipo_conector=conector.tipo_conector,
                    potencia_kw=(
                        float(conector.potencia_kw)
                        if conector.potencia_kw is not None
                        else None
                    ),
                    estado_operativo=conector.estado_operativo,
                )
                for conector in estacion.conectores
            ],
        )
        for estacion, latitud, longitud in filas
    ]


@router.get(
    "/{estacion_id}",
    response_model=EstacionDetalle,
)
def obtener_detalle_estacion(
    estacion_id: UUID,
    db: Session = Depends(obtener_db),
):
    fila = db.execute(
        select(
            EstacionCarga.id,
            EstacionCarga.nombre,
            EstacionCarga.direccion,
            func.ST_Y(
                EstacionCarga.ubicacion
            ).label("latitud"),
            func.ST_X(
                EstacionCarga.ubicacion
            ).label("longitud"),
            Zona.clave.label("zona_clave"),
        )
        .outerjoin(
            Zona,
            EstacionCarga.zona_id == Zona.id,
        )
        .where(EstacionCarga.id == estacion_id)
    ).one_or_none()

    if fila is None:
        raise HTTPException(
            status_code=404,
            detail="Estación no encontrada",
        )

    conectores = db.execute(
        select(ConectorCarga)
        .where(ConectorCarga.estacion_id == estacion_id)
        .order_by(ConectorCarga.numero_grupo)
    ).scalars().all()

    return EstacionDetalle(
        id=fila.id,
        nombre=fila.nombre,
        direccion=fila.direccion,
        latitud=float(fila.latitud),
        longitud=float(fila.longitud),
        zona_clave=fila.zona_clave,
        conectores=[
            ConectorDetalle(
                tipo_conector=c.tipo_conector,
                cantidad=c.cantidad,
                potencia_kw=(
                    float(c.potencia_kw)
                    if c.potencia_kw is not None
                    else None
                ),
                estado_operativo=c.estado_operativo,
            )
            for c in conectores
        ],
    )