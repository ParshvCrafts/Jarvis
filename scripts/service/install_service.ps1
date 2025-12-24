# JARVIS Windows Service Installation Script
# 
# This script sets up JARVIS to run as a Windows service using NSSM
# (Non-Sucking Service Manager)
#
# Requirements:
#   - NSSM installed (https://nssm.cc/download)
#   - Administrator privileges
#
# Usage:
#   Run PowerShell as Administrator
#   .\install_service.ps1

param(
    [string]$PythonPath = "",
    [string]$JarvisPath = "",
    [string]$ServiceName = "JARVIS"
)

# Check for admin privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script requires Administrator privileges." -ForegroundColor Red
    Write-Host "Please run PowerShell as Administrator and try again."
    exit 1
}

# Find NSSM
$nssm = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssm) {
    Write-Host "ERROR: NSSM not found." -ForegroundColor Red
    Write-Host "Please install NSSM from https://nssm.cc/download"
    Write-Host "and add it to your PATH."
    exit 1
}

# Find Python if not specified
if (-not $PythonPath) {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        $PythonPath = $python.Source
    } else {
        Write-Host "ERROR: Python not found." -ForegroundColor Red
        Write-Host "Please specify Python path with -PythonPath parameter."
        exit 1
    }
}

# Find JARVIS directory if not specified
if (-not $JarvisPath) {
    $JarvisPath = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}

$RunScript = Join-Path $JarvisPath "run.py"
if (-not (Test-Path $RunScript)) {
    Write-Host "ERROR: run.py not found at $RunScript" -ForegroundColor Red
    Write-Host "Please specify JARVIS path with -JarvisPath parameter."
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "JARVIS Windows Service Installation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Python: $PythonPath"
Write-Host "JARVIS: $JarvisPath"
Write-Host "Service: $ServiceName"
Write-Host ""

# Check if service already exists
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "Service '$ServiceName' already exists." -ForegroundColor Yellow
    $response = Read-Host "Do you want to remove and reinstall it? (y/n)"
    if ($response -eq 'y') {
        Write-Host "Stopping and removing existing service..."
        & nssm stop $ServiceName 2>$null
        & nssm remove $ServiceName confirm
    } else {
        Write-Host "Installation cancelled."
        exit 0
    }
}

# Install service
Write-Host "Installing service..." -ForegroundColor Green

& nssm install $ServiceName $PythonPath $RunScript
& nssm set $ServiceName AppDirectory $JarvisPath
& nssm set $ServiceName DisplayName "JARVIS AI Assistant"
& nssm set $ServiceName Description "Personal AI assistant with voice control"
& nssm set $ServiceName Start SERVICE_AUTO_START
& nssm set $ServiceName ObjectName LocalSystem

# Set restart behavior
& nssm set $ServiceName AppExit Default Restart
& nssm set $ServiceName AppRestartDelay 10000

# Set stdout/stderr logging
$LogDir = Join-Path $JarvisPath "data\logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}
& nssm set $ServiceName AppStdout (Join-Path $LogDir "service_stdout.log")
& nssm set $ServiceName AppStderr (Join-Path $LogDir "service_stderr.log")
& nssm set $ServiceName AppStdoutCreationDisposition 4
& nssm set $ServiceName AppStderrCreationDisposition 4
& nssm set $ServiceName AppRotateFiles 1
& nssm set $ServiceName AppRotateBytes 10485760

# Set environment variables
$EnvFile = Join-Path $JarvisPath ".env"
if (Test-Path $EnvFile) {
    Write-Host "Loading environment from .env file..."
    $envVars = Get-Content $EnvFile | Where-Object { $_ -match '^\s*[^#].*=' }
    foreach ($line in $envVars) {
        $parts = $line -split '=', 2
        if ($parts.Count -eq 2) {
            $key = $parts[0].Trim()
            $value = $parts[1].Trim().Trim('"').Trim("'")
            & nssm set $ServiceName AppEnvironmentExtra "+$key=$value"
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Service installed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Commands:"
Write-Host "  Start:   nssm start $ServiceName"
Write-Host "  Stop:    nssm stop $ServiceName"
Write-Host "  Status:  nssm status $ServiceName"
Write-Host "  Edit:    nssm edit $ServiceName"
Write-Host "  Remove:  nssm remove $ServiceName"
Write-Host ""
Write-Host "Or use Windows Services (services.msc)"
Write-Host ""

$startNow = Read-Host "Start the service now? (y/n)"
if ($startNow -eq 'y') {
    Write-Host "Starting service..."
    & nssm start $ServiceName
    Start-Sleep -Seconds 2
    & nssm status $ServiceName
}
