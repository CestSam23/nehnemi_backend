from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.solicitud import SolicitudInfraestructura
from app.schemas.solicitud import ConteoCategoria


def obtener_agregados_solicitudes(
    db: Session,
    zona_id,
):
    total = db.execute(
        select(func.count(SolicitudInfraestructura.id))
        .where(SolicitudInfraestructura.zona_id == zona_id)
    ).scalar_one()

    filas_estado = db.execute(
        select(
            SolicitudInfraestructura.estado,
            func.count(SolicitudInfraestructura.id),
        )
        .where(SolicitudInfraestructura.zona_id == zona_id)
        .group_by(SolicitudInfraestructura.estado)
        .order_by(SolicitudInfraestructura.estado)
    ).all()

    filas_motivo = db.execute(
        select(
            SolicitudInfraestructura.motivo,
            func.count(SolicitudInfraestructura.id),
        )
        .where(SolicitudInfraestructura.zona_id == zona_id)
        .group_by(SolicitudInfraestructura.motivo)
        .order_by(SolicitudInfraestructura.motivo)
    ).all()

    return (
        total,
        [
            ConteoCategoria(
                valor=estado,
                cantidad=cantidad,
            )
            for estado, cantidad in filas_estado
        ],
        [
            ConteoCategoria(
                valor=motivo,
                cantidad=cantidad,
            )
            for motivo, cantidad in filas_motivo
        ],
    )