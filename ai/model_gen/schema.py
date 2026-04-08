"""Minecraft JSON model schema definitions.

These Pydantic models define the structure of valid Minecraft block and
item model JSON files. They're used with Outlines for structured generation
to guarantee valid output.
"""

from __future__ import annotations

from pydantic import BaseModel


class FaceUV(BaseModel):
    uv: list[float]  # [x1, y1, x2, y2]
    texture: str  # e.g., "#all" or "#top"
    rotation: int = 0
    cullface: str | None = None


class Element(BaseModel):
    from_: list[float]  # [x, y, z] — note: "from" is reserved in Python
    to: list[float]  # [x, y, z]
    faces: dict[str, FaceUV]

    model_config = {"populate_by_name": True}


class DisplayTransform(BaseModel):
    rotation: list[float] | None = None
    translation: list[float] | None = None
    scale: list[float] | None = None


class BlockModel(BaseModel):
    """Minecraft block model JSON structure."""

    parent: str | None = None  # e.g., "block/cube_all"
    textures: dict[str, str] = {}  # e.g., {"all": "modid:blocks/myblock"}
    elements: list[Element] = []
    display: dict[str, DisplayTransform] = {}


class ItemModel(BaseModel):
    """Minecraft item model JSON structure."""

    parent: str | None = None  # e.g., "item/generated" or "item/handheld"
    textures: dict[str, str] = {}  # e.g., {"layer0": "modid:items/myitem"}
    display: dict[str, DisplayTransform] = {}
