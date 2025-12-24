# =============================================================================
# JARVIS Development Script (PowerShell)
# Usage: .\scripts\dev.ps1 <command>
# =============================================================================

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "JARVIS Development Commands" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Setup:" -ForegroundColor Yellow
    Write-Host "  .\scripts\dev.ps1 install      - Install production dependencies"
    Write-Host "  .\scripts\dev.ps1 install-dev  - Install development dependencies"
    Write-Host ""
    Write-Host "Running:" -ForegroundColor Yellow
    Write-Host "  .\scripts\dev.ps1 run          - Run JARVIS (voice mode)"
    Write-Host "  .\scripts\dev.ps1 run-text     - Run JARVIS (text mode)"
    Write-Host "  .\scripts\dev.ps1 run-check    - Check configuration"
    Write-Host "  .\scripts\dev.ps1 run-mobile   - Start mobile PWA dev server"
    Write-Host ""
    Write-Host "Testing:" -ForegroundColor Yellow
    Write-Host "  .\scripts\dev.ps1 test         - Run all tests"
    Write-Host "  .\scripts\dev.ps1 verify       - Verify all imports"
    Write-Host ""
    Write-Host "Code Quality:" -ForegroundColor Yellow
    Write-Host "  .\scripts\dev.ps1 lint         - Run linters"
    Write-Host "  .\scripts\dev.ps1 format       - Format code"
    Write-Host ""
    Write-Host "Other:" -ForegroundColor Yellow
    Write-Host "  .\scripts\dev.ps1 clean        - Clean cache files"
}

function Install-Deps {
    Write-Host "Installing production dependencies..." -ForegroundColor Green
    pip install -r requirements.txt
}

function Install-DevDeps {
    Write-Host "Installing development dependencies..." -ForegroundColor Green
    pip install -r requirements-dev.txt
    Set-Location mobile
    npm install
    Set-Location ..
}

function Run-Jarvis {
    Write-Host "Starting JARVIS (voice mode)..." -ForegroundColor Green
    python run.py
}

function Run-Text {
    Write-Host "Starting JARVIS (text mode)..." -ForegroundColor Green
    python run.py --text
}

function Run-Check {
    Write-Host "Checking configuration..." -ForegroundColor Green
    python run.py --check-config
}

function Run-Mobile {
    Write-Host "Starting mobile PWA dev server..." -ForegroundColor Green
    Set-Location mobile
    npm run dev
    Set-Location ..
}

function Run-Tests {
    Write-Host "Running tests..." -ForegroundColor Green
    pytest tests/ -v
}

function Verify-Imports {
    Write-Host "Verifying imports..." -ForegroundColor Green
    python scripts/verify_imports.py
}

function Run-Lint {
    Write-Host "Running linters..." -ForegroundColor Green
    flake8 src/ --max-line-length=100 --ignore=E501,W503
    mypy src/ --ignore-missing-imports
}

function Format-Code {
    Write-Host "Formatting code..." -ForegroundColor Green
    black src/ --line-length=100
    isort src/ --profile=black
}

function Clean-Cache {
    Write-Host "Cleaning cache files..." -ForegroundColor Green
    Get-ChildItem -Path . -Recurse -Directory -Name "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path . -Recurse -Directory -Name ".pytest_cache" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path . -Recurse -Directory -Name ".mypy_cache" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path . -Recurse -File -Name "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue
    if (Test-Path "htmlcov") { Remove-Item -Recurse -Force "htmlcov" }
    if (Test-Path ".coverage") { Remove-Item -Force ".coverage" }
    Write-Host "Cleaned cache files" -ForegroundColor Green
}

# Execute command
switch ($Command.ToLower()) {
    "help"        { Show-Help }
    "install"     { Install-Deps }
    "install-dev" { Install-DevDeps }
    "run"         { Run-Jarvis }
    "run-text"    { Run-Text }
    "run-check"   { Run-Check }
    "run-mobile"  { Run-Mobile }
    "test"        { Run-Tests }
    "verify"      { Verify-Imports }
    "lint"        { Run-Lint }
    "format"      { Format-Code }
    "clean"       { Clean-Cache }
    default       { 
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Show-Help 
    }
}
