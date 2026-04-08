"""Texture generation configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TextureGenConfig:
    """Configuration for texture generation model."""

    # Model architecture
    img_channels: int = 3
    base_dim: int = 64
    dim_mults: tuple[int, ...] = (1, 2, 4)
    text_emb_dim: int = 128

    # Diffusion
    num_timesteps: int = 1000
    beta_start: float = 1e-4
    beta_end: float = 0.02

    # Training
    batch_size: int = 32
    learning_rate: float = 1e-4
    num_epochs: int = 100
    img_size: int = 16  # 16 or 32

    # Paths
    checkpoint_dir: str = "checkpoints/texture_gen"
    dataset_dir: str = "datasets/processed/textures"


# Toy config — trains fast on CPU for testing
TOY_CONFIG = TextureGenConfig(
    base_dim=32,
    dim_mults=(1, 2),
    num_timesteps=100,
    batch_size=8,
    num_epochs=5,
    img_size=16,
)

# Full config — needs GPU, real dataset
FULL_CONFIG = TextureGenConfig(
    base_dim=64,
    dim_mults=(1, 2, 4),
    num_timesteps=1000,
    batch_size=32,
    num_epochs=100,
    img_size=32,
)
