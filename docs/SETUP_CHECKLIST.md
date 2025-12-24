# JARVIS Setup Checklist

Use this checklist to verify your JARVIS installation is complete and all features are working.

---

## Core Setup (Required)

### Prerequisites
- [ ] Python 3.10+ installed
- [ ] Git installed
- [ ] Virtual environment created and activated

### Installation
```bash
# Clone repository (if not done)
git clone <repository-url>
cd Jarvis

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Linux/macOS)
source venv/bin/activate
```

### Dependencies
- [ ] Core dependencies installed
```bash
pip install -r requirements-core.txt
```

### Configuration
- [ ] Environment file created
```bash
copy .env.example .env  # Windows
cp .env.example .env    # Linux/macOS
```

- [ ] GROQ_API_KEY set in `.env`
  - Get from: https://console.groq.com/

### Verification
- [ ] Configuration check passes
```bash
python run.py --check-config
```

- [ ] JARVIS starts in text mode
```bash
python run.py --text
```

- [ ] Basic query works: "Hello, what can you do?"

---

## Weather (No Setup Needed)

**Status: ✅ Works immediately!**

### Verification
- [ ] Current weather works
```
You: What's the weather in Chicago?
Expected: Real weather data with temperature, conditions
```

- [ ] Forecast works
```
You: 7-day forecast for New York
Expected: Daily forecast for next 7 days
```

- [ ] Rain check works
```
You: Will it rain tomorrow in Seattle?
Expected: Precipitation prediction
```

---

## Calendar & Email (Google APIs)

### Google Cloud Setup
- [ ] Google Cloud project created
  - Go to: https://console.cloud.google.com/
  
- [ ] Calendar API enabled
  - APIs & Services → Library → Google Calendar API → Enable

- [ ] Gmail API enabled
  - APIs & Services → Library → Gmail API → Enable

- [ ] OAuth consent screen configured
  - APIs & Services → OAuth consent screen
  - User Type: External
  - Add scopes for Calendar and Gmail

- [ ] OAuth credentials created
  - APIs & Services → Credentials → Create Credentials → OAuth client ID
  - Application type: Desktop app

- [ ] Credentials file saved
  - Download JSON and save as `config/google_credentials.json`

### Calendar Verification
- [ ] First authorization completed
```
You: What's on my calendar today?
Expected: Browser opens for Google sign-in, then shows events
```

- [ ] Create event works
```
You: Schedule a test meeting tomorrow at 3pm
Expected: Event created on calendar
```

### Email Verification
- [ ] Read emails works
```
You: Check my unread emails
Expected: List of recent unread emails
```

- [ ] Send email works (with confirmation)
```
You: Send a test email to myself
Expected: JARVIS asks for confirmation before sending
```

---

## Smart Home

### Option A: MQTT
- [ ] MQTT broker installed (Mosquitto)
```bash
# Windows
choco install mosquitto

# Linux
sudo apt install mosquitto
```

- [ ] Broker running
```bash
mosquitto -v
```

- [ ] paho-mqtt installed
```bash
pip install paho-mqtt
```

- [ ] Configuration in `config/settings.yaml`
```yaml
tools:
  mqtt:
    enabled: true
    broker_host: localhost
    broker_port: 1883
```

### Option B: Home Assistant
- [ ] Home Assistant instance accessible
- [ ] Long-lived access token created
- [ ] Token added to `.env`
```
HOME_ASSISTANT_URL=http://homeassistant.local:8123
HOME_ASSISTANT_TOKEN=your_token_here
```

### Smart Home Verification
- [ ] Device control works
```
You: Turn on the living room lights
Expected: Light turns on (or simulated response if no devices)
```

---

## Documents (RAG)

### Installation
- [ ] ChromaDB installed
```bash
pip install chromadb
```

- [ ] PDF support installed
```bash
pip install pypdf
```

- [ ] DOCX support installed
```bash
pip install python-docx
```

### Setup
- [ ] Documents directory created
```bash
mkdir data/documents
```

### Verification
- [ ] Document ingestion works
```
You: Ingest the document at C:\path\to\test.pdf
Expected: Document processed and indexed
```

- [ ] Document search works
```
You: What does my document say about [topic]?
Expected: Answer with relevant information
```

---

## Voice Mode (Optional)

### Installation
- [ ] Voice dependencies installed
```bash
pip install -r requirements-voice.txt
```

- [ ] Microphone configured and working
- [ ] Speakers/headphones connected

### Verification
- [ ] Voice mode starts
```bash
python run.py
```

- [ ] Wake word detection works
  - Say "Hey Jarvis"
  - Expected: JARVIS responds

- [ ] Voice commands work
  - Say "Hey Jarvis, what time is it?"
  - Expected: JARVIS speaks the time

---

## Mobile App (Optional)

### Installation
- [ ] Node.js installed (v18+)
- [ ] Mobile app dependencies installed
```bash
cd mobile
npm install
```

### Running
- [ ] Development server starts
```bash
npm run dev
```

- [ ] App accessible at http://localhost:3000
- [ ] Can connect to JARVIS backend

---

## Learning & Personalization

### Verification
- [ ] Preferences are saved
```
You: What's the weather?
JARVIS: For which city?
You: Chicago
[Restart JARVIS]
You: What's the weather?
Expected: Uses Chicago automatically
```

- [ ] Preferences database created
  - Check: `data/preferences.db` exists

---

## Conversation Features

### Verification
- [ ] Context tracking works
```
You: What's the weather in Chicago?
You: What about tomorrow?
Expected: Shows tomorrow's forecast for Chicago
```

- [ ] Proactive suggestions appear
```
You: What's the weather in New York?
Expected: Response includes suggestion like "Would you like the forecast for tomorrow?"
```

---

## Performance Dashboard (Optional)

### Verification
- [ ] Dashboard accessible
  - Start JARVIS
  - Open: http://localhost:8080/dashboard
  - Expected: Performance metrics displayed

---

## Quick Status Check

Run this command to see feature status:
```bash
python run.py --check-config
```

Expected output shows:
```
✅ Configuration valid

Features:
  ✅ LLM: Groq
  ✅ LLM: Ollama (local)
  ✅ Voice Pipeline
  ✅ System Control
  ...
```

---

## Troubleshooting

### Common Issues

**"GROQ_API_KEY not set"**
- Add your Groq API key to `.env` file

**"Module not found"**
- Ensure virtual environment is activated
- Run `pip install -r requirements-core.txt`

**"Google authorization failed"**
- Delete `config/google_token.json`
- Ensure OAuth consent screen is configured
- Try authorization again

**"Weather not working"**
- Check internet connection
- Try different city name format

**"Voice not detecting"**
- Check microphone permissions
- Adjust wake word threshold in config

---

## Summary

| Feature | Required Setup | Status |
|---------|---------------|--------|
| Core | GROQ_API_KEY | Required |
| Weather | None | ✅ Ready |
| Calendar | Google Cloud | Optional |
| Email | Google Cloud | Optional |
| Smart Home | MQTT/HA | Optional |
| Documents | pip install | Optional |
| Voice | requirements-voice.txt | Optional |
| Mobile | npm install | Optional |

---

## Next Steps

1. ✅ Complete core setup
2. ✅ Test weather (works immediately)
3. 📋 Set up Google APIs for calendar/email (if needed)
4. 📋 Configure smart home (if you have devices)
5. 📋 Install document support (if needed)
6. 🎉 Enjoy your AI assistant!
