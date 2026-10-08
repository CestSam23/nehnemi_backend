import uuid
from datetime import datetime
from decimal import Decimal

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EstacionCarga(Base):
    __tablename__ = "estaciones_carga"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    identificador_fuente: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    nombre: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )

    direccion: Mapped[str | None] = mapped_column(
        nullable=True,
    )

    ubicacion: Mapped[object] = mapped_column(
        Geometry(
            geometry_type="POINT",
            srid=4326,
        ),
        nullable=False,
    )

    zona_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("zonas.id"),
        nullable=True,
    )

    fuente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fuentes_datos.id"),
        nullable=False,
    )

    estado_demostracion: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    conectores: Mapped[list["ConectorCarga"]] = relationship(
        back_populates="estacion",
    )


class ConectorCarga(Base):
    __tablename__ = "conectores_carga"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    estacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("estaciones_carga.id"),
        nullable=False,
    )

    numero_grupo: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    cantidad: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    tipo_conector: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    potencia_kw: Mapped[Decimal | None] = mapped_column(
        Numeric,
        nullable=True,
    )

    estado_operativo: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    procedencia_estado: Mapped[str | None] = mapped_column(
        nullable=True,
    )

    estacion: Mapped["EstacionCarga"] = relationship(
        back_populates="conectores",
    )