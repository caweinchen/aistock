param(
  [string]$RepoPath = $PSScriptRoot,
  [string]$PythonExe = "py",
  [string[]]$PythonArgs = @("-3"),
  [int]$BackendPort = 8000,
  [switch]$OpenFirewall,
  [switch]$StartBackend
)

$ErrorActionPreference = "Stop"

function Write-Step {
  param([string]$Message)
  Write-Host ""
  Write-Host $Message -ForegroundColor Cyan
}

function Invoke-Checked {
  param(
    [string]$Label,
    [scriptblock]$Command
  )

  Write-Host "-> $Label"
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "$Label failed with exit code $LASTEXITCODE"
  }
}

function Get-LocalIPv4 {
  $addresses = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
      $_.IPAddress -notlike "127.*" -and
      $_.IPAddress -notlike "169.254.*" -and
      $_.PrefixOrigin -ne "WellKnown"
    } |
    Select-Object -ExpandProperty IPAddress

  if ($addresses) {
    return $addresses[0]
  }

  return "<server-ip>"
}

$RepoPath = (Resolve-Path $RepoPath).Path
$BackendPath = Join-Path $RepoPath "backend"
$FrontendPath = Join-Path $RepoPath "frontend"
$VenvPython = Join-Path $RepoPath ".venv\Scripts\python.exe"
$EnvFile = Join-Path $BackendPath ".env"
$EnvExample = Join-Path $BackendPath ".env.example"

Write-Host "============================================"
Write-Host "        AIStock Windows Deploy Helper"
Write-Host "============================================"
Write-Host "Repository: $RepoPath"

if (-not (Test-Path $BackendPath)) {
  throw "Backend directory not found: $BackendPath"
}

if (-not (Test-Path $FrontendPath)) {
  throw "Frontend directory not found: $FrontendPath"
}

Write-Step "[1/7] Checking required tools"
if (-not (Get-Command $PythonExe -ErrorAction SilentlyContinue)) {
  throw "Python command not found: $PythonExe. Install Python 3.11+ and try again."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm command not found. Install Node.js LTS and try again."
}

Invoke-Checked "Python version" { & $PythonExe @PythonArgs --version }
Invoke-Checked "npm version" { npm --version }

Write-Step "[2/7] Creating Python virtual environment"
if (-not (Test-Path $VenvPython)) {
  Invoke-Checked "Create .venv" { & $PythonExe @PythonArgs -m venv (Join-Path $RepoPath ".venv") }
} else {
  Write-Host "-> .venv already exists, reusing it"
}

Write-Step "[3/7] Installing backend dependencies"
Invoke-Checked "Upgrade pip" { & $VenvPython -m pip install --upgrade pip }
Invoke-Checked "Install backend requirements" { & $VenvPython -m pip install -r (Join-Path $BackendPath "requirements.txt") }

Write-Step "[4/7] Preparing backend environment file"
if (-not (Test-Path $EnvFile)) {
  if (-not (Test-Path $EnvExample)) {
    throw ".env.example not found: $EnvExample"
  }
  Copy-Item $EnvExample $EnvFile
  Write-Host "-> Created backend\.env from backend\.env.example" -ForegroundColor Yellow
  Write-Host "-> Edit backend\.env and set DB_PASSWORD, DB_NAME, TUSHARE_TOKEN before production use" -ForegroundColor Yellow
} else {
  Write-Host "-> backend\.env already exists, leaving it unchanged"
}

Write-Step "[5/7] Installing frontend dependencies"
Push-Location $FrontendPath
try {
  Invoke-Checked "npm install" { npm install }
} finally {
  Pop-Location
}

Write-Step "[6/7] Optional Windows firewall rule"
if ($OpenFirewall) {
  $ruleName = "AIStock API $BackendPort"
  try {
    $existingRule = netsh advfirewall firewall show rule name="$ruleName" 2>$null
    if ($LASTEXITCODE -eq 0 -and $existingRule) {
      netsh advfirewall firewall set rule name="$ruleName" new enable=yes | Out-Null
      Write-Host "-> Enabled existing firewall rule: $ruleName"
    } else {
      netsh advfirewall firewall add rule name="$ruleName" dir=in action=allow protocol=TCP localport=$BackendPort | Out-Null
      Write-Host "-> Added firewall rule: $ruleName"
    }
  } catch {
    Write-Host "-> Failed to update firewall. Run PowerShell as Administrator or open TCP $BackendPort manually." -ForegroundColor Yellow
  }
} else {
  Write-Host "-> Skipped. Re-run with -OpenFirewall to open TCP $BackendPort."
}

Write-Step "[7/7] Deployment preparation complete"
$serverIp = Get-LocalIPv4
Write-Host "Backend local URL:  http://127.0.0.1:$BackendPort"
Write-Host "Backend device URL: http://$serverIp`:$BackendPort"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "1. Edit backend\.env and confirm database/TuShare settings."
Write-Host "2. Start backend:"
Write-Host "   cd backend"
Write-Host "   ..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port $BackendPort"
Write-Host "3. Start frontend:"
Write-Host "   cd frontend"
Write-Host "   npm run web"
Write-Host "4. In mobile app settings, use the real backend IP: $serverIp`:$BackendPort"

if ($StartBackend) {
  Write-Step "Starting backend now"
  Push-Location $BackendPath
  try {
    & $VenvPython -m uvicorn app.main:app --host 0.0.0.0 --port $BackendPort
  } finally {
    Pop-Location
  }
}
