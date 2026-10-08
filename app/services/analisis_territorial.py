"""Motor v1: reglas contractuales, sin inferencia de representatividad poblacional."""
from sqlalchemy import text

VERSION = 'RECOMENDACIONES_V1'


def consulta(db, sql, **params):
    return db.execute(text(sql), params)


def percentil_estricto(valor, distribucion):
    valores = [v for v in distribucion if v is not None]
    if not valores or valor is None:
        return None
    return round(100 * sum(v < valor for v in valores) / len(valores), 2)


def nivel(score):
    return 'MUY_BAJA' if score < 25 else 'BAJA' if score < 50 else 'MEDIA' if score < 75 else 'ALTA'


def confianza(n):
    return 'BAJA' if n < 30 else 'MEDIA' if n < 100 else 'ALTA'


def datos_ciudadanos(db):
    # Sólo perfiles con consentimiento. Los eventos se deduplican por ciudadano.
    filas = consulta(db, '''
        WITH perfiles AS (
            SELECT p.id, p.zona_id, p.tiene_automovil, p.propulsion,
                   p.barrera_principal,
                   EXISTS(SELECT 1 FROM solicitudes_infraestructura s
                          WHERE s.perfil_ciudadano_id=p.id AND s.zona_id=p.zona_id)
                   OR EXISTS(SELECT 1 FROM interacciones i
                             WHERE i.perfil_ciudadano_id=p.id AND i.zona_id=p.zona_id)
                   AS activo
            FROM perfiles_ciudadanos p
            JOIN zonas z ON z.id=p.zona_id
            WHERE p.consentimiento_agregado=true AND z.tipo='AGEB'
        )
        SELECT z.id zona_id, z.clave,
               COALESCE(MAX(v.valor_numerico),0)::float AS viviendas,
               COUNT(p.id)::int AS n,
               COUNT(p.id) FILTER (WHERE p.tiene_automovil=true)::int AS con_auto,
               COUNT(p.id) FILTER (WHERE p.tiene_automovil=true AND p.propulsion IN ('ELECTRICO','HIBRIDO_ENCHUFABLE'))::int AS con_ev,
               COUNT(p.id) FILTER (WHERE p.activo)::int AS activos,
               COUNT(p.id) FILTER (WHERE p.barrera_principal='PRECIO')::int AS precio,
               COUNT(p.id) FILTER (WHERE p.barrera_principal='INFORMACION_DUDAS')::int AS informacion
        FROM zonas z
        LEFT JOIN perfiles p ON p.zona_id=z.id
        LEFT JOIN observaciones v ON v.zona_id=z.id AND v.clave_metrica='VIVIENDAS_HABITADAS'
        WHERE z.tipo='AGEB' AND z.activa=true
        GROUP BY z.id,z.clave
    ''').mappings().all()
    return {str(r['zona_id']): dict(r) for r in filas}


def evaluar_ciudadanos(db, zona_id, todos):
    fila = todos[str(zona_id)]
    n = fila['n']
    # Regla conservadora: BAJA confianza implica score no disponible.
    if n < 30:
        return [], {'participantes_validos': n, 'confianza': 'BAJA', 'motivo': 'MUESTRA_OPERATIVA_INSUFICIENTE'}
    candidatos = [r for r in todos.values() if r['n'] >= 30]
    # Sólo se compara con zonas que cumplen el mismo criterio de suficiencia.
    def cobertura(r):
        return 1000*r['n']/r['viviendas'] if r['viviendas'] > 0 else None
    def actividad(r):
        return r['activos']/r['n'] if r['n'] else None
    evaluaciones=[]
    cobertura_pct=percentil_estricto(cobertura(fila),[cobertura(r) for r in candidatos])
    actividad_pct=percentil_estricto(actividad(fila),[actividad(r) for r in candidatos])
    if cobertura_pct is not None and actividad_pct is not None:
        score=round((cobertura_pct+actividad_pct)/2,2)
        evaluaciones.append(('PARTICIPACION',score,{
            'cobertura_nehnemi_score': cobertura_pct, 'actividad_score': actividad_pct,
            'participantes_validos': n,'participantes_activos':fila['activos'],
            'participantes_por_1000_viviendas':round(cobertura(fila),4),
            'proporcion_activos':round(actividad(fila),6),
            'zonas_comparables':len(candidatos),
            'nota':'Muestra voluntaria; no representa estadísticamente a toda la población.'
        }))
    con_auto=fila['con_auto']
    if con_auto >= 30:
        tasa=fila['con_ev']/con_auto
        comparables=[r['con_ev']/r['con_auto'] for r in todos.values() if r['con_auto']>=30]
        score=percentil_estricto(tasa,comparables)
        evaluaciones.append(('ADOPCION',score,{
            'participantes_con_ev':fila['con_ev'], 'participantes_con_automovil':con_auto,
            'tasa_ev':round(tasa,6),'zonas_comparables':len(comparables),
            'nota':'Proporción entre participantes voluntarios, no tasa poblacional.'
        }))
    return evaluaciones,{'participantes_validos':n,'confianza':confianza(n)}


