import uuid

from sqlalchemy import Boolean, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PerfilCiudadano(Base):
    __tablename__ = "perfiles_ciudadanos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    zona_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("zonas.id"),
        nullable=True,
    )

    tiene_automovil: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    propulsion: Mapped[str] = mapped_column(
        Enum(
            "ELECTRICO",
            "HIBRIDO_ENCHUFABLE",
            "HIBRIDO",
            "COMBUSTION",
            "OTRO",
            "SIN_AUTOMOVIL",
            name="tipo_propulsion",
            create_type=False,
        ),
        nullable=False,
    )

    consideraria_ev: Mapped[str] = mapped_column(
        Enum(
            "SI",
            "NO",
            "NO_SE",
            name="respuesta_consideracion",
            create_type=False,
        ),
        nullable=False,
    )

    barrera_principal: Mapped[str] = mapped_column(
        Enum(
            "PRECIO",
            "CARGA",
            "AUTONOMIA",
            "INFORMACION_DUDAS",
            "CARACTERISTICAS_VEHICULO",
            "NO_INTERESA",
            "OTRA",
            "NINGUNA",
            name="tipo_barrera_declarada",
            create_type=False,
        ),
        nullable=False,
    )

    consentimiento_agregado: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )