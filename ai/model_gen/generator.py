"""Model JSON generator using structured generation.

Uses either:
  1. Outlines + a small LLM for AI-powered generation
  2. Template-based fallback for when no LLM is available
"""

from __future__ import annotations

import json
import os
import re
import uuid
from typing import Literal
from pathlib import Path

from model_gen.schema import BlockModel, ItemModel, Element, FaceUV


_CUSTOM_CORPUS_CACHE: tuple[Path | None, list[dict]] = (None, [])


def generate_model(
    prompt: str,
    model_type: Literal["block", "item"] = "block",
    mode: Literal["generate", "remix"] = "generate",
    source_json: str | None = None,
    texture_name: str | None = None,
) -> dict:
    """Generate a Minecraft model JSON.

    For the scaffold, this uses template-based generation.
    The full implementation will use Outlines + a small LLM.

    Returns:
        Dict with id, prompt, model_json (pretty-printed), model_type.
    """
    model_json = _generate_from_custom_corpus(prompt, model_type)
    if model_json is None:
        if model_type == "block":
            model_json = _generate_block(prompt)
        else:
            model_json = _generate_item(prompt)

    if texture_name:
        model_json = _bind_texture(model_json, model_type, texture_name)

    return {
        "id": uuid.uuid4().hex[:12],
        "prompt": prompt,
        "model_json": json.dumps(model_json, indent=2),
        "model_type": model_type,
    }


def _bind_texture(model_json: dict, model_type: str, texture_name: str) -> dict:
    """Force generated model textures to point at the same resource name."""
    clean_name = _slug(texture_name)
    if model_type == "item":
        resource = f"modid:items/{clean_name}"
    else:
        resource = f"modid:blocks/{clean_name}"

    updated = dict(model_json)
    textures = updated.get("textures")
    if isinstance(textures, dict) and textures:
        updated["textures"] = {str(k): resource for k in textures.keys()}
    else:
        key = "layer0" if model_type == "item" else "all"
        updated["textures"] = {key: resource}
    return updated


def _generate_from_custom_corpus(prompt: str, model_type: str) -> dict | None:
    """Retrieve the closest model JSON from a custom training corpus."""
    entries = _load_custom_corpus()
    if not entries:
        return None

    query_tokens = _tokens(prompt)
    best: dict | None = None
    best_score = 0.0

    for entry in entries:
        entry_type = str(entry.get("model_type", "block"))
        if entry_type != model_type:
            continue
        prompt_tokens = set(entry.get("tokens", []))
        if not prompt_tokens:
            continue
        score = len(query_tokens & prompt_tokens) / max(len(query_tokens | prompt_tokens), 1)
        if score > best_score:
            best_score = score
            best = entry

    if best is None or best_score <= 0:
        return None

    completion = best.get("completion")
    return completion if isinstance(completion, dict) else None


def _load_custom_corpus() -> list[dict]:
    global _CUSTOM_CORPUS_CACHE

    corpus_path = _resolve_corpus_path()
    cached_path, cached_entries = _CUSTOM_CORPUS_CACHE
    if corpus_path is None:
        _CUSTOM_CORPUS_CACHE = (None, [])
        return []
    if cached_path == corpus_path:
        return cached_entries

    entries: list[dict] = []
    with open(corpus_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            completion = row.get("completion")
            if isinstance(completion, str):
                try:
                    completion = json.loads(completion)
                except json.JSONDecodeError:
                    continue

            if not isinstance(completion, dict):
                continue

            entries.append(
                {
                    "prompt": row.get("prompt", ""),
                    "model_type": row.get("model_type", "block"),
                    "completion": completion,
                    "tokens": sorted(_tokens(str(row.get("prompt", "")))),
                }
            )

    _CUSTOM_CORPUS_CACHE = (corpus_path, entries)
    return entries


def _resolve_corpus_path() -> Path | None:
    env_path = os.getenv("MODFORGE_MODEL_DATASET")
    if env_path:
        path = Path(env_path).expanduser().resolve()
        return path if path.exists() else None

    default = Path(__file__).resolve().parents[1] / "checkpoints" / "model_gen" / "models.jsonl"
    return default if default.exists() else None


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) >= 2}


def _generate_block(prompt: str) -> dict:
    """Generate a block model (template-based fallback)."""
    # Simple heuristic: produce a cube_all or cube_column based on prompt
    prompt_lower = prompt.lower()

    if any(kw in prompt_lower for kw in ["giraffe", "animal", "creature", "statue"]):
        return _generate_animal_statue_model()

    if any(kw in prompt_lower for kw in ["gun", "pistol", "rifle", "blaster", "cannon"]):
        return _generate_gun_model()

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


def _generate_animal_statue_model() -> dict:
    """Build a simple multi-element animal-like statue block model."""
    elements = [
        _box([6, 0, 6], [10, 8, 10]),  # torso
        _box([6, 8, 5], [10, 14, 9]),  # neck
        _box([5, 14, 4], [11, 16, 10]),  # head
        _box([6.5, 0, 4], [7.5, 8, 5]),  # leg 1
        _box([8.5, 0, 4], [9.5, 8, 5]),  # leg 2
        _box([6.5, 0, 11], [7.5, 8, 12]),  # leg 3
        _box([8.5, 0, 11], [9.5, 8, 12]),  # leg 4
    ]
    return {
        "textures": {"all": "modid:blocks/custom_model"},
        "elements": elements,
    }


def _generate_gun_model() -> dict:
    """Build a simple multi-element gun-like block model."""
    elements = [
        _box([3, 8, 6], [14, 11, 10]),  # receiver
        _box([2, 9, 7], [3, 10, 9]),  # stock end
        _box([14, 9, 7], [16, 10, 9]),  # barrel
        _box([7, 4, 7], [10, 8, 9]),  # grip
        _box([6, 11, 7], [11, 13, 9]),  # top rail/sight
    ]
    return {
        "textures": {"all": "modid:blocks/custom_model"},
        "elements": elements,
    }


def _box(from_xyz: list[float], to_xyz: list[float]) -> dict:
    uv = [0.0, 0.0, 16.0, 16.0]
    faces = {
        "down": FaceUV(uv=uv, texture="#all"),
        "up": FaceUV(uv=uv, texture="#all"),
        "north": FaceUV(uv=uv, texture="#all"),
        "south": FaceUV(uv=uv, texture="#all"),
        "west": FaceUV(uv=uv, texture="#all"),
        "east": FaceUV(uv=uv, texture="#all"),
    }
    return Element(from_=from_xyz, to=to_xyz, faces=faces).model_dump(
        by_alias=True,
        exclude_none=True,
    )
