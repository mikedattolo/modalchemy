"""Minecraft 1.7.10 JSON model schema definitions.

These Pydantic models define a conservative subset of the model JSON format used
by Minecraft 1.7.10. The generator uses this schema both for validation and for
construction of strongly-typed model objects.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FaceUV(BaseModel):
    uv: list[float]  # [x1, y1, x2, y2]
    texture: str  # e.g., "#all" or "#top"
    rotation: int = 0
    cullface: str | None = None


class Element(BaseModel):
    from_: list[float] = Field(alias="from")  # [x, y, z]
    to: list[float]  # [x, y, z]
    faces: dict[str, FaceUV]

    model_config = {"populate_by_name": True}


class DisplayTransform(BaseModel):
    rotation: list[float] | None = None
    translation: list[float] | None = None
    scale: list[float] | None = None


class BlockModel(BaseModel):
    """Minecraft block model JSON structure."""

    parent: str | None = None
    textures: dict[str, str] = Field(default_factory=dict)
    elements: list[Element] = Field(default_factory=list)
    display: dict[str, DisplayTransform] = Field(default_factory=dict)


class ItemModel(BaseModel):
    """Minecraft item model JSON structure."""

    parent: str | None = None
    textures: dict[str, str] = Field(default_factory=dict)
    display: dict[str, DisplayTransform] = Field(default_factory=dict)
