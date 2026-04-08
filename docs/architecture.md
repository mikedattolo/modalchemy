# Architecture Overview

ModForge is composed of three main components that communicate over local HTTP:

```
┌─────────────────────────────────────────────────────┐
│                   Desktop App                       │
│            (Tauri 2 + React + TypeScript)            │
│                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │  Import   │ │Workspace │ │ Texture  │ │ Model  │ │
│  │  Page     │ │ Browser  │ │   Gen    │ │  Gen   │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ │
│       │             │            │            │      │
└───────┼─────────────┼────────────┼────────────┼──────┘
        │ HTTP :8420  │            │ HTTP :8421 │
┌───────┴─────────────┴────┐ ┌────┴────────────┴──────┐
│   Backend Service        │ │   AI Inference Server   │
│   (Python / FastAPI)     │ │   (Python / FastAPI)    │
│                          │ │                         │
│  ┌────────────────────┐  │ │  ┌──────────────────┐   │
│  │ Decompile Pipeline │  │ │  │ Texture Diffusion│   │
│  │ • Validate JAR     │  │ │  │   (TinyUNet)     │   │
│  │ • Extract          │  │ │  ├──────────────────┤   │
│  │ • Run CFR          │  │ │  │ Model JSON Gen   │   │
│  │ • Report           │  │ │  │  (Structured)    │   │
│  └────────────────────┘  │ │  └──────────────────┘   │
│  ┌────────────────────┐  │ │                         │
│  │ Workspace Manager  │  │ │                         │
│  │ • Browse tree      │  │ │                         │
│  │ • Read files       │  │ │                         │
│  │ • Export           │  │ │                         │
│  └────────────────────┘  │ │                         │
└──────────────────────────┘ └─────────────────────────┘
```

## Technology Choices

### Desktop Shell: Tauri 2

- **Why not Electron?** Tauri produces ~5 MB binaries vs Electron's ~100+ MB.
  It uses the OS WebView (WebView2 on Windows 11 = Chromium-based, pre-installed).
- **Security:** Tauri's security model is more restrictive by default. The
  frontend cannot directly call system APIs without explicit Tauri commands.
- **Trade-off:** Requires Rust toolchain for building. The Rust code is minimal
  (just the shell + plugin wiring).

### Frontend: React 18 + TypeScript + Vite

- Fast HMR development loop with Vite
- TypeScript catches bugs at compile time
- Tailwind CSS for utility-first styling (small bundle, no runtime)
- Radix UI for accessible, unstyled primitives
- react-router-dom for client-side routing between pages

### Backend: Python 3.11 + FastAPI

- FastAPI gives auto-generated OpenAPI docs (visit `/docs` when running)
- Python is the natural choice for ML/AI integration
- `python-multipart` handles JAR file uploads
- The backend is a standalone HTTP server; the Tauri app connects to it
- **Why not bundle Python inside Tauri?** Keeping them separate is simpler
  to develop, debug, and means the backend can also be used headless.

### Decompiler: CFR (default)

- [CFR](https://github.com/leibnitz27/cfr) is a high-quality open-source Java
  decompiler that handles Java 6–8 bytecode well (which is what MC 1.6.4/1.7.10
  mods target).
- The pipeline is pluggable: swap CFR for FernFlower or Procyon via settings.
- CFR is invoked as a subprocess (`java -jar cfr.jar`) — no JNI needed.

### AI: PyTorch + Diffusers + Outlines

- **Texture generation:** A tiny UNet diffusion model trained on pixel art.
  Uses the same DDPM formulation as Stable Diffusion but with ~1000× fewer
  parameters. Can run on CPU (slowly) or GPU.
- **Model JSON generation:** Uses [Outlines](https://github.com/outlines-dev/outlines)
  for structured generation — guarantees the output conforms to the Minecraft
  model JSON schema. Currently falls back to template-based generation.
- **Why not use an API (OpenAI, etc.)?** The requirement is fully local/offline.

## Data Flow

### Import & Decompile

```
User selects .jar
  → Frontend POSTs to /api/decompile
    → Backend validates JAR (zipfile, has .class files, Forge metadata)
    → Extracts to workspace/{id}/classes/ and workspace/{id}/resources/
    → Runs CFR on classes/ → workspace/{id}/sources/
    → Generates report.json
  ← Returns DecompileReport JSON
Frontend navigates to Workspace Browser
```

### AI Texture Generation

```
User enters prompt + size
  → Frontend POSTs to AI server /api/textures/generate
    → Inference server runs diffusion model (or placeholder)
  ← Returns base64 PNG
Frontend displays in grid
```

## Directory Layout

```
modforge/
├── app/                    # Tauri + React desktop app
│   ├── src/                # React components and pages
│   ├── src-tauri/          # Tauri Rust code
│   └── package.json
├── backend/                # Python FastAPI backend
│   ├── modforge/
│   │   ├── api/            # REST endpoints
│   │   ├── decompiler/     # JAR pipeline
│   │   └── workspace/      # Workspace management
│   └── tests/
├── ai/                     # AI models and training
│   ├── texture_gen/        # UNet diffusion model
│   ├── model_gen/          # JSON model generator
│   ├── inference/          # Inference server
│   ├── training/           # Training scripts
│   └── datasets/           # Dataset preparation
├── scripts/                # Dev setup & utilities
├── docs/                   # This documentation
└── tools/                  # External binaries (gitignored)
```
