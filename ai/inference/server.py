"""AI inference server — FastAPI app serving texture and model generation.

Run with:
    python -m inference.server --port 8421
"""

from __future__ import annotations

import argparse
import base64
import io
import os
import uuid
from pathlib import Path

import uvicorn
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel

from model_gen.generator import generate_model
from texture_gen.model import TinyUNet
from texture_gen.scheduler import DDPMScheduler

app = FastAPI(
    title="ModForge AI Inference",
    version="0.1.0",
    description="Local AI inference for texture and model generation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "http://localhost:5173", "https://tauri.localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_TEXTURE_RUNTIME: dict[str, object] = {"initialized": False, "enabled": False}
_ACTIVE_TEXTURE_CHECKPOINT: str | None = None
_ACTIVE_MODEL_DATASET: str | None = None


# ── Texture endpoints ───────────────────────────────────────────

class TextureRequest(BaseModel):
    prompt: str
    size: int = 16  # 16 or 32
    mode: str = "generate"


@app.post("/api/textures/generate")
async def generate_texture(req: TextureRequest):
    """Generate a pixel-art texture from a prompt.

    Currently returns a placeholder colored image.
    The full implementation will use the trained diffusion model.
    """
    size = max(16, min(req.size, 32))
    img = _generate_texture_with_runtime(size, req.prompt)
    b64 = _image_to_base64(img)

    return {
        "id": uuid.uuid4().hex[:12],
        "prompt": req.prompt,
        "image_base64": b64,
        "size": size,
    }


@app.post("/api/textures/remix")
async def remix_texture(
    image: UploadFile,
    prompt: str = "",
    size: str = "16",
):
    """Remix an existing texture.

    Currently returns the input image tinted. The full implementation
    will use img2img diffusion.
    """
    img_bytes = await image.read()
    src = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    sz = int(size)
    src = src.resize((sz, sz), Image.NEAREST)

    # Placeholder: slight color shift
    import numpy as np

    arr = np.array(src, dtype=np.float32)
    arr = np.clip(arr * 0.8 + 30, 0, 255).astype(np.uint8)
    remixed = Image.fromarray(arr)
    b64 = _image_to_base64(remixed)

    return {
        "id": uuid.uuid4().hex[:12],
        "prompt": prompt or "remix",
        "image_base64": b64,
        "size": sz,
    }


# ── Model endpoints ─────────────────────────────────────────────

class ModelRequest(BaseModel):
    prompt: str
    model_type: str = "block"  # "block" or "item"
    mode: str = "generate"


class AssetRequest(BaseModel):
    prompt: str
    texture_prompt: str | None = None
    size: int = 16
    model_type: str = "block"


class RuntimeConfigRequest(BaseModel):
    texture_checkpoint: str | None = None
    model_dataset: str | None = None


@app.post("/api/models/generate")
async def generate_model_endpoint(req: ModelRequest):
    """Generate a Minecraft JSON model from a prompt."""
    result = generate_model(
        prompt=req.prompt,
        model_type=req.model_type,  # type: ignore[arg-type]
        mode=req.mode,  # type: ignore[arg-type]
    )
    return result


@app.post("/api/assets/generate")
async def generate_asset_bundle(req: AssetRequest):
    """Generate a texture and matching model in one request."""
    size = max(16, min(req.size, 32))
    texture_prompt = (req.texture_prompt or req.prompt).strip()
    texture_name = _slug(texture_prompt)

    image = _generate_texture_with_runtime(size, texture_prompt)
    image_b64 = _image_to_base64(image)

    model = generate_model(
        prompt=req.prompt,
        model_type=req.model_type,  # type: ignore[arg-type]
        texture_name=texture_name,
    )

    return {
        "id": uuid.uuid4().hex[:12],
        "prompt": req.prompt,
        "texture": {
            "id": uuid.uuid4().hex[:12],
            "prompt": texture_prompt,
            "image_base64": image_b64,
            "size": size,
            "texture_name": texture_name,
        },
        "model": model,
    }


@app.get("/api/config/options")
async def get_config_options():
    """List available model/texture assets and active runtime selection."""
    texture_options = [str(p) for p in _discover_texture_checkpoints()]
    model_options = [str(p) for p in _discover_model_datasets()]
    runtime = _get_texture_runtime()
    active_texture = _ACTIVE_TEXTURE_CHECKPOINT or runtime.get("checkpoint")
    active_model = _ACTIVE_MODEL_DATASET or os.getenv("MODFORGE_MODEL_DATASET")

    return {
        "texture_checkpoints": texture_options,
        "model_datasets": model_options,
        "active_texture_checkpoint": active_texture,
        "active_model_dataset": active_model,
    }


@app.put("/api/config/active")
async def set_active_config(req: RuntimeConfigRequest):
    """Set active texture checkpoint and model dataset for runtime testing."""
    global _ACTIVE_TEXTURE_CHECKPOINT, _ACTIVE_MODEL_DATASET

    if req.texture_checkpoint:
        checkpoint = Path(req.texture_checkpoint).expanduser().resolve()
        if not checkpoint.exists():
            return {"ok": False, "error": "Texture checkpoint not found"}
        _ACTIVE_TEXTURE_CHECKPOINT = str(checkpoint)

    if req.model_dataset:
        dataset = Path(req.model_dataset).expanduser().resolve()
        if not dataset.exists():
            return {"ok": False, "error": "Model dataset not found"}
        _ACTIVE_MODEL_DATASET = str(dataset)
        os.environ["MODFORGE_MODEL_DATASET"] = _ACTIVE_MODEL_DATASET

    _TEXTURE_RUNTIME.clear()
    _TEXTURE_RUNTIME.update({"initialized": False, "enabled": False})

    options = await get_config_options()
    return {"ok": True, "active": options}


# ── Health ───────────────────────────────────────────────────────

@app.get("/health")
async def health():
    runtime = _get_texture_runtime()
    model_dataset = os.getenv("MODFORGE_MODEL_DATASET")
    return {
        "status": "ok",
        "version": "0.1.0",
        "gpu_available": _check_gpu(),
        "custom_texture_checkpoint": runtime.get("checkpoint"),
        "custom_model_dataset": model_dataset,
    }


# ── Helpers ──────────────────────────────────────────────────────

def _placeholder_texture(size: int, prompt: str) -> Image.Image:
    """Generate a simple placeholder texture based on prompt keywords."""
    import hashlib

    h = hashlib.md5(prompt.encode()).hexdigest()  # noqa: S324 -- not for security
    r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    img = Image.new("RGB", (size, size))
    pixels = img.load()
    assert pixels is not None
    for y in range(size):
        for x in range(size):
            # Create a noisy pixel-art-ish pattern
            noise = ((x * 7 + y * 13 + int(h[6:8], 16)) % 40) - 20
            pixels[x, y] = (
                max(0, min(255, r + noise)),
                max(0, min(255, g + noise + (x % 3) * 5)),
                max(0, min(255, b + noise - (y % 3) * 5)),
            )
    return img


def _generate_texture_with_runtime(size: int, prompt: str) -> Image.Image:
    runtime = _get_texture_runtime()
    if not runtime.get("enabled"):
        return _placeholder_texture(size, prompt)

    model = runtime["model"]
    scheduler = runtime["scheduler"]
    device = runtime["device"]
    train_size = runtime["train_size"]

    import hashlib
    import torch

    seed = int(hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8], 16)
    generator = torch.Generator(device=device)
    generator.manual_seed(seed)

    with torch.no_grad():
        x = torch.randn((1, 3, train_size, train_size), generator=generator, device=device)
        num_steps = min(100, scheduler.num_timesteps)
        steps = torch.linspace(scheduler.num_timesteps - 1, 0, steps=num_steps, device=device).long()

        for t in steps.tolist():
            t_batch = torch.tensor([t], device=device)
            pred_noise = model(x, t_batch)
            x = scheduler.step(pred_noise, t=t, x_t=x)

        image = ((x[0].clamp(-1, 1) + 1) * 127.5).byte().cpu()
        import numpy as np

        arr = image.permute(1, 2, 0).numpy().astype(np.uint8)
        pil_img = Image.fromarray(arr, mode="RGB")

    if pil_img.size != (size, size):
        pil_img = pil_img.resize((size, size), Image.NEAREST)
    return pil_img


