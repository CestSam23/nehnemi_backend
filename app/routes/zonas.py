from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.database import obtener_db
from app.models.zona import Zona
from app.schemas.zona import ZonaDetalle, ZonaResumen

from app.models.indicador import IndicadorActual
from app.schemas.indicador import IndicadorZona, IndicadoresZona

import json

from fastapi.responses import JSONResponse
from sqlalchemy import and_, func

from app.services.indicadores import obtener_indicadores_actuales

from sqlalchemy.orm import aliased

from app.schemas.resumen_zona import (
    InfraestructuraResumen,
    ResumenZona,
)

from app.schemas.senal import SenalesZona
from app.services.diagnostico import generar_senales

from app.schemas.solicitud import SolicitudesZona
from app.services.solicitudes import obtener_agregados_solicitudes

router = APIRouter(
    prefix="/zonas",
    tags=["Zonas"],
)

@router.get("", response_model=list[ZonaResumen])
def listar_zonas(
    tipo: Literal["CDMX", "ALCALDIA", "AGEB"] | None = Query(default=None),
    zona_padre: str | None = Query(default=None),
    buscar: str | None = Query(default=None),
    db: Session = Depends(obtener_db),
):
    ZonaPadre = aliased(Zona)

    consulta = (
        select(
            Zona.clave,
            Zona.tipo,
            Zona.nombre,
            ZonaPadre.clave.label("zona_padre_clave"),
        )
        .outerjoin(
            ZonaPadre,
            Zona.zona_padre_id == ZonaPadre.id,
        )
        .where(Zona.activa.is_(True))
    )

    if tipo is not None:
        consulta = consulta.where(Zona.tipo == tipo)

    if zona_padre is not None:
        consulta = consulta.where(
            ZonaPadre.clave == zona_padre
        )

    if buscar:
        termino = buscar.strip()

        if termino:
            consulta = consulta.where(
                Zona.nombre.ilike(f"%{termino}%")
                | Zona.clave.ilike(f"%{termino}%")
            )

    consulta = consulta.order_by(
        Zona.tipo,
        Zona.nombre,
    )

    filas = db.execute(consulta).all()

    return [
        ZonaResumen(
            clave=fila.clave,
            tipo=fila.tipo,
            nombre=fila.nombre,
            zona_padre_clave=fila.zona_padre_clave,
        )
        for fila in filas
    ]


@router.get("/mapa")
def obtener_mapa(
    tipo: Literal["ALCALDIA", "AGEB"] = Query(...),
    dimension: Literal[
        "ADOPCION",
        "INFRAESTRUCTURA",
        "PARTICIPACION",
        "ACCESIBILIDAD",
    ] = Query(...),
    db: Session = Depends(obtener_db),
):
    consulta = (
        select(
            Zona.clave,
            Zona.tipo,
            Zona.nombre,
            func.ST_AsGeoJSON(Zona.geometria).label("geometria"),
            IndicadorActual.puntuacion,
            IndicadorActual.nivel,
            IndicadorActual.confianza,
        )
        .outerjoin(
            IndicadorActual,
            and_(
                IndicadorActual.zona_id == Zona.id,
                IndicadorActual.dimension == dimension,
            ),
        )
        .where(
            Zona.tipo == tipo,
            Zona.activa.is_(True),
            Zona.geometria.is_not(None),
        )
        .order_by(Zona.clave)
    )

    filas = db.execute(consulta).all()

    features = []

    for fila in filas:
        disponible = fila.puntuacion is not None

        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(fila.geometria),
                "properties": {
                    "clave": fila.clave,
                    "tipo": fila.tipo,
                    "nombre": fila.nombre,
                    "dimension": dimension,
                    "disponible": disponible,
                    "puntuacion": (
                        float(fila.puntuacion)
                        if disponible
                        else None
                    ),
                    "nivel": (
                        fila.nivel
                        if disponible
                        else None
                    ),
                    "confianza": (
                        fila.confianza
                        if disponible
                        else None
                    ),
                },
            }
        )

    return JSONResponse(
        content={
            "type": "FeatureCollection",
            "features": features,
        }
    )


