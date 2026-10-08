from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import obtener_db
from app.services.panorama_ampliado import obtener_panorama_ampliado


router = APIRouter(
    prefix="/panorama",
    tags=["Panorama"],
)


@router.get("")
def obtener_panorama(
    db: Session = Depends(obtener_db),
):
    """
    Panorama general de electromovilidad en CDMX.

    Incluye:
    - Cobertura territorial
    - Infraestructura de carga
    - Distribución de indicadores
    - Participación ciudadana
    - Solicitudes de infraestructura
    - Ventas de vehículos eléctricos
    - Zonas prioritarias

    Conserva compatibilidad con la respuesta anterior.
    """

    # --------------------------------------------------
    # 1. PANORAMA AMPLIADO
    # --------------------------------------------------

    ampliacion = obtener_panorama_ampliado(db)

    # --------------------------------------------------
    # 2. INFORMACIÓN COMPLEMENTARIA
    # --------------------------------------------------

    fuentes_documentadas = db.execute(
        text("""
            SELECT COUNT(*)
            FROM fuentes_datos
        """)
    ).scalar_one()

    # --------------------------------------------------
    # 3. DISPONIBILIDAD DE DIMENSIONES
    # --------------------------------------------------

    distribuciones = ampliacion["distribuciones"]

    dimensiones = {}

    motivos_no_disponibilidad = {
        "ADOPCION": "Sin datos territoriales suficientes",
        "INFRAESTRUCTURA": "Sin evaluaciones territoriales disponibles",
        "PARTICIPACION": "Sin evaluación territorial consolidada",
        "ACCESIBILIDAD": "Sin evaluaciones territoriales disponibles",
    }

    for dimension, datos in distribuciones.items():
        disponible = datos["disponibles"] > 0

        dimensiones[dimension] = {
            "disponible": disponible,
        }

        if not disponible:
            dimensiones[dimension]["motivo"] = (
                motivos_no_disponibilidad.get(
                    dimension,
                    "Sin datos suficientes",
                )
            )

    # --------------------------------------------------
    # 4. RESPUESTA FINAL
    # --------------------------------------------------

    return {
        "fecha_actualizacion": datetime.now(
            timezone.utc
        ).isoformat(),

        # Compatibilidad con el endpoint anterior.
        "cobertura_territorial": ampliacion["territorio"],

        "fuentes_documentadas": fuentes_documentadas,

        "dimensiones": dimensiones,

        # Nuevos bloques.
        **ampliacion,
    }