def _get_texture_runtime() -> dict[str, object]:
    if _TEXTURE_RUNTIME.get("initialized"):
        return _TEXTURE_RUNTIME

    _TEXTURE_RUNTIME["initialized"] = True

    ckpt_path = _resolve_texture_checkpoint()
    if ckpt_path is None:
        return _TEXTURE_RUNTIME

    try:
        import torch

        checkpoint = torch.load(ckpt_path, map_location="cpu")
        cfg = checkpoint.get("config")

        base_dim = int(getattr(cfg, "base_dim", 64))
        dim_mults = tuple(getattr(cfg, "dim_mults", (1, 2, 4)))
        text_emb_dim = int(getattr(cfg, "text_emb_dim", 128))
        num_timesteps = int(getattr(cfg, "num_timesteps", 1000))
        beta_start = float(getattr(cfg, "beta_start", 1e-4))
        beta_end = float(getattr(cfg, "beta_end", 0.02))
        img_size = int(getattr(cfg, "img_size", 16))

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = TinyUNet(
            img_channels=3,
            base_dim=base_dim,
            dim_mults=dim_mults,
            text_emb_dim=text_emb_dim,
        ).to(device)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()

        scheduler = DDPMScheduler(
            num_timesteps=num_timesteps,
            beta_start=beta_start,
            beta_end=beta_end,
        )

        _TEXTURE_RUNTIME.update(
            {
                "enabled": True,
                "device": device,
                "model": model,
                "scheduler": scheduler,
                "train_size": img_size,
                "checkpoint": str(ckpt_path),
            }
        )
    except Exception:
        _TEXTURE_RUNTIME["enabled"] = False

    return _TEXTURE_RUNTIME


