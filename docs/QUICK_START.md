# JARVIS Quick Start Guide

Get JARVIS running in 5 minutes.

## Prerequisites

- **Python 3.10+** (3.11 recommended)
- **Node.js 18+** (for mobile PWA, optional)
- **At least one LLM API key** (Groq recommended - free tier available)

## Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-repo/jarvis.git
cd jarvis

# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (Windows CMD)
venv\Scripts\activate.bat

# Activate (macOS/Linux)
source venv/bin/activate
```

## Step 2: Install Dependencies

**Choose your installation tier:**

### Option A: Minimal (Text Mode Only) - Recommended for First Run
```bash
pip install -r requirements-core.txt
```

### Option B: With Mobile API Support
```bash
pip install -r requirements-api.txt
```

### Option C: With Voice Features
```bash
pip install -r requirements-voice.txt
```

### Option D: Full Installation
```bash
# Windows (avoids C++ compilation issues)
pip install -r requirements-windows.txt

# macOS/Linux
pip install -r requirements-full.txt
```

### Option E: Use Installation Script
```bash
python scripts/install.py
```

**⚠️ Windows Users:** Avoid `requirements-full.txt` directly as some packages (webrtcvad, dlib) require Visual Studio Build Tools. Use `requirements-windows.txt` instead.

## Step 3: Configure API Keys

Create a `.env` file in the project root:

```bash
# Required: At least one LLM provider
GROQ_API_KEY=your_groq_api_key_here

# Optional: Additional providers
GEMINI_API_KEY=your_gemini_api_key
MISTRAL_API_KEY=your_mistral_api_key

# Optional: For production security
JARVIS_JWT_SECRET=your_secret_key_here
JARVIS_ADMIN_USER=admin
JARVIS_ADMIN_PASSWORD=your_secure_password
```

**Get free API keys:**
- Groq: https://console.groq.com (fastest, recommended)
- Gemini: https://makersuite.google.com/app/apikey
- Mistral: https://console.mistral.ai

## Step 4: Run JARVIS

```bash
# Text mode (no microphone needed)
python run.py --text
```

You should see:
```
============================================================
JARVIS v2.0.0 - Text Mode
Type 'quit' or 'exit' to stop
Type 'status' for system status
Type 'help' for available commands
Dashboard: http://127.0.0.1:8080/dashboard
Mobile API: http://0.0.0.0:8000/api/docs
============================================================

You: 
```

## Step 5: Your First Command

Try these commands:

```
You: Hello JARVIS
You: What can you do?
You: What's 25 * 47?
You: Open notepad
```

## Step 6: Mobile App (Optional)

```bash
# In a new terminal
cd mobile
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

**Login:**
- Username: `admin`
- Password: `jarvis` (or your custom password)

---

## What's Next?

### Enable Voice Mode
```bash
# Full voice mode (requires microphone)
python run.py
```

Say "Hey JARVIS" to activate, then speak your command.

### Connect IoT Devices
1. Flash ESP32 with JARVIS firmware
2. Configure WiFi in `config/settings.yaml`
3. Devices auto-discover via mDNS

### Customize Settings
Edit `config/settings.yaml`:
```yaml
voice:
  wake_word: "jarvis"
  tts_voice: "en-US-GuyNeural"

llm:
  default_provider: "groq"
  temperature: 0.7
```

### View Performance Dashboard
Open http://localhost:8080/dashboard to see:
- Response times
- Cache hit rates
- Resource usage

---

## Troubleshooting

### "No LLM provider available"
→ Check your `.env` file has at least one valid API key

### "Microphone not found"
→ Use text mode: `python run.py --text`

### "Mobile app can't connect"
→ Ensure JARVIS is running and check firewall settings

### "Import error" / "ModuleNotFoundError"
→ Install core dependencies first:
```bash
pip install -r requirements-core.txt
```

### Windows: "error: Microsoft Visual C++ 14.0 required"
→ Use Windows-specific requirements:
```bash
pip install -r requirements-windows.txt
```
This avoids packages that need C++ compilation (webrtcvad, dlib).

### "pydantic" or "yaml" not found
→ These are core dependencies. Run:
```bash
pip install pydantic pydantic-settings python-dotenv pyyaml loguru
```

### Verify your installation
```bash
python scripts/verify_imports.py
```

---

## Commands Reference

| Command | Description |
|---------|-------------|
| `python run.py` | Full voice mode |
| `python run.py --text` | Text-only mode |
| `python run.py --check-config` | Validate configuration |
| `python run.py --legacy` | Use legacy modules |

---

*JARVIS v2.0.0 - Your AI Assistant*
