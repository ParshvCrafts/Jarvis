"""Authentication modules for JARVIS."""

from loguru import logger

# Import with graceful fallback for missing dependencies
try:
    from .face_auth import FaceAuthenticator
except ImportError as e:
    logger.warning(f"Face authentication not available: {e}")
    FaceAuthenticator = None

try:
    from .voice_auth import VoiceAuthenticator
except ImportError as e:
    logger.warning(f"Voice authentication not available: {e}")
    VoiceAuthenticator = None

try:
    from .liveness import LivenessDetector
except ImportError as e:
    logger.warning(f"Liveness detection not available: {e}")
    LivenessDetector = None

try:
    from .session import SessionManager
except ImportError as e:
    logger.warning(f"Session manager not available: {e}")
    SessionManager = None

try:
    from .auth_manager import AuthenticationManager
except ImportError as e:
    logger.warning(f"Authentication manager not available: {e}")
    AuthenticationManager = None

__all__ = [
    "FaceAuthenticator",
    "VoiceAuthenticator",
    "LivenessDetector",
    "SessionManager",
    "AuthenticationManager",
]
