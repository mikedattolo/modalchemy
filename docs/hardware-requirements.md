# Hardware Requirements

## Minimum (UI + Decompilation only)

| Component | Requirement |
|---|---|
| OS | Windows 11 22H2+ (Linux/macOS experimental) |
| CPU | Any x86-64 (Intel/AMD) |
| RAM | 4 GB |
| Disk | 500 MB for app + tools |
| GPU | Not required |
| Java | JRE 8+ (for CFR decompiler) |

This is sufficient to:
- Run the desktop app
- Import and decompile mod JARs
- Browse workspaces
- Use AI features with placeholder/template generation

## Recommended (AI inference on CPU)

| Component | Requirement |
|---|---|
| CPU | 4+ cores (Intel i5 / AMD Ryzen 5 or better) |
| RAM | 8 GB |
| Disk | 2 GB |
| GPU | Not required (but slow) |

The toy diffusion model (~500K parameters) can run inference on CPU. Expect
~5-15 seconds per 16×16 texture.

## Recommended (AI inference on GPU)

| Component | Requirement |
|---|---|
| CPU | 4+ cores |
| RAM | 16 GB |
| Disk | 5 GB |
| GPU | NVIDIA with 4+ GB VRAM (GTX 1650 or better) |
| CUDA | 11.8 or 12.x |

GPU inference is ~50-100× faster than CPU for the diffusion model.

## For AI Training

### Toy model training

| Component | Requirement |
|---|---|
| CPU | Any modern CPU |
| RAM | 8 GB |
| Time | ~5 minutes on CPU, ~30 seconds on GPU |

### Full model training

| Component | Requirement |
|---|---|
| GPU | NVIDIA RTX 3060+ (8 GB VRAM minimum) |
| RAM | 16 GB+ |
| Disk | 10 GB (datasets + checkpoints) |
| Time | 2-8 hours depending on dataset size and GPU |

### LLM fine-tuning (model JSON generation — planned)

| Component | Requirement |
|---|---|
| GPU | NVIDIA RTX 3090+ (24 GB VRAM) or use QLoRA with 8 GB |
| RAM | 32 GB |
| Time | 4-12 hours |

## Software Requirements

| Software | Version | Purpose |
|---|---|---|
| Node.js | 20 LTS+ | Frontend build |
| Rust | 1.75+ | Tauri desktop shell |
| Python | 3.11+ | Backend + AI |
| Java | 8+ | CFR decompiler runtime |
| CUDA Toolkit | 11.8+ | GPU acceleration (optional) |

## Platform Support

| Platform | Status |
|---|---|
| Windows 11 | Primary target, fully supported |
| Windows 10 | Should work (WebView2 may need install) |
| Ubuntu 22.04+ | Experimental, setup script provided |
| macOS 13+ | Experimental, setup script provided |
