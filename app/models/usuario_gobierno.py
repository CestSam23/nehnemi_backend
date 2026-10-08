import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ENUM
from app.database import Base


class UsuarioGobierno(Base):
    __tablename__ = "usuarios_gobierno"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    nombre: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )

    correo: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    contrasena_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    rol: Mapped[str] = mapped_column(
        ENUM(
            "ANALISTA",
            "ADMINISTRADOR",
            name="rol_gobierno",
            create_type=False,
        ),
        nullable=False,
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )