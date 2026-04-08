"""Prepare a model JSON dataset from a collection of Minecraft model files.

Usage:
    python -m datasets.prepare_models --input /path/to/model/jsons --output datasets/processed/models

This script:
  1. Scans for .json files matching Minecraft model format
  2. Validates each against the expected schema
  3. Generates prompt/completion pairs for training
  4. Saves as JSONL for fine-tuning or structured generation training

IMPORTANT: You must supply your own model JSON files.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def prepare(input_dir: Path, output_dir: Path) -> None:
    """Process raw model JSON files into training data."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "models.jsonl"

    entries: list[dict] = []

    for json_path in sorted(input_dir.rglob("*.json")):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning("Skipping %s: %s", json_path, e)
            continue

        # Basic validation: must have "parent" or "elements"
        if "parent" not in data and "elements" not in data:
            logger.debug("Skipping %s: no parent or elements", json_path)
            continue

        # Infer model type and prompt from filename/path
        name = json_path.stem.replace("_", " ").replace("-", " ")
        is_item = "item" in str(json_path).lower() or (
            data.get("parent", "").startswith("item/")
        )
        model_type = "item" if is_item else "block"

        prompt = f"Generate a Minecraft {model_type} model for: {name}"

        entries.append(
            {
                "prompt": prompt,
                "completion": json.dumps(data, separators=(",", ":")),
                "model_type": model_type,
                "source": json_path.name,
            }
        )

    with open(output_file, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    logger.info("Processed %d model files → %s", len(entries), output_file)


def main():
    parser = argparse.ArgumentParser(description="Prepare model JSON training dataset")
    parser.add_argument("--input", type=Path, required=True, help="Input directory with JSONs")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("datasets/processed/models"),
        help="Output directory",
    )
    args = parser.parse_args()

    prepare(args.input, args.output)


if __name__ == "__main__":
    main()
