# ModForge Development Setup — Windows (PowerShell)
# Run: .\scripts\setup-dev.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== ModForge Development Setup ===" -ForegroundColor Cyan

# ── Check prerequisites ──────────────────────────────────────
function Test-Command($cmd) {
    $null = Get-Command $cmd -ErrorAction SilentlyContinue
    return $?
}

$missing = @()
if (-not (Test-Command "node"))   { $missing += "Node.js (https://nodejs.org)" }
if (-not (Test-Command "python")) { $missing += "Python 3.11+ (https://python.org)" }
if (-not (Test-Command "java"))   { $missing += "Java 8+ (https://adoptium.net)" }
if (-not (Test-Command "cargo"))  { $missing += "Rust (https://rustup.rs)" }

if ($missing.Count -gt 0) {
    Write-Host "`nMissing prerequisites:" -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host "`nInstall the above and re-run this script." -ForegroundColor Yellow
    exit 1
}

Write-Host "`n[1/5] Prerequisites OK" -ForegroundColor Green

# ── Download CFR decompiler ──────────────────────────────────
$cfrDir = Join-Path $PSScriptRoot "..\tools\cfr"
$cfrJar = Join-Path $cfrDir "cfr.jar"

if (-not (Test-Path $cfrJar)) {
    Write-Host "[2/5] Downloading CFR decompiler..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path $cfrDir | Out-Null
    $cfrUrl = "https://github.com/leibnitz27/cfr/releases/download/0.152/cfr-0.152.jar"
    Invoke-WebRequest -Uri $cfrUrl -OutFile $cfrJar
    Write-Host "  Downloaded to $cfrJar" -ForegroundColor Green
} else {
    Write-Host "[2/5] CFR already downloaded" -ForegroundColor Green
}

# ── Install frontend dependencies ────────────────────────────
Write-Host "[3/5] Installing frontend dependencies..." -ForegroundColor Cyan
Push-Location (Join-Path $PSScriptRoot "..\app")
npm install
Pop-Location
Write-Host "  Frontend deps installed" -ForegroundColor Green

# ── Install backend dependencies ─────────────────────────────
Write-Host "[4/5] Installing backend dependencies..." -ForegroundColor Cyan
Push-Location (Join-Path $PSScriptRoot "..\backend")
python -m pip install -e ".[dev]" --quiet
Pop-Location
Write-Host "  Backend deps installed" -ForegroundColor Green

# ── Install AI dependencies ──────────────────────────────────
Write-Host "[5/5] Installing AI dependencies..." -ForegroundColor Cyan
Push-Location (Join-Path $PSScriptRoot "..\ai")
python -m pip install -e ".[dev]" --quiet
Pop-Location
Write-Host "  AI deps installed" -ForegroundColor Green

# ── Create workspace directory ───────────────────────────────
$wsDir = Join-Path $PSScriptRoot "..\workspaces"
New-Item -ItemType Directory -Force -Path $wsDir | Out-Null

Write-Host "`n=== Setup Complete ===" -ForegroundColor Green
Write-Host @"

Next steps:
  1. Start the backend:
     cd backend
     python -m uvicorn modforge.main:app --reload --port 8420

  2. Start the AI inference server (optional):
     cd ai
     python -m inference.server --port 8421

  3. Start the desktop app:
     cd app
     npm run tauri dev

"@ -ForegroundColor White