def _resolve_texture_checkpoint() -> Path | None:
    if _ACTIVE_TEXTURE_CHECKPOINT:
        active = Path(_ACTIVE_TEXTURE_CHECKPOINT).expanduser().resolve()
        return active if active.exists() else None

    env_path = os.getenv("MODFORGE_TEXTURE_CHECKPOINT")
    if env_path:
        explicit = Path(env_path).expanduser().resolve()
        return explicit if explicit.exists() else None

    default_dir = Path(__file__).resolve().parents[1] / "checkpoints" / "texture_gen"
    if not default_dir.exists():
        return None

    checkpoints = sorted(default_dir.glob("*.pt"), key=lambda p: p.stat().st_mtime)
    return checkpoints[-1] if checkpoints else None


def _discover_texture_checkpoints() -> list[Path]:
    options: list[Path] = []
    default_dir = Path(__file__).resolve().parents[1] / "checkpoints" / "texture_gen"
    if default_dir.exists():
        options.extend(sorted(default_dir.glob("*.pt"), key=lambda p: p.stat().st_mtime))

    env_path = os.getenv("MODFORGE_TEXTURE_CHECKPOINT")
    if env_path:
        env_ckpt = Path(env_path).expanduser().resolve()
        if env_ckpt.exists() and env_ckpt not in options:
            options.append(env_ckpt)

    return options


def _discover_model_datasets() -> list[Path]:
    options: list[Path] = []

    default = Path(__file__).resolve().parents[1] / "checkpoints" / "model_gen" / "models.jsonl"
    if default.exists():
        options.append(default)

    datasets_root = Path(__file__).resolve().parents[1] / "datasets" / "processed"
    if datasets_root.exists():
        options.extend(sorted(datasets_root.glob("**/models*.jsonl")))

    env_path = os.getenv("MODFORGE_MODEL_DATASET")
    if env_path:
        env_dataset = Path(env_path).expanduser().resolve()
        if env_dataset.exists() and env_dataset not in options:
            options.append(env_dataset)

    seen: set[str] = set()
    unique: list[Path] = []
    for option in options:
        key = str(option.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(option)
    return unique


def _slug(text: str) -> str:
    return "_".join(text.lower().split()[:4]).replace("-", "_")[:32]


def _image_to_base64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _check_gpu() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except ImportError:
        return False


def main():
    parser = argparse.ArgumentParser(description="ModForge AI Inference Server")
    parser.add_argument("--port", type=int, default=8421)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
