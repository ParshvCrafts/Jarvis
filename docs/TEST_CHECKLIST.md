# JARVIS Test Checklist

Comprehensive testing guide for JARVIS before production deployment.

## Pre-Test Setup

### Environment
- [ ] Python 3.10+ installed
- [ ] Node.js 18+ installed
- [ ] Virtual environment activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured with API keys
- [ ] `config/settings.yaml` reviewed

### Hardware (Optional)
- [ ] Microphone connected and working
- [ ] Speakers/headphones connected
- [ ] ESP32 devices powered and on network

---

## 1. Core System Tests

### 1.1 Startup
- [ ] `python run.py --check-config` passes
- [ ] `python run.py --text` starts without errors
- [ ] Dashboard accessible at http://localhost:8080/dashboard
- [ ] Mobile API accessible at http://localhost:8000/api/docs

### 1.2 LLM Providers
- [ ] Groq provider responds (if configured)
- [ ] Gemini provider responds (if configured)
- [ ] Mistral provider responds (if configured)
- [ ] Provider fallback works when one fails
- [ ] Rate limiting triggers fallback

### 1.3 Text Commands
- [ ] Simple greeting: "Hello JARVIS"
- [ ] Math: "What is 25 * 47?"
- [ ] Time: "What time is it?"
- [ ] System: "Open notepad" (Windows)
- [ ] Complex: "Search for Python tutorials"

---

## 2. Voice System Tests

### 2.1 Wake Word Detection
- [ ] "Hey JARVIS" activates listening
- [ ] False positives are minimal
- [ ] Cooldown period works
- [ ] LED/audio feedback on activation

### 2.2 Speech-to-Text
- [ ] Clear speech transcribes correctly
- [ ] Background noise handled
- [ ] Multiple accents work
- [ ] Silence detection stops recording

### 2.3 Text-to-Speech
- [ ] Responses are spoken clearly
- [ ] Voice selection works
- [ ] Speed adjustment works
- [ ] Interruption stops TTS

### 2.4 Conversation Mode
- [ ] Stays listening after response
- [ ] Times out after 30 seconds
- [ ] Can be manually deactivated

---

## 3. Mobile App Tests

### 3.1 Authentication
- [ ] Login with default credentials (admin/jarvis)
- [ ] Login with custom credentials
- [ ] Invalid credentials show error
- [ ] Token stored after login
- [ ] Protected routes redirect when not logged in
- [ ] Logout clears tokens
- [ ] Token refresh works (wait 15+ minutes)

### 3.2 Home Screen
- [ ] Greeting shows based on time
- [ ] Quick actions send commands
- [ ] Recent commands display
- [ ] System status shows
- [ ] Voice button navigates to Voice screen

### 3.3 Voice Screen
- [ ] Microphone permission requested
- [ ] Recording starts on button tap
- [ ] Audio visualization shows
- [ ] Recording stops on second tap
- [ ] Transcription displays
- [ ] Response displays
- [ ] Text input works as fallback
- [ ] Conversation history scrolls

### 3.4 Devices Screen
- [ ] Device list loads
- [ ] Device status shows (online/offline)
- [ ] Light toggle works
- [ ] Brightness slider works
- [ ] Door unlock requires PIN
- [ ] PIN validation works
- [ ] Lock button works
- [ ] Pull-to-refresh updates list

### 3.5 Settings Screen
- [ ] Settings load correctly
- [ ] Voice toggle works
- [ ] TTS speed slider works
- [ ] Notifications toggle works
- [ ] Cache stats display
- [ ] Clear cache works
- [ ] Registered devices show
- [ ] Logout works

### 3.6 History Screen
- [ ] Command history loads
- [ ] Search filters results
- [ ] Pagination works
- [ ] Tap re-runs command

### 3.7 Offline Mode
- [ ] Offline indicator shows when disconnected
- [ ] Cached data displays offline
- [ ] Commands queue when offline
- [ ] Pending count shows
- [ ] Sync happens when back online

### 3.8 PWA Features
- [ ] App installable on mobile
- [ ] Works in standalone mode
- [ ] Service worker registers
- [ ] Static assets cached

---

## 4. IoT Device Tests

