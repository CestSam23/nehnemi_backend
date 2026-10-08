from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.zona import Zona


def obtener_ageb_por_ubicacion(
    db: Session,
    latitud: float,
    longitud: float,
):
    punto = func.ST_SetSRID(
        func.ST_MakePoint(
            longitud,
            latitud,
        ),
        4326,
    )

    return db.execute(
        select(Zona)
        .where(
            Zona.tipo == "AGEB",
            Zona.activa.is_(True),
            func.ST_Covers(
                Zona.geometria,
                punto,
            ),
        )
        .limit(1)
    ).scalar_one_or_none()