# JARVIS Mobile API Documentation

The Mobile API provides RESTful endpoints and WebSocket communication for mobile app integration with JARVIS.

## Quick Start

### Starting the API

The Mobile API starts automatically with JARVIS:

```bash
# Full mode (voice + API)
python run.py

# Text mode (API still available)
python run.py --text
```

Default endpoints:
- **REST API**: `http://localhost:8000/api/v1/`
- **API Docs**: `http://localhost:8000/api/docs`
- **WebSocket**: `ws://localhost:8000/api/v1/ws`

### Authentication

1. **Login** to get tokens:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "jarvis"}'
```

2. **Use token** in subsequent requests:
```bash
curl http://localhost:8000/api/v1/status \
  -H "Authorization: Bearer <your_access_token>"
```

3. **Refresh token** when expired:
```bash
curl -X POST http://localhost:8000/api/v1/auth/token/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<your_refresh_token>"}'
```

---

## REST API Endpoints

### Authentication (`/api/v1/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/login` | Authenticate and get tokens |
| POST | `/token/refresh` | Refresh access token |
| POST | `/logout` | Revoke current token |
| POST | `/password/change` | Change password |
| GET | `/devices` | List registered devices |
| DELETE | `/devices/{id}` | Revoke device access |

#### POST `/auth/login`

**Request:**
```json
{
  "username": "admin",
  "password": "jarvis",
  "device_name": "My iPhone",
  "device_type": "ios"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900,
  "user_id": "uuid",
  "device_id": "uuid"
}
```

### Commands (`/api/v1/command`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/` | Send text command |
| GET | `/history` | Get command history |

#### POST `/command`

**Request:**
```json
{
  "text": "What's the weather like?",
  "context": {},
  "stream": false
}
```

**Response:**
```json
{
  "command_id": "uuid",
  "text": "What's the weather like?",
  "response": "The weather is sunny with a high of 72°F.",
  "processing_time_ms": 1234.5,
  "cached": false,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Status (`/api/v1/status`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Get system status |

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "uptime_seconds": 3600.5,
  "components": [
    {"name": "jarvis_core", "status": "healthy"},
    {"name": "llm_router", "status": "healthy"},
    {"name": "cache", "status": "healthy"}
  ],
  "cache_stats": {...},
  "resource_usage": {...}
}
```

### Devices (`/api/v1/devices`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List IoT devices |
| GET | `/{id}` | Get device details |
| POST | `/{id}/action` | Control device |

#### POST `/devices/{id}/action`

**Request:**
```json
{
  "action": "on",
  "value": null
}
```

Actions: `on`, `off`, `toggle`, `set_position`, `lock`, `unlock`

**Response:**
```json
{
  "success": true,
  "device_id": "light-1",
  "action": "on",
  "message": "Action 'on' executed on light-1",
  "new_state": {"action": "on"}
}
```

### Voice (`/api/v1/voice`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/transcribe` | Upload audio for STT |
| POST | `/transcribe/base64` | STT with base64 audio |
| GET | `/speak` | Get TTS audio |
| POST | `/speak` | Get TTS as base64 |
| GET | `/voices` | List available voices |
| GET | `/status` | Voice service status |

#### POST `/voice/transcribe`

Upload audio file (wav, mp3, webm, ogg, m4a):

```bash
curl -X POST http://localhost:8000/api/v1/voice/transcribe \
  -H "Authorization: Bearer <token>" \
  -F "file=@recording.wav"
```

**Response:**
```json
{
  "text": "Turn on the lights",
  "confidence": 0.95,
  "language": "en",
  "processing_time_ms": 456.7
}
```

#### GET `/voice/speak`

```bash
curl "http://localhost:8000/api/v1/voice/speak?text=Hello&voice=en-US-GuyNeural" \
  -H "Authorization: Bearer <token>" \
  --output speech.mp3
```

### Settings (`/api/v1/settings`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Get user settings |
| PUT | `/` | Update settings |

**Settings object:**
```json
{
  "voice_enabled": true,
  "tts_voice": "en-US-GuyNeural",
  "tts_speed": 1.0,
  "wake_word_enabled": true,
  "notifications_enabled": true,
  "dark_mode": true,
  "language": "en"
}
```

