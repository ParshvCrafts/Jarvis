# JARVIS One-Command Setup Script (Windows PowerShell)
# Usage: .\setup.ps1
# Or with options: .\setup.ps1 -SkipVenv -Tier full

param(
    [switch]$SkipVenv,
    [string]$Tier = "full",
    [switch]$Help
)

$ErrorActionPreference = "Stop"

# Colors
function Write-Header { param($text) Write-Host "`n$("=" * 60)" -ForegroundColor Cyan; Write-Host $text -ForegroundColor Cyan; Write-Host "$("=" * 60)`n" -ForegroundColor Cyan }
function Write-Success { param($text) Write-Host "✓ $text" -ForegroundColor Green }
function Write-Warn { param($text) Write-Host "⚠ $text" -ForegroundColor Yellow }
function Write-Err { param($text) Write-Host "✗ $text" -ForegroundColor Red }
function Write-Info { param($text) Write-Host "  $text" -ForegroundColor White }

if ($Help) {
    Write-Host @"
JARVIS Setup Script

Usage: .\setup.ps1 [options]

Options:
  -SkipVenv    Skip virtual environment creation
  -Tier        Requirements tier: minimal, core, full, dev (default: full)
  -Help        Show this help message

Examples:
  .\setup.ps1                    # Full setup with venv
  .\setup.ps1 -Tier core         # Core features only
  .\setup.ps1 -SkipVenv          # Use existing Python environment
"@
    exit 0
}

Write-Header "JARVIS Setup Script"
Write-Host "Setting up JARVIS - Your Personal AI Assistant`n"

# Check Python
Write-Header "Checking Python"
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -ge 3 -and $minor -ge 10) {
            Write-Success "Python $major.$minor detected"
        } else {
            Write-Err "Python 3.10+ required, found $major.$minor"
            exit 1
        }
    }
} catch {
    Write-Err "Python not found. Please install Python 3.10+"
    exit 1
}

# Create virtual environment
if (-not $SkipVenv) {
    Write-Header "Creating Virtual Environment"
    
    if (Test-Path "venv") {
        Write-Warn "Virtual environment already exists"
        $response = Read-Host "Recreate? (y/N)"
        if ($response -eq "y" -or $response -eq "Y") {
            Remove-Item -Recurse -Force "venv"
            python -m venv venv
            Write-Success "Virtual environment recreated"
        } else {
            Write-Info "Using existing virtual environment"
        }
    } else {
        python -m venv venv
        Write-Success "Virtual environment created"
    }
    
    # Activate venv
    Write-Info "Activating virtual environment..."
    & .\venv\Scripts\Activate.ps1
}

# Upgrade pip
Write-Header "Upgrading pip"
python -m pip install --upgrade pip --quiet
Write-Success "pip upgraded"

# Install requirements
Write-Header "Installing Dependencies ($Tier tier)"

$reqFile = "requirements.txt"
if ($Tier -ne "full") {
    $reqFile = "requirements-$Tier.txt"
}

if (Test-Path $reqFile) {
    Write-Info "Installing from $reqFile..."
    python -m pip install -r $reqFile --quiet
    Write-Success "Dependencies installed"
} else {
    Write-Err "Requirements file not found: $reqFile"
    exit 1
}

# Verify critical dependencies
Write-Header "Verifying Dependencies"
$criticalPackages = @("loguru", "pydantic", "python-dotenv", "pyyaml")
$missingPackages = @()

foreach ($pkg in $criticalPackages) {
    $result = python -c "import $pkg" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "$pkg installed"
    } else {
        Write-Err "$pkg missing"
        $missingPackages += $pkg
    }
}

if ($missingPackages.Count -gt 0) {
    Write-Err "Some critical packages are missing. Please check installation."
    exit 1
}

# Create directories
Write-Header "Creating Directories"
$dirs = @("data", "data/screenshots", "data/browser_data", "logs", "cache")
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Success "Created $dir/"
    } else {
        Write-Info "$dir/ already exists"
    }
}

# Create config from example if needed
Write-Header "Setting Up Configuration"
if (-not (Test-Path "config/settings.yaml")) {
    if (Test-Path "config/settings.yaml.example") {
        Copy-Item "config/settings.yaml.example" "config/settings.yaml"
        Write-Success "Created config/settings.yaml from example"
    } else {
        Write-Warn "No settings.yaml.example found"
    }
} else {
    Write-Info "config/settings.yaml already exists"
}

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Success "Created .env from example"
        Write-Warn "Please edit .env and add your API keys!"
    } else {
        Write-Warn "No .env.example found"
    }
} else {
    Write-Info ".env already exists"
}

# Run first-time setup
Write-Header "Running First-Time Setup"
try {
    python -c "from src.core.setup_wizard import run_first_time_setup; run_first_time_setup()" 2>$null
    Write-Success "First-time setup complete"
} catch {
    Write-Info "First-time setup will run on first JARVIS start"
}

# Validate installation
Write-Header "Validating Installation"
python run.py --check-config

Write-Header "Setup Complete!"
Write-Host @"
JARVIS is ready to use!

Next steps:
1. Edit .env and add your API keys:
   - GROQ_API_KEY (required for LLM)
   - Other optional keys

2. Start JARVIS:
   .\start.bat           # Full voice mode
   .\start-text.bat      # Text-only mode
   python run.py         # Direct run

3. Say "Hey Jarvis" to wake up!

For help: python run.py --help
"@
