# JARVIS Architecture

This document provides a comprehensive overview of the JARVIS AI assistant architecture.

## System Overview

```mermaid
flowchart TB
    subgraph Input["Input Layer"]
        MIC[🎤 Microphone]
        TG[📱 Telegram]
        CLI[⌨️ CLI]
    end

    subgraph Voice["Voice Pipeline"]
        WW[Wake Word Detection]
        VAD[Voice Activity Detection]
        STT[Speech-to-Text]
        TTS[Text-to-Speech]
    end

    subgraph Auth["Authentication"]
        FACE[Face Recognition]
        VOICE_AUTH[Voice Verification]
        LIVE[Liveness Detection]
    end

    subgraph Core["Core System"]
        ROUTER[Intent Router]
        LLM[LLM Manager]
        MEMORY[Memory Systems]
        EVENTS[Event Bus]
        HEALTH[Health Monitor]
    end

    subgraph Agents["Agent System"]
        SUPER[Supervisor Agent]
        RESEARCH[Research Agent]
        SYSTEM[System Agent]
        CODE[Coding Agent]
        IOT_AGENT[IoT Agent]
        COMM[Communication Agent]
    end

    subgraph External["External Services"]
        GROQ[Groq API]
        GEMINI[Gemini API]
        MISTRAL[Mistral API]
        OLLAMA[Ollama Local]
        WEB[Web Search]
    end

    subgraph Hardware["Hardware Layer"]
        ESP32[ESP32 Devices]
        LIGHTS[Smart Lights]
        DOORS[Door Locks]
    end

    subgraph Output["Output Layer"]
        SPEAKER[🔊 Speaker]
        TG_OUT[📱 Telegram]
        DISPLAY[🖥️ Display]
    end

    %% Input flow
    MIC --> WW
    WW --> VAD
    VAD --> STT
    TG --> ROUTER
    CLI --> ROUTER

    %% Auth flow
    STT --> Auth
    Auth --> ROUTER

    %% Core processing
    STT --> ROUTER
    ROUTER --> SUPER
    SUPER --> LLM
    LLM --> External

    %% Agent routing
    SUPER --> RESEARCH
    SUPER --> SYSTEM
    SUPER --> CODE
    SUPER --> IOT_AGENT
    SUPER --> COMM

    %% Memory
    ROUTER <--> MEMORY
    SUPER <--> MEMORY

    %% IoT
    IOT_AGENT --> ESP32
    ESP32 --> LIGHTS
    ESP32 --> DOORS

    %% Output
    LLM --> TTS
    TTS --> SPEAKER
    SUPER --> TG_OUT
    SUPER --> DISPLAY

    %% Event bus connections
    EVENTS -.-> Voice
    EVENTS -.-> Core
    EVENTS -.-> Agents
    HEALTH -.-> Core
```

## Component Details

### 1. Input Layer

| Component | Description | Location |
|-----------|-------------|----------|
| Microphone | Audio input for voice commands | Hardware |
| Telegram | Remote command interface | `src/telegram/` |
| CLI | Text-based command interface | `run.py --text` |

### 2. Voice Pipeline

```mermaid
sequenceDiagram
    participant M as Microphone
    participant WW as Wake Word
    participant VAD as VAD
    participant STT as STT
    participant R as Router

    M->>WW: Audio Stream
    WW->>WW: Detect "Hey JARVIS"
    WW->>VAD: Activate
    VAD->>VAD: Detect Speech
    VAD->>STT: Speech Audio
    STT->>R: Transcribed Text
```

| Component | Technology | File |
|-----------|------------|------|
| Wake Word | Porcupine/Custom | `src/voice/wake_word_enhanced.py` |
| VAD | Silero VAD | `src/voice/stt_enhanced.py` |
| STT | Whisper/Groq | `src/voice/stt_enhanced.py` |
| TTS | Edge TTS/pyttsx3 | `src/voice/tts.py` |

### 3. Authentication System

```mermaid
flowchart LR
    subgraph Auth["Multi-Factor Authentication"]
        F[Face Recognition] --> V[Voice Verification]
        V --> L[Liveness Detection]
        L --> D{Decision}
        D -->|Pass| A[Authenticated]
        D -->|Fail| R[Rejected]
    end
```