### Cache (`/api/v1/cache`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stats` | Get cache statistics |
| DELETE | `/` | Clear cache |

---

## WebSocket API

### Connection

Connect with JWT token:
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws?token=<jwt_token>');
```

### Message Format

All messages use JSON:
```json
{
  "type": "command",
  "data": {"text": "Hello JARVIS"},
  "message_id": "optional-uuid"
}
```

### Client → Server Messages

| Type | Data | Description |
|------|------|-------------|
| `command` | `{text: string}` | Send text command |
| `audio_chunk` | `{audio: base64}` | Stream audio for STT |
| `cancel` | `{}` | Cancel current operation |
| `ping` | `{}` | Keep-alive ping |
| `subscribe` | `{topic: string}` | Subscribe to topic |
| `unsubscribe` | `{topic: string}` | Unsubscribe from topic |

### Server → Client Messages

| Type | Data | Description |
|------|------|-------------|
| `response_chunk` | `{chunk: string, index: int}` | Streaming response |
| `response_complete` | `{response: string, processing_time_ms: float}` | Full response |
| `tts_ready` | `{audio_url: string}` | TTS audio available |
| `device_state_changed` | `{device_id: string, state: object}` | IoT update |
| `notification` | `{title: string, message: string}` | Notification |
| `health_alert` | `{alert_type: string, message: string}` | Health warning |
| `pong` | `{timestamp: float}` | Ping response |
| `error` | `{error: string}` | Error message |

### Example: Streaming Command

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws?token=...');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'command',
    data: { text: 'Tell me a story' }
  }));
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  
  if (msg.type === 'response_chunk') {
    console.log('Chunk:', msg.data.chunk);
  } else if (msg.type === 'response_complete') {
    console.log('Done:', msg.data.response);
  }
};
```

---

## Push Notifications (ntfy.sh)

JARVIS uses [ntfy.sh](https://ntfy.sh) for push notifications.

### Setup

1. Install ntfy app on your phone ([iOS](https://apps.apple.com/app/ntfy/id1625396347) / [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy))

2. Subscribe to your topic (shown in API response after login)

3. Notifications are sent automatically for:
   - Command responses (when app not active)
   - IoT alerts (door opened, etc.)
   - Reminders
   - System alerts

### Notification Types

| Type | Priority | Tags |
|------|----------|------|
| Command Response | Default | 🤖 💬 |
| IoT Alert | High | 🏠 ⚠️ |
| Reminder | High | 🔔 🕐 |
| System Alert | High/Max | 💻 ⚠️ |

---

## Rate Limiting

- **60 requests per minute** per IP address
- WebSocket connections are not rate-limited
- Rate limit headers included in responses

---

## Error Handling

All errors return JSON:
```json
{
  "error": "Error type",
  "detail": "Detailed message",
  "code": "ERROR_CODE"
}
```

Common HTTP status codes:
- `400` - Bad request / validation error
- `401` - Unauthorized / invalid token
- `403` - Forbidden / insufficient permissions
- `404` - Not found
- `429` - Rate limit exceeded
- `500` - Internal server error

---

## Security Best Practices

1. **Store tokens securely** - Use secure storage, not localStorage
2. **Refresh tokens proactively** - Before they expire
3. **Use HTTPS in production** - Never send tokens over HTTP
4. **Implement token refresh** - Handle 401 responses gracefully
5. **Register devices** - Track and revoke device access as needed

---

## Configuration

Add to `config/settings.yaml`:

```yaml
api:
  enabled: true
  host: "0.0.0.0"
  port: 8000
  
  # JWT settings
  jwt_secret: "your-secret-key"  # Auto-generated if not set
  access_token_expire_minutes: 15
  refresh_token_expire_days: 7
  
  # Rate limiting
  rate_limit_per_minute: 60
  
  # CORS origins (for PWA)
  cors_origins:
    - "http://localhost:3000"
    - "https://your-domain.com"
```

---

## Dependencies

Required packages (already in requirements.txt):
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `python-jose[cryptography]` - JWT handling
- `passlib[bcrypt]` - Password hashing
- `httpx` - HTTP client (for notifications)

Install if missing:
```bash
pip install python-jose[cryptography] passlib[bcrypt]
```

---

*JARVIS Mobile API v1.0.0 - Phase 6*
