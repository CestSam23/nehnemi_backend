from fastapi import FastAPI
from sqlalchemy import text

from app.database import engine
from app.routes.zonas import router as zonas_router
from app.routes.estaciones import router as estaciones_router
from app.routes.ciudadanos import router as ciudadanos_router
from app.routes.solicitudes import router as solicitudes_router
from app.routes.interacciones import router as interacciones_router
from app.routes.autenticacion import router as autenticacion_router
from app.routes.fuentes import router as fuentes_router
from app.routes.contenidos import router as contenidos_router
from app.routes.panorama import router as panorama_router
from app.routes.analisis_territorial import router as analisis_router


app = FastAPI(
    title="Nehnemi API",
    version="1.0.0",
    description="API de Nehnemi para electromovilidad en la Ciudad de México",
)

app.include_router(fuentes_router, prefix="/api/v1")
app.include_router(contenidos_router, prefix="/api/v1")

app.include_router(
    zonas_router,
    prefix="/api/v1",
)

app.include_router(
    estaciones_router,
    prefix="/api/v1",
)

app.include_router(
    ciudadanos_router,
    prefix="/api/v1",
)

app.include_router(
    solicitudes_router,
    prefix="/api/v1",
)

app.include_router(
    interacciones_router,
    prefix="/api/v1",
)

app.include_router(
    autenticacion_router,
    prefix="/api/v1",
)

app.include_router(
    panorama_router,
    prefix="/api/v1",
)

app.include_router(
    analisis_router,
    prefix="/api/v1",
)

@app.get("/health", tags=["Sistema"])
def health():
    with engine.connect() as conexion:
        conexion.execute(text("SELECT 1"))

    return {
        "estado": "ok",
        "base_datos": "conectada",
    }