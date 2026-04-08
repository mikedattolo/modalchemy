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
```

Checkpoints are saved to `ai/checkpoints/texture_gen/`.

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

**Current implementation:** Template-based fallback that selects a parent model
(`cube_all`, `cube_column`, `stairs`, etc.) based on prompt keywords.

**Planned implementation:** [Outlines](https://github.com/outlines-dev/outlines)
with a small language model (e.g., TinyLlama) fine-tuned on Minecraft model
JSON files. Outlines guarantees the output conforms to a Pydantic schema.

### Dataset Preparation

```bash
cd ai

python -m datasets.prepare_models \
  --input /path/to/model/jsons \
  --output datasets/processed/models
```

This produces `datasets/processed/models/models.jsonl` — one JSON object per
line with `prompt` and `completion` fields.

### Training (planned)

The model JSON generator training is not yet implemented. The planned approach:

1. Fine-tune a small LLM (TinyLlama-1.1B or similar) on the JSONL data
2. Use Outlines for constrained generation at inference time
3. The schema constraint ensures 100% valid output

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
- `GET /health` — check server status and GPU availability
- `GET /docs` — OpenAPI documentation

### Using a trained model

Place your checkpoint in `ai/checkpoints/texture_gen/` and the inference
server will load it automatically. Without a checkpoint, it falls back to
placeholder generation.

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
