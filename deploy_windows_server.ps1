param(
  [string]$RepoPath = "C:\apps\AIStock-new",
  [string]$PythonExe = "py"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $RepoPath)) {
  Write-Host "Repository not found at $RepoPath" -ForegroundColor Red
  exit 1
}

Set-Location $RepoPath

Write-Host "[1/6] Creating virtual environment..." -ForegroundColor Cyan
& $PythonExe -3 -m venv .venv

Write-Host "[2/6] Activating virtual environment..." -ForegroundColor Cyan
. .\.venv\Scripts\Activate.ps1

Write-Host "[3/6] Installing backend dependencies..." -ForegroundColor Cyan
pip install -r backend\requirements.txt

Write-Host "[4/6] Setting runtime environment..." -ForegroundColor Cyan
$env:DB_HOST = if ($env:DB_HOST) { $env:DB_HOST } else { "127.0.0.1" }
$env:DB_PORT = if ($env:DB_PORT) { $env:DB_PORT } else { "3306" }
$env:DB_USERNAME = if ($env:DB_USERNAME) { $env:DB_USERNAME } else { "aistock" }
$env:DB_PASSWORD = if ($env:DB_PASSWORD) { $env:DB_PASSWORD } else { "AI@stock!234" }
$env:DB_NAME = if ($env:DB_NAME) { $env:DB_NAME } else { "ai_stock" }
$env:APP_HOST = if ($env:APP_HOST) { $env:APP_HOST } else { "0.0.0.0" }
$env:APP_PORT = if ($env:APP_PORT) { $env:APP_PORT } else { "8000" }

Write-Host "[5/6] Opening firewall port 8000..." -ForegroundColor Cyan
try {
  netsh advfirewall firewall show rule name="AIStock API" | Out-Null
  netsh advfirewall firewall set rule name="AIStock API" new enable=yes | Out-Null
} catch {
  netsh advfirewall firewall add rule name="AIStock API" dir=in action=allow protocol=TCP localport=8000 | Out-Null
}

Write-Host "[6/6] Starting backend server..." -ForegroundColor Green
Write-Host "Open http://<server-ip>:8000/health to verify." -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop the server." -ForegroundColor Yellow
Set-Location backend
python start.py
