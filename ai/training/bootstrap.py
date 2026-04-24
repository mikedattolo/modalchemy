"""One-command bootstrap for Minecraft 1.7.10 asset generation training.

This script is meant for first-time setup:
1. Build datasets from decompiled workspaces
2. Build the model retrieval corpus
3. Optionally train a starter texture checkpoint
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from texture_gen.config import FULL_CONFIG, TOY_CONFIG
from training.train_from_workspaces import (
    AI_ROOT,
    REPO_ROOT,
    build_model_corpus,
    collect_workspace_assets,
)
from training.train_texture import train as train_texture
from datasets.prepare_models import prepare as prepare_models
from datasets.prepare_textures import prepare as prepare_textures


def bootstrap(
    workspaces_dir: Path,
    *,
    size: int,
    train_texture: bool,
    config_name: str,
    epochs: int | None,
    max_vram_gb: float | None,
    auto_gpu: bool,
) -> dict[str, object]:
    raw_root = AI_ROOT / "datasets" / "raw" / "from_workspaces"
    raw_textures = raw_root / "textures"
    raw_models = raw_root / "models"
    processed_textures = AI_ROOT / "datasets" / "processed" / "textures_from_workspaces"
    processed_models = AI_ROOT / "datasets" / "processed" / "models_from_workspaces"
    corpus_output = AI_ROOT / "checkpoints" / "model_gen" / "models.jsonl"

    raw_root.mkdir(parents=True, exist_ok=True)
    texture_count, model_count = collect_workspace_assets(workspaces_dir, raw_textures, raw_models)

    prepare_textures(raw_textures, processed_textures, size)
    prepare_models(raw_models, processed_models)

    prepared_models_jsonl = processed_models / "models.jsonl"
    corpus_size = build_model_corpus(prepared_models_jsonl, corpus_output)

    checkpoint_path: str | None = None
    if train_texture:
        config = replace(TOY_CONFIG if config_name == "toy" else FULL_CONFIG)
        config.dataset_dir = str(processed_textures)
        config.img_size = size
        config.checkpoint_dir = str(AI_ROOT / "checkpoints" / "texture_gen")
        if epochs is not None and epochs > 0:
            config.num_epochs = epochs

        train_texture(config, max_vram_gb=max_vram_gb, auto_gpu=auto_gpu)
        ckpts = sorted((AI_ROOT / "checkpoints" / "texture_gen").glob("*.pt"), key=lambda p: p.stat().st_mtime)
        if ckpts:
            checkpoint_path = str(ckpts[-1])

    return {
        "workspaces": str(workspaces_dir),
        "textures_collected": texture_count,
        "models_collected": model_count,
        "model_corpus_entries": corpus_size,
        "processed_textures": str(processed_textures),
        "processed_models": str(processed_models),
        "model_dataset": str(corpus_output),
        "texture_checkpoint": checkpoint_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap ModForge AI training from workspaces")
    parser.add_argument(
        "--workspaces-dir",
        type=Path,
        default=REPO_ROOT / "workspaces",
        help="Directory containing decompiled ModForge workspaces",
    )
    parser.add_argument("--size", type=int, default=16, choices=[16, 32], help="Texture size")
    parser.add_argument(
        "--train-texture",
        action="store_true",
        help="Also train a starter texture checkpoint after preparing datasets",
    )
    parser.add_argument("--config", choices=["toy", "full"], default="toy", help="Texture training preset")
    parser.add_argument("--epochs", type=int, default=None, help="Override training epochs")
    parser.add_argument("--max-vram-gb", type=float, default=None, help="Optional CUDA memory cap")
    parser.add_argument("--no-auto-gpu", action="store_true", help="Disable automatic GPU batch tuning")
    args = parser.parse_args()

    if not args.workspaces_dir.exists():
        raise SystemExit(f"Workspaces directory not found: {args.workspaces_dir}")

    result = bootstrap(
        args.workspaces_dir,
        size=args.size,
        train_texture=args.train_texture,
        config_name=args.config,
        epochs=args.epochs,
        max_vram_gb=args.max_vram_gb,
        auto_gpu=not args.no_auto_gpu,
    )

    print("Bootstrap complete")
    for key, value in result.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
