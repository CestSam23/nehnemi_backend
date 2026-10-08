from sqlalchemy import text
from sqlalchemy.orm import Session


NIVELES = ("MUY_BAJA", "BAJA", "MEDIA", "ALTA")
DIMENSIONES = (
    "ADOPCION",
    "INFRAESTRUCTURA",
    "PARTICIPACION",
    "ACCESIBILIDAD",
)


def _escalar(db: Session, sql: str, params=None):
    return db.execute(
        text(sql),
        params or {},
    ).scalar()


def _filas(db: Session, sql: str, params=None):
    return [
        dict(fila)
        for fila in db.execute(
            text(sql),
            params or {},
        ).mappings().all()
    ]


def obtener_panorama_ampliado(db: Session) -> dict:
    """
    Complementa el panorama gubernamental existente.

    No modifica información.
    No recalcula indicadores.
    No genera recomendaciones nuevas.
    """

    # --------------------------------------------------
    # TERRITORIO
    # --------------------------------------------------

    territorio = {
        "alcaldias": _escalar(
            db,
            """
            SELECT COUNT(*)
            FROM zonas
            WHERE tipo = 'ALCALDIA'
              AND activa = TRUE
            """,
        ),
        "agebs": _escalar(
            db,
            """
            SELECT COUNT(*)
            FROM zonas
            WHERE tipo = 'AGEB'
              AND activa = TRUE
            """,
        ),
    }

    # --------------------------------------------------
    # INFRAESTRUCTURA
    # --------------------------------------------------

    infraestructura = _filas(
        db,
        """
        SELECT
            (SELECT COUNT(*)
             FROM estaciones_carga)
                AS estaciones_registradas,

            (SELECT COALESCE(SUM(cantidad), 0)
             FROM conectores_carga)
                AS conectores_registrados,

            (SELECT COALESCE(SUM(potencia_kw * cantidad), 0)
             FROM conectores_carga)
                AS potencia_total_kw
        """,
    )[0]

    infraestructura["potencia_nominal_agregada_kw"] = (
        infraestructura["potencia_total_kw"]
    )

    infraestructura["metodologia_potencia"] = {
        "formula": "SUM(cantidad * potencia_kw)",
        "interpretacion": (
            "Suma nominal estimada de potencia de los "
            "conectores registrados."
        ),
        "supuesto": (
            "La potencia registrada corresponde a "
            "cada conector del grupo."
        ),
        "limitaciones": [
            "No representa potencia simultánea disponible.",
            "No confirma el estado operativo de las estaciones.",
            "Depende de la calidad de los datos originales.",
        ],
    }

    infraestructura["estado_operativo_verificado"] = False

    # --------------------------------------------------
    # DISTRIBUCIONES DE INDICADORES
    # --------------------------------------------------

    filas_indicadores = _filas(
        db,
        """
        SELECT
            ia.dimension::text AS dimension,
            ia.nivel::text AS nivel,
            COUNT(*) AS cantidad
        FROM indicadores_actuales ia
        JOIN zonas z ON z.id = ia.zona_id
        WHERE z.tipo = 'AGEB'
          AND z.activa = TRUE
        GROUP BY
            ia.dimension,
            ia.nivel
        """,
    )

    distribuciones = {}

    total_agebs = territorio["agebs"]

    for dimension in DIMENSIONES:
        distribuciones[dimension] = {
            "disponibles": 0,
            "sin_datos": total_agebs,
            "niveles": {
                nivel: 0
                for nivel in NIVELES
            },
        }

    for fila in filas_indicadores:
        dimension = fila["dimension"]
        nivel = fila["nivel"]
        cantidad = fila["cantidad"]

        if dimension not in distribuciones:
            continue

        if nivel not in NIVELES:
            continue

        distribuciones[dimension]["niveles"][nivel] += cantidad
        distribuciones[dimension]["disponibles"] += cantidad

    for dimension in DIMENSIONES:
        disponibles = distribuciones[dimension]["disponibles"]

        distribuciones[dimension]["sin_datos"] = max(
            0,
            total_agebs - disponibles,
        )

    # --------------------------------------------------
    # PARTICIPACIÓN
    # --------------------------------------------------

    participacion = _filas(
        db,
        """
        SELECT
            (SELECT COUNT(*)
             FROM perfiles_ciudadanos)
                AS ciudadanos_registrados,

            (SELECT COUNT(*)
             FROM perfiles_ciudadanos
             WHERE consentimiento_agregado = TRUE)
                AS ciudadanos_consentimiento_agregado,

            (SELECT COUNT(*)
             FROM interacciones)
                AS interacciones_registradas,

            (SELECT COUNT(*)
             FROM solicitudes_infraestructura)
                AS solicitudes_registradas
        """,
    )[0]

    # --------------------------------------------------
    # SOLICITUDES POR ESTADO
    # --------------------------------------------------

    estados = (
        "REGISTRADA",
        "EN_REVISION",
        "ATENDIDA",
        "DESCARTADA",
    )

    solicitudes = {
        "total": participacion["solicitudes_registradas"],
        "por_estado": {
            estado: 0
            for estado in estados
        },
    }

    filas_solicitudes = _filas(
        db,
        """
        SELECT
            estado::text AS estado,
            COUNT(*) AS cantidad
        FROM solicitudes_infraestructura
        GROUP BY estado
        """,
    )

    for fila in filas_solicitudes:
        solicitudes["por_estado"][fila["estado"]] = fila["cantidad"]

    # --------------------------------------------------
    # VENTAS EV: DATOS REALES
    # --------------------------------------------------

    ventas = _filas(
        db,
        """
        SELECT
            o.periodo,
            o.valor_numerico AS vehiculos,
            o.unidad,
            f.clave AS fuente
        FROM observaciones o
        JOIN zonas z ON z.id = o.zona_id
        JOIN fuentes_datos f ON f.id = o.fuente_id
        WHERE o.clave_metrica = 'VENTAS_EV'
          AND z.clave = '09'
        ORDER BY o.periodo
        """,
    )

    for venta in ventas:
        venta["vehiculos"] = (
            float(venta["vehiculos"])
            if venta["vehiculos"] is not None
            else None
        )

    ultimo_periodo = ventas[-1] if ventas else None

    ventas_ev = {
        "ambito": "CDMX",
        "ultimo_periodo": (
            ultimo_periodo["periodo"]
            if ultimo_periodo
            else None
        ),
        "ultimo_valor": (
            ultimo_periodo["vehiculos"]
            if ultimo_periodo
            else None
        ),
        "serie_mensual": ventas,
        "periodos_disponibles": len(ventas),
    }

    # --------------------------------------------------
    # ZONAS PRIORITARIAS
    # --------------------------------------------------
    # Solo la recomendación más reciente de cada AGEB.
    # No se duplican las recomendaciones históricas.
    # --------------------------------------------------

    zonas_prioritarias = _filas(
        db,
        """
        WITH ultimas AS (
            SELECT DISTINCT ON (r.zona_id)
                r.zona_id,
                r.id,
                r.barrera_principal,
                r.accion,
                r.prioridad,
                r.confianza,
                r.creado_en
            FROM recomendaciones r
            ORDER BY
                r.zona_id,
                r.creado_en DESC,
                r.id DESC
        )
        SELECT
            z.clave AS clave_zona,
            z.nombre AS nombre_zona,
            u.id AS recomendacion_id,
            u.barrera_principal::text AS barrera_principal,
            u.accion::text AS accion,
            u.prioridad::text AS prioridad,
            u.confianza::text AS confianza,
            u.creado_en
        FROM ultimas u
        JOIN zonas z ON z.id = u.zona_id
        WHERE z.tipo = 'AGEB'
          AND z.activa = TRUE
          AND u.prioridad IN ('ALTA', 'MEDIA')
        ORDER BY
            CASE u.prioridad
                WHEN 'ALTA' THEN 0
                WHEN 'MEDIA' THEN 1
                ELSE 2
            END,
            u.creado_en DESC
        LIMIT 20
        """,
    )

    for zona in zonas_prioritarias:
        zona["creado_en"] = zona["creado_en"].isoformat()

    return {
        "territorio": territorio,
        "infraestructura": infraestructura,
        "distribuciones": distribuciones,
        "participacion": participacion,
        "solicitudes": solicitudes,
        "ventas_ev": ventas_ev,
        "zonas_prioritarias": zonas_prioritarias,
    }