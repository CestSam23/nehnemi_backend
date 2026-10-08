from typing import Any

from pydantic import BaseModel, Field


class InteraccionCrear(BaseModel):
    tipo: str = Field(
        min_length=1,
        max_length=80,
    )

    metadatos: dict[str, Any] = Field(
        default_factory=dict,
    )


class InteraccionCreada(BaseModel):
    id: int
    tipo: str