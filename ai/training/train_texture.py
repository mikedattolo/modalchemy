"""Train the pixel-art texture diffusion model.

Usage:
    python -m training.train_texture --config toy    # Quick test on CPU
    python -m training.train_texture --config full   # Full training (GPU)

The training loop:
  1. Loads the dataset (16×16 or 32×32 PNG images)
  2. Creates the TinyUNet + DDPMScheduler
  3. For each epoch:
     a. Sample random images
     b. Sample random timesteps
     c. Add noise at those timesteps
     d. Predict noise with the UNet
     e. MSE loss between predicted and actual noise
  4. Save checkpoints periodically
"""

from __future__ import annotations

import argparse
import logging
import math
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from texture_gen.config import TOY_CONFIG, FULL_CONFIG, TextureGenConfig
from texture_gen.model import TinyUNet
from texture_gen.scheduler import DDPMScheduler
from training.texture_dataset import TextureDataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def train(
    config: TextureGenConfig,
    *,
    max_vram_gb: float | None = None,
    auto_gpu: bool = True,
) -> None:
    """Run the texture model training loop."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    gpu_info = _detect_gpu()
    logger.info("Training on %s", device)
    if gpu_info:
        logger.info(
            "Detected GPU: %s (%.2f GB VRAM)",
            gpu_info["name"],
            gpu_info["total_vram_gb"],
        )

    if device.type == "cuda" and max_vram_gb is not None:
        _set_vram_limit(max_vram_gb, float(gpu_info["total_vram_gb"]) if gpu_info else None)

    if auto_gpu:
        _auto_tune_for_gpu(config, gpu_info, max_vram_gb)

    logger.info("Config: %s", config)

    # Dataset
    dataset = TextureDataset(
        root=Path(config.dataset_dir),
        img_size=config.img_size,
    )
    if len(dataset) == 0:
        logger.error(
            "No images found in %s. Run dataset preparation first. "
            "See docs/ai-training.md for instructions.",
            config.dataset_dir,
        )
        return

    loader = DataLoader(
        dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=0,
        drop_last=True,
    )

    # Model
    model = TinyUNet(
        img_channels=config.img_channels,
        base_dim=config.base_dim,
        dim_mults=config.dim_mults,
        text_emb_dim=config.text_emb_dim,
    ).to(device)

    scheduler = DDPMScheduler(
        num_timesteps=config.num_timesteps,
        beta_start=config.beta_start,
        beta_end=config.beta_end,
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate)

    # Training loop
    checkpoint_dir = Path(config.checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    for epoch in range(config.num_epochs):
        total_loss = 0.0
        for batch_idx, images in enumerate(loader):
            images = images.to(device)
            noise = torch.randn_like(images)
            t = torch.randint(0, config.num_timesteps, (images.shape[0],), device=device)

            noisy = scheduler.add_noise(images, noise, t.cpu()).to(device)
            predicted_noise = model(noisy, t)

            loss = F.mse_loss(predicted_noise, noise)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        avg_loss = total_loss / max(len(loader), 1)
        logger.info("Epoch %d/%d — loss: %.6f", epoch + 1, config.num_epochs, avg_loss)

        # Save checkpoint every 10 epochs or at the end
        if (epoch + 1) % 10 == 0 or epoch == config.num_epochs - 1:
            ckpt_path = checkpoint_dir / f"texture_gen_epoch{epoch + 1}.pt"
            torch.save(
                {
                    "epoch": epoch + 1,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "loss": avg_loss,
                    "config": config,
                },
                ckpt_path,
            )
            logger.info("Saved checkpoint: %s", ckpt_path)

    logger.info("Training complete.")


def main():
    parser = argparse.ArgumentParser(description="Train texture generation model")
    parser.add_argument(
        "--config",
        choices=["toy", "full"],
        default="toy",
        help="Training configuration preset",
    )
    parser.add_argument("--dataset", type=str, help="Override dataset directory")
    parser.add_argument("--epochs", type=int, help="Override number of epochs")
    parser.add_argument(
        "--max-vram-gb",
        type=float,
        default=None,
        help="Optional per-process VRAM cap in GB for CUDA training",
    )
    parser.add_argument(
        "--no-auto-gpu",
        action="store_true",
        help="Disable automatic GPU-aware batch-size tuning",
    )
    args = parser.parse_args()

    config = TOY_CONFIG if args.config == "toy" else FULL_CONFIG
    if args.dataset:
        config.dataset_dir = args.dataset
    if args.epochs:
        config.num_epochs = args.epochs

    train(config, max_vram_gb=args.max_vram_gb, auto_gpu=not args.no_auto_gpu)


def _detect_gpu() -> dict[str, object] | None:
    if not torch.cuda.is_available():
        return None
    props = torch.cuda.get_device_properties(0)
    return {
        "name": props.name,
        "total_vram_gb": props.total_memory / (1024**3),
    }


def _set_vram_limit(limit_gb: float, total_gb: float | None) -> None:
    if total_gb is None or total_gb <= 0:
        return
    fraction = max(0.05, min(0.98, limit_gb / total_gb))
    torch.cuda.set_per_process_memory_fraction(fraction, device=0)
    logger.info(
        "Set CUDA per-process memory fraction to %.2f (limit %.2f GB / total %.2f GB)",
        fraction,
        limit_gb,
        total_gb,
    )


def _auto_tune_for_gpu(
    config: TextureGenConfig,
    gpu_info: dict[str, object] | None,
    max_vram_gb: float | None,
) -> None:
    if gpu_info is None:
        return

    total_gb = float(gpu_info["total_vram_gb"])
    budget_gb = min(total_gb, max_vram_gb) if max_vram_gb is not None else total_gb

    # Heuristic for memory per sample in this TinyUNet diffusion setup.
    # Keeps training stable on mid-tier GPUs like RTX 3060 12GB.
    if config.img_size <= 16:
        per_sample_gb = 0.16 if config.base_dim >= 64 else 0.10
    else:
        per_sample_gb = 0.42 if config.base_dim >= 64 else 0.24

    usable_gb = max(1.0, budget_gb * 0.72)
    suggested = max(1, math.floor(usable_gb / per_sample_gb))

    if suggested < config.batch_size:
        logger.info(
            "Auto-tuned batch_size: %d -> %d based on %.2f GB VRAM budget",
            config.batch_size,
            suggested,
            budget_gb,
        )
        config.batch_size = suggested


if __name__ == "__main__":
    main()
