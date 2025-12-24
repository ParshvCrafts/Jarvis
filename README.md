# JARVIS - Advanced Personal AI Assistant

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Status-In%20Development-yellow.svg" alt="Status">
</p>

JARVIS is a comprehensive, modular AI assistant system inspired by Iron Man's AI companion. Built with security, reliability, and extensibility in mind, it provides voice control, face recognition, IoT integration, and intelligent task automation.

## 🌟 Features

### 🔐 Security & Authentication
- **Face Recognition** with anti-spoofing (liveness detection via blink/head movement)
- **Voice Verification** using speaker embeddings
- **Multi-factor Authentication** with session management
- **Command Authorization Levels** (low/medium/high security)
- **Secure IoT Communication** with HMAC-SHA256 token authentication

### 🎤 Voice Interface
- **Wake Word Detection** ("Hey Jarvis") using openWakeWord
- **Speech-to-Text** with Faster-Whisper (local, GPU-accelerated)
- **Voice Activity Detection** using Silero VAD
- **Text-to-Speech** with Edge-TTS (natural voices)
- **Interruptible Responses** - stops speaking when you talk

### 🧠 AI Brain
- **Intelligent LLM Router** with FREE providers only:
  - Groq (fast, 14,400 req/day free)
  - Google Gemini (complex reasoning, 1M tokens/min free)
  - Ollama (offline capability, local models)
- **Task-based Routing**: Fast queries → Groq, Complex → Gemini, Local → Ollama
- **Response Caching** with SQLite for repeated queries
- **LangGraph-based Agent System** with specialized sub-agents:
  - Research Agent (web search, weather, multi-source synthesis)
  - Coding Agent (Aider integration, code generation)
  - System Agent (app control, file management)
  - IoT Agent (smart home control)
  - Communication Agent (email, calendar)
- **Memory Systems**:
  - Short-term: Conversation buffer with sliding window
  - Long-term: ChromaDB vector store for semantic search
  - Episodic: SQLite for preferences, routines, history

### 🛠️ Agentic Tools (Phase 7)
- **Weather** (FREE - No API key needed):
  - Current weather for any city worldwide
  - 7-day forecast with conditions
  - Rain/precipitation predictions
  - Automatic location learning
- **Calendar** (FREE - Google Calendar):
  - View today's schedule
  - Create/update/delete events
  - Check availability
  - Natural language date parsing
- **Email** (FREE - Gmail API):
  - Read inbox and search emails
  - Send emails with confirmation
  - Summarize email threads
- **Smart Home** (FREE - MQTT/Home Assistant):
  - Control lights, switches, thermostats
  - Device discovery and status
  - Scene activation
- **Documents** (FREE - ChromaDB RAG):
  - Ingest PDF, DOCX, TXT files
  - Semantic search across documents
  - Q&A with source citations

### 🎓 Learning & Personalization (Phase 7)
- **User Preferences**: Remembers your preferred locations, units, response style
- **Usage Patterns**: Learns your routines and common queries
- **Adaptive Responses**: Adjusts verbosity, formality, and suggestions
- **Location Learning**: Automatically sets default city after repeated use

### 💬 Natural Conversation (Phase 7)
- **Context Tracking**: Maintains conversation state across turns
- **Reference Resolution**: Understands "What about tomorrow?" after weather query
- **Clarification System**: Asks for missing info ("For which city?")
- **Proactive Suggestions**: Offers relevant follow-ups

### 🔮 Proactive Intelligence
- **Geofencing** with OwnTracks integration
- **Routine Learning** from command patterns
- **Context-Aware Responses** based on time and active app
- **Automation Suggestions** based on detected patterns

### 💻 System Control
- Application launching and management
- Window control (focus, minimize, maximize)
- Keyboard/mouse automation
- Screenshot capture
- Clipboard operations
- Volume control
- **Browser Automation** with Playwright:
  - Google Docs integration (create, dictate, format)
  - Web research automation
  - Form filling
