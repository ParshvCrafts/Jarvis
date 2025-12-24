# JARVIS Authentication Guide

JARVIS includes a comprehensive authentication system with face recognition, voice verification, and liveness detection to ensure only authorized users can access the system.

## Authentication Status

| Feature | Library | Status |
|---------|---------|--------|
| Face Recognition | `face_recognition` + OpenCV | ✅ Implemented |
| Voice Verification | `resemblyzer` | ✅ Implemented |
| Liveness Detection | OpenCV (blink + head movement) | ✅ Implemented |
| Session Management | JWT tokens | ✅ Implemented |
| Multi-user Support | Single user (multiple encodings) | ⚠️ Partial |

## Quick Start

### Enable Authentication

By default, authentication is **disabled**. To enable it:

1. Edit `config/settings.yaml`:
```yaml
auth:
  enabled: true
  require_on_startup: true  # Require auth when JARVIS starts
```

2. Install dependencies:
```bash
pip install face_recognition opencv-python resemblyzer
```

3. Enroll your face:
```
You: "Enroll my face"
JARVIS: "Starting face enrollment..."
```

## Features

### Face Recognition

Uses the `face_recognition` library (based on dlib) for accurate face detection and verification.

**Capabilities:**
- Multiple face encodings per user for robustness
- Configurable tolerance (strictness)
- HOG (CPU) or CNN (GPU) detection models
- Real-time face detection with visual feedback

**Configuration:**
```yaml
auth:
  face_recognition:
    enabled: true
    tolerance: 0.5        # Lower = stricter (0.4-0.6 recommended)
    model: "hog"          # "hog" (faster) or "cnn" (more accurate)
    num_jitters: 1        # Re-sampling for encoding accuracy
```

### Voice Verification

Uses `resemblyzer` for speaker embedding and verification.

**Capabilities:**
- Speaker embedding comparison
- Works with any spoken phrase
- Configurable similarity threshold

**Configuration:**
```yaml
auth:
  voice_verification:
    enabled: true
    similarity_threshold: 0.75  # Higher = stricter
    min_audio_duration: 1.5     # Minimum seconds of audio
    sample_rate: 16000
```

### Liveness Detection

Prevents spoofing with photos or videos using:
- **Blink detection** - Detects natural eye blinks
- **Head movement** - Detects natural head movements

**Configuration:**
```yaml
auth:
  liveness_detection:
    enabled: true
    ear_threshold: 0.25       # Eye aspect ratio for blink
    consec_frames: 3          # Frames for blink detection
    head_movement_enabled: true
    timeout: 10               # Seconds before timeout
```

## Voice Commands

### Enrollment

```
"Enroll my face"        - Start face enrollment (captures 5 samples)
"Enroll my voice"       - Start voice enrollment (records 3 samples)
```

### Authentication

```
"Authenticate me"       - Perform full authentication
"Verify my identity"    - Same as authenticate
"Login"                 - Same as authenticate
```

### Session Management

```
"Logout"                - End current session
"Am I authenticated?"   - Check authentication status
```

## Authentication Flow

### Full Authentication

1. **Liveness Check** (if enabled)
   - User must blink naturally
   - Detects head movement
   - Prevents photo/video spoofing

2. **Face Verification** (if enabled)
   - Captures face from camera
   - Compares with enrolled encodings
   - Returns confidence score

3. **Voice Verification** (if enabled)
   - Records voice sample
   - Compares speaker embedding
   - Returns similarity score

4. **Session Creation**
   - Creates JWT session token
   - Sets authorization level based on factors verified

### Authorization Levels

| Level | Requirements | Allowed Commands |
|-------|--------------|------------------|
| LOW | Any single factor | query, search, weather, time |
| MEDIUM | Face + Liveness | app_control, file_operations, browser |
| HIGH | Face + Voice + Liveness | door_unlock, system_settings, iot_control |

## Enrollment Process

### Face Enrollment

1. Start enrollment:
```
You: "Enroll my face"
```

2. JARVIS opens camera preview
3. Position your face in the frame (green rectangle shows detection)
4. Press SPACE to capture each sample
5. Move your head slightly between captures for variety
6. 5 samples are captured by default