def indicadores_actuales(db,zona_id):
    rows=consulta(db,'''SELECT dimension::text dimension,puntuacion::float puntuacion,nivel::text nivel,
        confianza::text confianza,componentes FROM indicadores_actuales WHERE zona_id=:z''',z=zona_id).mappings()
    return {r['dimension']:dict(r) for r in rows}


def recomendacion(db,zona_id,todos):
    indicadores=indicadores_actuales(db,zona_id)
    r=todos[str(zona_id)]
    solicitudes=consulta(db,'''SELECT count(*) FROM solicitudes_infraestructura
        WHERE zona_id=:z AND estado IN ('REGISTRADA','EN_REVISION')''',z=zona_id).scalar_one()
    # Demanda relativa: solicitudes activas por 1000 viviendas; percentil estricto entre AGEB con denominador.
    demandas=consulta(db,'''SELECT z.id::text zona_id,
        count(s.id)::float*1000/NULLIF(MAX(v.valor_numerico),0) tasa
        FROM zonas z JOIN observaciones v ON v.zona_id=z.id AND v.clave_metrica='VIVIENDAS_HABITADAS'
        LEFT JOIN solicitudes_infraestructura s ON s.zona_id=z.id AND s.estado IN ('REGISTRADA','EN_REVISION')
        WHERE z.tipo='AGEB' AND z.activa=true AND v.valor_numerico>0
        GROUP BY z.id''').mappings().all()
    demanda=next((float(x['tasa']) for x in demandas if x['zona_id']==str(zona_id)),None)
    pct=percentil_estricto(demanda,[float(x['tasa']) for x in demandas])
    infra=indicadores.get('INFRAESTRUCTURA')
    acceso=indicadores.get('ACCESIBILIDAD')
    adopcion=indicadores.get('ADOPCION')
    participacion=indicadores.get('PARTICIPACION')
    infra_baja=infra and infra['nivel'] in ('BAJA','MUY_BAJA')
    evidencia={'solicitudes_activas':solicitudes,'percentil_demanda':pct,
              'demanda_por_1000_viviendas':demanda,'participantes_validos':r['n'],
              'indicadores':{k:{'nivel':v['nivel'],'puntuacion':v['puntuacion']} for k,v in indicadores.items()},
              'nota':'Solicitudes voluntarias no prueban necesidad técnica ni representatividad.'}
    # Orden de reglas del contrato, con guardas de suficiencia y denominador.
    if r['n']<30 and (solicitudes>0 or infra_baja):
        barrera,accion,prioridad='EVIDENCIA_INSUFICIENTE','RECOPILAR_MAS_DATOS','MEDIA'
        razones=['La evidencia ciudadana todavía tiene confianza baja.','La infraestructura limitada o las solicitudes justifican levantar más información.']
    elif infra_baja and solicitudes>0 and pct is not None and pct>=75 and r['n']>=30:
        barrera,accion,prioridad='INFRAESTRUCTURA','EVALUAR_EXPANSION_CARGA','ALTA'
        razones=['Infraestructura baja y demanda relativa de carga en percentil 75 o superior.','Se requiere validación técnica antes de decidir una instalación.']
    elif participacion and participacion['nivel'] in ('BAJA','MUY_BAJA'):
        barrera,accion,prioridad='PARTICIPACION','AUMENTAR_PARTICIPACION','MEDIA'
        razones=['Participación comparativamente baja entre zonas con evidencia suficiente.']
    elif acceso and acceso['nivel'] in ('BAJA','MUY_BAJA') and r['n']>=30 and r['precio']/r['n']>=0.5:
        barrera,accion,prioridad='ACCESIBILIDAD_ECONOMICA','EVALUAR_ACCESIBILIDAD_ECONOMICA','MEDIA'
        razones=['Condiciones de acceso bajas y al menos la mitad de participantes declaró barrera de precio.']
    elif adopcion and adopcion['nivel'] in ('BAJA','MUY_BAJA') and infra and infra['nivel'] in ('MEDIA','ALTA') and r['n']>=30 and r['informacion']/r['n']>=0.5:
        barrera,accion,prioridad='INFORMACION','INTERVENCION_INFORMATIVA','MEDIA'
        razones=['Adopción baja, infraestructura disponible y barreras informativas declaradas.']
    elif solicitudes>0:
        barrera,accion,prioridad='EVIDENCIA_INSUFICIENTE','INVESTIGAR','MEDIA'
        razones=['Hay solicitudes registradas que requieren revisión y contraste con evidencia territorial.']
    else:
        barrera,accion,prioridad='SIN_CUELLO_PRIORITARIO','MONITOREAR','BAJA'
        razones=['No se cumplen las condiciones para una intervención prioritaria según las reglas v1.']
    return {'barrera_principal':barrera,'accion':accion,'prioridad':prioridad,
            'confianza':confianza(r['n']),'razones':razones,'evidencia':evidencia,'version_reglas':VERSION}