- **Development Tools**:
  - Git operations (status, commit, push, pull)
  - VS Code/Windsurf integration
  - Safe terminal command execution

### 🏠 IoT Integration
- ESP32-based light switch control
- ESP32-based door lock control
- mDNS device discovery
- Secure token-based authentication
- Status monitoring and heartbeat

### 📱 Remote Access
- Telegram bot interface
- Voice note processing
- Location-based triggers
- Rich responses with inline keyboards

### ⚡ Performance Optimization (Phase 5)
- **Response Streaming**: Start hearing responses in <1 second
- **Intelligent Caching**: Multi-level cache (Memory → SQLite → Semantic)
- **Command Prediction**: Learns your patterns, pre-loads common queries
- **Performance Dashboard**: Real-time metrics at `http://localhost:8080/dashboard`
- **Parallel Execution**: Concurrent agent operations
- **Resource Monitoring**: Automatic memory management

## 📋 Requirements

- **Python**: 3.11+
- **OS**: Windows 10/11 (primary), Linux/macOS (partial support)
- **Hardware**:
  - Webcam (for face recognition)
  - Microphone (for voice commands)
  - Speakers (for TTS output)
  - Optional: NVIDIA GPU (for faster Whisper)

## 🚀 Quick Start

### 1. Clone and Setup Virtual Environment

```bash
cd "c:\Users\p1a2r\OneDrive\Desktop\Git Hub Projects\Agentic AI\Jarvis"

# Activate virtual environment
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS
```

### 2. Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Install face_recognition (requires CMake and Visual Studio Build Tools on Windows)
# See: https://github.com/ageitgey/face_recognition#installation

# Install Playwright browsers (for web automation)
playwright install
```

### 3. Configure Environment

```bash
# Copy example environment file
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/macOS

# Edit .env with your API keys
```

**Required API Keys:**
- `GROQ_API_KEY` - Get from [Groq Console](https://console.groq.com/)

**Optional API Keys:**
- `ANTHROPIC_API_KEY` - For Claude fallback
- `TELEGRAM_BOT_TOKEN` - For Telegram integration
- `IOT_SHARED_SECRET` - For ESP32 device authentication

### 4. Verify Configuration

```bash
# Check configuration and see which features are enabled
python run.py --check-config
```

### 5. Run JARVIS

```bash
# Full mode with voice (uses all enhanced features)
python run.py

# Text-only mode (no audio hardware needed)
python run.py --text

