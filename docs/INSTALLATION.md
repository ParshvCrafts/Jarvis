# JARVIS Installation Guide

Platform-specific installation instructions for Windows, Linux, and macOS.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Windows Installation](#windows-installation)
3. [Linux Installation](#linux-installation)
4. [macOS Installation](#macos-installation)
5. [Post-Installation](#post-installation)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### All Platforms

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.9+ | 3.11 recommended |
| Git | Any | For cloning repository |
| Internet | Required | For LLM APIs |

### Hardware (Optional)

| Component | Purpose |
|-----------|---------|
| Microphone | Voice commands |
| Speakers | TTS output |
| Webcam | Face recognition |
| ESP32 | Smart home control |

---

## Windows Installation

### Step 1: Install Python

1. Download Python 3.11 from [python.org](https://www.python.org/downloads/)
2. **Important**: Check "Add Python to PATH" during installation
3. Verify installation:
   ```powershell
   python --version
   # Should show: Python 3.11.x
   ```

### Step 2: Install Visual C++ Build Tools

Some packages require compilation. Install Visual C++ Build Tools:

1. Download from [Visual Studio Downloads](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. Run installer, select "Desktop development with C++"
3. Restart computer after installation

### Step 3: Clone and Setup

```powershell
# Clone repository
git clone https://github.com/yourusername/jarvis.git
cd jarvis

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you get execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Configure Environment

```powershell
# Copy example environment file
copy .env.example .env

# Edit with notepad or your preferred editor
notepad .env
```

Add your API keys:
```
GROQ_API_KEY=your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here
```

### Step 5: Verify Installation

```powershell
# Run pre-flight check
python scripts/preflight_check.py

# Check configuration
python run.py --check-config
```

### Step 6: Run JARVIS

```powershell
# Text mode (recommended for first run)
python run.py --text

# Full voice mode
python run.py
```

### Windows Service Installation (Optional)

To run JARVIS as a Windows service:

1. Install NSSM from [nssm.cc](https://nssm.cc/download)
2. Add NSSM to PATH
3. Run installer as Administrator:
   ```powershell
   # Run PowerShell as Administrator
   .\scripts\service\install_service.ps1
   ```

### Windows-Specific Issues

**Audio Device Not Found:**
```powershell
# List audio devices
python -c "import sounddevice; print(sounddevice.query_devices())"

# Set specific device in settings.yaml
# audio:
#   input_device: 1
#   output_device: 2
```

**Permission Denied Errors:**
- Run PowerShell as Administrator for service installation
- Check antivirus isn't blocking Python

---

## Linux Installation

### Ubuntu/Debian

#### Step 1: Install System Dependencies

```bash
# Update package list
sudo apt update

# Install Python and pip
sudo apt install python3.11 python3.11-venv python3-pip

# Install audio dependencies
sudo apt install portaudio19-dev python3-pyaudio

# Install other dependencies
sudo apt install ffmpeg libespeak1

# For face recognition (optional)
sudo apt install cmake libopenblas-dev liblapack-dev
```

#### Step 2: Clone and Setup

```bash
# Clone repository
git clone https://github.com/yourusername/jarvis.git
cd jarvis

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

#### Step 3: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with nano or vim
nano .env
```

Add your API keys:
```
GROQ_API_KEY=your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here
```

#### Step 4: Set Permissions

```bash
# Restrict .env file permissions
chmod 600 .env

# Add user to audio group (for microphone access)
sudo usermod -a -G audio $USER

# Add user to video group (for camera access)
sudo usermod -a -G video $USER

# Log out and back in for group changes to take effect
```

#### Step 5: Verify Installation

```bash
# Run pre-flight check
python scripts/preflight_check.py

# Check configuration
python run.py --check-config
```

#### Step 6: Run JARVIS

```bash
# Text mode
python run.py --text

# Full voice mode
python run.py
```

### Systemd Service Installation (Optional)

```bash
# Copy service file
sudo cp scripts/service/jarvis.service /etc/systemd/system/

# Edit service file with your paths
sudo nano /etc/systemd/system/jarvis.service
# Update: User, WorkingDirectory, ExecStart paths

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable jarvis

# Start service
sudo systemctl start jarvis

# Check status
sudo systemctl status jarvis

# View logs
journalctl -u jarvis -f
```

### Fedora/RHEL

```bash
# Install dependencies
sudo dnf install python3.11 python3-pip portaudio-devel ffmpeg espeak-ng

# Rest of installation same as Ubuntu
```

### Arch Linux

```bash
# Install dependencies
sudo pacman -S python python-pip portaudio ffmpeg espeak-ng

# Rest of installation same as Ubuntu
```

### Linux-Specific Issues

**PulseAudio Issues:**
```bash
# Check PulseAudio is running
pulseaudio --check

# Restart PulseAudio
pulseaudio -k
pulseaudio --start

# Or use ALSA directly in settings.yaml
# audio:
#   backend: "alsa"
```

**Permission Denied for /dev/video0:**
```bash
# Check current permissions
ls -la /dev/video0

# Add user to video group
sudo usermod -a -G video $USER

# Reboot or re-login
```

---

## macOS Installation

### Step 1: Install Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Step 2: Install Dependencies

```bash
# Install Python
brew install python@3.11

# Install audio dependencies
brew install portaudio ffmpeg

# Install Xcode Command Line Tools (if not already installed)
xcode-select --install
```

### Step 3: Clone and Setup

```bash
# Clone repository
git clone https://github.com/yourusername/jarvis.git
cd jarvis

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with nano or TextEdit
nano .env
```

### Step 5: Grant Permissions

macOS requires explicit permissions for microphone and camera:

1. **Microphone**: System Preferences → Security & Privacy → Privacy → Microphone
   - Add Terminal (or your IDE) to allowed apps

2. **Camera**: System Preferences → Security & Privacy → Privacy → Camera
   - Add Terminal (or your IDE) to allowed apps

3. **Accessibility** (for system control): System Preferences → Security & Privacy → Privacy → Accessibility
   - Add Terminal (or your IDE) to allowed apps

### Step 6: Verify and Run

```bash
# Run pre-flight check
python scripts/preflight_check.py

# Text mode
python run.py --text

# Full voice mode
python run.py
```

### LaunchAgent Installation (Optional)

Create `~/Library/LaunchAgents/com.jarvis.assistant.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jarvis.assistant</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/jarvis/venv/bin/python</string>
        <string>/path/to/jarvis/run.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/jarvis</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/path/to/jarvis/data/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/jarvis/data/logs/stderr.log</string>
</dict>
</plist>
```

Load the service:
```bash
launchctl load ~/Library/LaunchAgents/com.jarvis.assistant.plist
```

### macOS-Specific Issues

**Apple Silicon (M1/M2) Compatibility:**
```bash
# Some packages may need Rosetta
softwareupdate --install-rosetta

# Or install native ARM versions
arch -arm64 pip install package_name
```

**Microphone Permission Denied:**
- Go to System Preferences → Security & Privacy → Privacy → Microphone
- Ensure Terminal/IDE is checked
- Restart Terminal after granting permission

---

## Post-Installation

### 1. Run Pre-Flight Check

```bash
python scripts/preflight_check.py --verbose
```

This validates:
- ✓ Python version
- ✓ Required packages
- ✓ Configuration files
- ✓ API keys
- ✓ Audio hardware
- ✓ Module imports

### 2. Configure Settings

Edit `config/settings.yaml` for your preferences:

```yaml
jarvis:
  name: "JARVIS"

voice:
  wake_word:
    phrase: "hey jarvis"
    threshold: 0.5
  
llm:
  default_provider: "groq"
```

### 3. Run Audio Calibration

```bash
python -c "from src.voice.calibration import run_calibration; run_calibration()"
```

### 4. Test Voice Commands

```bash
# Start in text mode first
python run.py --text

# Type commands to test
> What time is it?
> Help
```

### 5. Run Benchmarks (Optional)

```bash
python scripts/benchmark.py --quick
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Activate venv: `source venv/bin/activate` |
| `No API keys configured` | Check `.env` file has valid keys |
| `Audio device not found` | Check system audio settings, run `sounddevice.query_devices()` |
| `Permission denied` | Check file permissions, run as appropriate user |
| `CUDA not available` | Install CUDA toolkit or use CPU-only mode |

### Getting Help

1. Check [KNOWN_ISSUES.md](KNOWN_ISSUES.md)
2. Review logs in `data/logs/`
3. Run with `--debug` flag
4. Open GitHub issue with details

---

*JARVIS Installation Guide - Phase 4.5*