@router.get("/{clave}", response_model=ZonaDetalle)
def obtener_zona(
    clave: str,
    db: Session = Depends(obtener_db),
):
    ZonaPadre = aliased(Zona)

    consulta = (
        select(
            Zona.clave,
            Zona.tipo,
            Zona.nombre,
            Zona.activa,
            ZonaPadre.clave.label("zona_padre_clave"),
        )
        .outerjoin(
            ZonaPadre,
            Zona.zona_padre_id == ZonaPadre.id,
        )
        .where(Zona.clave == clave)
    )

    fila = db.execute(consulta).one_or_none()

    if fila is None:
        raise HTTPException(
            status_code=404,
            detail="Zona no encontrada",
        )

    return ZonaDetalle(
        clave=fila.clave,
        tipo=fila.tipo,
        nombre=fila.nombre,
        zona_padre_clave=fila.zona_padre_clave,
        activa=fila.activa,
    )

@router.get(
    "/{clave}/indicadores",
    response_model=IndicadoresZona,
)
def obtener_indicadores_zona(
    clave: str,
    db: Session = Depends(obtener_db),
):
    zona_id = db.execute(
        select(Zona.id)
        .where(
            Zona.clave == clave,
            Zona.activa.is_(True),
        )
    ).scalar_one_or_none()

    if zona_id is None:
        raise HTTPException(
            status_code=404,
            detail="Zona no encontrada",
        )

    return IndicadoresZona(
        zona_clave=clave,
        indicadores=obtener_indicadores_actuales(
            db,
            zona_id,
        ),
    )

@router.get(
    "/{clave}/resumen",
    response_model=ResumenZona,
)
def obtener_resumen_zona(
    clave: str,
    db: Session = Depends(obtener_db),
):
    ZonaPadre = aliased(Zona)

    fila = db.execute(
        select(
            Zona.id,
            Zona.clave,
            Zona.tipo,
            Zona.nombre,
            ZonaPadre.clave.label("zona_padre_clave"),
        )
        .outerjoin(
            ZonaPadre,
            Zona.zona_padre_id == ZonaPadre.id,
        )
        .where(
            Zona.clave == clave,
            Zona.activa.is_(True),
        )
    ).one_or_none()

    if fila is None:
        raise HTTPException(
            status_code=404,
            detail="Zona no encontrada",
        )

    indicadores = obtener_indicadores_actuales(
        db,
        fila.id,
    )

    indicador_infraestructura = next(
        (
            indicador
            for indicador in indicadores
            if indicador.dimension == "INFRAESTRUCTURA"
            and indicador.disponible
        ),
        None,
    )

    infraestructura = None

    if indicador_infraestructura is not None:
        componentes = (
            indicador_infraestructura.componentes
            or {}
        )

        infraestructura = InfraestructuraResumen(
            estaciones=int(
                componentes.get(
                    "estaciones_en_zona",
                    0,
                )
            ),
            conectores=int(
                componentes.get(
                    "conectores_en_zona",
                    0,
                )
            ),
            potencia_total_kw=float(
                componentes.get(
                    "potencia_total_kw",
                    0,
                )
            ),
            distancia_estacion_m=(
                float(componentes["distancia_estacion_m"])
                if componentes.get("distancia_estacion_m")
                is not None
                else None
            ),
        )

    return ResumenZona(
        clave=fila.clave,
        tipo=fila.tipo,
        nombre=fila.nombre,
        zona_padre_clave=fila.zona_padre_clave,
        indicadores=indicadores,
        infraestructura=infraestructura,
    )

@router.get(
    "/{clave}/senales",
    response_model=SenalesZona,
)
def obtener_senales_zona(
    clave: str,
    db: Session = Depends(obtener_db),
):
    zona_id = db.execute(
        select(Zona.id)
        .where(
            Zona.clave == clave,
            Zona.activa.is_(True),
        )
    ).scalar_one_or_none()

    if zona_id is None:
        raise HTTPException(
            status_code=404,
            detail="Zona no encontrada",
        )

    indicadores = obtener_indicadores_actuales(
        db,
        zona_id,
    )

    return SenalesZona(
        zona_clave=clave,
        senales=generar_senales(indicadores),
    )

@router.get(
    "/{clave}/solicitudes",
    response_model=SolicitudesZona,
)
def obtener_solicitudes_zona(
    clave: str,
    db: Session = Depends(obtener_db),
):
    zona_id = db.execute(
        select(Zona.id)
        .where(
            Zona.clave == clave,
            Zona.activa.is_(True),
        )
    ).scalar_one_or_none()

    if zona_id is None:
        raise HTTPException(
            status_code=404,
            detail="Zona no encontrada",
        )

    total, por_estado, por_motivo = (
        obtener_agregados_solicitudes(
            db,
            zona_id,
        )
    )

    return SolicitudesZona(
        zona_clave=clave,
        total=total,
        por_estado=por_estado,
        por_motivo=por_motivo,
    )