# Legacy mode (use original non-enhanced modules)
python run.py --legacy
```

## 📁 Project Structure

```
Jarvis/
├── config/
│   └── settings.yaml           # Main configuration file
├── data/                       # Runtime data (created automatically)
│   ├── face_encodings/         # Enrolled face data
│   ├── voice_prints/           # Enrolled voice data
│   ├── chroma_db/              # Vector memory storage
│   ├── llm_cache/              # LLM response cache
│   ├── browser_data/           # Browser session data
│   ├── logs/                   # Application logs
│   └── episodic.db             # SQLite database
├── src/
│   ├── auth/                   # Authentication modules
│   │   ├── face_auth.py        # Face recognition
│   │   ├── voice_auth.py       # Voice verification
│   │   ├── liveness.py         # Anti-spoofing
│   │   ├── session.py          # Session management
│   │   └── auth_manager.py     # Unified auth interface
│   ├── core/                   # Core modules
│   │   ├── config.py           # Configuration management
│   │   ├── logger.py           # Logging setup
│   │   ├── llm.py              # Base LLM integration
│   │   ├── llm_providers.py    # Gemini, Mistral, OpenRouter clients
│   │   └── llm_router.py       # Intelligent LLM routing
│   ├── voice/                  # Voice pipeline
│   │   ├── wake_word.py        # Wake word detection (legacy)
│   │   ├── wake_word_enhanced.py  # Enhanced wake word
│   │   ├── stt.py              # Speech-to-text (legacy)
│   │   ├── stt_enhanced.py     # Enhanced STT with preprocessing
│   │   ├── tts.py              # Text-to-speech
│   │   ├── pipeline.py         # Voice pipeline (legacy)
│   │   └── pipeline_enhanced.py   # Enhanced pipeline with conversation mode
│   ├── agents/                 # Agent system
│   │   ├── base.py             # Base agent classes
│   │   ├── tools.py            # Tool definitions (legacy)
│   │   ├── tools_enhanced.py   # Enhanced tools with Aider, research
│   │   ├── supervisor.py       # Supervisor agent
│   │   └── specialized.py      # Specialized agents
│   ├── memory/                 # Memory systems
│   │   ├── conversation.py     # Short-term memory
│   │   ├── vector_store.py     # Long-term semantic memory
│   │   └── episodic.py         # Structured memory
│   ├── system/                 # System control
│   │   ├── controller.py       # OS integration
│   │   ├── browser.py          # Playwright browser automation
│   │   └── dev_tools.py        # Git, VS Code integration
│   ├── iot/                    # IoT integration
│   │   ├── esp32_controller.py # ESP32 communication (legacy)
│   │   └── esp32_enhanced.py   # Enhanced with mDNS, heartbeat
│   ├── telegram/               # Telegram bot
│   │   ├── bot.py              # Bot implementation (legacy)
│   │   └── bot_enhanced.py     # Enhanced with 2FA, rich UI
│   ├── proactive/              # Proactive intelligence
│   │   └── intelligence.py     # Geofencing, routine learning
│   ├── jarvis.py               # Main application (legacy)
│   └── jarvis_unified.py       # Unified application (recommended)
├── tests/                      # Test suite
├── docs/                       # Documentation
├── scripts/                    # Utility scripts
├── run.py                      # Entry point
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── CHANGELOG.md                # Version history
└── README.md
```

## ⚙️ Configuration

Edit `config/settings.yaml` to customize JARVIS:

### Voice Settings
```yaml
voice:
  wake_word:
    phrase: "hey jarvis"
    threshold: 0.5
  speech_to_text:
    model: "base.en"  # tiny, base, small, medium, large
    device: "cpu"     # cpu or cuda
  text_to_speech:
    voice: "en-US-GuyNeural"
```

### LLM Settings
```yaml
llm:
  primary:
    provider: "groq"
    model: "llama-3.3-70b-versatile"
  secondary:
    provider: "ollama"
    model: "llama3.2"
```

### Authentication Settings
```yaml
auth:
  session_timeout: 1800  # 30 minutes
  face_recognition:
    tolerance: 0.5
  liveness_detection:
    enabled: true
    timeout: 10
```

## 🔧 Hardware Setup (IoT)

### Shopping List
| Item | Purpose | Approx. Price |
|------|---------|---------------|
| ESP32-WROOM-32 DevKit (x2) | Microcontrollers | $10-15 each |
| MG996R Servo (x2) | Light/door actuation | $8-12 each |
| 5V 4A Power Supply | Servo power | $10-15 |
| Jumper Wires | Connections | $5-8 |
| 3M VHB Heavy Duty Tape | Mounting | $10-15 |
| Steel Fishing Line (50lb) | Door cable pull | $5-10 |
| Reed Switch (optional) | Door state detection | $3-5 |

### Wiring Diagram - Light Switch

```
ESP32                    MG996R Servo
┌─────────┐              ┌─────────┐
│         │              │         │
│    GPIO13├─────────────┤ Signal  │ (Orange)
│         │              │         │
│     GND ├──────┬───────┤ GND     │ (Brown)
│         │      │       │         │
└─────────┘      │       │ VCC     │ (Red)
                 │       └────┬────┘
                 │            │
            ┌────┴────────────┴────┐
            │     5V Power Supply  │
            └──────────────────────┘
