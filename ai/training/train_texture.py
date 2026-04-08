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


def train(config: TextureGenConfig) -> None:
    """Run the texture model training loop."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Training on %s", device)
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
    args = parser.parse_args()

    config = TOY_CONFIG if args.config == "toy" else FULL_CONFIG
    if args.dataset:
        config.dataset_dir = args.dataset
    if args.epochs:
        config.num_epochs = args.epochs

    train(config)


if __name__ == "__main__":
    main()
