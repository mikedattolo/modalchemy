"""Model JSON generator for Minecraft 1.7.10 assets.

Generation strategy:
1. Retrieval from custom corpus (if available)
2. Rule-based structural synthesis from prompt intent
3. Texture binding and compatibility validation
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from model_gen.schema import BlockModel, Element, FaceUV, ItemModel

_CUSTOM_CORPUS_CACHE: tuple[Path | None, list[dict]] = (None, [])


@dataclass(slots=True)
class PromptSpec:
    base_name: str
    family: str
    complexity: str


def generate_model(
    prompt: str,
    model_type: Literal["block", "item"] = "block",
    mode: Literal["generate", "remix"] = "generate",
    source_json: str | None = None,
    texture_name: str | None = None,
) -> dict:
    """Generate a Minecraft model JSON and return metadata for downstream use."""
    model_json = _generate_from_custom_corpus(prompt, model_type)
    if model_json is None:
        spec = _parse_prompt(prompt)
        if model_type == "block":
            model_json = _generate_block_from_spec(spec)
        else:
            model_json = _generate_item_from_spec(spec)

    if texture_name:
        model_json = _bind_texture(model_json, model_type, texture_name)

    model_json = _validate_model_shape(model_json, model_type)

    return {
        "id": uuid.uuid4().hex[:12],
        "prompt": prompt,
        "model_json": json.dumps(model_json, indent=2),
        "model_type": model_type,
        "compatibility": {"minecraft": "1.7.10", "mode": mode},
    }


def _parse_prompt(prompt: str) -> PromptSpec:
    prompt_lower = prompt.lower()
    slug = _slug(prompt)

    family = "cube"
    if any(k in prompt_lower for k in ["log", "column", "pillar", "barrel"]):
        family = "column"
    elif any(k in prompt_lower for k in ["slab", "half"]):
        family = "slab"
    elif any(k in prompt_lower for k in ["stair", "steps"]):
        family = "stairs"
    elif any(k in prompt_lower for k in ["statue", "animal", "creature", "totem"]):
        family = "statue"
    elif any(k in prompt_lower for k in ["gun", "rifle", "pistol", "blaster", "cannon"]):
        family = "tool3d"

    complexity = "simple"
    if any(k in prompt_lower for k in ["ornate", "detailed", "complex", "ancient"]):
        complexity = "complex"

    return PromptSpec(base_name=slug, family=family, complexity=complexity)


def _generate_block_from_spec(spec: PromptSpec) -> dict:
    if spec.family == "column":
        return BlockModel(
            parent="block/cube_column",
            textures={
                "end": f"modid:blocks/{spec.base_name}_top",
                "side": f"modid:blocks/{spec.base_name}_side",
            },
        ).model_dump(by_alias=True, exclude_none=True)

    if spec.family == "slab":
        return BlockModel(
            parent="block/slab",
            textures={
                "bottom": f"modid:blocks/{spec.base_name}",
                "top": f"modid:blocks/{spec.base_name}",
                "side": f"modid:blocks/{spec.base_name}",
            },
        ).model_dump(by_alias=True, exclude_none=True)

    if spec.family == "stairs":
        return BlockModel(
            parent="block/stairs",
            textures={
                "bottom": f"modid:blocks/{spec.base_name}",
                "top": f"modid:blocks/{spec.base_name}",
                "side": f"modid:blocks/{spec.base_name}",
            },
        ).model_dump(by_alias=True, exclude_none=True)

    if spec.family == "statue":
        return {
            "textures": {"all": f"modid:blocks/{spec.base_name}"},
            "elements": _statue_elements(spec.complexity),
        }

    if spec.family == "tool3d":
        return {
            "textures": {"all": f"modid:blocks/{spec.base_name}"},
            "elements": _gun_elements(spec.complexity),
        }

    return BlockModel(
        parent="block/cube_all",
        textures={"all": f"modid:blocks/{spec.base_name}"},
    ).model_dump(by_alias=True, exclude_none=True)


def _generate_item_from_spec(spec: PromptSpec) -> dict:
    handheld_keywords = {"sword", "axe", "pickaxe", "shovel", "hoe", "tool", "gun"}
    is_handheld = any(key in spec.base_name for key in handheld_keywords)
    return ItemModel(
        parent="item/handheld" if is_handheld else "item/generated",
        textures={"layer0": f"modid:items/{spec.base_name}"},
    ).model_dump(by_alias=True, exclude_none=True)


def _bind_texture(model_json: dict, model_type: str, texture_name: str) -> dict:
    clean_name = _slug(texture_name)
    resource = f"modid:{'items' if model_type == 'item' else 'blocks'}/{clean_name}"

    updated = dict(model_json)
    textures = updated.get("textures")
    if isinstance(textures, dict) and textures:
        updated["textures"] = {str(k): resource for k in textures.keys()}
    else:
        key = "layer0" if model_type == "item" else "all"
        updated["textures"] = {key: resource}
    return updated


def _validate_model_shape(model_json: dict, model_type: str) -> dict:
    if model_type == "item":
        return ItemModel.model_validate(model_json).model_dump(by_alias=True, exclude_none=True)

    block = BlockModel.model_validate(model_json)
    if block.elements:
        normalized_elements = [Element.model_validate(el).model_dump(by_alias=True, exclude_none=True) for el in block.elements]
        out = block.model_dump(by_alias=True, exclude_none=True)
        out["elements"] = normalized_elements
        return out
    return block.model_dump(by_alias=True, exclude_none=True)


def _generate_from_custom_corpus(prompt: str, model_type: str) -> dict | None:
    entries = _load_custom_corpus()
    if not entries:
        return None

    query_tokens = _tokens(prompt)
    best: dict | None = None
    best_score = 0.0

    for entry in entries:
        if str(entry.get("model_type", "block")) != model_type:
            continue
        prompt_tokens = set(entry.get("tokens", []))
        if not prompt_tokens:
            continue

        overlap = len(query_tokens & prompt_tokens)
        union = max(len(query_tokens | prompt_tokens), 1)
        score = overlap / union
        if overlap >= 2:
            score += 0.2

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


def _slug(text: str) -> str:
    clean = re.sub(r"[^a-z0-9_\- ]+", "", text.lower())
    return "_".join(clean.split()[:4]).replace("-", "_")[:32] or "generated_asset"


def _statue_elements(complexity: str) -> list[dict]:
    elements = [
        _box([6, 0, 6], [10, 8, 10]),
        _box([6, 8, 5], [10, 14, 9]),
        _box([5, 14, 4], [11, 16, 10]),
        _box([6.5, 0, 4], [7.5, 8, 5]),
        _box([8.5, 0, 4], [9.5, 8, 5]),
        _box([6.5, 0, 11], [7.5, 8, 12]),
        _box([8.5, 0, 11], [9.5, 8, 12]),
    ]
    if complexity == "complex":
        elements.extend([
            _box([4.5, 10, 7], [6, 12, 9]),
            _box([10, 10, 7], [11.5, 12, 9]),
        ])
    return elements


def _gun_elements(complexity: str) -> list[dict]:
    elements = [
        _box([3, 8, 6], [14, 11, 10]),
        _box([2, 9, 7], [3, 10, 9]),
        _box([14, 9, 7], [16, 10, 9]),
        _box([7, 4, 7], [10, 8, 9]),
        _box([6, 11, 7], [11, 13, 9]),
    ]
    if complexity == "complex":
        elements.extend([
            _box([4, 10, 6.5], [6, 12, 9.5]),
            _box([11, 10, 6.5], [13, 12, 9.5]),
        ])
    return elements


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
    return Element(from_=from_xyz, to=to_xyz, faces=faces).model_dump(by_alias=True, exclude_none=True)
