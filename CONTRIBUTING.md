# Contributing to ModForge

Thank you for your interest in contributing to ModForge! This guide covers
everything you need to get started.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Branch Naming](#branch-naming)
- [Commit Conventions](#commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Code Style](#code-style)
- [Where to Contribute](#where-to-contribute)
- [Reporting Issues](#reporting-issues)

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
By participating, you agree to uphold this code. Report unacceptable behavior
via the channels listed in that document.

---

## Getting Started

### Prerequisites

| Tool | Version | Check with |
|---|---|---|
| Node.js | 20 LTS+ | `node --version` |
| Rust | 1.75+ | `rustc --version` |
| Python | 3.11+ | `python --version` |
| Java | 8+ | `java -version` |

### First-time setup

```bash
# Clone your fork
git clone https://github.com/<your-user>/modalchemy.git
cd modalchemy

# Windows
.\scripts\setup-dev.ps1

# Linux / macOS
bash scripts/setup-dev.sh
```

The setup script installs all dependencies and downloads the CFR decompiler.
See the [Development Guide](docs/development.md) for running each service.

---

## Development Workflow

1. **Pick or create an issue** — check the issue tracker for
   `good first issue` or `help wanted` labels.
2. **Create a branch** from `main` (see naming conventions below).
3. **Make your changes** — keep commits focused and atomic.
4. **Run tests locally** before pushing:
   ```bash
   # Backend
   cd backend && pytest

   # AI module
   cd ai && pytest

   # Frontend
   cd app && npm run lint && npm run typecheck
   ```
5. **Push and open a PR** against `main`.
6. **Address review feedback** — CI must pass before merge.

---

## Branch Naming

Use descriptive prefixes:

| Prefix | Purpose | Example |
|---|---|---|
| `feat/` | New feature | `feat/add-fernflower-decompiler` |
| `fix/` | Bug fix | `fix/jar-extraction-unicode` |
| `docs/` | Documentation only | `docs/api-reference-update` |
| `refactor/` | Code refactor (no behavior change) | `refactor/pipeline-cleanup` |
| `test/` | Test additions | `test/workspace-api-integration` |
| `ci/` | CI/CD changes | `ci/add-windows-runner` |

---

## Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

### Types

| Type | When |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no logic change |
| `refactor` | Code change with no feature/fix |
| `test` | Adding or fixing tests |
| `ci` | CI/CD changes |
| `chore` | Build scripts, deps, tooling |

### Scopes

`app`, `backend`, `ai`, `docs`, `ci`, `scripts`

### Examples

```
feat(backend): add FernFlower decompiler support
fix(app): prevent crash on empty workspace tree
docs(ai): expand training guide with QLoRA section
test(backend): add integration tests for workspace export
```

---

## Pull Request Process

1. **Fill out the PR template** — describe what changed, why, and how to test.
2. **Keep PRs focused** — one feature or fix per PR. Split large changes.
3. **CI must pass** — lint, type-check, and all tests green.
4. **One approval required** — a maintainer will review. Address comments in
   follow-up commits, then squash on merge.
5. **No force-pushes** to shared branches.

### PR size guidelines

| Size | Lines changed | Expectation |
|---|---|---|
| Small | < 100 | Quick review |
| Medium | 100–400 | Standard review |
| Large | 400+ | Consider splitting |

---

## Code Style

### Python (backend + AI)

- Formatter: **Ruff** (`ruff format`)
- Linter: **Ruff** (`ruff check`)
- Line length: 99
- Lint rules: E, F, I, N, W, UP, B, SIM
- Type hints: use on public functions; `from __future__ import annotations`
- Tests: pytest

```bash
# Auto-format
cd backend && ruff format . && ruff check --fix .
cd ai && ruff format . && ruff check --fix .
```

### TypeScript / React (frontend)

- Linter: **ESLint** with `@typescript-eslint`
- Type-check: `tsc --noEmit`
- Styling: **Tailwind CSS** utility classes (no CSS modules)
- Components: functional components with hooks
- Imports: absolute via `@/` alias

```bash
cd app && npm run lint && npm run typecheck
```

### Rust (Tauri shell)

- Formatter: `cargo fmt`
- Linter: `cargo clippy`
- The Rust layer is intentionally minimal; most logic lives in Python.

---

## Where to Contribute

### Good areas for first contributions

- Add missing decompiler backends (FernFlower, Procyon)
- Improve workspace file viewer (syntax highlighting, search)
- Add more model JSON templates for common block types
- Write integration tests for the decompile pipeline
- Improve error messages and UI feedback
- Documentation improvements

### Areas needing expertise

- Training pipeline optimization (GPU, mixed precision)
- Outlines + LLM integration for structured model generation
- Tauri plugin development for native dialogs
- CI/CD for building distributable Windows `.msi` packages

---

## Reporting Issues

### Bug reports

Include:
- OS and version
- Python / Node / Java / Rust versions
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs (check `workspaces/*/logs/`)

### Feature requests

- Describe the use case, not just the solution
- Check existing issues for duplicates

### Security vulnerabilities

**Do not open public issues.** See [SECURITY.md](SECURITY.md) for
responsible disclosure instructions.
