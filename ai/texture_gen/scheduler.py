"""DDPM noise scheduler for the texture diffusion model."""

from __future__ import annotations

import torch
import torch.nn.functional as F


class DDPMScheduler:
    """Minimal DDPM scheduler for training and inference.

    Args:
        num_timesteps: Total diffusion timesteps.
        beta_start: Starting noise level.
        beta_end: Ending noise level.
    """

    def __init__(
        self,
        num_timesteps: int = 1000,
        beta_start: float = 1e-4,
        beta_end: float = 0.02,
    ):
        self.num_timesteps = num_timesteps
        self.betas = torch.linspace(beta_start, beta_end, num_timesteps)
        self.alphas = 1.0 - self.betas
        self.alpha_cumprod = torch.cumprod(self.alphas, dim=0)
        self.alpha_cumprod_prev = F.pad(self.alpha_cumprod[:-1], (1, 0), value=1.0)

    def add_noise(
        self,
        x_start: torch.Tensor,
        noise: torch.Tensor,
        t: torch.Tensor,
    ) -> torch.Tensor:
        """Add noise to x_start at timestep t."""
        sqrt_alpha = self.alpha_cumprod[t].sqrt()[:, None, None, None].to(x_start.device)
        sqrt_one_minus = (1 - self.alpha_cumprod[t]).sqrt()[:, None, None, None].to(
            x_start.device
        )
        return sqrt_alpha * x_start + sqrt_one_minus * noise

    @torch.no_grad()
    def step(
        self,
        model_output: torch.Tensor,
        t: int,
        x_t: torch.Tensor,
    ) -> torch.Tensor:
        """Single reverse diffusion step."""
        beta = self.betas[t]
        alpha = self.alphas[t]
        alpha_bar = self.alpha_cumprod[t]
        alpha_bar_prev = self.alpha_cumprod_prev[t]

        # Predict x_0
        pred_x0 = (x_t - (1 - alpha_bar).sqrt() * model_output) / alpha_bar.sqrt()
        pred_x0 = pred_x0.clamp(-1, 1)

        # Compute mean
        coeff1 = beta * alpha_bar_prev.sqrt() / (1 - alpha_bar)
        coeff2 = (1 - alpha_bar_prev) * alpha.sqrt() / (1 - alpha_bar)
        mean = coeff1 * pred_x0 + coeff2 * x_t

        if t > 0:
            noise = torch.randn_like(x_t)
            variance = beta * (1 - alpha_bar_prev) / (1 - alpha_bar)
            return mean + variance.sqrt() * noise
        return mean
