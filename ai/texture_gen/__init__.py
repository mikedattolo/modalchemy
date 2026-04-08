"""Pixel-art texture generation sub-package.

Architecture: a small UNet-based diffusion model trained on 16×16 and 32×32
Minecraft-style pixel art. The model is intentionally tiny so it can run on
CPU (slowly) or a modest GPU.

The default "toy" config uses:
  - 64-dim base channels (vs 256+ in full Stable Diffusion)
  - 3 down-blocks
  - Text conditioning via a tiny CLIP text encoder or learned embeddings
  - DDPM scheduler with 100 steps (reducible via DDIM)
"""
