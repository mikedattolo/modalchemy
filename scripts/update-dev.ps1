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

function Install-AiDependencies($pythonExe) {
    # Try the normal editable install first, then progressively safer fallbacks.
    $attempts = @(
        @{ Name = "editable dev"; Args = @("-e", ".[dev]", "--quiet") },
        @{ Name = "editable dev no cache"; Args = @("--no-cache-dir", "-e", ".[dev]") },
        @{ Name = "staged deps no cache"; Args = @("--no-cache-dir", "torch", "torchvision", "diffusers", "transformers", "accelerate", "safetensors", "Pillow", "fastapi", "python-multipart", "uvicorn[standard]", "pydantic", "outlines", "pytest", "ruff") }
    )

    foreach ($attempt in $attempts) {
        Write-Host "  AI dependency attempt: $($attempt.Name)" -ForegroundColor DarkCyan
        & $pythonExe -m pip install @($attempt.Args)
        if ($LASTEXITCODE -eq 0) {
            if ($attempt.Name -eq "staged deps no cache") {
                & $pythonExe -m pip install --no-cache-dir -e . --no-deps
                if ($LASTEXITCODE -ne 0) {
                    continue
                }
            }

            return $true
        }

        Write-Host "    attempt failed (pip exit code $LASTEXITCODE)" -ForegroundColor Yellow
    }

    return $false
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

$pythonVersionRaw = (& python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if ($LASTEXITCODE -eq 0) {
    $parts = $pythonVersionRaw.Trim().Split('.')
    if ($parts.Length -ge 2) {
        $pyMajor = [int]$parts[0]
        $pyMinor = [int]$parts[1]
        if ($pyMajor -ne 3 -or $pyMinor -lt 10 -or $pyMinor -gt 12) {
            Write-Host "[ERROR] Python 3.10, 3.11, or 3.12 is required for stable AI dependency installs (detected $pythonVersionRaw)." -ForegroundColor Red
            exit 1
        }
    }
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
if (-not (Install-AiDependencies $aiPython)) {
    Pop-Location
    throw "Failed to update AI dependencies after multiple attempts. Try Python 3.11 and re-run update."
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