### Voice Enrollment

1. Start enrollment:
```
You: "Enroll my voice"
```

2. JARVIS prompts you to speak
3. Speak naturally for 3 seconds
4. Repeat 3 times for accuracy

## Configuration Reference

### Full Settings

```yaml
auth:
  # Master switch - set to false to skip all authentication
  enabled: false
  
  # Require authentication on startup
  require_on_startup: false
  
  # Session timeout in seconds (30 minutes)
  session_timeout: 1800
  
  # Lockout after failed attempts
  max_failed_attempts: 3
  lockout_duration: 300  # 5 minutes
  
  face_recognition:
    enabled: true
    tolerance: 0.5
    model: "hog"
    num_jitters: 1
    
  liveness_detection:
    enabled: true
    ear_threshold: 0.25
    consec_frames: 3
    head_movement_enabled: true
    timeout: 10
    
  voice_verification:
    enabled: true
    similarity_threshold: 0.75
    min_audio_duration: 1.5
    sample_rate: 16000

  authorization_levels:
    low: ["query", "search", "weather", "time", "reminder"]
    medium: ["app_control", "file_operations", "browser", "email"]
    high: ["door_unlock", "system_settings", "delete_files", "iot_control"]
```

## Development Mode

For development, you can disable authentication entirely:

```yaml
auth:
  enabled: false
```

This skips all authentication checks and allows full access.

## Troubleshooting

### "Face recognition not available"

Install the required libraries:
```bash
pip install face_recognition opencv-python numpy
```

On Windows, you may need to install dlib first:
```bash
pip install cmake
pip install dlib
pip install face_recognition
```

### "No face detected"

- Ensure good lighting
- Face the camera directly
- Remove glasses if reflective
- Check camera permissions

### "Face verification failed"

- Re-enroll with more samples
- Try different lighting conditions
- Lower the tolerance (e.g., 0.6)

### "Voice authentication not available"

Install resemblyzer:
```bash
pip install resemblyzer soundfile
```

### "Liveness check failed"

- Blink naturally (not too fast)
- Move your head slightly
- Ensure face is fully visible
- Check for good lighting

## Security Considerations

1. **Biometric Data Storage**
   - Face encodings stored in `data/face_encodings/`
   - Voice prints stored in `data/voice_prints/`
   - Data is pickled numpy arrays (not raw images/audio)

2. **Session Security**
   - JWT tokens with configurable expiry
   - Automatic lockout after failed attempts
   - Sessions invalidated on logout

3. **Liveness Detection**
   - Prevents basic photo attacks
   - Not foolproof against sophisticated attacks
   - Consider additional factors for high-security use

## Multi-User Support

Currently, JARVIS supports a single user with multiple face/voice encodings. True multi-user support (different profiles, preferences per user) is planned for a future release.

**Current behavior:**
- All enrolled faces/voices belong to "the user"
- No user identification (just verification)
- Single set of preferences

## API Reference

### AuthenticationManager

```python
from src.auth import AuthenticationManager

auth = AuthenticationManager(data_dir="data")

# Check enrollment status
status = auth.get_enrollment_status()
# Returns: {face_enrolled, face_count, voice_enrolled, voice_count, ...}

# Enroll face from camera
success, msg = auth.enroll_face_from_camera(num_samples=5)

# Enroll voice from microphone
success, msg = auth.enroll_voice_from_microphone(num_samples=3)

# Authenticate
result = auth.authenticate(
    require_face=True,
    require_voice=False,
    require_liveness=True,
)
# Returns: AuthenticationResult with success, session, confidences

# Check command authorization
authorized, msg = auth.check_command_authorization("door_unlock")

# Logout
auth.logout()
```

### FaceAuthenticator

```python
from src.auth import FaceAuthenticator

face_auth = FaceAuthenticator(encodings_dir="data/face_encodings")

# Check if available
if face_auth.is_available:
    # Enroll a face
    success = face_auth.enroll_face(frame)
    
    # Verify a face
    is_match, confidence = face_auth.verify_face(frame)
    
    # Get enrollment count
    count = face_auth.get_enrollment_count()
```

---

**Need help?** Ask JARVIS: "How do I set up face authentication?"
