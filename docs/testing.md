# Testing Guide

How to run tests, add new tests, and understand the test architecture.

---

## Quick Start

```bash
# Backend tests (10 tests)
cd backend
pip install -e ".[dev]"
pytest -v

# AI tests (9 tests)
cd ai
pip install -e ".[dev]"
pytest -v

# Run everything from the root
cd backend && pytest -v && cd ../ai && pytest -v && cd ..
```

---

## Test Suites

### Backend (`backend/tests/`)

| File | Tests | What it covers |
|---|---|---|
| `test_api.py` | 4 | FastAPI endpoint integration (health, decompile, workspaces, settings) |
| `test_validator.py` | 3 | JAR validation (valid JAR, not-a-zip, no-classes) |
| `test_pipeline.py` | 3 | End-to-end decompilation pipeline |

**Fixtures** are in `conftest.py`:
- `sample_jar` — creates a temporary JAR with a valid `.class` file
- `pipeline` — a configured `DecompilePipeline` with a temp workspace
- `client` — FastAPI `TestClient` for HTTP-level tests

### AI (`ai/tests/`)

| File | Tests | What it covers |
|---|---|---|
| `test_texture_gen.py` | 5 | TinyUNet forward pass, DDPM scheduler, training step, config |
| `test_model_gen.py` | 4 | JSON model schema, block/item generation, templates |

---

## Running Subsets

```bash
# Run a single test file
pytest tests/test_api.py -v

# Run a single test by name
pytest -k "test_health" -v

# Run tests matching a pattern
pytest -k "validator" -v

# Stop on first failure
pytest -x

# Show print output
pytest -s

# With coverage
pytest --cov=modforge --cov-report=term-missing
```

---

## Writing New Tests

### Backend API Tests

Use the FastAPI `TestClient` from the `client` fixture:

```python
def test_new_endpoint(client):
    response = client.get("/api/new-endpoint")
    assert response.status_code == 200
    data = response.json()
    assert "expected_key" in data
```

For endpoints that hit the filesystem, use `tmp_path` and monkeypatch:

```python
def test_decompile_with_workspace(client, tmp_path, monkeypatch, sample_jar):
    monkeypatch.setattr("modforge.config.settings.workspace_dir", str(tmp_path))
    # ...
```

### AI Tests

AI tests use small configs to stay fast:

```python
from texture_gen.config import TextureGenConfig

def test_my_feature():
    config = TextureGenConfig(
        base_dim=16,
        dim_mults=(1, 2),
        num_timesteps=10,
        batch_size=2,
        num_epochs=1,
        img_size=16,
    )
    # Use config to create models/run inference
```

Keep AI tests CPU-only. Use small dimensions (`base_dim=16`, `img_size=16`)
and few timesteps (`num_timesteps=10`) so tests complete in seconds.

---

## Test Architecture

```
backend/tests/
├── conftest.py          # Shared fixtures (client, sample_jar, pipeline)
├── test_api.py          # HTTP integration tests
├── test_validator.py    # Unit tests for JAR validation
└── test_pipeline.py     # Integration tests for decompile pipeline

ai/tests/
├── test_texture_gen.py  # Unit tests for diffusion model + scheduler
└── test_model_gen.py    # Unit tests for JSON model generation
```

### Fixture Hierarchy

```
conftest.py
  ├── sample_jar (session)     → creates a temp JAR once per session
  ├── pipeline (function)      → fresh pipeline per test
  └── client (session)         → FastAPI TestClient, shared
```

---

## CI Integration

Tests run automatically on every push and PR via GitHub Actions
(`.github/workflows/ci.yml`):

- **backend-lint**: `ruff check backend/`
- **backend-test**: `pytest` in `backend/`
- **ai-lint**: `ruff check ai/`
- **ai-test**: `pytest` in `ai/`
- **frontend-lint**: `eslint` + `tsc --noEmit` in `app/`

All jobs must pass for a PR to be merged.

---

## What's Not Tested (Yet)

- **Frontend**: No React component tests yet. Planned: Vitest + Testing Library.
- **Tauri Rust**: No Rust unit tests yet. Planned: `cargo test` for Tauri commands.
- **E2E**: No end-to-end tests yet. Planned: Playwright or similar for the full desktop flow.
- **AI integration**: Inference server endpoints are not tested (would require model fixtures).

These are tracked as future improvements.
