"""
Authentication Module for Mobile API.

Provides JWT-based authentication with:
- Access tokens (short-lived, 15 min)
- Refresh tokens (long-lived, 7 days)
- Device registration and management
- Password hashing with bcrypt
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from dataclasses import dataclass, field
from loguru import logger

try:
    from jose import JWTError, jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    JWTError = Exception

# Password hashing - try bcrypt, fallback to sha256
pwd_context = None
HASH_METHOD = None

if JWT_AVAILABLE:
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        # Test if bcrypt works
        pwd_context.hash("test")
        HASH_METHOD = "bcrypt"
    except Exception:
        # Fallback to sha256_crypt
        try:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
            HASH_METHOD = "sha256_crypt"
        except Exception:
            # Manual fallback using hashlib
            import hashlib
            HASH_METHOD = "hashlib"
            
            class SimplePwdContext:
                """Simple password context using hashlib."""
                def hash(self, password: str) -> str:
                    import secrets
                    salt = secrets.token_hex(16)
                    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
                    return f"sha256${salt}${hashed}"
                
                def verify(self, password: str, hashed: str) -> bool:
                    try:
                        parts = hashed.split("$")
                        if len(parts) != 3 or parts[0] != "sha256":
                            return False
                        salt = parts[1]
                        expected = hashlib.sha256((salt + password).encode()).hexdigest()
                        return expected == parts[2]
                    except Exception:
                        return False
            
            pwd_context = SimplePwdContext()


@dataclass
class TokenPair:
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes in seconds


@dataclass
class DeviceInfo:
    """Registered device information."""
    device_id: str
    device_name: str
    device_type: str  # ios, android, web
    user_id: str
    registered_at: datetime
    last_seen: datetime
    push_token: Optional[str] = None
    is_active: bool = True


@dataclass
class User:
    """User information."""
    user_id: str
    username: str
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    devices: List[str] = field(default_factory=list)


class AuthConfig:
    """Authentication configuration."""
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
    ):
        import os
        # Get secret from environment or generate one
        self.secret_key = secret_key or os.environ.get("JARVIS_JWT_SECRET") or secrets.token_urlsafe(32)
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        
        if not os.environ.get("JARVIS_JWT_SECRET") and not secret_key:
            logger.warning(
                "JWT secret auto-generated. Set JARVIS_JWT_SECRET environment variable for production!"
            )


class AuthManager:
    """
    Manages authentication for the Mobile API.
    
    Handles:
    - User authentication
    - JWT token generation and validation
    - Device registration
    - Token refresh
    """
    
    def __init__(self, config: Optional[AuthConfig] = None):
        if not JWT_AVAILABLE:
            logger.warning("JWT libraries not available. Install python-jose and passlib.")
        
        self.config = config or AuthConfig()
        
        # In-memory storage (replace with database in production)
        self._users: Dict[str, User] = {}
        self._devices: Dict[str, DeviceInfo] = {}
        self._refresh_tokens: Dict[str, str] = {}  # token -> user_id
        self._revoked_tokens: set = set()
        
        # Create default admin user if none exists
        self._create_default_user()
    
    def _create_default_user(self) -> None:
        """Create a default admin user for initial setup."""
        import os
        
        if not self._users:
            # Get credentials from environment or use defaults
            default_username = os.environ.get("JARVIS_ADMIN_USER", "admin")
            default_password = os.environ.get("JARVIS_ADMIN_PASSWORD", "jarvis")
            
            self.create_user(default_username, default_password, is_admin=True)
            
            if os.environ.get("JARVIS_ADMIN_PASSWORD"):
                logger.info(f"Created admin user from environment: {default_username}")
            else:
                logger.warning(
                    f"Created default admin user (username: {default_username}, password: jarvis). "
                    "Set JARVIS_ADMIN_USER and JARVIS_ADMIN_PASSWORD environment variables for production!"
                )
    
    def create_user(
        self,
        username: str,
        password: str,
        is_admin: bool = False,
    ) -> Optional[User]:
        """Create a new user."""
        if not JWT_AVAILABLE:
            return None
        
        if username in [u.username for u in self._users.values()]:
            logger.warning(f"User {username} already exists")
            return None
        
        user_id = str(uuid.uuid4())
        hashed_password = pwd_context.hash(password)
        
        user = User(
            user_id=user_id,
            username=username,
            hashed_password=hashed_password,
            is_admin=is_admin,
        )
        
        self._users[user_id] = user
        logger.info(f"Created user: {username}")
        return user
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password."""
        if not JWT_AVAILABLE:
            return None
        
        for user in self._users.values():
            if user.username == username:
                if pwd_context.verify(password, user.hashed_password):
                    if user.is_active:
                        return user
                    logger.warning(f"User {username} is inactive")
                    return None
                logger.warning(f"Invalid password for user {username}")
                return None
        
        logger.warning(f"User {username} not found")
        return None
    
    def create_access_token(
        self,
        user_id: str,
        device_id: Optional[str] = None,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a JWT access token."""
        if not JWT_AVAILABLE:
            return ""
        
        expire = datetime.utcnow() + timedelta(minutes=self.config.access_token_expire_minutes)
        
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
        }
        
        if device_id:
            payload["device_id"] = device_id
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create a refresh token."""
        if not JWT_AVAILABLE:
            return ""
        
        expire = datetime.utcnow() + timedelta(days=self.config.refresh_token_expire_days)
        
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": str(uuid.uuid4()),  # Unique token ID for revocation
        }
        
        token = jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)
        self._refresh_tokens[token] = user_id
        
        return token
    
    def create_token_pair(
        self,
        user_id: str,
        device_id: Optional[str] = None,
    ) -> TokenPair:
        """Create both access and refresh tokens."""
        access_token = self.create_access_token(user_id, device_id)
        refresh_token = self.create_refresh_token(user_id)
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.config.access_token_expire_minutes * 60,
        )
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        if not JWT_AVAILABLE:
            return None
        
        if token in self._revoked_tokens:
            logger.warning("Token has been revoked")
            return None
        
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
            )
            
            if payload.get("type") != token_type:
                logger.warning(f"Invalid token type: expected {token_type}")
                return None
            
            return payload
            
        except JWTError as e:
            logger.warning(f"Token verification failed: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[TokenPair]:
        """Use refresh token to get new access token."""
        payload = self.verify_token(refresh_token, token_type="refresh")
        
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id or user_id not in self._users:
            return None
        
        # Revoke old refresh token and create new pair
        self._revoked_tokens.add(refresh_token)
        if refresh_token in self._refresh_tokens:
            del self._refresh_tokens[refresh_token]
        
        return self.create_token_pair(user_id)
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a token."""
        self._revoked_tokens.add(token)
        if token in self._refresh_tokens:
            del self._refresh_tokens[token]
        return True
    
    def revoke_all_user_tokens(self, user_id: str) -> int:
        """Revoke all tokens for a user."""
        count = 0
        tokens_to_remove = []
        
        for token, uid in self._refresh_tokens.items():
            if uid == user_id:
                self._revoked_tokens.add(token)
                tokens_to_remove.append(token)
                count += 1
        
        for token in tokens_to_remove:
            del self._refresh_tokens[token]
        
        return count
    
    def register_device(
        self,
        user_id: str,
        device_name: str,
        device_type: str,
        push_token: Optional[str] = None,
    ) -> DeviceInfo:
        """Register a new device for a user."""
        device_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        device = DeviceInfo(
            device_id=device_id,
            device_name=device_name,
            device_type=device_type,
            user_id=user_id,
            registered_at=now,
            last_seen=now,
            push_token=push_token,
        )
        
        self._devices[device_id] = device
        
        # Add device to user's device list
        if user_id in self._users:
            self._users[user_id].devices.append(device_id)
        
        logger.info(f"Registered device {device_name} ({device_type}) for user {user_id}")
        return device
    
    def update_device_push_token(self, device_id: str, push_token: str) -> bool:
        """Update push notification token for a device."""
        if device_id not in self._devices:
            return False
        
        self._devices[device_id].push_token = push_token
        return True
    
    def update_device_last_seen(self, device_id: str) -> bool:
        """Update last seen timestamp for a device."""
        if device_id not in self._devices:
            return False
        
        self._devices[device_id].last_seen = datetime.utcnow()
        return True
    
    def get_user_devices(self, user_id: str) -> List[DeviceInfo]:
        """Get all devices for a user."""
        return [d for d in self._devices.values() if d.user_id == user_id and d.is_active]
    
    def revoke_device(self, device_id: str) -> bool:
        """Revoke a device's access."""
        if device_id not in self._devices:
            return False
        
        self._devices[device_id].is_active = False
        return True
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        for user in self._users.values():
            if user.username == username:
                return user
        return None
    
    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """Change user password."""
        if not JWT_AVAILABLE:
            return False
        
        user = self._users.get(user_id)
        if not user:
            return False
        
        if not pwd_context.verify(old_password, user.hashed_password):
            return False
        
        user.hashed_password = pwd_context.hash(new_password)
        
        # Revoke all existing tokens
        self.revoke_all_user_tokens(user_id)
        
        return True


# Singleton instance
_auth_manager: Optional[AuthManager] = None


def get_auth_manager(config: Optional[AuthConfig] = None) -> AuthManager:
    """Get or create the global auth manager."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager(config)
    return _auth_manager
