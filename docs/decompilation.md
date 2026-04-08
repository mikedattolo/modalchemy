# Decompilation Pipeline

## Overview

The decompilation pipeline takes a Minecraft Forge mod JAR file and produces:

1. **Decompiled Java source** — best-effort `.java` files from `.class` bytecode
2. **Extracted resources** — textures (PNG), sounds (OGG), lang files, configs
3. **Structured workspace** — clean folder layout ready for browsing/export
4. **Report** — JSON file summarizing the decompilation results

## Pipeline Steps

### 1. Validation

The pipeline first validates the uploaded JAR:

- **Is it a ZIP?** Uses Python's `zipfile.is_zipfile()`.
- **Contains .class files?** A valid mod JAR must have compiled Java classes.
- **Forge metadata?** Checks for:
  - `mcmod.info` — standard Forge mod metadata file
  - `cpw/mods/fml/` — FML package structure (1.6.4 / 1.7.10 era)
  - `net/minecraftforge/` — Forge classes

The validator extracts:
- Mod ID, mod name, Minecraft version
- Mod loader type (Forge vs unknown)

### 2. Extraction

The JAR is extracted into a workspace directory:

```
workspaces/{jar_name}_{hash}/
├── classes/          # Raw .class files (input to decompiler)
├── sources/          # Decompiled .java files (output)
├── resources/        # All non-class files from the JAR
│   ├── assets/       # Textures, sounds, lang
│   ├── mcmod.info
│   └── ...
├── logs/
│   └── decompile.log
└── report.json
```

Files are extracted preserving their directory structure. `META-INF` signature
files (`.SF`, `.RSA`, `.DSA`) are skipped.

### 3. Decompilation

The default decompiler is **CFR** (Benoit Bhatt's decompiler). It's invoked as:

```
java -jar tools/cfr/cfr.jar workspaces/{id}/classes --outputdir workspaces/{id}/sources
```

CFR handles Java 6/7/8 bytecode well, which covers all 1.6.4 and 1.7.10 mods.

#### Pluggable Decompilers

The decompiler is selected via settings. Currently supported:

| Decompiler | Status | Notes |
|---|---|---|
| **CFR** | Implemented | Default. Best for MC mods. |
| FernFlower | Planned | Widely used (IntelliJ uses it). |
| Procyon | Planned | Good for complex generics. |

To add a new decompiler, implement a new method in `pipeline.py` following
the `_run_cfr()` pattern.

### 4. Report Generation

After decompilation, a `report.json` is saved:

```json
{
  "workspace_id": "mymod_a1b2c3d4",
  "jar_name": "mymod-1.0.jar",
  "mod_loader": "forge",
  "minecraft_version": "1.7.10",
  "source_files": 42,
  "resource_files": 128,
  "errors": [],
  "created_at": "2026-04-08T12:00:00Z"
}
```

## Error Handling

- If CFR is not downloaded, the pipeline still extracts resources but reports
  0 source files and logs the error.
- If Java is not installed, a clear error is returned.
- Individual class decompilation failures are captured in the CFR log, not
  as pipeline errors (CFR handles these gracefully).
- A 300-second timeout prevents runaway decompilation.

## Size Limits

- Maximum JAR size: 200 MB (configurable via `MODFORGE_MAX_JAR_SIZE_MB`)
- The upload endpoint streams chunks to avoid loading the entire file in memory.

## API Reference

### `POST /api/decompile`

Upload a `.jar` file as multipart form data.

**Request:** `Content-Type: multipart/form-data` with field `file`.

**Response:**
```json
{
  "workspace_id": "string",
  "jar_name": "string",
  "mod_loader": "string",
  "minecraft_version": "string",
  "source_files": 0,
  "resource_files": 0,
  "errors": [],
  "created_at": "string"
}
```

**Error codes:**
- `400` — Not a JAR, no class files
- `413` — JAR exceeds size limit
