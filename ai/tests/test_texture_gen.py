"""Tests for the texture generation model architecture."""

import torch

from texture_gen.model import TinyUNet
from texture_gen.scheduler import DDPMScheduler


def test_tiny_unet_forward_16():
    model = TinyUNet(img_channels=3, base_dim=32, dim_mults=(1, 2))
    x = torch.randn(2, 3, 16, 16)
    t = torch.randint(0, 100, (2,))
    out = model(x, t)
    assert out.shape == (2, 3, 16, 16)


def test_tiny_unet_forward_with_text():
    model = TinyUNet(img_channels=3, base_dim=32, dim_mults=(1, 2), text_emb_dim=64)
    x = torch.randn(2, 3, 16, 16)
    t = torch.randint(0, 100, (2,))
    text = torch.randn(2, 64)
    out = model(x, t, text_emb=text)
    assert out.shape == (2, 3, 16, 16)


def test_scheduler_add_noise():
    scheduler = DDPMScheduler(num_timesteps=100)
    x = torch.randn(2, 3, 16, 16)
    noise = torch.randn_like(x)
    t = torch.tensor([0, 50])
    noisy = scheduler.add_noise(x, noise, t)
    assert noisy.shape == x.shape


def test_scheduler_step():
    scheduler = DDPMScheduler(num_timesteps=100)
    x = torch.randn(1, 3, 16, 16)
    model_output = torch.randn_like(x)
    result = scheduler.step(model_output, t=50, x_t=x)
    assert result.shape == x.shape


def test_scheduler_step_t0():
    scheduler = DDPMScheduler(num_timesteps=100)
    x = torch.randn(1, 3, 16, 16)
    model_output = torch.randn_like(x)
    result = scheduler.step(model_output, t=0, x_t=x)
    assert result.shape == x.shape
