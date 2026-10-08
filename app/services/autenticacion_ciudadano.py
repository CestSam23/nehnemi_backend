import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET no está definida")


JWT_ALGORITHM = "HS256"
JWT_DIAS = 365

bearer = HTTPBearer(auto_error=False)


def crear_token_ciudadano(
    perfil_id: UUID,
) -> str:
    ahora = datetime.now(timezone.utc)

    payload = {
        "sub": str(perfil_id),
        "tipo": "ciudadano",
        "iat": ahora,
        "exp": ahora + timedelta(days=JWT_DIAS),
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def obtener_id_ciudadano(
    credenciales: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> UUID:
    if credenciales is None:
        raise HTTPException(
            status_code=401,
            detail="Token ciudadano requerido",
        )

    try:
        payload = jwt.decode(
            credenciales.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )

        if payload.get("tipo") != "ciudadano":
            raise ValueError()

        return UUID(payload["sub"])

    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(
            status_code=401,
            detail="Token ciudadano inválido",
        )