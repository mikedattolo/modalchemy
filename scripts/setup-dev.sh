#!/usr/bin/env bash
# ModForge Development Setup — Linux / macOS
# Run: bash scripts/setup-dev.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== ModForge Development Setup ==="

# ── Check prerequisites ──────────────────────────────────────
missing=()
command -v node    >/dev/null 2>&1 || missing+=("Node.js (https://nodejs.org)")
command -v python3 >/dev/null 2>&1 || missing+=("Python 3.11+ (https://python.org)")
command -v java    >/dev/null 2>&1 || missing+=("Java 8+ (https://adoptium.net)")
command -v cargo   >/dev/null 2>&1 || missing+=("Rust (https://rustup.rs)")

if [ ${#missing[@]} -gt 0 ]; then
    echo ""
    echo "Missing prerequisites:"
    for m in "${missing[@]}"; do
        echo "  - $m"
    done
    echo ""
    echo "Install the above and re-run this script."
    exit 1
fi

echo "[1/5] Prerequisites OK"

# ── Download CFR decompiler ──────────────────────────────────
CFR_DIR="$ROOT_DIR/tools/cfr"
CFR_JAR="$CFR_DIR/cfr.jar"

if [ ! -f "$CFR_JAR" ]; then
    echo "[2/5] Downloading CFR decompiler..."
    mkdir -p "$CFR_DIR"
    curl -fsSL "https://github.com/leibnitz27/cfr/releases/download/0.152/cfr-0.152.jar" -o "$CFR_JAR"
    echo "  Downloaded to $CFR_JAR"
else
    echo "[2/5] CFR already downloaded"
fi

# ── Install frontend dependencies ────────────────────────────
echo "[3/5] Installing frontend dependencies..."
cd "$ROOT_DIR/app"
npm install
echo "  Frontend deps installed"

# ── Install backend dependencies ─────────────────────────────
echo "[4/5] Installing backend dependencies..."
cd "$ROOT_DIR/backend"
python3 -m pip install -e ".[dev]" --quiet
echo "  Backend deps installed"

# ── Install AI dependencies ──────────────────────────────────
echo "[5/5] Installing AI dependencies..."
cd "$ROOT_DIR/ai"
python3 -m pip install -e ".[dev]" --quiet
echo "  AI deps installed"

# ── Create workspace directory ───────────────────────────────
mkdir -p "$ROOT_DIR/workspaces"

echo ""
echo "=== Setup Complete ==="
cat <<EOF

Next steps:
  1. Start the backend:
     cd backend
     uvicorn modforge.main:app --reload --port 8420

  2. Start the AI inference server (optional):
     cd ai
     python3 -m inference.server --port 8421

  3. Start the desktop app:
     cd app
     npm run tauri dev

EOF
