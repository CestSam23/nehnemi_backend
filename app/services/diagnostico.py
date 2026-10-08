from app.schemas.indicador import IndicadorZona
from app.schemas.senal import SenalDiagnostica


def generar_senales(
    indicadores: list[IndicadorZona],
) -> list[SenalDiagnostica]:
    senales = []

    por_dimension = {
        indicador.dimension: indicador
        for indicador in indicadores
    }

    infraestructura = por_dimension.get("INFRAESTRUCTURA")

    if infraestructura and infraestructura.disponible:
        componentes = infraestructura.componentes or {}

        estaciones = componentes.get("estaciones_en_zona")
        conectores = componentes.get("conectores_en_zona")
        distancia = componentes.get("distancia_estacion_m")

        if estaciones == 0:
            senales.append(
                SenalDiagnostica(
                    codigo="SIN_INFRAESTRUCTURA_LOCAL",
                    categoria="INFRAESTRUCTURA",
                    valor=0,
                    unidad="estaciones",
                    descripcion=(
                        "No se identificaron estaciones de carga "
                        "dentro de la zona."
                    ),
                )
            )

        if conectores == 0:
            senales.append(
                SenalDiagnostica(
                    codigo="SIN_CONECTORES_LOCALES",
                    categoria="INFRAESTRUCTURA",
                    valor=0,
                    unidad="conectores",
                    descripcion=(
                        "No se identificaron conectores de carga "
                        "dentro de la zona."
                    ),
                )
            )

        if distancia is not None and distancia >= 2000:
            senales.append(
                SenalDiagnostica(
                    codigo="DISTANCIA_CARGA_ELEVADA",
                    categoria="INFRAESTRUCTURA",
                    valor=float(distancia),
                    unidad="m",
                    descripcion=(
                        "La estación de carga identificada más cercana "
                        "se encuentra a dos kilómetros o más."
                    ),
                )
            )

        if infraestructura.nivel in ("MUY_BAJA", "BAJA"):
            senales.append(
                SenalDiagnostica(
                    codigo="INFRAESTRUCTURA_BAJA",
                    categoria="INFRAESTRUCTURA",
                    valor=float(infraestructura.puntuacion),
                    unidad="puntos",
                    descripcion=(
                        "La evaluación comparativa de infraestructura "
                        "de carga de la zona es baja."
                    ),
                )
            )

    accesibilidad = por_dimension.get("ACCESIBILIDAD")

    if accesibilidad and accesibilidad.disponible:
        componentes = accesibilidad.componentes or {}

        tenencia = componentes.get("tenencia_automovil")
        viviendas_auto = componentes.get("viviendas_con_automovil")

        if tenencia is not None and tenencia >= 0.5:
            senales.append(
                SenalDiagnostica(
                    codigo="ALTA_TENENCIA_AUTOMOVIL",
                    categoria="ACCESIBILIDAD",
                    valor=round(float(tenencia) * 100, 2),
                    unidad="porcentaje",
                    descripcion=(
                        "Al menos la mitad de las viviendas habitadas "
                        "de la zona cuentan con automóvil."
                    ),
                )
            )

        if viviendas_auto is not None:
            senales.append(
                SenalDiagnostica(
                    codigo="VIVIENDAS_CON_AUTOMOVIL",
                    categoria="ACCESIBILIDAD",
                    valor=int(viviendas_auto),
                    unidad="viviendas",
                    descripcion=(
                        "Número de viviendas habitadas con automóvil "
                        "registrado en la evidencia territorial."
                    ),
                )
            )

    for dimension in ("ADOPCION", "PARTICIPACION"):
        indicador = por_dimension.get(dimension)

        if indicador is None or not indicador.disponible:
            senales.append(
                SenalDiagnostica(
                    codigo=f"SIN_EVIDENCIA_{dimension}",
                    categoria="EVIDENCIA",
                    descripcion=(
                        f"No existe evidencia suficiente para evaluar "
                        f"la dimensión {dimension.lower()}."
                    ),
                )
            )

    return senales