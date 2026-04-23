# ModForge Development Update — Windows (PowerShell)
# Run: .\scripts\update-dev.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== ModForge Update ===" -ForegroundColor Cyan
$Root = Join-Path $PSScriptRoot ".."
Set-Location $Root

function Test-Command($cmd) {
    $null = Get-Command $cmd -ErrorAction SilentlyContinue
    return $?
}

if (-not (Test-Command "git")) {
    Write-Host "[ERROR] git is required for update." -ForegroundColor Red
    exit 1
}
if (-not (Test-Command "python")) {
    Write-Host "[ERROR] python is required for update." -ForegroundColor Red
    exit 1
}
if (-not (Test-Command "npm")) {
    Write-Host "[ERROR] npm is required for update." -ForegroundColor Red
    exit 1
}

$repoOk = Test-Path (Join-Path $Root ".git")
if (-not $repoOk) {
    Write-Host "[ERROR] This folder is not a git repository root." -ForegroundColor Red
    exit 1
}

$status = git status --porcelain
if ($status) {
    Write-Host "[!] Working tree has local changes. Skipping git pull to avoid conflicts." -ForegroundColor Yellow
} else {
    Write-Host "[1/5] Pulling latest changes..." -ForegroundColor Cyan
    git pull --ff-only
}

Write-Host "[2/5] Updating frontend dependencies..." -ForegroundColor Cyan
Push-Location (Join-Path $Root "app")
npm install
Pop-Location

Write-Host "[3/5] Updating backend dependencies..." -ForegroundColor Cyan
Push-Location (Join-Path $Root "backend")
python -m pip install -e ".[dev]" --quiet
Pop-Location

Write-Host "[4/5] Updating AI dependencies..." -ForegroundColor Cyan
Push-Location (Join-Path $Root "ai")
python -m pip install -e ".[dev]" --quiet

# If NVIDIA GPU is available, replace CPU torch wheel with CUDA-enabled wheel.
$hasNvidiaSmi = Test-Command "nvidia-smi"
if ($hasNvidiaSmi) {
    $torchCudaTag = if ($env:MODFORGE_TORCH_CUDA_TAG) { $env:MODFORGE_TORCH_CUDA_TAG } else { "cu124" }
    $torchIndexUrl = "https://download.pytorch.org/whl/$torchCudaTag"
    Write-Host "  NVIDIA GPU detected. Installing CUDA-enabled PyTorch ($torchCudaTag)..." -ForegroundColor Cyan
    python -m pip install --upgrade --force-reinstall torch torchvision torchaudio --index-url $torchIndexUrl
} else {
    Write-Host "  NVIDIA GPU not detected; keeping default CPU PyTorch." -ForegroundColor Yellow
}
Pop-Location

Write-Host "[5/5] Ensuring external tools are present..." -ForegroundColor Cyan
python (Join-Path $Root "scripts\download-tools.py")

Write-Host "`n=== Update Complete ===" -ForegroundColor Green
Write-Host "You can now run start.bat" -ForegroundColor White
