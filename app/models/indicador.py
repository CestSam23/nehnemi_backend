from datetime import datetime

from sqlalchemy import Enum, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IndicadorActual(Base):
    __tablename__ = "indicadores_actuales"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    zona_id: Mapped[object] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    dimension: Mapped[str] = mapped_column(
        Enum(
            "ADOPCION",
            "INFRAESTRUCTURA",
            "PARTICIPACION",
            "ACCESIBILIDAD",
            name="dimension_indicador",
            create_type=False,
        ),
        nullable=False,
    )

    puntuacion: Mapped[float] = mapped_column(
        Numeric(6, 2),
        nullable=False,
    )

    nivel: Mapped[str] = mapped_column(
        Enum(
            "MUY_BAJA",
            "BAJA",
            "MEDIA",
            "ALTA",
            name="nivel_indicador",
            create_type=False,
        ),
        nullable=False,
    )

    confianza: Mapped[str] = mapped_column(
        Enum(
            "BAJA",
            "MEDIA",
            "ALTA",
            name="nivel_confianza",
            create_type=False,
        ),
        nullable=False,
    )

    tamano_muestra: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    version_formula: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    componentes: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    explicacion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    calculado_en: Mapped[datetime] = mapped_column(
        nullable=False,
    )