```

### Flashing ESP32

1. Install Arduino IDE and ESP32 board support
2. Copy code from `src/iot/esp32_controller.py` (see `ESP32_LIGHT_SWITCH_CODE`)
3. Update WiFi credentials and shared secret
4. Flash to ESP32
5. Add device in JARVIS config or let mDNS discover it

## 🎯 Usage Examples

### Voice Commands
- "Hey Jarvis, what's the weather in Chicago?"
- "Hey Jarvis, will it rain tomorrow?"
- "Hey Jarvis, what's on my calendar today?"
- "Hey Jarvis, schedule a meeting tomorrow at 2pm"
- "Hey Jarvis, read my latest emails"
- "Hey Jarvis, turn on the living room lights"
- "Hey Jarvis, open Chrome"
- "Hey Jarvis, search for Python tutorials"
- "Hey Jarvis, take a screenshot"
- "Hey Jarvis, what time is it?"

### Text Mode
```
You: What's the weather in Chicago?

JARVIS: ☀️ Current Weather in Chicago, Illinois
Temperature: 29°F (feels like 22°F)
Conditions: Clear sky
Humidity: 57%
Wind: 5.3 mph WSW

Forecast:
- Sunday: 🌫️ 31°F / 18°F - Foggy
- Monday: 🌧️ 42°F / 29°F - Light drizzle

💡 Would you like the forecast for tomorrow?

You: What about New York?

JARVIS: ☁️ Current Weather in New York, NY
Temperature: 35°F (feels like 28°F)
Conditions: Overcast
...
```

### Conversation Context
```
You: What's the weather?
JARVIS: For which city? (I'll remember your answer for next time)

You: Chicago
JARVIS: ☀️ Chicago: 29°F, Clear sky...

[Next session]
You: What's the weather?
JARVIS: ☀️ Chicago: 32°F... [Remembers your preference!]
```

### Telegram
Send messages or voice notes to your JARVIS Telegram bot for remote access.

## 🔒 Security Considerations

1. **Never commit `.env` file** - Contains sensitive API keys
2. **Use strong shared secrets** for IoT devices
3. **Keep face/voice enrollments secure** - They're your biometric data
4. **Review command authorization levels** in config
5. **Door unlock requires high authorization** - Face + liveness verification

## 🐛 Troubleshooting

### Face Recognition Not Working
```bash
# Windows: Install Visual Studio Build Tools first
# Then install dlib and face_recognition
pip install cmake
pip install dlib
pip install face_recognition
```

### Wake Word Not Detecting
- Check microphone permissions
- Adjust `threshold` in config (lower = more sensitive)
- Ensure quiet environment for initial testing

### LLM Errors
- Verify API keys in `.env`
- Check Ollama is running: `ollama serve`
- Try text mode to isolate voice issues

### ESP32 Not Connecting
- Verify WiFi credentials in firmware
- Check shared secret matches config
- Ensure devices are on same network

## 📈 Roadmap

- [ ] Custom wake word training
- [x] Calendar integration (Google Calendar) ✅ Phase 7
- [x] Email integration (Gmail) ✅ Phase 7
- [x] Weather integration (Open-Meteo) ✅ Phase 7
- [x] Smart home (MQTT/Home Assistant) ✅ Phase 7
- [x] Document Q&A (RAG) ✅ Phase 7
- [x] Learning user patterns ✅ Phase 7
- [ ] Multi-user support
- [ ] Web dashboard
- [ ] Docker containerization

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details.

## 🙏 Acknowledgments

- [OpenWakeWord](https://github.com/dscripka/openWakeWord) - Wake word detection
- [Faster-Whisper](https://github.com/guillaumekln/faster-whisper) - Speech recognition
- [Silero VAD](https://github.com/snakers4/silero-vad) - Voice activity detection
- [Edge-TTS](https://github.com/rany2/edge-tts) - Text-to-speech
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent orchestration
- [ChromaDB](https://github.com/chroma-core/chroma) - Vector storage

---

<p align="center">
  Built with ❤️ for the future of personal AI assistants
</p>
