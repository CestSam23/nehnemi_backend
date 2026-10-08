from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import obtener_db
from app.models.estacion import ConectorCarga, EstacionCarga
from app.models.zona import Zona
from app.schemas.estacion import (
    ConectorCargaRespuesta,
    EstacionCargaRespuesta,
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
    zona_clave: str | None = Query(default=None),
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

    if zona_clave is not None:
        zona_id = db.execute(
            select(Zona.id).where(
                Zona.clave == zona_clave,
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

    filas = db.execute(consulta).all()

    return [
        EstacionCargaRespuesta(
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