| Component | Technology | File |
|-----------|------------|------|
| Face Recognition | face_recognition | `src/auth/face_recognition.py` |
| Voice Verification | Speaker embedding | `src/auth/voice_auth.py` |
| Liveness Detection | Motion analysis | `src/auth/liveness.py` |

### 4. Core System

#### LLM Manager

```mermaid
flowchart TB
    subgraph LLM["LLM Manager"]
        R[Router] --> P1[Groq]
        R --> P2[Gemini]
        R --> P3[Mistral]
        R --> P4[OpenRouter]
        R --> P5[Ollama]
        
        P1 --> F{Fallback}
        F -->|Fail| P2
        F -->|Fail| P3
        F -->|Fail| P5
    end
```

| Provider | Use Case | Speed | Cost |
|----------|----------|-------|------|
| Groq | Fast queries | ⚡ Fast | Free tier |
| Gemini | Complex reasoning | Medium | Free tier |
| Mistral | Code generation | Medium | Free tier |
| Ollama | Offline/Privacy | Slow | Free |

#### Memory Systems

```mermaid
flowchart LR
    subgraph Memory["Memory Architecture"]
        C[Conversation Buffer] --> S[Short-term]
        V[Vector Store] --> L[Long-term]
        E[Episodic DB] --> H[Historical]
    end
```

| Type | Technology | Purpose |
|------|------------|---------|
| Conversation | In-memory buffer | Recent context |
| Vector | ChromaDB | Semantic search |
| Episodic | SQLite | Historical events |

### 5. Agent System

```mermaid
flowchart TB
    subgraph Agents["LangGraph Agent System"]
        S[Supervisor] --> |Route| A1[Research]
        S --> |Route| A2[System]
        S --> |Route| A3[Coding]
        S --> |Route| A4[IoT]
        S --> |Route| A5[Communication]
        
        A1 --> |Result| S
        A2 --> |Result| S
        A3 --> |Result| S
        A4 --> |Result| S
        A5 --> |Result| S
    end
```

| Agent | Capabilities | Tools |
|-------|--------------|-------|
| Research | Web search, summarization | Tavily, Wikipedia |
| System | App control, screenshots | pyautogui, subprocess |
| Coding | Code generation, Git | VS Code, Git CLI |
| IoT | Device control | ESP32 HTTP API |
| Communication | Email, messaging | SMTP, Telegram |

### 6. IoT Architecture

```mermaid
flowchart TB
    subgraph JARVIS["JARVIS Server"]
        C[IoT Controller]
        Q[Command Queue]
        S[State Cache]
    end

    subgraph Network["Local Network"]
        M[mDNS Discovery]
    end

    subgraph Devices["ESP32 Devices"]
        D1[Light Controller]
        D2[Door Controller]
    end

    C --> Q
    Q --> M
    M --> D1
    M --> D2
    D1 --> S
    D2 --> S
```

#### ESP32 Firmware Stack

```
┌─────────────────────────────────────┐
│           main.py                   │
│    (HTTP Server & Routes)           │
├─────────────────────────────────────┤
│  wifi_manager  │  http_server       │
│  auth          │  servo_control     │
│  led_status    │  mdns_service      │
│  storage       │  logger            │
├─────────────────────────────────────┤
│         MicroPython                 │
├─────────────────────────────────────┤
│           ESP32                     │
└─────────────────────────────────────┘
```

### 7. Event Bus

```mermaid
flowchart LR
    subgraph Publishers
        V[Voice Pipeline]
        A[Agents]
        I[IoT Controller]
    end

    subgraph EventBus["Event Bus"]
        E[Event Router]
    end

    subgraph Subscribers
        H[Health Monitor]
        L[Logger]
        T[Telegram]
        U[UI]
    end

    V --> E
    A --> E
    I --> E
    E --> H
    E --> L
    E --> T
    E --> U
```

#### Event Types

| Event | Payload | Triggered By |
|-------|---------|--------------|
| `wake_word_detected` | `{confidence}` | Voice Pipeline |
| `command_received` | `{text, source}` | Voice/Telegram |
| `agent_started` | `{agent, query}` | Supervisor |
| `agent_completed` | `{agent, result}` | Agent |
| `device_state_changed` | `{device_id, state}` | IoT Controller |
| `health_check` | `{component, status}` | Health Monitor |

