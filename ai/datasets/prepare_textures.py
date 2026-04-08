"""Prepare a texture dataset from a collection of Minecraft-style PNG files.

Usage:
    python -m datasets.prepare_textures --input /path/to/raw/pngs --output datasets/processed/textures

This script:
  1. Scans the input directory for PNG files
  2. Validates each image (correct size, RGB, etc.)
  3. Optionally resizes to target dimensions
  4. Copies valid images to the output directory
  5. Generates a metadata.json with labels (from filenames)

IMPORTANT: You must supply your own images. See docs/ai-training.md for
sources of permissively licensed pixel art.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

VALID_SIZES = {(16, 16), (32, 32), (64, 64), (128, 128), (256, 256)}


def prepare(input_dir: Path, output_dir: Path, target_size: int = 16) -> None:
    """Process raw texture images into a training-ready dataset."""
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata: list[dict] = []
    processed = 0
    skipped = 0

    for img_path in sorted(input_dir.rglob("*.png")):
        try:
            img = Image.open(img_path).convert("RGB")
        except Exception as e:
            logger.warning("Skipping %s: %s", img_path, e)
            skipped += 1
            continue

        # Resize if needed
        if img.size != (target_size, target_size):
            img = img.resize((target_size, target_size), Image.NEAREST)

        # Generate a label from the filename
        label = img_path.stem.replace("_", " ").replace("-", " ").lower()

        # Save
        out_name = f"{processed:05d}.png"
        img.save(output_dir / out_name)

        metadata.append(
            {
                "file": out_name,
                "label": label,
                "original": str(img_path.name),
                "size": target_size,
            }
        )
        processed += 1

    # Write metadata
    meta_path = output_dir / "metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    logger.info("Processed %d images (%d skipped) → %s", processed, skipped, output_dir)
    logger.info("Metadata: %s", meta_path)


def main():
    parser = argparse.ArgumentParser(description="Prepare texture training dataset")
    parser.add_argument("--input", type=Path, required=True, help="Input directory with PNGs")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("datasets/processed/textures"),
        help="Output directory",
    )
    parser.add_argument("--size", type=int, default=16, choices=[16, 32], help="Target size")
    args = parser.parse_args()

    prepare(args.input, args.output, args.size)


if __name__ == "__main__":
    main()
