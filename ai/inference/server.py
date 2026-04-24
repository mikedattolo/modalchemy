"""AI inference server — FastAPI app serving texture and model generation.

Run with:
    python -m inference.server --port 8421
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile
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
_TRAINING_LOCK = threading.Lock()
_TRAINING_PROCESS: subprocess.Popen[str] | None = None
_TRAINING_STATE: dict[str, object] = {
    "running": False,
    "mode": None,
    "pid": None,
    "started_at": None,
    "ended_at": None,
    "exit_code": None,
    "command": None,
    "log_path": None,
}


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


class AssetSaveRequest(AssetRequest):
    output_dir: str
    namespace: str = "modid"
    asset_name: str | None = None


class RuntimeConfigRequest(BaseModel):
    texture_checkpoint: str | None = None
    model_dataset: str | None = None


class TrainingRequest(BaseModel):
    mode: str = "workspace"  # workspace | texture
    config: str = "full"  # toy | full
    size: int = 16
    epochs: int | None = None
    max_vram_gb: float | None = None
    auto_gpu: bool = True
    train_texture: bool = True
    workspaces_dir: str | None = None
    dataset_dir: str | None = None


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


@app.post("/api/assets/generate-and-save")
async def generate_and_save_asset_bundle(req: AssetSaveRequest):
    """Generate a texture + model pair and persist them in MC 1.7.10 folder layout."""
    generated = await generate_asset_bundle(req)

    output_root = Path(req.output_dir).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    model_type = str(req.model_type or "block")
    texture_name = req.asset_name or generated["texture"]["texture_name"]
    texture_name = _slug(texture_name)
    namespace = _slug(req.namespace) or "modid"

    texture_bytes = base64.b64decode(generated["texture"]["image_base64"])
    texture_subdir = "items" if model_type == "item" else "blocks"
    model_subdir = "item" if model_type == "item" else "block"

    tex_path = output_root / "assets" / namespace / "textures" / texture_subdir / f"{texture_name}.png"
    model_path = output_root / "assets" / namespace / "models" / model_subdir / f"{texture_name}.json"

    tex_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.parent.mkdir(parents=True, exist_ok=True)

    tex_path.write_bytes(texture_bytes)
    model_path.write_text(generated["model"]["model_json"], encoding="utf-8")

    blockstate_path: Path | None = None
    if model_type == "block":
        blockstate_path = output_root / "assets" / namespace / "blockstates" / f"{texture_name}.json"
        blockstate_path.parent.mkdir(parents=True, exist_ok=True)
        blockstate = {"variants": {"normal": {"model": f"{namespace}:{texture_name}"}}}
        blockstate_path.write_text(json.dumps(blockstate, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "asset_name": texture_name,
        "namespace": namespace,
        "paths": {
            "texture": str(tex_path),
            "model": str(model_path),
            "blockstate": str(blockstate_path) if blockstate_path else None,
        },
        "generated": generated,
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


@app.get("/api/training/hardware")
async def get_training_hardware():
    """Report detected GPU and VRAM telemetry for training UI."""
    return _get_gpu_telemetry()


@app.get("/api/training/status")
async def get_training_status():
    """Return current training status and latest log lines."""
    with _TRAINING_LOCK:
        snapshot = dict(_TRAINING_STATE)

    log_tail = []
    log_path = snapshot.get("log_path")
    if isinstance(log_path, str) and Path(log_path).exists():
        try:
            lines = Path(log_path).read_text(encoding="utf-8", errors="replace").splitlines()
            log_tail = lines[-120:]
        except Exception:
            log_tail = []

    snapshot["log_tail"] = log_tail
    return snapshot


@app.post("/api/training/start")
async def start_training(req: TrainingRequest):
    """Start a background training process for texture/workspace pipelines."""
    global _TRAINING_PROCESS

    with _TRAINING_LOCK:
        if bool(_TRAINING_STATE.get("running")):
            raise HTTPException(status_code=409, detail="Training is already running")

        mode = req.mode.strip().lower()
        if mode not in {"workspace", "texture"}:
            raise HTTPException(status_code=400, detail="mode must be 'workspace' or 'texture'")

        if req.config not in {"toy", "full"}:
            raise HTTPException(status_code=400, detail="config must be 'toy' or 'full'")

        if req.size not in {16, 32}:
            raise HTTPException(status_code=400, detail="size must be 16 or 32")

        cmd = [sys.executable]
        if mode == "workspace":
            cmd.extend(["-m", "training.train_from_workspaces", "--size", str(req.size), "--config", req.config])
            if req.train_texture:
                cmd.append("--train-texture")
            if req.workspaces_dir:
                cmd.extend(["--workspaces-dir", req.workspaces_dir])
        else:
            cmd.extend(["-m", "training.train_texture", "--config", req.config])
            if req.dataset_dir:
                cmd.extend(["--dataset", req.dataset_dir])

        if req.epochs is not None and req.epochs > 0:
            cmd.extend(["--epochs", str(req.epochs)])
        if req.max_vram_gb is not None and req.max_vram_gb > 0:
            cmd.extend(["--max-vram-gb", str(req.max_vram_gb)])
        if not req.auto_gpu:
            cmd.append("--no-auto-gpu")

        logs_dir = _ai_root() / "outputs" / "training_logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        started = datetime.now(timezone.utc)
        stamp = started.strftime("%Y%m%d-%H%M%S")
        log_path = logs_dir / f"training-{stamp}.log"

        log_file = open(log_path, "w", encoding="utf-8")
        try:
            process = subprocess.Popen(
                cmd,
                cwd=_ai_root(),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except Exception as exc:
            log_file.close()
            raise HTTPException(status_code=500, detail=f"Failed to start training: {exc}") from exc

        _TRAINING_PROCESS = process
        _TRAINING_STATE.update(
            {
                "running": True,
                "mode": mode,
                "pid": process.pid,
                "started_at": started.isoformat(),
                "ended_at": None,
                "exit_code": None,
                "command": " ".join(cmd),
                "log_path": str(log_path),
            }
        )

        watcher = threading.Thread(
            target=_watch_training_process,
            args=(process, log_file),
            daemon=True,
        )
        watcher.start()

    return {"ok": True, "pid": _TRAINING_STATE.get("pid"), "log_path": _TRAINING_STATE.get("log_path")}


@app.post("/api/training/stop")
async def stop_training():
    """Stop the active background training process."""
    global _TRAINING_PROCESS
    with _TRAINING_LOCK:
        process = _TRAINING_PROCESS
        if process is None or not bool(_TRAINING_STATE.get("running")):
            return {"ok": True, "message": "No training process is running"}

    process.terminate()
    return {"ok": True, "message": "Stop signal sent"}


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
    """Generate deterministic Minecraft-like pixel art when no checkpoint exists."""
    import hashlib
    import random

    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    seed = int(digest[:16], 16)
    rng = random.Random(seed)

    palette = _infer_palette(prompt, digest)
    img = Image.new("RGB", (size, size), palette["mid"])
    px = img.load()
    assert px is not None

    pattern = _infer_pattern(prompt)
    for y in range(size):
        for x in range(size):
            base = _sample_pattern_color(pattern, x, y, size, palette, rng)
            shade = ((x * 5 + y * 3 + seed) % 9) - 4
            px[x, y] = _shade_color(base, shade)

    # subtle edge framing to make generated UV seams read better in game
    edge_color = _shade_color(palette["dark"], -6)
    for i in range(size):
        px[0, i] = edge_color
        px[i, 0] = edge_color
        if i % 2 == 0:
            px[size - 1, i] = _shade_color(edge_color, 2)
            px[i, size - 1] = _shade_color(edge_color, 2)

    return img


def _infer_pattern(prompt: str) -> str:
    lower = prompt.lower()
    if any(key in lower for key in ["ore", "stone", "cobble", "rock", "brick"]):
        return "mineral"
    if any(key in lower for key in ["wood", "log", "oak", "spruce", "birch"]):
        return "grain"
    if any(key in lower for key in ["metal", "iron", "steel", "copper", "gold"]):
        return "plate"
    if any(key in lower for key in ["leaf", "grass", "moss", "plant"]):
        return "foliage"
    return "noise"


def _infer_palette(prompt: str, digest: str) -> dict[str, tuple[int, int, int]]:
    lower = prompt.lower()
    if "redstone" in lower:
        return {"light": (224, 72, 67), "mid": (186, 41, 40), "dark": (108, 18, 22)}
    if any(key in lower for key in ["emerald", "leaf", "grass", "moss"]):
        return {"light": (109, 201, 89), "mid": (66, 150, 61), "dark": (35, 94, 38)}
    if any(key in lower for key in ["diamond", "ice", "water", "crystal"]):
        return {"light": (150, 224, 227), "mid": (81, 173, 189), "dark": (42, 109, 125)}
    if any(key in lower for key in ["wood", "oak", "spruce", "plank"]):
        return {"light": (168, 132, 84), "mid": (132, 95, 58), "dark": (89, 61, 34)}

    r, g, b = int(digest[:2], 16), int(digest[2:4], 16), int(digest[4:6], 16)
    mid = (r, g, b)
    return {
        "light": _shade_color(mid, 30),
        "mid": mid,
        "dark": _shade_color(mid, -36),
    }


def _sample_pattern_color(
    pattern: str,
    x: int,
    y: int,
    size: int,
    palette: dict[str, tuple[int, int, int]],
    rng,
) -> tuple[int, int, int]:
    if pattern == "grain":
        return palette["light"] if (x // max(1, size // 8)) % 2 == 0 else palette["mid"]
    if pattern == "plate":
        if (x + y) % max(2, size // 4) == 0:
            return palette["light"]
        return palette["mid"]
    if pattern == "foliage":
        return palette["light"] if (x + 2 * y) % 5 == 0 else palette["mid"]
    if pattern == "mineral":
        return palette["light"] if rng.random() > 0.75 else palette["dark"]
    return palette["light"] if rng.random() > 0.85 else palette["mid"]


def _shade_color(color: tuple[int, int, int], delta: int) -> tuple[int, int, int]:
    return tuple(max(0, min(255, c + delta)) for c in color)


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


def _watch_training_process(process: subprocess.Popen[str], log_file) -> None:
    """Wait for training process completion and update state."""
    global _TRAINING_PROCESS
    try:
        exit_code = process.wait()
    finally:
        try:
            log_file.close()
        except Exception:
            pass

    with _TRAINING_LOCK:
        _TRAINING_STATE["running"] = False
        _TRAINING_STATE["exit_code"] = exit_code
        _TRAINING_STATE["ended_at"] = datetime.now(timezone.utc).isoformat()
        _TRAINING_PROCESS = None


def _get_gpu_telemetry() -> dict[str, object]:
    try:
        import torch
    except ImportError:
        return {
            "gpu_available": False,
            "name": None,
            "total_vram_gb": None,
            "free_vram_gb": None,
            "allocated_vram_gb": None,
            "reserved_vram_gb": None,
            "recommended_max_vram_gb": None,
            "torch_installed": False,
            "torch_version": None,
            "torch_cuda_version": None,
            "cuda_device_count": 0,
            "nvidia_smi_ok": False,
            "nvidia_smi_summary": None,
            "diagnostic": "PyTorch is not installed in the AI environment.",
        }

    torch_version = getattr(torch, "__version__", None)
    torch_cuda_version = getattr(torch.version, "cuda", None)
    device_count = torch.cuda.device_count() if hasattr(torch.cuda, "device_count") else 0
    smi_ok, smi_summary = _nvidia_smi_summary()

    if not torch.cuda.is_available():
        if torch_cuda_version is None:
            reason = "PyTorch is CPU-only build (torch.version.cuda is None). Install CUDA-enabled PyTorch."
        elif not smi_ok:
            reason = "CUDA build is present but nvidia-smi did not report a working GPU/driver."
        else:
            reason = "CUDA runtime is present but torch.cuda.is_available() is False."
        return {
            "gpu_available": False,
            "name": None,
            "total_vram_gb": None,
            "free_vram_gb": None,
            "allocated_vram_gb": None,
            "reserved_vram_gb": None,
            "recommended_max_vram_gb": None,
            "torch_installed": True,
            "torch_version": torch_version,
            "torch_cuda_version": torch_cuda_version,
            "cuda_device_count": int(device_count),
            "nvidia_smi_ok": smi_ok,
            "nvidia_smi_summary": smi_summary,
            "diagnostic": reason,
        }

    props = torch.cuda.get_device_properties(0)
    total_gb = props.total_memory / (1024**3)
    allocated_gb = torch.cuda.memory_allocated(0) / (1024**3)
    reserved_gb = torch.cuda.memory_reserved(0) / (1024**3)
    try:
        free_bytes, total_bytes = torch.cuda.mem_get_info(0)
        free_gb = free_bytes / (1024**3)
        total_gb = total_bytes / (1024**3)
    except Exception:
        free_gb = None

    recommended = round(max(1.0, total_gb * 0.85), 2)
    return {
        "gpu_available": True,
        "name": props.name,
        "total_vram_gb": round(total_gb, 2),
        "free_vram_gb": round(free_gb, 2) if free_gb is not None else None,
        "allocated_vram_gb": round(allocated_gb, 2),
        "reserved_vram_gb": round(reserved_gb, 2),
        "recommended_max_vram_gb": recommended,
        "torch_installed": True,
        "torch_version": torch_version,
        "torch_cuda_version": torch_cuda_version,
        "cuda_device_count": int(device_count),
        "nvidia_smi_ok": smi_ok,
        "nvidia_smi_summary": smi_summary,
        "diagnostic": "CUDA GPU detected and ready.",
    }


def _nvidia_smi_summary() -> tuple[bool, str | None]:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total,memory.free",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except FileNotFoundError:
        return False, "nvidia-smi not found on PATH"
    except Exception as exc:
        return False, f"nvidia-smi error: {exc}"

    if result.returncode != 0:
        msg = (result.stderr or result.stdout).strip()
        return False, msg or "nvidia-smi returned non-zero status"

    line = result.stdout.strip().splitlines()
    if not line:
        return False, "nvidia-smi returned no GPU rows"

    return True, line[0].strip()


def _ai_root() -> Path:
    return Path(__file__).resolve().parents[1]


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
