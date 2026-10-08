from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import obtener_db


router = APIRouter(
    prefix="/panorama",
    tags=["Panorama"],
)


@router.get("")
def obtener_panorama(
    db: Session = Depends(obtener_db),
):
    estadisticas = db.execute(
        text("""
            SELECT
                (
                    SELECT COUNT(*)
                    FROM zonas
                    WHERE tipo = 'ALCALDIA'
                ) AS alcaldias,

                (
                    SELECT COUNT(*)
                    FROM zonas
                    WHERE tipo = 'AGEB'
                ) AS agebs,

                (
                    SELECT COUNT(*)
                    FROM estaciones_carga
                ) AS estaciones_registradas,

                (
                    SELECT COALESCE(SUM(cantidad), 0)
                    FROM conectores_carga
                ) AS conectores_registrados,

                (
                    SELECT COUNT(*)
                    FROM solicitudes_infraestructura
                ) AS solicitudes_registradas,

                (
                    SELECT COUNT(*)
                    FROM fuentes_datos
                ) AS fuentes_documentadas
        """)
    ).mappings().one()

    return {
        "fecha_actualizacion": datetime.now(
            timezone.utc
        ).isoformat(),

        "cobertura_territorial": {
            "alcaldias": estadisticas["alcaldias"],
            "agebs": estadisticas["agebs"],
        },

        "infraestructura": {
            "estaciones_registradas": (
                estadisticas["estaciones_registradas"]
            ),
            "conectores_registrados": (
                estadisticas["conectores_registrados"]
            ),
            "estado_operativo_verificado": False,
        },

        "participacion": {
            "solicitudes_registradas": (
                estadisticas["solicitudes_registradas"]
            ),
        },

        "fuentes_documentadas": (
            estadisticas["fuentes_documentadas"]
        ),

        "dimensiones": {
            "ADOPCION": {
                "disponible": False,
                "motivo": "Sin datos territoriales suficientes",
            },
            "INFRAESTRUCTURA": {
                "disponible": True,
            },
            "PARTICIPACION": {
                "disponible": False,
                "motivo": "Sin evaluación territorial consolidada",
            },
            "ACCESIBILIDAD": {
                "disponible": True,
            },
        },
    }