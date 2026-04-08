"""AI inference server — FastAPI app serving texture and model generation.

Run with:
    python -m inference.server --port 8421
"""

from __future__ import annotations

import argparse
import base64
import io
import uuid

import uvicorn
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel

from ai.model_gen.generator import generate_model

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
    img = _placeholder_texture(size, req.prompt)
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


@app.post("/api/models/generate")
async def generate_model_endpoint(req: ModelRequest):
    """Generate a Minecraft JSON model from a prompt."""
    result = generate_model(
        prompt=req.prompt,
        model_type=req.model_type,  # type: ignore[arg-type]
        mode=req.mode,  # type: ignore[arg-type]
    )
    return result


# ── Health ───────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "gpu_available": _check_gpu()}


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
