# ModForge

> A Windows 11 desktop app that imports, decompiles, and browses Minecraft Forge
> mod JARs (1.6.4 / 1.7.10), and generates pixel-art textures and block/item
> JSON models with local AI — fully offline after initial setup.

![Status](https://img.shields.io/badge/status-scaffold-yellow)
![CI](https://img.shields.io/github/actions/workflow/status/mikedattolo/modalchemy/ci.yml?label=CI)
![License](https://img.shields.io/badge/license-MIT-blue)

<!-- TODO: replace with real screenshots -->
| Import & Decompile | Workspace Browser | AI Texture Gen |
|---|---|---|
| *screenshot placeholder* | *screenshot placeholder* | *screenshot placeholder* |

---

## Features

- **Import Forge mod JARs** — drag-and-drop or file picker; validates JAR
  structure for Forge 1.6.4 and 1.7.10 mods.
- **Decompile & Extract** — runs CFR (pluggable) to produce best-effort Java
  source, extracts textures, sounds, lang files, configs, and generates a
  structured workspace folder.
- **Workspace Browser** — tree-view of decompiled projects with syntax
  highlighting, search, and one-click export.
- **AI Texture Generation** — local pixel-art diffusion model; 16×16 and 32×32
  Minecraft-style textures from text prompts.
- **AI Model Generation** — structured JSON model output for blocks/items;
  optionally conditioned on a generated texture.
- **Remix Mode** — feed an existing texture or model and generate variants.
- **Fully Offline** — everything runs on your machine after initial setup.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Desktop shell | **Tauri 2** (Rust + WebView2) | ~5 MB binary, native Windows 11 look, secure |
| Frontend | **React 18 + TypeScript + Vite** | Fast HMR, type-safe, huge ecosystem |
| UI components | **Radix UI + Tailwind CSS** | Accessible, themeable, lightweight |
| Backend service | **Python 3.11+ / FastAPI** | Best ML ecosystem, async, OpenAPI docs |
| Decompiler | **CFR** (default), pluggable | High-quality open-source Java decompiler |
| AI — textures | **PyTorch + diffusers** (small UNet) | Industry-standard, runs on CPU or CUDA |
| AI — models | **Structured generation (Outlines + small LLM)** | Guarantees valid JSON schema output |
| CI | **GitHub Actions** | Lint, test, build on every PR |

---

## Repository Layout

```
├── app/                    # Tauri + React desktop application
│   ├── src/                # React pages & components
│   ├── src-tauri/          # Tauri Rust backend
│   ├── package.json
│   └── vite.config.ts
├── backend/                # Python FastAPI backend service
│   ├── modforge/           # Main package
│   │   ├── api/            # REST endpoints
│   │   ├── decompiler/     # JAR decompile + extract pipeline
│   │   └── workspace/      # Workspace management
│   ├── tests/              # pytest test suite
│   └── pyproject.toml
├── ai/                     # AI training & inference
│   ├── texture_gen/        # Texture diffusion model
│   ├── model_gen/          # JSON model generator
│   ├── inference/          # FastAPI inference server
│   ├── training/           # Training entry points
│   └── datasets/           # Dataset prep scripts
├── scripts/                # Dev setup & utility scripts
├── docs/                   # Extended documentation
├── tools/                  # External tool binaries (gitignored)
├── SECURITY.md             # Security & legal notice
└── LICENSE
```

---

## Getting Started

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| **Windows 11** | 22H2+ | Primary target; Linux/macOS experimental |
| **Node.js** | 20 LTS+ | For frontend build |
| **Rust** | 1.75+ | For Tauri; install via [rustup](https://rustup.rs) |
| **Python** | 3.11+ | For backend + AI |
| **Java** | 8+ | Only needed at runtime for CFR decompiler |
| **CUDA** (optional) | 11.8+ | GPU-accelerated AI inference/training |

### Quick Start (Windows)

```powershell
# 1 — Clone
git clone https://github.com/mikedattolo/modalchemy.git
cd modalchemy

# 2 — Run the setup script (installs deps, downloads CFR)
.\scripts\setup-dev.ps1

# 3 — Start the backend
cd backend
python -m uvicorn modforge.main:app --reload --port 8420

# 4 — In another terminal, start the desktop app
cd app
npm run tauri dev
```

### Quick Start (Linux / macOS)

```bash
# 1 — Clone & setup
git clone https://github.com/mikedattolo/modalchemy.git
cd modalchemy
bash scripts/setup-dev.sh

# 2 — Backend
cd backend && uvicorn modforge.main:app --reload --port 8420 &

# 3 — App
cd app && npm run tauri dev
```

### Running AI Inference

```bash
cd ai
pip install -r requirements.txt
python -m inference.server --port 8421
```

See [docs/ai-training.md](docs/ai-training.md) for training your own models.

---

## What's Working vs Stubbed

| Component | Status |
|---|---|
| Tauri + React UI skeleton (all 5 pages) | **Working** — renders, navigates |
| Backend FastAPI server + OpenAPI docs | **Working** — starts, serves endpoints |
| JAR validation & extraction | **Working** — extracts JARs to workspace |
| CFR decompilation integration | **Working** — calls CFR, captures output |
| Decompile report (JSON) | **Working** — generated after pipeline |
| AI inference server endpoints | **Stubbed** — returns placeholder data |
| Texture generation model | **Scaffold** — training pipeline + toy config |
| Model JSON generation | **Scaffold** — structured gen pipeline |
| Dataset preparation | **Scaffold** — scripts with real structure |
| Remix mode | **Stubbed** — UI wired, backend placeholder |

---

## Development

```bash
# Run backend tests
cd backend && pytest

# Run frontend lint + type-check
cd app && npm run lint && npm run typecheck

# Run AI module tests
cd ai && pytest
```

---

## Documentation

- [Architecture Overview](docs/architecture.md)
- [Decompilation Pipeline](docs/decompilation.md)
- [AI Training Guide](docs/ai-training.md)
- [Hardware Requirements](docs/hardware-requirements.md)
- [Security & Legal](SECURITY.md)

---

## Contributing

1. Fork & create a feature branch
2. Make changes with tests
3. Ensure CI passes: `npm run lint`, `pytest`, `cargo clippy`
4. Open a PR against `main`

---

## License

MIT — see [LICENSE](LICENSE).

**Important:** Read [SECURITY.md](SECURITY.md) for legal considerations around
mod decompilation and AI training data before using this tool.