### 8. Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant V as Voice Pipeline
    participant A as Auth
    participant R as Router
    participant S as Supervisor
    participant AG as Agent
    participant L as LLM
    participant T as TTS

    U->>V: "Hey JARVIS, what's the weather?"
    V->>V: Wake word detected
    V->>V: Record speech
    V->>V: Transcribe (STT)
    V->>A: Authenticate
    A->>R: Verified user
    R->>S: Route query
    S->>S: Classify intent
    S->>AG: Delegate to Research Agent
    AG->>L: Generate response
    L->>AG: Weather information
    AG->>S: Result
    S->>T: Speak response
    T->>U: "The weather is..."
```

## Directory Structure

```
jarvis/
├── config/
│   └── settings.yaml       # Main configuration
├── data/
│   ├── logs/              # Application logs
│   ├── memory/            # Persistent memory
│   └── benchmarks/        # Performance data
├── docs/
│   ├── ARCHITECTURE.md    # This file
│   ├── USER_GUIDE.md      # User documentation
│   ├── DEVELOPER_GUIDE.md # Developer documentation
│   └── HARDWARE_SETUP.md  # Hardware guide
├── firmware/
│   └── esp32/             # ESP32 MicroPython firmware
├── scripts/
│   ├── preflight_check.py # System validation
│   ├── benchmark.py       # Performance testing
│   └── service/           # Service installation
├── src/
│   ├── agents/            # LangGraph agents
│   ├── auth/              # Authentication
│   ├── core/              # Core systems
│   ├── iot/               # IoT controller
│   ├── memory/            # Memory systems
│   ├── proactive/         # Proactive features
│   ├── system/            # System control
│   ├── telegram/          # Telegram bot
│   ├── voice/             # Voice pipeline
│   └── jarvis_unified.py  # Main application
├── tests/
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── run.py                 # Entry point
└── requirements.txt       # Dependencies
```

## Configuration

### Environment Variables (.env)

```bash
# LLM Providers
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=...
MISTRAL_API_KEY=...
OPENAI_API_KEY=sk-...

# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_ALLOWED_USERS=123456789

# IoT
IOT_SHARED_SECRET=your_secret_here

# Optional
TAVILY_API_KEY=...
```

### Settings (config/settings.yaml)

```yaml
jarvis:
  name: "JARVIS"
  wake_word: "hey jarvis"
  
voice:
  stt_provider: "groq"
  tts_provider: "edge"
  vad_threshold: 0.5
  
llm:
  default_provider: "groq"
  fallback_providers: ["gemini", "ollama"]
  
agents:
  enabled: ["research", "system", "coding", "iot"]
```

## Security Model

```mermaid
flowchart TB
    subgraph Security["Security Layers"]
        L1[Authentication] --> L2[Authorization]
        L2 --> L3[Input Validation]
        L3 --> L4[Secure Communication]
    end

    subgraph Auth["Authentication"]
        F[Face] & V[Voice] & L[Liveness]
    end

    subgraph Authz["Authorization"]
        W[Whitelist] & R[Rate Limit]
    end

    subgraph Valid["Validation"]
        S[Sanitization] & C[Command Filter]
    end

    subgraph Comm["Communication"]
        H[HMAC Signing] & T[TLS]
    end
```

## Performance Targets

| Metric | Target | Measured |
|--------|--------|----------|
| Wake word latency | < 100ms | TBD |
| STT latency | < 1000ms | TBD |
| LLM response (simple) | < 2000ms | TBD |
| End-to-end (simple) | < 3000ms | TBD |
| End-to-end (complex) | < 8000ms | TBD |

## Scaling Considerations

### Current Limitations
- Single-user design
- Local network IoT only
- No distributed processing

### Future Enhancements
- Multi-user support with profiles
- Cloud IoT integration
- Distributed agent execution
- Mobile app integration

## Related Documentation

- [User Guide](USER_GUIDE.md) - End-user documentation
- [Developer Guide](DEVELOPER_GUIDE.md) - Development documentation
- [Hardware Setup](HARDWARE_SETUP.md) - IoT hardware guide
- [API Reference](API_REFERENCE.md) - Internal API documentation
