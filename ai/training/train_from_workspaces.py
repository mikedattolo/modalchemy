"""Build AI datasets directly from decompiled workspaces and optionally train.

Usage examples:
    # Build processed datasets only
    python -m training.train_from_workspaces

    # Build datasets + train custom texture checkpoint
    python -m training.train_from_workspaces --train-texture --config full --epochs 40

This script scans ModForge workspace outputs, extracts Minecraft textures and
model JSON files, prepares training datasets, and can kick off texture training.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
from dataclasses import replace
from pathlib import Path

from datasets.prepare_models import prepare as prepare_models
from datasets.prepare_textures import prepare as prepare_textures
from texture_gen.config import FULL_CONFIG, TOY_CONFIG
from training.train_texture import train as train_texture

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
AI_ROOT = Path(__file__).resolve().parents[1]


def collect_workspace_assets(
    workspaces_dir: Path,
    raw_textures_dir: Path,
    raw_models_dir: Path,
) -> tuple[int, int]:
    """Collect texture PNGs and model JSONs from decompiled workspace folders."""
    raw_textures_dir.mkdir(parents=True, exist_ok=True)
    raw_models_dir.mkdir(parents=True, exist_ok=True)

    texture_count = 0
    model_count = 0
    seen_hashes: set[str] = set()

    for workspace in sorted(workspaces_dir.iterdir()):
        if not workspace.is_dir():
            continue
        resources = workspace / "resources"
        if not resources.exists():
            continue

        texture_glob = resources.glob("assets/**/textures/**/*.png")
        model_glob = resources.glob("assets/**/models/**/*.json")

        for texture_path in texture_glob:
            digest = _file_hash(texture_path)
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)

            out_name = f"tex_{texture_count:06d}_{texture_path.name}"
            shutil.copy2(texture_path, raw_textures_dir / out_name)
            texture_count += 1

        for model_path in model_glob:
            digest = _file_hash(model_path)
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)

            out_name = f"model_{model_count:06d}_{model_path.name}"
            shutil.copy2(model_path, raw_models_dir / out_name)
            model_count += 1

    return texture_count, model_count


def build_model_corpus(processed_models_jsonl: Path, output_jsonl: Path) -> int:
    """Build a curated model corpus used by inference-time retrieval."""
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    kept = 0
    with open(processed_models_jsonl, "r", encoding="utf-8") as src, open(
        output_jsonl, "w", encoding="utf-8"
    ) as dst:
        for line in src:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                completion_raw = entry.get("completion", "")
                completion = json.loads(completion_raw) if isinstance(completion_raw, str) else completion_raw
            except json.JSONDecodeError:
                continue

            if not isinstance(completion, dict):
                continue

            if "parent" not in completion and "elements" not in completion:
                continue

            clean = {
                "prompt": str(entry.get("prompt", "")).strip(),
                "model_type": str(entry.get("model_type", "block")).strip() or "block",
                "completion": completion,
            }
            dst.write(json.dumps(clean, separators=(",", ":")) + "\n")
            kept += 1

    return kept


def _file_hash(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(data).hexdigest()  # noqa: S324 -- dedupe identifier only


def main() -> None:
    parser = argparse.ArgumentParser(description="Train ModForge AI from decompiled workspaces")
    parser.add_argument(
        "--workspaces-dir",
        type=Path,
        default=REPO_ROOT / "workspaces",
        help="Directory containing decompiled workspaces",
    )
    parser.add_argument("--size", type=int, default=16, choices=[16, 32], help="Texture size")
    parser.add_argument(
        "--train-texture",
        action="store_true",
        help="Also train a texture model checkpoint after dataset prep",
    )
    parser.add_argument(
        "--config",
        choices=["toy", "full"],
        default="full",
        help="Texture training config preset when --train-texture is enabled",
    )
    parser.add_argument("--epochs", type=int, default=None, help="Override texture epochs")
    parser.add_argument(
        "--max-vram-gb",
        type=float,
        default=None,
        help="Optional per-process VRAM cap in GB during texture training",
    )
    parser.add_argument(
        "--no-auto-gpu",
        action="store_true",
        help="Disable automatic GPU-aware batch-size tuning",
    )
    args = parser.parse_args()

    if not args.workspaces_dir.exists():
        logger.error("Workspaces directory not found: %s", args.workspaces_dir)
        return

    raw_root = AI_ROOT / "datasets" / "raw" / "from_workspaces"
    raw_textures = raw_root / "textures"
    raw_models = raw_root / "models"
    processed_textures = AI_ROOT / "datasets" / "processed" / "textures_from_workspaces"
    processed_models = AI_ROOT / "datasets" / "processed" / "models_from_workspaces"
    corpus_output = AI_ROOT / "checkpoints" / "model_gen" / "models.jsonl"

    if raw_root.exists():
        shutil.rmtree(raw_root)
    raw_root.mkdir(parents=True, exist_ok=True)

    logger.info("Collecting assets from %s", args.workspaces_dir)
    texture_count, model_count = collect_workspace_assets(args.workspaces_dir, raw_textures, raw_models)
    logger.info("Collected %d textures and %d model JSONs", texture_count, model_count)

    logger.info("Preparing texture dataset")
    prepare_textures(raw_textures, processed_textures, args.size)

    logger.info("Preparing model dataset")
    prepare_models(raw_models, processed_models)

    prepared_models_jsonl = processed_models / "models.jsonl"
    kept = build_model_corpus(prepared_models_jsonl, corpus_output)
    logger.info("Built model corpus with %d entries: %s", kept, corpus_output)

    if args.train_texture:
        config = replace(TOY_CONFIG if args.config == "toy" else FULL_CONFIG)
        config.dataset_dir = str(processed_textures)
        config.img_size = args.size
        config.checkpoint_dir = str(AI_ROOT / "checkpoints" / "texture_gen")
        if args.epochs is not None:
            config.num_epochs = args.epochs

        logger.info("Starting texture training with config=%s epochs=%s", args.config, config.num_epochs)
        train_texture(
            config,
            max_vram_gb=args.max_vram_gb,
            auto_gpu=not args.no_auto_gpu,
        )

    logger.info("Done. You can now run inference with custom data/checkpoints.")


if __name__ == "__main__":
    main()
