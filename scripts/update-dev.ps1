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

function Ensure-VenvPython($modulePath) {
    $venvDir = Join-Path $modulePath ".venv"
    $venvPython = Join-Path $venvDir "Scripts\python.exe"

    if (-not (Test-Path $venvPython)) {
        Write-Host "  Creating virtual environment in $venvDir" -ForegroundColor Cyan
        python -m venv $venvDir
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  Built-in venv creation failed; trying virtualenv fallback..." -ForegroundColor Yellow

            python -m pip install --user --upgrade virtualenv --quiet
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to install virtualenv fallback for $venvDir"
            }

            python -m virtualenv $venvDir
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to create virtual environment at $venvDir (venv and virtualenv both failed)."
            }
        }
    }

    & $venvPython -m pip install --upgrade pip setuptools wheel --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to bootstrap pip tooling in $venvDir"
    }

    return $venvPython
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
$backendPath = Join-Path $Root "backend"
$backendPython = Ensure-VenvPython $backendPath
Push-Location $backendPath
& $backendPython -m pip install -e ".[dev]" --quiet
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    throw "Failed to update backend dependencies (pip exit code $LASTEXITCODE)."
}
Pop-Location

Write-Host "[4/5] Updating AI dependencies..." -ForegroundColor Cyan
$aiPath = Join-Path $Root "ai"
$aiPython = Ensure-VenvPython $aiPath
Push-Location $aiPath
& $aiPython -m pip install -e ".[dev]" --quiet
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    throw "Failed to update AI dependencies (pip exit code $LASTEXITCODE)."
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

Write-Host "[5/5] Ensuring external tools are present..." -ForegroundColor Cyan
python (Join-Path $Root "scripts\download-tools.py")

Write-Host "`n=== Update Complete ===" -ForegroundColor Green
Write-Host "You can now run start.bat" -ForegroundColor White
