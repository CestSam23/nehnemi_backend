from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.indicador import IndicadorActual
from app.schemas.indicador import IndicadorZona


DIMENSIONES = [
    "ADOPCION",
    "INFRAESTRUCTURA",
    "PARTICIPACION",
    "ACCESIBILIDAD",
]


def obtener_indicadores_actuales(
    db: Session,
    zona_id,
) -> list[IndicadorZona]:
    filas = db.execute(
        select(IndicadorActual)
        .where(IndicadorActual.zona_id == zona_id)
    ).scalars().all()

    por_dimension = {
        fila.dimension: fila
        for fila in filas
    }

    indicadores = []

    for dimension in DIMENSIONES:
        fila = por_dimension.get(dimension)

        if fila is None:
            indicadores.append(
                IndicadorZona(
                    dimension=dimension,
                    disponible=False,
                )
            )
            continue

        indicadores.append(
            IndicadorZona(
                dimension=dimension,
                disponible=True,
                puntuacion=float(fila.puntuacion),
                nivel=fila.nivel,
                confianza=fila.confianza,
                tamano_muestra=fila.tamano_muestra,
                componentes=fila.componentes,
                explicacion=fila.explicacion,
            )
        )

    return indicadores