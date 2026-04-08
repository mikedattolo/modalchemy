"""PyTorch Dataset for pixel-art textures."""

from __future__ import annotations

from pathlib import Path

import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms


class TextureDataset(Dataset):
    """Load PNG textures from a directory for training.

    All images are resized to img_size × img_size and normalized to [-1, 1].
    """

    EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}

    def __init__(self, root: Path, img_size: int = 16):
        self.root = root
        self.img_size = img_size
        self.paths: list[Path] = []

        if root.exists():
            self.paths = sorted(
                p for p in root.rglob("*") if p.suffix.lower() in self.EXTENSIONS
            )

        self.transform = transforms.Compose(
            [
                transforms.Resize((img_size, img_size), interpolation=Image.NEAREST),
                transforms.ToTensor(),  # [0, 1]
                transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),  # [-1, 1]
            ]
        )

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, idx: int) -> torch.Tensor:
        img = Image.open(self.paths[idx]).convert("RGB")
        return self.transform(img)
