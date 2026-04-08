# Development Guide

This guide walks through running ModForge locally for development, including
all three services and common workflows.

---

## Architecture Recap

ModForge runs three processes locally:

| Process | Port | Purpose |
|---|---|---|
| **Tauri + Vite** (frontend) | 1420 | Desktop app UI |
| **Backend** (FastAPI) | 8420 | Decompile pipeline, workspace API |
| **AI inference** (FastAPI) | 8421 | Texture & model generation |

The frontend talks to the backend and AI server over HTTP. Each can be
developed and restarted independently.

---

## Running All Services

You need **three terminal windows** (or use a multiplexer like tmux).

### Terminal 1 — Backend

```bash
cd backend
uvicorn modforge.main:app --reload --port 8420
```

- Auto-reloads on Python file changes
- OpenAPI docs at http://localhost:8420/docs
- Health check: http://localhost:8420/health

### Terminal 2 — AI Inference Server

```bash
cd ai
python -m inference.server --port 8421
```

- OpenAPI docs at http://localhost:8421/docs
- Optional — the app works without it (AI features show errors gracefully)

### Terminal 3 — Desktop App

```bash
cd app
npm run tauri dev
```

- Vite HMR on port 1420 — React changes reflect instantly
- Tauri opens a native window pointing to the Vite dev server
- Rust changes trigger a full rebuild (slower)

### Frontend-only development (no Tauri)

If you don't need the native shell (or don't have Rust installed):

```bash
cd app
npm run dev
```

Opens http://localhost:5173 in your browser. All features work except
Tauri-specific APIs (native file dialogs, etc.).

---

## Project Structure

```
modalchemy/
├── app/                       # Desktop application
│   ├── src/                   # React source
│   │   ├── components/        # Shared UI components
│   │   ├── pages/             # Route pages
│   │   ├── App.tsx            # Router + layout
│   │   ├── main.tsx           # Entry point
│   │   └── index.css          # Tailwind + globals
│   ├── src-tauri/             # Tauri Rust backend
│   │   ├── src/
│   │   │   ├── main.rs        # Windows entry point
│   │   │   └── lib.rs         # Tauri setup + commands
│   │   ├── Cargo.toml
│   │   └── tauri.conf.json    # Tauri configuration
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── tailwind.config.js
│
├── backend/                   # Python FastAPI backend
│   ├── modforge/
│   │   ├── api/               # REST endpoint modules
│   │   │   ├── decompile.py   # POST /api/decompile
│   │   │   ├── workspace.py   # GET /api/workspaces/*
│   │   │   └── settings.py    # GET/PUT /api/settings
│   │   ├── decompiler/        # JAR processing pipeline
│   │   │   ├── pipeline.py    # Orchestrator
│   │   │   └── validator.py   # JAR validation + metadata
│   │   ├── workspace/         # Workspace utilities
│   │   ├── config.py          # Settings (env vars)
│   │   └── main.py            # FastAPI app factory
│   ├── tests/                 # pytest test suite
│   └── pyproject.toml
│
├── ai/                        # AI models and training
│   ├── texture_gen/           # Diffusion model
│   │   ├── model.py           # TinyUNet architecture
│   │   ├── scheduler.py       # DDPM noise scheduler
│   │   └── config.py          # Training configurations
│   ├── model_gen/             # JSON model generator
│   │   ├── schema.py          # Pydantic Minecraft schemas
│   │   └── generator.py       # Template-based generation
│   ├── inference/             # Inference server
│   │   └── server.py          # FastAPI app
│   ├── training/              # Training scripts
│   │   ├── train_texture.py   # Texture model training
│   │   └── texture_dataset.py # PyTorch dataset
│   ├── datasets/              # Dataset preparation
│   │   ├── prepare_textures.py
│   │   └── prepare_models.py
│   └── tests/
│
├── scripts/                   # Setup & utilities
│   ├── setup-dev.ps1          # Windows setup
│   ├── setup-dev.sh           # Linux/macOS setup
│   └── download-tools.py      # Download CFR, etc.
│
├── docs/                      # Documentation
├── tools/                     # External binaries (gitignored)
└── workspaces/                # Decompiled mod data (gitignored)
```

---

## IDE Setup

### VS Code (recommended)

Useful extensions:
- **Python** (ms-python.python) — IntelliSense, debugging
- **Ruff** (charliermarsh.ruff) — Python linting/formatting
- **ESLint** (dbaeumer.vscode-eslint) — TypeScript linting
- **Tailwind CSS IntelliSense** (bradlc.vscode-tailwindcss)
- **rust-analyzer** (rust-lang.rust-analyzer) — if editing Tauri code
- **Even Better TOML** (tamasfe.even-better-toml)

Workspace settings suggestion:
```json
{
  "python.defaultInterpreterPath": "./backend/.venv/bin/python",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

### PyCharm / IntelliJ

- Mark `backend/` and `ai/` as Python source roots
- Configure the Python interpreter to use the venv from each module
- Mark `app/src` as a JavaScript source root

---

## Hot Reloading

| Layer | Reload behavior |
|---|---|
| React components | Instant (Vite HMR) |
| CSS / Tailwind | Instant |
| Python backend | Auto-restart on save (uvicorn `--reload`) |
| Python AI server | Manual restart needed |
| Rust / Tauri | Full rebuild on change (~10-30s) |

---

## Debugging

### Backend (Python)

```bash
# Run with debug logging
cd backend
MODFORGE_LOG_LEVEL=DEBUG uvicorn modforge.main:app --reload --port 8420

# Or attach a debugger via VS Code launch.json:
# {
#   "type": "python",
#   "request": "launch",
#   "module": "uvicorn",
#   "args": ["modforge.main:app", "--reload", "--port", "8420"]
# }
```

### Frontend (React)

- DevTools open automatically in Tauri dev mode (see `lib.rs`)
- Use browser DevTools → Network tab to inspect API calls
- React DevTools extension works in the Tauri WebView

### AI Module

```bash
# Run inference with verbose output
cd ai
python -m inference.server --port 8421 2>&1 | tee ai-debug.log
```

---

## Common Tasks

### Add a new API endpoint

1. Create or edit a file in `backend/modforge/api/`
2. Add a router with `APIRouter(tags=["your_tag"])`
3. Register it in `backend/modforge/main.py`:
   ```python
   from modforge.api.your_module import router as your_router
   app.include_router(your_router, prefix="/api")
   ```
4. Add tests in `backend/tests/test_your_module.py`

### Add a new frontend page

1. Create `app/src/pages/YourPage.tsx`
2. Add a route in `app/src/App.tsx`
3. Add a nav link in `app/src/components/Sidebar.tsx`

### Add a new decompiler backend

See [Decompiler Plugins Guide](decompiler-plugins.md).

---

## Virtual Environments

The setup scripts install packages globally. For isolated development,
create venvs:

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# AI
cd ai
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```
