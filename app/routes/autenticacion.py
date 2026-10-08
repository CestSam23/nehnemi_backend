import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
)
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import obtener_db
from app.models.usuario_gobierno import UsuarioGobierno
from app.services.contrasenas import verificar_contrasena


load_dotenv()

router = APIRouter(
    prefix="/autenticacion",
    tags=["Autenticación gubernamental"],
)

COOKIE_NOMBRE = "nehneni_sesion"
JWT_SECRET = os.environ["JWT_GOBIERNO_SECRET"]
JWT_ALGORITHM = "HS256"
DURACION_MINUTOS = 30

# False únicamente para desarrollo local mediante HTTP.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"


class Credenciales(BaseModel):
    correo: str
    contrasena: str


class UsuarioSesion(BaseModel):
    id: UUID
    nombre: str
    correo: str
    rol: str


def obtener_usuario_gobierno(
    request: Request,
    db: Session = Depends(obtener_db),
) -> UsuarioGobierno:
    token = request.cookies.get(COOKIE_NOMBRE)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Sesión gubernamental requerida",
        )

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )

        if payload.get("tipo") != "gobierno":
            raise ValueError("Tipo de token incorrecto")

        usuario_id = UUID(payload["sub"])

    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(
            status_code=401,
            detail="Sesión gubernamental no válida",
        )

    usuario = db.execute(
        select(UsuarioGobierno).where(
            UsuarioGobierno.id == usuario_id,
            UsuarioGobierno.activo.is_(True),
        )
    ).scalar_one_or_none()

    if usuario is None:
        raise HTTPException(
            status_code=401,
            detail="Usuario gubernamental no válido",
        )

    return usuario


def requerir_administrador(
    usuario: UsuarioGobierno = Depends(obtener_usuario_gobierno),
) -> UsuarioGobierno:
    if usuario.rol != "ADMINISTRADOR":
        raise HTTPException(
            status_code=403,
            detail="Se requiere el rol ADMINISTRADOR",
        )

    return usuario


@router.post("/iniciar-sesion")
def iniciar_sesion(
    datos: Credenciales,
    response: Response,
    db: Session = Depends(obtener_db),
):
    usuario = db.execute(
        select(UsuarioGobierno).where(
            UsuarioGobierno.correo == datos.correo.strip().lower(),
            UsuarioGobierno.activo.is_(True),
        )
    ).scalar_one_or_none()

    if usuario is None or not verificar_contrasena(
        datos.contrasena,
        usuario.contrasena_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Credenciales incorrectas",
        )

    ahora = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "sub": str(usuario.id),
            "tipo": "gobierno",
            "iat": ahora,
            "exp": ahora + timedelta(minutes=DURACION_MINUTOS),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    response.set_cookie(
        key=COOKIE_NOMBRE,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=DURACION_MINUTOS * 60,
        path="/api/v1",
    )

    return {
        "id": str(usuario.id),
        "nombre": usuario.nombre,
        "correo": usuario.correo,
        "rol": usuario.rol,
    }


@router.get("/sesion", response_model=UsuarioSesion)
def consultar_sesion(
    usuario: UsuarioGobierno = Depends(obtener_usuario_gobierno),
):
    return UsuarioSesion(
        id=usuario.id,
        nombre=usuario.nombre,
        correo=usuario.correo,
        rol=usuario.rol,
    )


@router.post("/cerrar-sesion", status_code=204)
def cerrar_sesion(response: Response):
    response.delete_cookie(
        key=COOKIE_NOMBRE,
        path="/api/v1",
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )