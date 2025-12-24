# JARVIS Tool Setup Guide

This guide covers setting up all Phase 7 agentic tools for JARVIS.

## Table of Contents

- [Weather (No Setup Required)](#weather-no-setup-required)
- [Calendar Setup (Google Calendar)](#calendar-setup-google-calendar)
- [Email Setup (Gmail)](#email-setup-gmail)
- [Smart Home Setup](#smart-home-setup)
- [Documents Setup (RAG)](#documents-setup-rag)

---

## Weather (No Setup Required)

**Status: ✅ Works immediately!**

The weather tool uses [Open-Meteo](https://open-meteo.com/), a free weather API that requires no API key.

### Features
- Current weather for any city worldwide
- 7-day forecast with conditions
- Rain/precipitation predictions
- Automatic caching (30 minutes)

### Example Commands
```
"What's the weather in Chicago?"
"Will it rain tomorrow in Seattle?"
"7-day forecast for New York"
"What's the temperature in London?"
```

### Configuration (Optional)

Edit `config/settings.yaml` to customize:

```yaml
tools:
  weather:
    enabled: true
    cache_ttl: 1800  # 30 minutes
    temperature_unit: fahrenheit  # or celsius
    wind_speed_unit: mph  # or kmh
```

---

## Calendar Setup (Google Calendar)

**Status: ⚙️ Requires Google Cloud setup**

### Prerequisites
- Google account
- Google Cloud Console access

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name it "JARVIS Assistant" (or similar)
4. Click "Create"

### Step 2: Enable Calendar API

1. In your project, go to "APIs & Services" → "Library"
2. Search for "Google Calendar API"
3. Click on it and press "Enable"

### Step 3: Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - User Type: External
   - App name: JARVIS
   - User support email: Your email
   - Developer contact: Your email
   - Scopes: Add `https://www.googleapis.com/auth/calendar`
4. Application type: "Desktop app"
5. Name: "JARVIS Desktop"
6. Click "Create"

### Step 4: Download Credentials

1. Click the download icon next to your OAuth client
2. Save the file as `config/google_credentials.json`

### Step 5: First Authorization

1. Start JARVIS: `python run.py --text`
2. Ask: "What's on my calendar today?"
3. A browser window will open for Google authorization
4. Sign in and grant calendar access
5. Token will be saved for future use

### Example Commands
```
"What's on my calendar today?"
"What meetings do I have tomorrow?"
"Schedule a meeting with John tomorrow at 2pm"
"Cancel my 3pm meeting"
"Am I free on Friday afternoon?"
```

### Configuration

```yaml
tools:
  calendar:
    enabled: true
    credentials_file: config/google_credentials.json
    default_calendar: primary
    default_reminder: 30  # minutes before
```

---

## Email Setup (Gmail)

**Status: ⚙️ Requires Google Cloud setup (same project as Calendar)**

### Prerequisites
- Completed Calendar setup (same Google Cloud project)

### Step 1: Enable Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your JARVIS project
3. Go to "APIs & Services" → "Library"
4. Search for "Gmail API"
5. Click on it and press "Enable"

### Step 2: Update OAuth Scopes

1. Go to "APIs & Services" → "OAuth consent screen"
2. Click "Edit App"
3. Go to "Scopes" section
4. Add these scopes:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/gmail.modify`
5. Save changes

### Step 3: Re-authorize (if needed)

If you already authorized for Calendar, you may need to re-authorize:

1. Delete `config/google_token.json` (if exists)
2. Start JARVIS and ask an email question
3. Complete the authorization flow again

### Example Commands
```
"Check my unread emails"
"Read my latest 5 emails"
"Search emails from John"
"Send an email to john@example.com about the meeting"
"Summarize my inbox"
```

### Configuration

```yaml
tools:
  email:
    enabled: true
    credentials_file: config/google_credentials.json
    max_results: 10
    require_confirmation: true  # Ask before sending
```

### Security Note

⚠️ **Email sending requires confirmation by default.** JARVIS will show you the email content and ask for confirmation before sending.

---

## Smart Home Setup

**Status: ⚙️ Requires MQTT broker or Home Assistant**

Choose one of two options:

### Option A: MQTT Setup

#### Prerequisites
- MQTT broker (e.g., Mosquitto)
- MQTT-compatible devices

#### Step 1: Install Mosquitto (if needed)

**Windows:**
```bash
# Download from https://mosquitto.org/download/
# Or use chocolatey:
choco install mosquitto
```

**Linux:**
```bash
sudo apt install mosquitto mosquitto-clients
```

#### Step 2: Configure JARVIS

Edit `config/settings.yaml`:

```yaml
tools:
  mqtt:
    enabled: true
    broker_host: localhost
    broker_port: 1883
    username: ""  # Optional
    password: ""  # Optional
    topic_prefix: "jarvis"
```

#### Step 3: Install MQTT Library

```bash
pip install paho-mqtt
```

### Option B: Home Assistant Setup

#### Prerequisites
- Home Assistant instance running
- Long-lived access token

#### Step 1: Get Access Token

1. Open Home Assistant
2. Click your profile (bottom left)
3. Scroll to "Long-Lived Access Tokens"
4. Click "Create Token"
5. Name it "JARVIS"
6. Copy the token (you won't see it again!)

#### Step 2: Configure JARVIS

Edit `.env`:
```
HOME_ASSISTANT_URL=http://homeassistant.local:8123
HOME_ASSISTANT_TOKEN=your_long_lived_token_here
```

Edit `config/settings.yaml`:
```yaml
tools:
  home_assistant:
    enabled: true
    url: ${HOME_ASSISTANT_URL}
    verify_ssl: false  # Set true for HTTPS
```

### Example Commands
```
"Turn on the living room lights"
"Turn off all lights"
"Set the thermostat to 72 degrees"
"What's the temperature in the bedroom?"
"Lock the front door"
"Is the garage door open?"
```

---

## Documents Setup (RAG)

**Status: ⚙️ Requires additional packages**

### Step 1: Install Dependencies

```bash
pip install chromadb pypdf python-docx
```

### Step 2: Create Documents Directory

```bash
mkdir data/documents
```

### Step 3: Ingest Documents

Place documents in `data/documents/` or use JARVIS commands:

```
"Ingest the document at C:\path\to\file.pdf"
"Add this PDF to my documents: C:\reports\annual.pdf"
```

### Supported Formats
- PDF (`.pdf`)
- Word Documents (`.docx`)
- Text files (`.txt`)
- Markdown (`.md`)

### Example Commands
```
"What does my lease say about pets?"
"Search my documents for return policy"
"Summarize the main points of my report"
"Find information about vacation days in the employee handbook"
```

### Configuration

```yaml
tools:
  documents:
    enabled: true
    storage_path: data/documents
    chunk_size: 500
    chunk_overlap: 50
    collection_name: jarvis_docs
```

### How It Works

1. **Ingestion**: Documents are split into chunks and embedded
2. **Storage**: Embeddings stored in ChromaDB vector database
3. **Search**: Semantic search finds relevant chunks
4. **Response**: LLM generates answer with source citations

---

## Troubleshooting

### Weather Not Working
- Check internet connection
- Verify city name spelling
- Try with country: "London, UK" vs "London, Ontario"

### Calendar/Email Authorization Failed
- Delete `config/google_token.json`
- Ensure OAuth consent screen is configured
- Check that APIs are enabled in Google Cloud

### Smart Home Devices Not Found
- Verify MQTT broker is running: `mosquitto -v`
- Check Home Assistant URL is accessible
- Verify access token is valid

### Documents Not Searchable
- Ensure ChromaDB is installed: `pip install chromadb`
- Check document was ingested successfully
- Try re-ingesting the document

---

## Quick Reference

| Tool | Setup Required | API Key Needed |
|------|---------------|----------------|
| Weather | None | No |
| Calendar | Google Cloud | No (OAuth) |
| Email | Google Cloud | No (OAuth) |
| MQTT | Broker | No |
| Home Assistant | HA Instance | Token |
| Documents | pip install | No |

---

## Next Steps

After setting up tools, see:
- [Setup Checklist](SETUP_CHECKLIST.md) - Verify all features
- [User Guide](USER_GUIDE.md) - Detailed usage instructions
- [README](../README.md) - Project overview
