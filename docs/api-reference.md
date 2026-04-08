# API Reference

ModForge exposes two HTTP APIs — the **Backend** (port 8420) and the **AI
Inference Server** (port 8421). Both are FastAPI applications with interactive
docs at `/docs` when running.

---

## Backend API (port 8420)

Base URL: `http://localhost:8420`

### Health

#### `GET /health`

Check that the backend is running.

**Response** `200`
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

### Decompile

#### `POST /api/decompile`

Upload a Forge mod JAR for decompilation.

**Request**
- Content-Type: `multipart/form-data`
- Body: `file` — the `.jar` file (max 200 MB)

**Response** `200` — `DecompileReport`
```json
{
  "workspace_id": "mymod_a1b2c3d4",
  "jar_name": "mymod-1.0.jar",
  "mod_loader": "forge",
  "minecraft_version": "1.7.10",
  "source_files": 42,
  "resource_files": 128,
  "errors": [],
  "created_at": "2026-04-08T12:00:00+00:00"
}
```

**Errors**

| Code | Condition |
|---|---|
| `400` | File is not a `.jar`, not a valid ZIP, or contains no `.class` files |
| `413` | JAR exceeds `MODFORGE_MAX_JAR_SIZE_MB` (default 200) |

---

### Workspaces

#### `GET /api/workspaces`

List all decompiled workspaces.

**Response** `200`
```json
[
  {
    "id": "mymod_a1b2c3d4",
    "jar_name": "mymod-1.0.jar",
    "created_at": "2026-04-08T12:00:00+00:00"
  }
]
```

Returns an empty array if no workspaces exist yet.

---

#### `GET /api/workspaces/{workspace_id}/tree`

Get the recursive file tree for a workspace.

**Path parameters**

| Parameter | Type | Description |
|---|---|---|
| `workspace_id` | string | Workspace directory name |

**Response** `200`
```json
{
  "name": "mymod_a1b2c3d4",
  "path": ".",
  "is_dir": true,
  "children": [
    {
      "name": "sources",
      "path": "sources",
      "is_dir": true,
      "children": [
        {
          "name": "MyMod.java",
          "path": "sources/com/example/MyMod.java",
          "is_dir": false
        }
      ]
    }
  ]
}
```

**Errors**

| Code | Condition |
|---|---|
| `403` | Invalid workspace ID (path traversal attempt) |
| `404` | Workspace not found |

---

#### `GET /api/workspaces/{workspace_id}/file?path={relative_path}`

Read the text content of a file inside a workspace.

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `path` | string | Relative path inside the workspace (e.g., `sources/com/example/MyMod.java`) |

**Response** `200` — `text/plain`

The raw file content as UTF-8 text.

**Errors**

| Code | Condition |
|---|---|
| `403` | Path traversal detected |
| `404` | File or workspace not found |

---

### Settings

#### `GET /api/settings`

Read current application settings.

**Response** `200`
```json
{
  "backend_port": 8420,
  "ai_port": 8421,
  "workspace_dir": "./workspaces",
  "decompiler": "cfr",
  "java_path": "java",
  "theme": "dark",
  "auto_decompile": true
}
```

---

#### `PUT /api/settings`

Update application settings. All fields are optional — only provided fields
are updated.

**Request** `application/json`
```json
{
  "decompiler": "fernflower",
  "auto_decompile": false
}
```

**Response** `200` — the full updated settings object (same shape as GET).

---

## AI Inference API (port 8421)

Base URL: `http://localhost:8421`

### Health

#### `GET /health`

**Response** `200`
```json
{
  "status": "ok",
  "version": "0.1.0",
  "gpu_available": false
}
```

---

### Texture Generation

#### `POST /api/textures/generate`

Generate a pixel-art texture from a text prompt.

**Request** `application/json`
```json
{
  "prompt": "cobblestone block, mossy, dark fantasy",
  "size": 16,
  "mode": "generate"
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `prompt` | string | *(required)* | Text description of the desired texture |
| `size` | int | 16 | Output size in pixels (16 or 32) |
| `mode` | string | "generate" | Generation mode ("generate" or "remix") |

**Response** `200`
```json
{
  "id": "a1b2c3d4e5f6",
  "prompt": "cobblestone block, mossy, dark fantasy",
  "image_base64": "<base64-encoded PNG>",
  "size": 16
}
```

The `image_base64` field contains a base64-encoded PNG image. Decode it
and display with `data:image/png;base64,<value>`.

---

#### `POST /api/textures/remix`

Remix an existing texture with an optional prompt.

**Request** `multipart/form-data`

| Field | Type | Description |
|---|---|---|
| `image` | file | Source PNG texture to remix |
| `prompt` | string | Optional guidance for the remix |
| `size` | string | Target size ("16" or "32") |

**Response** `200` — same shape as `/api/textures/generate`.

---

### Model Generation

#### `POST /api/models/generate`

Generate a Minecraft block/item JSON model from a text prompt.

**Request** `application/json`
```json
{
  "prompt": "wooden barrel block with iron bands",
  "model_type": "block",
  "mode": "generate"
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `prompt` | string | *(required)* | Description of the desired model |
| `model_type` | string | "block" | Type of model: "block" or "item" |
| `mode` | string | "generate" | Generation mode: "generate" or "remix" |

**Response** `200`
```json
{
  "id": "f6e5d4c3b2a1",
  "prompt": "wooden barrel block with iron bands",
  "model_json": "{\n  \"parent\": \"block/cube_column\",\n  ...}",
  "model_type": "block"
}
```

The `model_json` field is a pretty-printed JSON string conforming to
Minecraft's model format. Parse it with `JSON.parse()` on the client.

---

## Error Format

All error responses use FastAPI's standard format:

```json
{
  "detail": "Human-readable error message"
}
```

For validation errors (422):
```json
{
  "detail": [
    {
      "loc": ["body", "prompt"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## CORS

Both servers allow requests from:
- `http://localhost:1420` (Tauri dev server)
- `http://localhost:5173` (Vite dev server)
- `https://tauri.localhost` (Tauri production)

---

## Interactive Docs

When running locally, visit:
- Backend: http://localhost:8420/docs (Swagger UI)
- AI server: http://localhost:8421/docs (Swagger UI)

These are auto-generated from the FastAPI route definitions and are always
up-to-date with the code.
