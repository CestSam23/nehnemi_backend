"""Rutas de análisis Nehnemi v1. Importar dependencias de auth del módulo existente."""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import obtener_db
from app.services.analisis_territorial import (
    consulta, datos_ciudadanos, evaluar_ciudadanos, recomendacion, nivel, confianza,
)
# AJUSTAR SÓLO si el proyecto utiliza nombres distintos para estas dependencias:
from app.routes.autenticacion import obtener_usuario_gobierno, requerir_administrador

router = APIRouter(tags=['Análisis territorial'])


def buscar_zona(db, clave):
    zona = consulta(db, 'SELECT id, clave, tipo::text tipo FROM zonas WHERE clave=:c AND activa=true', c=clave).mappings().first()
    if not zona:
        raise HTTPException(404, 'Zona no encontrada')
    if zona['tipo'] != 'AGEB':
        raise HTTPException(422, 'La evaluación ciudadana v1 requiere una AGEB')
    return zona


@router.get('/zonas/{clave_zona}/recomendaciones')
def leer_recomendaciones(clave_zona: str, db: Session = Depends(obtener_db), _=Depends(obtener_usuario_gobierno)):
    zona=buscar_zona(db,clave_zona)
    filas=consulta(db, '''SELECT id,barrera_principal::text,accion::text,prioridad::text,
      confianza::text,razones,evidencia,version_reglas,creado_en
      FROM recomendaciones WHERE zona_id=:z ORDER BY creado_en DESC,id DESC LIMIT 30''',z=zona['id']).mappings().all()
    return {'zona_clave':clave_zona,'recomendaciones':[dict(f) for f in filas]}


@router.post('/zonas/{clave_zona}/evaluar')
def evaluar_zona(clave_zona: str, db: Session = Depends(obtener_db), _=Depends(requerir_administrador)):
    zona=buscar_zona(db,clave_zona)
    # Evitar dos evaluaciones concurrentes para la misma AGEB.
    consulta(db, 'SELECT pg_advisory_xact_lock(hashtext(:c))',c=clave_zona)
    todos=datos_ciudadanos(db)
    nuevas,estado=evaluar_ciudadanos(db,zona['id'],todos)
    # Guardar únicamente indicadores que cumplen condiciones de cálculo.
    for dimension,score,componentes in nuevas:
        consulta(db, '''INSERT INTO evaluaciones_indicadores
           (zona_id,dimension,puntuacion,nivel,confianza,tamano_muestra,version_formula,componentes,explicacion)
           VALUES (:z,CAST(:d AS dimension_indicador),:s,CAST(:nivel AS nivel_indicador),
                   CAST(:conf AS nivel_confianza),:n,:v,CAST(:componentes AS jsonb),:exp)''',
            z=zona['id'],d=dimension,s=score,nivel=nivel(score),conf=confianza(todos[str(zona['id'])]['n']),
            n=todos[str(zona['id'])]['n'],v=dimension+'_V1',componentes=json.dumps(componentes),
            exp='Percentil estricto de zonas comparables; participación voluntaria no representativa.')
    # Si deja de haber evidencia suficiente (ej. borrado de perfil), no debemos mantener
    # una puntuación anterior como actual: el GET debe tratarla como no disponible.
    rec=recomendacion(db,zona['id'],todos)
    fila=consulta(db, '''INSERT INTO recomendaciones
      (zona_id,barrera_principal,accion,prioridad,confianza,razones,evidencia,version_reglas)
      VALUES (:z,CAST(:b AS tipo_barrera_diagnosticada),CAST(:a AS accion_recomendada),
              CAST(:p AS prioridad_recomendacion),CAST(:c AS nivel_confianza),
              CAST(:r AS jsonb),CAST(:e AS jsonb),:v)
      RETURNING id,creado_en''',z=zona['id'],b=rec['barrera_principal'],a=rec['accion'],
      p=rec['prioridad'],c=rec['confianza'],r=json.dumps(rec['razones']),
      e=json.dumps(rec['evidencia']),v=rec['version_reglas']).mappings().one()
    db.commit()
    return {'zona_clave':clave_zona,'evaluacion_actualizada':{
        'dimensiones_recalculadas':[d for d,_,_ in nuevas],**estado},
        'recomendacion':{'id':fila['id'],'creado_en':fila['creado_en'],**rec}}


@router.get('/tendencias/electromovilidad')
def tendencias(db: Session = Depends(obtener_db), _=Depends(obtener_usuario_gobierno)):
    filas=consulta(db, '''SELECT o.periodo,o.valor_numerico::float AS valor,o.unidad,
      f.clave AS fuente FROM observaciones o
      JOIN zonas z ON z.id=o.zona_id JOIN fuentes_datos f ON f.id=o.fuente_id
      WHERE z.clave='09' AND o.clave_metrica='VENTAS_EV' AND o.valor_numerico IS NOT NULL
      ORDER BY o.periodo''').mappings().all()
    return {'series':[{'clave_metrica':'VENTAS_EV','zona_clave':'09',
        'fuente':'INEGI_RAIAVL_EV','puntos':[dict(x) for x in filas]}] if filas else [],
        'disponible':bool(filas)}
