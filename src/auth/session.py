"""
Session Management Module for JARVIS.

Handles authenticated sessions with timeout, token generation,
and authorization level tracking.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set

from loguru import logger

# Optional JWT support
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    jwt = None
    logger.warning("PyJWT not installed. Session tokens will use simple format.")


class AuthLevel(Enum):
    """Authorization levels for commands."""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class Session:
    """Represents an authenticated session."""
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    auth_level: AuthLevel
    face_verified: bool = False
    voice_verified: bool = False
    liveness_verified: bool = False
    metadata: Dict = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.now() > self.expires_at
    
    @property
    def is_fully_authenticated(self) -> bool:
        """Check if all authentication factors are verified."""
        return self.face_verified and self.voice_verified and self.liveness_verified
    
    def refresh(self, timeout_seconds: int) -> None:
        """Refresh the session expiry."""
        self.last_activity = datetime.now()
        self.expires_at = self.last_activity + timedelta(seconds=timeout_seconds)
    
    def to_dict(self) -> Dict:
        """Convert session to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "auth_level": self.auth_level.name,
            "face_verified": self.face_verified,
            "voice_verified": self.voice_verified,
            "liveness_verified": self.liveness_verified,
        }


class SessionManager:
    """
    Manages authenticated sessions for JARVIS.
    
    Features:
    - Session creation and validation
    - Automatic timeout handling
    - Authorization level management
    - JWT token generation for IoT devices
    """
    
    def __init__(
        self,
        session_timeout: int = 1800,
        max_failed_attempts: int = 3,
        lockout_duration: int = 300,
        jwt_secret: Optional[str] = None,
    ):
        """
        Initialize the session manager.
        
        Args:
            session_timeout: Session timeout in seconds (default 30 min).
            max_failed_attempts: Max failed auth attempts before lockout.
            lockout_duration: Lockout duration in seconds.
            jwt_secret: Secret for JWT token generation.
        """
        self.session_timeout = session_timeout
        self.max_failed_attempts = max_failed_attempts
        self.lockout_duration = lockout_duration
        self.jwt_secret = jwt_secret or secrets.token_hex(32)
        
        # Active sessions
        self._sessions: Dict[str, Session] = {}
        
        # Failed attempt tracking
        self._failed_attempts: Dict[str, List[datetime]] = {}
        
        # Lockout tracking
        self._lockouts: Dict[str, datetime] = {}
        
        # Command authorization mapping
        self._command_levels: Dict[str, AuthLevel] = {}
    
    def configure_command_levels(
        self,
        low: List[str],
        medium: List[str],
        high: List[str],
    ) -> None:
        """
        Configure authorization levels for commands.
        
        Args:
            low: Commands requiring low authorization.
            medium: Commands requiring medium authorization.
            high: Commands requiring high authorization.
        """
        for cmd in low:
            self._command_levels[cmd] = AuthLevel.LOW
        for cmd in medium:
            self._command_levels[cmd] = AuthLevel.MEDIUM
        for cmd in high:
            self._command_levels[cmd] = AuthLevel.HIGH
        
        logger.debug(f"Configured {len(self._command_levels)} command authorization levels")
    
    def is_locked_out(self, user_id: str = "default") -> bool:
        """Check if user is locked out due to failed attempts."""
        if user_id not in self._lockouts:
            return False
        
        lockout_end = self._lockouts[user_id]
        if datetime.now() > lockout_end:
            del self._lockouts[user_id]
            self._failed_attempts.pop(user_id, None)
            return False
        
        return True
    
    def get_lockout_remaining(self, user_id: str = "default") -> int:
        """Get remaining lockout time in seconds."""
        if user_id not in self._lockouts:
            return 0
        
        remaining = (self._lockouts[user_id] - datetime.now()).total_seconds()
        return max(0, int(remaining))
    
    def record_failed_attempt(self, user_id: str = "default") -> bool:
        """
        Record a failed authentication attempt.
        
        Returns:
            True if user is now locked out.
        """
        now = datetime.now()
        
        if user_id not in self._failed_attempts:
            self._failed_attempts[user_id] = []
        
        # Clean old attempts (older than lockout duration)
        cutoff = now - timedelta(seconds=self.lockout_duration)
        self._failed_attempts[user_id] = [
            t for t in self._failed_attempts[user_id] if t > cutoff
        ]
        
        # Add new attempt
        self._failed_attempts[user_id].append(now)
        
        # Check if should lock out
        if len(self._failed_attempts[user_id]) >= self.max_failed_attempts:
            self._lockouts[user_id] = now + timedelta(seconds=self.lockout_duration)
            logger.warning(f"User {user_id} locked out for {self.lockout_duration}s")
            return True
        
        remaining = self.max_failed_attempts - len(self._failed_attempts[user_id])
        logger.warning(f"Failed auth attempt. {remaining} attempts remaining before lockout.")
        return False
    
    def clear_failed_attempts(self, user_id: str = "default") -> None:
        """Clear failed attempts after successful auth."""
        self._failed_attempts.pop(user_id, None)
        self._lockouts.pop(user_id, None)
    
    def create_session(
        self,
        user_id: str = "default",
        auth_level: AuthLevel = AuthLevel.LOW,
        face_verified: bool = False,
        voice_verified: bool = False,
        liveness_verified: bool = False,
    ) -> Session:
        """
        Create a new authenticated session.
        
        Args:
            user_id: User identifier.
            auth_level: Initial authorization level.
            face_verified: Whether face was verified.
            voice_verified: Whether voice was verified.
            liveness_verified: Whether liveness was verified.
            
        Returns:
            New Session object.
        """
        # Clear any existing session for this user
        self.invalidate_user_sessions(user_id)
        
        now = datetime.now()
        session = Session(
            session_id=secrets.token_urlsafe(32),
            user_id=user_id,
            created_at=now,
            last_activity=now,
            expires_at=now + timedelta(seconds=self.session_timeout),
            auth_level=auth_level,
            face_verified=face_verified,
            voice_verified=voice_verified,
            liveness_verified=liveness_verified,
        )
        
        self._sessions[session.session_id] = session
        self.clear_failed_attempts(user_id)
        
        logger.info(f"Created session {session.session_id[:8]}... for user {user_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID, if valid."""
        session = self._sessions.get(session_id)
        
        if session is None:
            return None
        
        if session.is_expired:
            self.invalidate_session(session_id)
            return None
        
        return session
    
    def get_active_session(self, user_id: str = "default") -> Optional[Session]:
        """Get the active session for a user."""
        for session in self._sessions.values():
            if session.user_id == user_id and not session.is_expired:
                return session
        return None
    
    def validate_session(self, session_id: str) -> bool:
        """Check if a session is valid."""
        return self.get_session(session_id) is not None
    
    def refresh_session(self, session_id: str) -> bool:
        """
        Refresh a session's expiry time.
        
        Returns:
            True if session was refreshed, False if invalid.
        """
        session = self.get_session(session_id)
        if session is None:
            return False
        
        session.refresh(self.session_timeout)
        logger.debug(f"Refreshed session {session_id[:8]}...")
        return True
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a specific session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Invalidated session {session_id[:8]}...")
            return True
        return False
    
    def invalidate_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user."""
        to_remove = [
            sid for sid, s in self._sessions.items()
            if s.user_id == user_id
        ]
        
        for sid in to_remove:
            del self._sessions[sid]
        
        if to_remove:
            logger.info(f"Invalidated {len(to_remove)} sessions for user {user_id}")
        
        return len(to_remove)
    
    def upgrade_session(
        self,
        session_id: str,
        face_verified: Optional[bool] = None,
        voice_verified: Optional[bool] = None,
        liveness_verified: Optional[bool] = None,
    ) -> bool:
        """
        Upgrade a session's authentication factors.
        
        Returns:
            True if session was upgraded.
        """
        session = self.get_session(session_id)
        if session is None:
            return False
        
        if face_verified is not None:
            session.face_verified = face_verified
        if voice_verified is not None:
            session.voice_verified = voice_verified
        if liveness_verified is not None:
            session.liveness_verified = liveness_verified
        
        # Update auth level based on verified factors
        if session.is_fully_authenticated:
            session.auth_level = AuthLevel.HIGH
        elif session.face_verified or session.voice_verified:
            session.auth_level = AuthLevel.MEDIUM
        else:
            session.auth_level = AuthLevel.LOW
        
        logger.info(f"Upgraded session {session_id[:8]}... to {session.auth_level.name}")
        return True
    
    def check_authorization(
        self,
        session_id: str,
        command: str,
    ) -> Tuple[bool, str]:
        """
        Check if a session is authorized for a command.
        
        Args:
            session_id: Session to check.
            command: Command to authorize.
            
        Returns:
            Tuple of (authorized, message).
        """
        session = self.get_session(session_id)
        
        if session is None:
            return False, "Invalid or expired session"
        
        # Refresh session on activity
        session.refresh(self.session_timeout)
        
        # Get required level for command
        required_level = self._command_levels.get(command, AuthLevel.LOW)
        
        if session.auth_level.value >= required_level.value:
            return True, f"Authorized for {command}"
        
        return False, f"Insufficient authorization. Required: {required_level.name}, Current: {session.auth_level.name}"
    
    def generate_jwt_token(
        self,
        session_id: str,
        expires_in: int = 300,
    ) -> Optional[str]:
        """
        Generate a JWT token for IoT device communication.
        
        Args:
            session_id: Session to generate token for.
            expires_in: Token expiry in seconds.
            
        Returns:
            JWT token string or None if invalid session.
        """
        session = self.get_session(session_id)
        if session is None:
            return None
        
        payload = {
            "session_id": session_id,
            "user_id": session.user_id,
            "auth_level": session.auth_level.name,
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
            "iat": datetime.utcnow(),
        }
        
        if not JWT_AVAILABLE:
            # Fallback to simple token format
            import base64
            import json
            token_data = json.dumps(payload, default=str)
            return base64.b64encode(token_data.encode()).decode()
        
        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        return token
    
    def verify_jwt_token(self, token: str) -> Optional[Dict]:
        """
        Verify a JWT token.
        
        Args:
            token: JWT token to verify.
            
        Returns:
            Token payload if valid, None otherwise.
        """
        try:
            if not JWT_AVAILABLE:
                # Fallback to simple token format
                import base64
                import json
                try:
                    token_data = base64.b64decode(token.encode()).decode()
                    payload = json.loads(token_data)
                    # Check expiration manually
                    exp = payload.get("exp")
                    if exp and datetime.fromisoformat(exp) < datetime.utcnow():
                        logger.debug("Token expired")
                        return None
                    if not self.validate_session(payload.get("session_id", "")):
                        return None
                    return payload
                except Exception as e:
                    logger.warning(f"Invalid token: {e}")
                    return None
            
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            
            # Verify session still exists
            if not self.validate_session(payload.get("session_id", "")):
                return None
            
            return payload
        except jwt.ExpiredSignatureError:
            logger.debug("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
    
    def cleanup_expired_sessions(self) -> int:
        """Remove all expired sessions."""
        expired = [
            sid for sid, s in self._sessions.items()
            if s.is_expired
        ]
        
        for sid in expired:
            del self._sessions[sid]
        
        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired sessions")
        
        return len(expired)
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get session information as dictionary."""
        session = self.get_session(session_id)
        if session is None:
            return None
        return session.to_dict()
