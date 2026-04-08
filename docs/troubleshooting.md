# Troubleshooting & FAQ

Common issues and how to fix them.

---

## Setup Issues

### `setup-dev.sh` fails with "missing prerequisites"

The setup script checks for `node`, `python3`, `java`, and `cargo`. Install
any missing tools:

| Tool | Install guide |
|---|---|
| Node.js 20 | https://nodejs.org — use the LTS installer |
| Python 3.11+ | https://python.org — or `brew install python@3.11` on macOS |
| Java 8+ | https://adoptium.net — download Temurin JDK |
| Rust | https://rustup.rs — run the installer |

After installing, **restart your terminal** so the PATH is updated, then run
the setup script again.

### `npm install` fails in `app/`

```
npm ERR! ERESOLVE could not resolve
```

Try deleting `node_modules` and the lock file, then reinstall:

```bash
cd app
rm -rf node_modules package-lock.json
npm install
```

If using Node 22+, some native Tauri dependencies may need `npm install --legacy-peer-deps`.

### `pip install -e ".[dev]"` fails for the AI module

```
setuptools will not proceed with this build
```

This happens if setuptools can't find the packages. The AI module uses
`[tool.setuptools.packages.find]` in `pyproject.toml` — make sure you're
running `pip install` from the `ai/` directory.

---

## Runtime Issues

### Backend won't start: "Address already in use"

Another process is using port 8420. Find and kill it:

```bash
# Linux / macOS
lsof -ti:8420 | xargs kill

# Windows
netstat -ano | findstr :8420
taskkill /PID <pid> /F
```

Or start on a different port:

```bash
uvicorn modforge.main:app --reload --port 8430
```

### "CFR jar not found" error during decompilation

The CFR decompiler needs to be downloaded first:

```bash
python scripts/download-tools.py
```

This downloads `cfr-0.152.jar` to `tools/cfr/cfr.jar`. If your network
blocks GitHub releases, download manually from
https://github.com/leibnitz27/cfr/releases and place the JAR at
`tools/cfr/cfr.jar`.

### "Java not found" error during decompilation

The decompiler needs Java at runtime. Verify Java is installed:

```bash
java -version
```

If Java is installed but not on PATH, set the full path in settings:

```bash
export MODFORGE_JAVA_PATH="/usr/lib/jvm/java-17-openjdk/bin/java"
```

Or update it in the app's Settings page.

### Decompilation times out (300s)

Very large mods (100+ MB) with thousands of class files may exceed the
default 300-second timeout. Current options:

1. Wait — the timeout is per-JAR, and the workspace is still partially created
2. Split the JAR manually (extract, remove unused packages, re-jar)

A configurable timeout is planned for a future release.

### Frontend shows "Could not load" or network errors

Make sure the backend is running on the expected port:

```bash
curl http://localhost:8420/health
# Should return: {"status":"ok","version":"0.1.0"}
```

If backend is on a different port, update the `BACKEND` constant in the
frontend page files.

---

## AI Issues

### AI server returns placeholder/random textures

This is expected if no trained model checkpoint is loaded. The default
behavior is to return procedurally generated placeholder textures. To get
real AI output:

1. Prepare a dataset (see [AI Training Guide](ai-training.md))
2. Train the model: `python -m training.train_texture --config toy`
3. Place the checkpoint in `ai/checkpoints/texture_gen/`
4. Restart the inference server

### CUDA out of memory during training

Reduce batch size:

```bash
python -m training.train_texture --config toy
```

The toy config uses batch size 8. You can also reduce it further by editing
`ai/texture_gen/config.py`.

### "No module named 'torch'" or "No module named 'ai'"

Make sure you installed the AI module's dependencies:

```bash
cd ai
pip install -e ".[dev]"
```

If using a virtual environment, make sure it's activated.

### Model generation returns simple templates

The model JSON generator currently uses template-based fallback rather than
AI. It selects `cube_all`, `cube_column`, `stairs`, `slab`, `item/generated`,
or `item/handheld` based on keywords in your prompt. The full AI-powered
generation using Outlines + LLM is planned.

---

## Tauri / Desktop Issues

### Tauri won't build: "WebView2 not found"

On Windows 10, you may need to install WebView2 manually:
https://developer.microsoft.com/en-us/microsoft-edge/webview2/

Windows 11 includes WebView2 by default.

### Tauri build fails on Linux

Install the required system dependencies:

```bash
# Ubuntu / Debian
sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget \
  libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev
```

See https://v2.tauri.app/start/prerequisites/ for your distro.

### DevTools don't open

DevTools only open in debug builds (default for `npm run tauri dev`).
If running a release build, DevTools are disabled.

---

## FAQ

### Can I decompile any JAR, not just Forge mods?

The validator requires `.class` files, but does not strictly require Forge
metadata. Non-Forge JARs will decompile with `mod_loader: "unknown"` and
`minecraft_version: "unknown"`.

### What Minecraft versions are supported?

Currently optimized for **1.6.4** and **1.7.10** era Forge mods (FML
package structure: `cpw.mods.fml.*`). The decompiler itself (CFR) handles
Java 6–17 bytecode, so newer mods may decompile but Forge metadata
detection may not work perfectly.

### Is an internet connection required?

Only for initial setup (downloading dependencies and CFR). After that,
everything runs fully offline.

### Can I use this on Linux/macOS?

The backend and AI modules work on any platform with Python 3.11+. The
Tauri desktop app builds on Linux and macOS but is primarily tested on
Windows 11. See [Hardware Requirements](hardware-requirements.md) for
platform support status.

### Where are decompiled workspaces stored?

By default, in the `workspaces/` directory at the repo root. Change this
with the `MODFORGE_WORKSPACE_DIR` environment variable or via the Settings page.

### How do I export a decompiled workspace?

Currently, workspaces are plain directories on disk. Navigate to the
workspace directory and copy/zip the contents. A one-click export feature
in the UI is planned.
