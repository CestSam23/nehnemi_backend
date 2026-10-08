import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Zona(Base):
    __tablename__ = "zonas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    clave: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
    )

    tipo: Mapped[str] = mapped_column(
        Enum(
            "CDMX",
            "ALCALDIA",
            "AGEB",
            name="tipo_zona",
            create_type=False,
        ),
        nullable=False,
    )

    nombre: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )

    zona_padre_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("zonas.id"),
        nullable=True,
    )

    geometria: Mapped[object | None] = mapped_column(
        Geometry(
            geometry_type="MULTIPOLYGON",
            srid=4326,
        ),
        nullable=True,
    )

    activa: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    zona_padre: Mapped["Zona | None"] = relationship(
        "Zona",
        remote_side=[id],
    )