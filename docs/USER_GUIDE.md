# JARVIS User Guide

A comprehensive guide to using JARVIS, your advanced personal AI assistant.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Voice Commands](#voice-commands)
3. [System Control](#system-control)
4. [Smart Home (IoT)](#smart-home-iot)
5. [Coding Assistant](#coding-assistant)
6. [Research & Information](#research--information)
7. [Telegram Integration](#telegram-integration)
8. [Configuration](#configuration)
9. [Troubleshooting](#troubleshooting)

---

## Getting Started

### First Run

1. **Verify Configuration**
   ```bash
   python run.py --check-config
   ```
   This shows which features are enabled and any missing configuration.

2. **Start JARVIS**
   ```bash
   # Full voice mode
   python run.py
   
   # Text-only mode (no microphone needed)
   python run.py --text
   ```

3. **Wake Word**
   - Say **"Hey Jarvis"** to activate
   - Wait for the audio cue (rising tone)
   - Speak your command clearly

### Conversation Mode

After the wake word, JARVIS enters **conversation mode** for 30 seconds:
- Ask follow-up questions without repeating the wake word
- Say **"that's all"** or **"goodbye"** to exit early
- Mode auto-exits after 30 seconds of silence

---

## Voice Commands

### Basic Interaction

| Say This | JARVIS Does |
|----------|-------------|
| "Hey Jarvis" | Activates listening mode |
| "What can you do?" | Shows help |
| "That's all" / "Goodbye" | Ends conversation |
| "Never mind" / "Cancel" | Cancels current action |

### Tips for Better Recognition

1. **Speak clearly** - Enunciate words
2. **Reduce background noise** - Close windows, turn off fans
3. **Wait for the beep** - Don't speak too early
4. **Keep commands concise** - Short, direct phrases work best

---

## System Control

### Opening Applications

```
"Open Chrome"
"Launch Notepad"
"Start Visual Studio Code"
"Open File Explorer"
"Run Calculator"
```

### Screenshots

```
"Take a screenshot"
"Capture my screen"
"Screenshot this"
```

Screenshots are saved to `data/screenshots/`.

### Volume Control

```
"Mute"
"Unmute"
"Volume up"
"Volume down"
"Set volume to 50 percent"
```

### Window Management

```
"Minimize this window"
"Maximize Chrome"
"Close Notepad"
```

---

## Smart Home (IoT)

### Lights

```
"Turn on the lights"
"Turn off the bedroom light"
"Dim the lights to 50 percent"
"Set lights to warm white"
"Toggle the lamp"
```

### Door Locks

```
"Lock the front door"
"Unlock the garage"
"Is the door locked?"
```

### Device Status

```
"What devices are online?"
"Show device status"
"Is the light on?"
```

### Setting Up IoT Devices

1. Configure `IOT_SHARED_SECRET` in `.env`
2. Flash ESP32 devices with JARVIS firmware
3. Devices auto-discover via mDNS
4. Check status: "What devices are online?"

---

## Coding Assistant

### Code Generation

```
"Write a Python function to sort a list"
"Create a JavaScript async function for API calls"
"Generate a REST API endpoint in Flask"
"Write a SQL query to find duplicate records"
```

### Code Explanation

```
"Explain this error: [paste error]"
"What does this code do?"
"Help me debug this function"
"Review this code for issues"
```

### Git Operations

```
"Git status"
"Commit with message 'fixed bug'"
"Push to origin"
"Pull from main"
"Create branch feature-login"
"Show git log"
```

### File Operations

```
"Read the file config.py"
"Create a new file called utils.py"
"What files are in the src folder?"
```

---

## Research & Information

### Web Search

```
"Search for Python tutorials"
"Look up the weather in Seattle"
"Find restaurants near me"
"What's the latest news about AI?"
```

### Questions

```
"What is machine learning?"
"Who invented the telephone?"
"How does photosynthesis work?"
"Explain quantum computing"
```

### Summarization

```
"Summarize this article: [URL]"
"Give me the key points of [topic]"
```

---

## Telegram Integration

### Setup

1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Add `TELEGRAM_BOT_TOKEN` to `.env`
3. Add your Telegram user ID to `allowed_users` in `settings.yaml`

### Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize bot |
| `/help` | Show help |
| `/status` | System status |
| `/devices` | IoT device list |

### Voice Notes

Send a voice note to JARVIS on Telegram - it will be transcribed and processed as a command.

### Two-Factor Confirmation

Sensitive actions (like unlocking doors) require confirmation via Telegram inline buttons.

---

## Configuration

### Environment Variables (`.env`)

```bash
# Required
GROQ_API_KEY=your_groq_key

# Optional LLM providers
GEMINI_API_KEY=your_gemini_key
MISTRAL_API_KEY=your_mistral_key
OPENROUTER_API_KEY=your_openrouter_key
ANTHROPIC_API_KEY=your_anthropic_key

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token

# IoT
IOT_SHARED_SECRET=your_shared_secret

# Security
JWT_SECRET=your_jwt_secret
```

### Settings (`config/settings.yaml`)

Key settings you can customize:

```yaml
voice:
  wake_word:
    phrase: "hey jarvis"
    threshold: 0.5  # Lower = more sensitive
  
  conversation:
    timeout: 30  # Seconds before auto-exit

audio_cues:
  enabled: true
  volume: 0.3

telegram:
  enabled: true
  allowed_users:
    - 123456789  # Your Telegram user ID
```

---

## Troubleshooting

### "Wake word not detected"

1. Check microphone is working: `python -c "import sounddevice; print(sounddevice.query_devices())"`
2. Reduce background noise
3. Lower threshold in settings: `wake_word.threshold: 0.3`
4. Speak closer to microphone

### "No LLM providers available"

1. Check API keys in `.env`
2. Run `python run.py --check-config`
3. Ensure at least one provider is configured

### "Telegram bot not responding"

1. Verify `TELEGRAM_BOT_TOKEN` is correct
2. Check your user ID is in `allowed_users`
3. Ensure bot is started: look for "Telegram bot started" in logs

### "IoT devices not found"

1. Verify `IOT_SHARED_SECRET` matches device firmware
2. Ensure devices are on same network
3. Check mDNS is working: devices should advertise `_jarvis-iot._tcp.local.`

### "Audio cues not playing"

1. Check speakers are connected
2. Verify `audio_cues.enabled: true` in settings
3. Test with: `python -c "from src.voice.audio_cues import play_cue; play_cue('notification', blocking=True)"`

### Viewing Logs

Logs are stored in `data/logs/`:
- `jarvis.log` - Main application log
- `voice.log` - Voice pipeline log
- `agents.log` - Agent system log

---

## Quick Reference Card

| Action | Command |
|--------|---------|
| Wake up | "Hey Jarvis" |
| Get help | "What can you do?" |
| End conversation | "Goodbye" / "That's all" |
| Open app | "Open [app name]" |
| Screenshot | "Take a screenshot" |
| Lights on/off | "Turn on/off the lights" |
| Lock door | "Lock the [door name]" |
| Search web | "Search for [query]" |
| Ask question | "What is [topic]?" |
| Git status | "Git status" |
| System status | "System status" |

---

## Getting Help

- **In-app**: Say "help" or "what can you do?"
- **Documentation**: See `docs/` folder
- **Issues**: Check GitHub issues
- **Logs**: Review `data/logs/jarvis.log`

---

---

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| Python | 3.9 or higher |
| RAM | 2 GB minimum, 4 GB recommended |
| Disk Space | 1 GB free |
| Microphone | Any USB or built-in mic |
| Speakers | For TTS output |
| Network | Internet for LLM APIs |

### Optional Hardware

| Component | Purpose |
|-----------|---------|
| Camera | Face recognition authentication |
| ESP32 | Smart home device control |

### Pre-Flight Check

Before running JARVIS, validate your system:

```bash
python scripts/preflight_check.py
```

This checks:
- ✓ Python version and dependencies
- ✓ Configuration files and API keys
- ✓ Audio hardware detection
- ✓ Module availability
- ✓ IoT device discovery

---

## Installation

### Quick Install (All Platforms)

```bash
# Clone repository
git clone https://github.com/yourusername/jarvis.git
cd jarvis

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/macOS)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# Verify installation
python scripts/preflight_check.py

# Run JARVIS
python run.py
```

### Platform-Specific Notes

**Windows:**
- Install Visual C++ Build Tools for some packages
- Run PowerShell as Administrator for service installation

**Linux:**
- Install `portaudio19-dev` for audio: `sudo apt install portaudio19-dev`
- May need `pulseaudio` for audio routing

**macOS:**
- Install Xcode Command Line Tools: `xcode-select --install`
- Grant microphone permissions in System Preferences

---

## FAQ

### General

**Q: Can I use JARVIS offline?**
A: Partially. Configure Ollama as your LLM provider for offline language model. Wake word and TTS can work offline, but web search requires internet.

**Q: How do I change the wake word?**
A: Edit `config/settings.yaml`:
```yaml
voice:
  wake_word:
    phrase: "computer"  # or your preferred phrase
```

**Q: Why is JARVIS slow to respond?**
A: Check which LLM provider is being used. Groq is fastest, Ollama (local) is slowest. Run `python scripts/benchmark.py` to measure performance.

### Voice

**Q: JARVIS doesn't hear me**
A: 
1. Run pre-flight check: `python scripts/preflight_check.py`
2. Check microphone in system settings
3. Lower wake word threshold in settings
4. Run audio calibration: `python -c "from src.voice.calibration import run_calibration; run_calibration()"`

**Q: Can I use a different TTS voice?**
A: Yes, configure in settings.yaml:
```yaml
voice:
  tts:
    provider: "edge"  # or "pyttsx3"
    voice: "en-US-AriaNeural"
```

### IoT

**Q: How do I add a new smart device?**
A: 
1. Flash ESP32 with JARVIS firmware (see HARDWARE_SETUP.md)
2. Configure WiFi and shared secret
3. Device auto-discovers via mDNS
4. Verify: "Hey Jarvis, what devices are online?"

**Q: Can I use other smart home platforms?**
A: Currently only ESP32 devices are supported. Integration with Home Assistant is planned for future releases.

### Security

**Q: Is my data sent to the cloud?**
A: Voice commands are sent to your configured LLM provider (Groq, Gemini, etc.) for processing. Use Ollama for fully local processing.

**Q: How do I secure my installation?**
A:
1. Keep `.env` file permissions restricted (600 on Linux)
2. Use strong `IOT_SHARED_SECRET`
3. Enable Telegram 2FA for remote access
4. Review `docs/SECURITY.md` for full guidelines

---

## Performance Features (Phase 5)

JARVIS includes advanced performance optimizations that make responses faster and more efficient.

### Response Streaming

JARVIS can start speaking responses before the full answer is generated:

- **How it works**: As the AI generates text, complete sentences are sent to text-to-speech immediately
- **Benefit**: You hear the first part of the response much faster (typically <1 second)
- **Configuration**: Enabled by default in `config/settings.yaml`:

```yaml
performance:
  streaming:
    enabled: true
    min_sentence_length: 10
```

### Intelligent Caching

Repeated or similar questions get instant responses from cache:

- **Multi-level cache**: Memory (fastest) → SQLite (persistent) → Semantic (similar queries)
- **Smart TTL**: Weather cached 30 min, static knowledge cached 7 days
- **Cache hit ratio**: Typically 60%+ for regular users

**Configuration:**
```yaml
cache:
  enabled: true
  semantic:
    enabled: true
    threshold: 0.92  # Similarity threshold
```

**Clear cache** (if needed):
- Restart JARVIS to clear memory cache
- Delete `data/cache/` folder to clear all caches

### Performance Dashboard

Monitor JARVIS performance in real-time:

1. **Access**: Open `http://localhost:8080/dashboard` in your browser
2. **Metrics shown**:
   - Response latency (STT, LLM, TTS, end-to-end)
   - Cache hit/miss ratio
   - Memory and CPU usage
   - Recent errors and alerts

**Configuration:**
```yaml
dashboard:
  enabled: true
  host: "127.0.0.1"
  port: 8080
```

### Command Prediction

JARVIS learns your patterns and pre-loads relevant data:

- **Time patterns**: Morning queries (weather, calendar) are pre-cached
- **Sequence patterns**: If you always ask X after Y, X is pre-loaded
- **Benefit**: Common queries become nearly instant

This happens automatically - no configuration needed.

### Performance Tuning Tips

1. **For faster responses**:
   - Use Groq as primary LLM (fastest inference)
   - Enable streaming for long responses
   - Keep cache enabled

2. **For lower memory usage**:
   - Reduce cache sizes in config
   - Disable semantic cache (uses ~500MB for embedding model)
   - Set lower `max_memory_mb` threshold

3. **For offline use**:
   - Use Ollama as LLM provider
   - Disable dashboard if not needed
   - Cache will still work locally

---

*JARVIS v2.0.0 - Phase 5.6 Complete*
