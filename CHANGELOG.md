# Changelog

All notable changes to ModForge are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2025-07-25

### Added

- **Desktop app** — Tauri 2 + React 18 + TypeScript + Tailwind CSS shell with
  five pages: Import, Workspace, Texture Generation, Model Generation, Settings.
- **Backend API** — FastAPI service (port 8420) with endpoints for JAR
  decompilation, workspace browsing, and settings management.
- **Decompile pipeline** — JAR validation, extraction, CFR decompilation, and
  JSON report generation. Pluggable architecture for alternative decompilers.
- **AI texture generation** — TinyUNet diffusion model (~500K params) with DDPM
  noise scheduler for 16×16 and 32×32 pixel-art textures.
- **AI model generation** — Template-based Minecraft block/item JSON model
  generator with Pydantic schema validation.
- **AI inference server** — FastAPI service (port 8421) for texture and model
  generation endpoints.
- **Training pipeline** — PyTorch training loop for the texture diffusion model
  with toy and full configuration presets.
- **Dataset preparation** — Scripts to prepare texture image datasets and
  model JSON datasets from Minecraft resource packs.
- **Setup scripts** — `setup-dev.ps1` (Windows) and `setup-dev.sh`
  (Linux/macOS) for one-command environment setup.
- **Tool downloader** — `download-tools.py` script to fetch CFR and other
  external decompiler tools.
- **Test suites** — 19 tests (10 backend, 9 AI) covering API endpoints,
  JAR validation, decompile pipeline, UNet architecture, DDPM scheduler,
  and model generation.
- **CI pipeline** — GitHub Actions workflow with backend lint/test,
  frontend lint/typecheck, and AI lint/test jobs.
- **Documentation** — Architecture overview, decompilation guide, AI training
  guide, hardware requirements, development guide, API reference,
  configuration reference, troubleshooting/FAQ, decompiler plugin guide,
  testing guide, contributing guidelines, and code of conduct.

[Unreleased]: https://github.com/mikedattolo/modalchemy/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mikedattolo/modalchemy/releases/tag/v0.1.0
