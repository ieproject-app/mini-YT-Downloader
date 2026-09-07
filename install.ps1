# =====================================================================
#  Mini YouTube Downloader - Online Installer (Windows)
#  Usage (PowerShell):
#      irm https://raw.githubusercontent.com/ieproject-app/mini-YT-Downloader/main/install.ps1 | iex
#  After install, run the app from any terminal:   miniyt
# =====================================================================

$ErrorActionPreference = "Stop"

# PowerShell 5.1 defaults to TLS 1.0/1.1 which GitHub rejects
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

$Repo     = "https://github.com/ieproject-app/mini-YT-Downloader"
$ZipUrl   = "$Repo/archive/refs/heads/main.zip"
$InstallRoot = Join-Path $env:LOCALAPPDATA "MiniYT"
$AppDir   = Join-Path $InstallRoot "app"
$VenvDir  = Join-Path $InstallRoot "venv"
$ShimDir  = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
$ShimPath = Join-Path $ShimDir "miniyt.cmd"

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  MINI YOUTUBE DOWNLOADER - ONLINE INSTALLER" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Python check ──────────────────────────────────────────────────
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "[X] Python was not found on this computer." -ForegroundColor Red
    Write-Host "    Install Python 3.9+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "    (check 'Add Python to PATH' during install), then re-run this installer." -ForegroundColor Yellow
    exit 1
}
$pyVer = & python --version 2>&1
Write-Host "[1/5] Python found: $pyVer" -ForegroundColor Green

# ── 2. Download source ───────────────────────────────────────────────
Write-Host "[2/5] Downloading app from GitHub..." -ForegroundColor Cyan
$TempZip = Join-Path $env:TEMP "miniyt_download.zip"
$TempDir = Join-Path $env:TEMP "miniyt_extract"
Invoke-WebRequest -Uri $ZipUrl -OutFile $TempZip -UseBasicParsing
if (Test-Path $TempDir) { Remove-Item $TempDir -Recurse -Force }
Expand-Archive -Path $TempZip -DestinationPath $TempDir -Force
Remove-Item $TempZip -Force
$Extracted = Get-ChildItem $TempDir -Directory | Select-Object -First 1

# ── 3. Install to %LOCALAPPDATA%\MiniYT\app ─────────────────────────
Write-Host "[3/5] Installing to $AppDir ..." -ForegroundColor Cyan
if (Test-Path $AppDir) { Remove-Item $AppDir -Recurse -Force }
New-Item -ItemType Directory -Path $AppDir -Force | Out-Null
Copy-Item -Path (Join-Path $Extracted.FullName "*") -Destination $AppDir -Recurse -Force
Remove-Item $TempDir -Recurse -Force

# Mark as installed -> runtime data goes to %LOCALAPPDATA%\MiniYT\data
New-Item -ItemType File -Path (Join-Path $AppDir "_engine\installed.flag") -Force | Out-Null

# ── 4. Python environment + dependencies ────────────────────────────
Write-Host "[4/5] Setting up Python environment (first install may take a few minutes)..." -ForegroundColor Cyan
if (-not (Test-Path $VenvDir)) {
    & python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { Write-Host "[X] Failed to create Python environment." -ForegroundColor Red; exit 1 }
}
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -r (Join-Path $AppDir "requirements.txt") --quiet
if ($LASTEXITCODE -ne 0) { Write-Host "[X] Failed to install Python dependencies." -ForegroundColor Red; exit 1 }

# ── 5. Register 'miniyt' command (PATH) ─────────────────────────────
Write-Host "[5/5] Registering the 'miniyt' command..." -ForegroundColor Cyan
if (-not (Test-Path $ShimDir)) { New-Item -ItemType Directory -Path $ShimDir -Force | Out-Null }
$ShimContent = "@echo off`r`n`"$VenvPython`" `"$AppDir\_engine\src\app.py`" %*"
Set-Content -Path $ShimPath -Value $ShimContent -Encoding ASCII

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  INSTALLATION SUCCESSFUL!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Run the app from ANY terminal:" -ForegroundColor White
Write-Host "      miniyt" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Downloads folder : $env:USERPROFILE\Downloads\MiniYT" -ForegroundColor Gray
Write-Host "  App data         : $InstallRoot" -ForegroundColor Gray
Write-Host ""
Write-Host "  Optional: Gemini API key (free) for the per-surah cut feature:" -ForegroundColor Gray
Write-Host "    https://aistudio.google.com/apikey" -ForegroundColor Gray
Write-Host "    (the app will offer to set it up on first launch)" -ForegroundColor Gray
Write-Host ""
Write-Host "  NOTE: close & reopen your terminal so 'miniyt' is recognized." -ForegroundColor Yellow
Write-Host ""

# Try to open the app right away (optional convenience; skipped when
# MINIYT_SKIP_LAUNCH=1 e.g. for automated tests)
if (-not $env:MINIYT_SKIP_LAUNCH) {
    $answer = Read-Host "Launch miniyt now? (Y/n)"
    if ($answer -notmatch "^[nN]") {
        & python $AppDir\_engine\src\app.py
    }
}
