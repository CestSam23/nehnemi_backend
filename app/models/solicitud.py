import uuid

from geoalchemy2 import Geometry
from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SolicitudInfraestructura(Base):
    __tablename__ = "solicitudes_infraestructura"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    perfil_ciudadano_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("perfiles_ciudadanos.id"),
        nullable=False,
    )

    zona_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("zonas.id"),
        nullable=False,
    )

    ubicacion: Mapped[object] = mapped_column(
        Geometry(
            geometry_type="POINT",
            srid=4326,
        ),
        nullable=False,
    )

    motivo: Mapped[str] = mapped_column(
        Enum(
            "VIVO_CERCA",
            "TRABAJO_CERCA",
            "TRANSITO_FRECUENTE",
            "TENGO_EV",
            "CONSIDERARIA_EV_CON_CARGA",
            "OTRO",
            name="motivo_solicitud",
            create_type=False,
        ),
        nullable=False,
    )

    comentario: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    estado: Mapped[str] = mapped_column(
        Enum(
            "REGISTRADA",
            "EN_REVISION",
            "ATENDIDA",
            "DESCARTADA",
            name="estado_solicitud",
            create_type=False,
        ),
        nullable=False,
    )