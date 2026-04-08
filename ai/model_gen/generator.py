"""Model JSON generator using structured generation.

Uses either:
  1. Outlines + a small LLM for AI-powered generation
  2. Template-based fallback for when no LLM is available
"""

from __future__ import annotations

import json
import uuid
from typing import Literal

from ai.model_gen.schema import BlockModel, ItemModel, Element, FaceUV


def generate_model(
    prompt: str,
    model_type: Literal["block", "item"] = "block",
    mode: Literal["generate", "remix"] = "generate",
    source_json: str | None = None,
) -> dict:
    """Generate a Minecraft model JSON.

    For the scaffold, this uses template-based generation.
    The full implementation will use Outlines + a small LLM.

    Returns:
        Dict with id, prompt, model_json (pretty-printed), model_type.
    """
    if model_type == "block":
        model_json = _generate_block(prompt)
    else:
        model_json = _generate_item(prompt)

    return {
        "id": uuid.uuid4().hex[:12],
        "prompt": prompt,
        "model_json": json.dumps(model_json, indent=2),
        "model_type": model_type,
    }


def _generate_block(prompt: str) -> dict:
    """Generate a block model (template-based fallback)."""
    # Simple heuristic: produce a cube_all or cube_column based on prompt
    prompt_lower = prompt.lower()

    if any(kw in prompt_lower for kw in ["log", "column", "pillar", "barrel"]):
        return BlockModel(
            parent="block/cube_column",
            textures={
                "end": f"modid:blocks/{_slug(prompt)}_top",
                "side": f"modid:blocks/{_slug(prompt)}_side",
            },
        ).model_dump(by_alias=True, exclude_none=True)

    if any(kw in prompt_lower for kw in ["slab", "half"]):
        return BlockModel(
            parent="block/slab",
            textures={
                "bottom": f"modid:blocks/{_slug(prompt)}_bottom",
                "top": f"modid:blocks/{_slug(prompt)}_top",
                "side": f"modid:blocks/{_slug(prompt)}_side",
            },
        ).model_dump(by_alias=True, exclude_none=True)

    if any(kw in prompt_lower for kw in ["stair", "steps"]):
        return BlockModel(
            parent="block/stairs",
            textures={
                "bottom": f"modid:blocks/{_slug(prompt)}",
                "top": f"modid:blocks/{_slug(prompt)}",
                "side": f"modid:blocks/{_slug(prompt)}",
            },
        ).model_dump(by_alias=True, exclude_none=True)

    # Default: cube_all
    return BlockModel(
        parent="block/cube_all",
        textures={"all": f"modid:blocks/{_slug(prompt)}"},
    ).model_dump(by_alias=True, exclude_none=True)


def _generate_item(prompt: str) -> dict:
    """Generate an item model (template-based fallback)."""
    prompt_lower = prompt.lower()

    if any(kw in prompt_lower for kw in ["sword", "axe", "pickaxe", "shovel", "hoe", "tool"]):
        return ItemModel(
            parent="item/handheld",
            textures={"layer0": f"modid:items/{_slug(prompt)}"},
        ).model_dump(by_alias=True, exclude_none=True)

    return ItemModel(
        parent="item/generated",
        textures={"layer0": f"modid:items/{_slug(prompt)}"},
    ).model_dump(by_alias=True, exclude_none=True)


def _slug(text: str) -> str:
    """Convert prompt text to a Minecraft-style resource name."""
    return "_".join(text.lower().split()[:4]).replace("-", "_")[:32]