### 4.1 Device Discovery
- [ ] ESP32 devices discovered via mDNS
- [ ] Manual IP configuration works
- [ ] Device appears in device list

### 4.2 Device Control
- [ ] Light on/off commands work
- [ ] Brightness control works
- [ ] Door lock/unlock works
- [ ] Sensor readings display

### 4.3 Real-time Updates
- [ ] State changes reflect immediately
- [ ] WebSocket updates received
- [ ] Mobile app shows changes

### 4.4 Security
- [ ] HMAC authentication works
- [ ] Invalid commands rejected
- [ ] Replay attacks prevented

---

## 5. Performance Tests

### 5.1 Response Times
- [ ] Simple commands < 2 seconds
- [ ] Complex commands < 5 seconds
- [ ] Cached responses < 500ms

### 5.2 Caching
- [ ] Cache hits logged
- [ ] Repeated queries faster
- [ ] Cache stats accurate
- [ ] Cache clear works

### 5.3 Streaming
- [ ] Long responses stream progressively
- [ ] Partial responses display
- [ ] Interruption stops stream

### 5.4 Resource Usage
- [ ] Memory usage stable
- [ ] CPU usage reasonable
- [ ] No memory leaks over time

---

## 6. Security Tests

### 6.1 Authentication
- [ ] JWT tokens expire correctly
- [ ] Refresh tokens work
- [ ] Invalid tokens rejected
- [ ] Rate limiting triggers (60 req/min)

### 6.2 Authorization
- [ ] Protected endpoints require auth
- [ ] Admin-only actions restricted
- [ ] Device-specific tokens work

### 6.3 Input Validation
- [ ] SQL injection prevented
- [ ] XSS prevented
- [ ] Command injection prevented

### 6.4 Sensitive Actions
- [ ] Door unlock requires PIN
- [ ] Delete operations confirm
- [ ] Password change requires old password

---

## 7. Error Handling Tests

### 7.1 Network Errors
- [ ] API timeout handled gracefully
- [ ] WebSocket reconnects automatically
- [ ] Offline mode activates

### 7.2 Invalid Input
- [ ] Empty commands handled
- [ ] Invalid JSON handled
- [ ] Large payloads rejected

### 7.3 System Errors
- [ ] LLM failures show error message
- [ ] IoT failures show error message
- [ ] Graceful degradation works

---

## 8. Integration Tests

### 8.1 End-to-End Voice
1. [ ] Say "Hey JARVIS"
2. [ ] Say "Turn on the lights"
3. [ ] Verify light turns on
4. [ ] Verify spoken confirmation

### 8.2 End-to-End Mobile
1. [ ] Open mobile app
2. [ ] Login
3. [ ] Tap voice button
4. [ ] Record "What's the weather?"
5. [ ] Verify response displays
6. [ ] Navigate to Devices
7. [ ] Toggle a light
8. [ ] Verify state changes

### 8.3 Multi-Device
- [ ] Desktop and mobile work simultaneously
- [ ] State syncs between devices
- [ ] Commands from either device work

---

## Test Results Template

```
Date: ___________
Tester: ___________
Version: ___________

Section 1: Core System
- Startup: PASS / FAIL
- LLM: PASS / FAIL
- Commands: PASS / FAIL

Section 2: Voice
- Wake Word: PASS / FAIL / N/A
- STT: PASS / FAIL / N/A
- TTS: PASS / FAIL / N/A

Section 3: Mobile
- Auth: PASS / FAIL
- Screens: PASS / FAIL
- Offline: PASS / FAIL

Section 4: IoT
- Discovery: PASS / FAIL / N/A
- Control: PASS / FAIL / N/A

Section 5: Performance
- Response Times: PASS / FAIL
- Caching: PASS / FAIL

Section 6: Security
- Auth: PASS / FAIL
- Validation: PASS / FAIL

Notes:
_________________________________
_________________________________
_________________________________
```

---

## Mock Mode Testing

For testing without hardware:

```bash
# Text mode (no microphone)
python run.py --text

# Mobile app with mock devices
# Devices screen shows mock devices automatically
```

Mock devices available:
- `light-1`: Living Room Light
- `door-1`: Front Door

---

*JARVIS Test Checklist v1.0*
