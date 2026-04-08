# Configuration Reference

All ModForge configuration options in one place.

---

## Backend Environment Variables

The backend reads environment variables prefixed with `MODFORGE_`. Set them
in your shell, a `.env` file (not committed), or your IDE run configuration.

| Variable | Type | Default | Description |
|---|---|---|---|
| `MODFORGE_WORKSPACE_DIR` | path | `./workspaces` | Directory for decompiled mod workspaces |
| `MODFORGE_TOOLS_DIR` | path | `./tools` | Directory containing external tools (CFR, etc.) |
| `MODFORGE_DECOMPILER` | string | `cfr` | Decompiler engine: `cfr`, `fernflower`, or `procyon` |
| `MODFORGE_JAVA_PATH` | string | `java` | Path to Java executable |
| `MODFORGE_CFR_JAR` | string | `cfr-0.152.jar` | CFR jar filename inside `tools/cfr/` |
| `MODFORGE_HOST` | string | `127.0.0.1` | Backend bind address |
| `MODFORGE_PORT` | int | `8420` | Backend port |
| `MODFORGE_AI_PORT` | int | `8421` | AI inference server port (for UI reference) |
| `MODFORGE_AUTO_DECOMPILE` | bool | `true` | Auto-decompile after JAR extraction |
| `MODFORGE_MAX_JAR_SIZE_MB` | int | `200` | Maximum upload JAR size in megabytes |

### Example `.env` file

```env
MODFORGE_WORKSPACE_DIR=/mnt/data/modforge-workspaces
MODFORGE_JAVA_PATH=/usr/lib/jvm/java-17-openjdk/bin/java
MODFORGE_MAX_JAR_SIZE_MB=500
MODFORGE_DECOMPILER=cfr
```

---

## AI Inference Server

The AI inference server is configured via command-line arguments:

```bash
python -m inference.server --host 127.0.0.1 --port 8421
```

| Argument | Default | Description |
|---|---|---|
| `--host` | `127.0.0.1` | Bind address |
| `--port` | `8421` | Server port |

---

## Training Configuration

Training presets are defined in `ai/texture_gen/config.py`:

### Toy Config (for testing)

```python
TextureGenConfig(
    base_dim=32,
    dim_mults=(1, 2),
    num_timesteps=100,
    batch_size=8,
    num_epochs=5,
    img_size=16,
)
```

### Full Config (for production)

```python
TextureGenConfig(
    base_dim=64,
    dim_mults=(1, 2, 4),
    num_timesteps=1000,
    batch_size=32,
    num_epochs=100,
    img_size=32,
)
```

### All Training Parameters

| Parameter | Type | Description |
|---|---|---|
| `img_channels` | int | Image color channels (3 = RGB) |
| `base_dim` | int | Base UNet channel width |
| `dim_mults` | tuple[int] | Channel multipliers per resolution level |
| `text_emb_dim` | int | Text conditioning embedding dimension |
| `num_timesteps` | int | Diffusion schedule length |
| `beta_start` | float | Starting noise level |
| `beta_end` | float | Ending noise level |
| `batch_size` | int | Training batch size |
| `learning_rate` | float | AdamW learning rate |
| `num_epochs` | int | Number of training passes |
| `img_size` | int | Training image resolution (16 or 32) |
| `checkpoint_dir` | str | Where to save model checkpoints |
| `dataset_dir` | str | Path to prepared training images |

Override via CLI:

```bash
python -m training.train_texture --config full --epochs 200 --dataset /path/to/data
```

---

## Tauri Configuration

The Tauri desktop shell is configured in `app/src-tauri/tauri.conf.json`:

| Setting | Value | Notes |
|---|---|---|
| `productName` | "ModForge" | Window title and executable name |
| `identifier` | "com.modforge.app" | Unique app ID |
| `windows[0].width` | 1280 | Default window width |
| `windows[0].height` | 820 | Default window height |
| `build.devUrl` | "http://localhost:1420" | Vite dev server URL |
| `plugins.fs.scope` | `["**"]` | File system access scope |

---

## Frontend Constants

API base URLs are set as constants in the page components:

| Constant | Default | Used in |
|---|---|---|
| `BACKEND` | `http://localhost:8420` | ImportPage, WorkspacePage, SettingsPage |
| `AI_BACKEND` | `http://localhost:8421` | TextureGenPage, ModelGenPage |

To change these, update the constants at the top of the respective page
files in `app/src/pages/`. A future improvement will centralize these into
an environment-based config.

---

## Settings API

Runtime settings can also be changed via the Settings page in the app or
the `PUT /api/settings` endpoint. These are currently stored in-memory and
reset on backend restart. Persistence is planned for a future release.

See [API Reference — Settings](api-reference.md#settings) for the full
request/response schema.
