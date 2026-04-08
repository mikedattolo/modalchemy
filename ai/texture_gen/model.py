"""Tiny UNet for pixel-art diffusion.

This is a minimal diffusion UNet suitable for 16×16 or 32×32 images.
It's designed to be trainable on a single consumer GPU in reasonable time.
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class SinusoidalPositionEmbedding(nn.Module):
    """Sinusoidal timestep embedding."""

    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        device = t.device
        half = self.dim // 2
        emb = math.log(10000) / (half - 1)
        emb = torch.exp(torch.arange(half, device=device) * -emb)
        emb = t[:, None].float() * emb[None, :]
        return torch.cat([emb.sin(), emb.cos()], dim=-1)


class ResBlock(nn.Module):
    """Residual block with time embedding injection."""

    def __init__(self, in_ch: int, out_ch: int, time_dim: int):
        super().__init__()
        self.conv1 = nn.Conv2d(in_ch, out_ch, 3, padding=1)
        self.conv2 = nn.Conv2d(out_ch, out_ch, 3, padding=1)
        self.norm1 = nn.GroupNorm(8, out_ch)
        self.norm2 = nn.GroupNorm(8, out_ch)
        self.time_mlp = nn.Linear(time_dim, out_ch)
        self.skip = nn.Conv2d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()

    def forward(self, x: torch.Tensor, t_emb: torch.Tensor) -> torch.Tensor:
        h = self.norm1(F.silu(self.conv1(x)))
        h = h + self.time_mlp(F.silu(t_emb))[:, :, None, None]
        h = self.norm2(F.silu(self.conv2(h)))
        return h + self.skip(x)


class TinyUNet(nn.Module):
    """Small UNet for pixel-art texture diffusion.

    Args:
        img_channels: Number of image channels (3 for RGB).
        base_dim: Base channel width (default 64 for toy model).
        dim_mults: Channel multipliers for each resolution level.
        text_emb_dim: Dimension of text conditioning embedding.
    """

    def __init__(
        self,
        img_channels: int = 3,
        base_dim: int = 64,
        dim_mults: tuple[int, ...] = (1, 2, 4),
        text_emb_dim: int = 128,
    ):
        super().__init__()
        time_dim = base_dim * 4

        # Time embedding
        self.time_embed = nn.Sequential(
            SinusoidalPositionEmbedding(base_dim),
            nn.Linear(base_dim, time_dim),
            nn.SiLU(),
            nn.Linear(time_dim, time_dim),
        )

        # Optional text conditioning projection
        self.text_proj = nn.Linear(text_emb_dim, time_dim)

        # Encoder
        dims = [base_dim * m for m in dim_mults]
        self.init_conv = nn.Conv2d(img_channels, dims[0], 3, padding=1)

        self.down_blocks = nn.ModuleList()
        self.down_samples = nn.ModuleList()
        for i in range(len(dims) - 1):
            self.down_blocks.append(ResBlock(dims[i], dims[i], time_dim))
            self.down_samples.append(nn.Conv2d(dims[i], dims[i + 1], 4, 2, 1))

        # Bottleneck
        self.mid_block = ResBlock(dims[-1], dims[-1], time_dim)

        # Decoder
        self.up_blocks = nn.ModuleList()
        self.up_samples = nn.ModuleList()
        for i in range(len(dims) - 1):
            in_ch = dims[-(i + 1)]
            out_ch = dims[-(i + 2)]
            self.up_samples.append(nn.ConvTranspose2d(in_ch, out_ch, 4, 2, 1))
            # Skip from encoder at this level has out_ch channels
            self.up_blocks.append(ResBlock(out_ch * 2, out_ch, time_dim))

        self.out_conv = nn.Conv2d(dims[0], img_channels, 1)

    def forward(
        self,
        x: torch.Tensor,
        t: torch.Tensor,
        text_emb: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Forward pass.

        Args:
            x: Noisy image [B, C, H, W].
            t: Timestep [B].
            text_emb: Optional text embedding [B, text_emb_dim].
        """
        t_emb = self.time_embed(t)
        if text_emb is not None:
            t_emb = t_emb + self.text_proj(text_emb)

        h = self.init_conv(x)
        skips = []

        # Down
        for block, down in zip(self.down_blocks, self.down_samples):
            h = block(h, t_emb)
            skips.append(h)
            h = down(h)

        # Mid
        h = self.mid_block(h, t_emb)

        # Up
        for up, block in zip(self.up_samples, self.up_blocks):
            h = up(h)
            skip = skips.pop()
            h = torch.cat([h, skip], dim=1)
            h = block(h, t_emb)

        return self.out_conv(h)
