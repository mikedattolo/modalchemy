# ModForge Development Setup — Windows (PowerShell)
# Run: .\scripts\setup-dev.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== ModForge Development Setup ===" -ForegroundColor Cyan

# ── Check prerequisites ──────────────────────────────────────
function Test-Command($cmd) {
    $null = Get-Command $cmd -ErrorAction SilentlyContinue
    return $?
}

function Ensure-VenvPython($modulePath) {
    $venvDir = Join-Path $modulePath ".venv"
    $venvPython = Join-Path $venvDir "Scripts\python.exe"

    if (-not (Test-Path $venvPython)) {
        Write-Host "  Creating virtual environment in $venvDir" -ForegroundColor Cyan
        python -m venv $venvDir
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create virtual environment at $venvDir"
        }
    }

    & $venvPython -m pip install --upgrade pip setuptools wheel --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to bootstrap pip tooling in $venvDir"
    }

    return $venvPython
}

$missing = @()
if (-not (Test-Command "node"))   { $missing += "Node.js 20 LTS (https://nodejs.org)" }
if (-not (Test-Command "python")) { $missing += "Python 3.10+ (https://python.org)" }
if (-not (Test-Command "java"))   { $missing += "Java 8+ (https://adoptium.net)" }
if (-not (Test-Command "cargo"))  { $missing += "Rust (https://rustup.rs)" }

# Check for Visual Studio Build Tools (required for Tauri / Rust on Windows)
$vsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$hasBuildTools = $false
if (Test-Path $vsWhere) {
    $vsInstalls = & $vsWhere -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>$null
    if ($vsInstalls) { $hasBuildTools = $true }
}
if (-not $hasBuildTools) {
    # Fallback: check if cl.exe or link.exe are on PATH
    if (Test-Command "cl") { $hasBuildTools = $true }
}
if (-not $hasBuildTools) {
    $missing += "Visual Studio Build Tools with C++ workload (https://visualstudio.microsoft.com/visual-cpp-build-tools/)"
}

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
$backendPath = Join-Path $PSScriptRoot "..\backend"
$backendPython = Ensure-VenvPython $backendPath
Push-Location $backendPath
& $backendPython -m pip install -e ".[dev]" --quiet
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    throw "Failed to install backend dependencies (pip exit code $LASTEXITCODE)."
}
Pop-Location
Write-Host "  Backend deps installed" -ForegroundColor Green

# ── Install AI dependencies ──────────────────────────────────
Write-Host "[5/5] Installing AI dependencies..." -ForegroundColor Cyan
$aiPath = Join-Path $PSScriptRoot "..\ai"
$aiPython = Ensure-VenvPython $aiPath
Push-Location $aiPath
& $aiPython -m pip install -e ".[dev]" --quiet
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    throw "Failed to install AI dependencies (pip exit code $LASTEXITCODE)."
}

# If NVIDIA GPU is available, replace CPU torch wheel with CUDA-enabled wheel.
$hasNvidiaSmi = Test-Command "nvidia-smi"
if ($hasNvidiaSmi) {
    $torchCudaTag = if ($env:MODFORGE_TORCH_CUDA_TAG) { $env:MODFORGE_TORCH_CUDA_TAG } else { "cu124" }
    $torchIndexUrl = "https://download.pytorch.org/whl/$torchCudaTag"
    Write-Host "  NVIDIA GPU detected. Installing CUDA-enabled PyTorch ($torchCudaTag)..." -ForegroundColor Cyan
    & $aiPython -m pip install --upgrade torch torchvision torchaudio --index-url $torchIndexUrl
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        throw "Failed to install CUDA-enabled PyTorch from $torchIndexUrl (pip exit code $LASTEXITCODE)."
    }

    & $aiPython -c "import torch; import sys; sys.exit(0 if (torch.version.cuda is not None and torch.cuda.is_available()) else 1)"
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        throw "CUDA-enabled PyTorch verification failed (torch.cuda.is_available() == False)."
    }
} else {
    Write-Host "  NVIDIA GPU not detected; keeping default CPU PyTorch." -ForegroundColor Yellow
}
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
    .\.venv\Scripts\python -m uvicorn modforge.main:app --reload --port 8420

  2. Start the AI inference server (optional):
     cd ai
      .\.venv\Scripts\python -m inference.server --port 8421

  3. Start the desktop app:
     cd app
     npm run tauri dev

"@ -ForegroundColor White
