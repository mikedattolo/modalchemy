# AI Training Guide

This document covers how to prepare datasets, train models, and run inference
for ModForge's AI features.

## Important: Data Sourcing

**ModForge does not ship any copyrighted Minecraft assets.** You must supply
your own training data. See [SECURITY.md](../SECURITY.md) for legal details.

### Permissible data sources for textures

| Source | License | Notes |
|---|---|---|
| Your own pixel art | Yours | Best option — full rights |
| CC0 pixel art packs | Public domain | [OpenGameArt.org](https://opengameart.org) has many |
| CC-BY pixel art | Attribution required | Check individual licenses |
| Procedurally generated | N/A | Write a script to generate training data |
| Screenshots (your own builds) | Yours | Lower quality but valid |

### For model JSONs

Minecraft's built-in model JSONs ship with the game. Under Mojang's EULA, you
can reference the format but should not redistribute verbatim copies. The dataset
prep script (`datasets/prepare_models.py`) expects you to point it at a directory
of JSON files.

---

## Texture Generation Model

### Architecture

- **Type:** DDPM (Denoising Diffusion Probabilistic Model)
- **Network:** TinyUNet — a small UNet with ~500K parameters
- **Input:** 16×16 or 32×32 RGB images
- **Conditioning:** Optional text embedding (128-dim)
- **Scheduler:** Linear beta schedule, 1000 timesteps (100 for toy)

### Dataset Preparation

```bash
cd ai

# Collect your PNG textures into a folder, then:
python -m datasets.prepare_textures \
  --input /path/to/your/textures \
  --output datasets/processed/textures \
  --size 16
```

This produces:
- `datasets/processed/textures/00000.png`, `00001.png`, ...
- `datasets/processed/textures/metadata.json` — filename-to-label mapping

**Recommended:** At least 500 images for the toy model, 5000+ for full quality.

### Training

```bash
# Toy model — runs on CPU, trains in minutes
python -m training.train_texture --config toy

# Full model — needs GPU, trains in hours
python -m training.train_texture --config full

# Custom options
python -m training.train_texture \
  --config full \
  --dataset /custom/path \
  --epochs 200

# Auto-detect GPU and cap training process VRAM (good for 12 GB cards)
python -m training.train_texture \
  --config full \
  --max-vram-gb 10
```

Checkpoints are saved to `ai/checkpoints/texture_gen/`.

### Fastest Path (Recommended)

If you already decompiled mods into `workspaces/`, this one command prepares
datasets and (optionally) trains a starter checkpoint:

```bash
cd ai

# dataset + model corpus only (fastest)
python -m training.bootstrap

# dataset + corpus + starter texture model
python -m training.bootstrap --train-texture --config toy --epochs 10
```

### Training Configuration

| Parameter | Toy | Full |
|---|---|---|
| Base channels | 32 | 64 |
| Resolution levels | 2 | 3 |
| Timesteps | 100 | 1000 |
| Batch size | 8 | 32 |
| Epochs | 5 | 100 |
| Image size | 16×16 | 32×32 |

---

## Model JSON Generation

### Architecture

The model JSON generator uses structured generation to produce valid Minecraft
block/item model JSON files.

**Current implementation:** Retrieval + schema-validated synthesis that maps
prompt intent into a 1.7.10-compatible structure (`cube_all`, `cube_column`,
`stairs`, multi-element meshes, etc.) and validates the final JSON via Pydantic.

**Optional future path:** Add an Outlines-constrained LLM for more expressive
model creativity after you have a large enough curated corpus.

### Dataset Preparation

```bash
cd ai

python -m datasets.prepare_models \
  --input /path/to/model/jsons \
  --output datasets/processed/models
```

This produces `datasets/processed/models/models.jsonl` — one JSON object per
line with `prompt` and `completion` fields.

### Training status

Model generation currently uses a retrieval + schema-validated synthesis
approach backed by your curated model corpus (`checkpoints/model_gen/models.jsonl`).
This means you can improve output quality immediately by adding more 1.7.10
model JSON examples from your own mod workspaces.

Future LLM fine-tuning is still possible, but **not required** to get useful
results from day one.

---

## Running Inference

### Start the inference server

```bash
cd ai
python -m inference.server --port 8421
```

The server provides:
- `POST /api/textures/generate` — generate a texture from a prompt
- `POST /api/textures/remix` — remix an existing texture
- `POST /api/models/generate` — generate a model JSON
- `POST /api/assets/generate` — generate matching texture + model bundle
- `POST /api/assets/generate-and-save` — generate and write files to the exact
  `assets/<namespace>/...` structure used by mods
- `GET /health` — check server status and GPU availability
- `GET /docs` — OpenAPI documentation

### Using a trained model

Place your checkpoint in `ai/checkpoints/texture_gen/` and the inference
server will load it automatically. Without a checkpoint, it falls back to
placeholder generation.

## Train Directly From Decompiled Workspaces

If you have already imported/decompiled many mods with ModForge, you can train
from that data directly.

This workflow scans `workspaces/*/resources/assets/**` for:
- Texture PNG files in `textures/**`
- Model JSON files in `models/**`

Then it builds:
- `ai/datasets/processed/textures_from_workspaces/`
- `ai/datasets/processed/models_from_workspaces/models.jsonl`
- `ai/checkpoints/model_gen/models.jsonl` (custom model-generation corpus)

### 1) Build datasets from workspaces

```bash
cd ai
python -m training.train_from_workspaces --size 16
```

### 2) Train a custom texture model (optional)

```bash
cd ai
python -m training.train_from_workspaces \
  --size 16 \
  --train-texture \
  --config full \
  --epochs 40 \
  --max-vram-gb 10
```

Notes:
- Training auto-detects your GPU model and VRAM when CUDA is available.
- `--max-vram-gb` sets a per-process CUDA memory cap to reduce OOM risk.
- Use `--no-auto-gpu` to disable automatic batch-size tuning.

### 3) Run inference with custom assets

```bash
cd ai
python -m inference.server --port 8421
```

Behavior:
- Texture generation: loads the newest checkpoint from
  `ai/checkpoints/texture_gen/*.pt` (or `MODFORGE_TEXTURE_CHECKPOINT`)
- Model generation: uses custom corpus at
  `ai/checkpoints/model_gen/models.jsonl` (or `MODFORGE_MODEL_DATASET`)

### 4) Override custom paths (optional)

```bash
MODFORGE_TEXTURE_CHECKPOINT=/abs/path/to/texture_gen_epoch40.pt \
MODFORGE_MODEL_DATASET=/abs/path/to/models.jsonl \
python -m inference.server --port 8421
```

## Practical Notes for 100+ Mods

- Yes, training from 100+ Forge 1.7.10 mods is feasible.
- Quality improves as data quality and variety improve (duplicates hurt).
- CPU training works for toy runs; real quality generally needs CUDA GPU.
- Keep legal constraints in mind for redistribution of trained weights.

---

## Reproducibility

All training runs are reproducible:
1. Dataset preparation is deterministic (sorted glob, sequential numbering)
2. Training uses PyTorch with explicit device placement
3. Checkpoints include full optimizer state for resumption
4. Config is saved alongside the checkpoint

To reproduce a training run:
```bash
# Same config + same data = same results (given same hardware)
python -m training.train_texture --config toy --dataset datasets/processed/textures
```
