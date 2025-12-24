"""
Pydantic Models for Mobile API.

Defines request/response schemas for all API endpoints.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Authentication Models
# ============================================================================

class LoginRequest(BaseModel):
    """Login request body."""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)
    device_name: Optional[str] = Field(None, max_length=100)
    device_type: Optional[str] = Field("web", pattern="^(ios|android|web)$")


class LoginResponse(BaseModel):
    """Login response with tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    device_id: Optional[str] = None


class TokenRefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Token refresh response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    old_password: str
    new_password: str = Field(..., min_length=6)


# ============================================================================
# Command Models
# ============================================================================

class CommandRequest(BaseModel):
    """Command request body."""
    text: str = Field(..., min_length=1, max_length=1000)
    context: Optional[Dict[str, Any]] = None
    stream: bool = False


class CommandResponse(BaseModel):
    """Command response."""
    command_id: str
    text: str
    response: str
    processing_time_ms: float
    cached: bool = False
    timestamp: datetime


class CommandHistoryItem(BaseModel):
    """Single command history entry."""
    command_id: str
    text: str
    response: str
    timestamp: datetime
    processing_time_ms: float
    source: str = "mobile"  # mobile, desktop, telegram


class CommandHistoryResponse(BaseModel):
    """Command history response."""
    commands: List[CommandHistoryItem]
    total: int
    page: int
    page_size: int


# ============================================================================
# Status Models
# ============================================================================

class ComponentStatus(str, Enum):
    """Component health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth(BaseModel):
    """Individual component health."""
    name: str
    status: ComponentStatus
    message: Optional[str] = None
    latency_ms: Optional[float] = None


class SystemStatusResponse(BaseModel):
    """System status response."""
    status: ComponentStatus
    version: str
    uptime_seconds: float
    components: List[ComponentHealth]
    cache_stats: Optional[Dict[str, Any]] = None
    resource_usage: Optional[Dict[str, Any]] = None


# ============================================================================
# Device Models
# ============================================================================

class DeviceType(str, Enum):
    """IoT device types."""
    LIGHT_SWITCH = "light_switch"
    DOOR_LOCK = "door_lock"
    SENSOR = "sensor"
    GENERIC = "generic"


class DeviceState(str, Enum):
    """Device states."""
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class IoTDevice(BaseModel):
    """IoT device information."""
    device_id: str
    name: str
    device_type: DeviceType
    state: DeviceState
    is_on: Optional[bool] = None
    position: Optional[int] = None  # 0-100 for dimmers
    last_seen: Optional[datetime] = None
    ip_address: Optional[str] = None


class DeviceListResponse(BaseModel):
    """List of IoT devices."""
    devices: List[IoTDevice]
    total: int


class DeviceActionRequest(BaseModel):
    """Device action request."""
    action: str = Field(..., pattern="^(on|off|toggle|set_position|lock|unlock)$")
    value: Optional[int] = Field(None, ge=0, le=100)  # For set_position


class DeviceActionResponse(BaseModel):
    """Device action response."""
    success: bool
    device_id: str
    action: str
    message: str
    new_state: Optional[Dict[str, Any]] = None


# ============================================================================
# Voice Models
# ============================================================================

class TranscribeResponse(BaseModel):
    """Speech-to-text response."""
    text: str
    confidence: float
    language: Optional[str] = None
    processing_time_ms: float


class SpeakRequest(BaseModel):
    """Text-to-speech request."""
    text: str = Field(..., min_length=1, max_length=5000)
    voice: Optional[str] = None
    speed: float = Field(1.0, ge=0.5, le=2.0)


# ============================================================================
# Settings Models
# ============================================================================

class UserSettings(BaseModel):
    """User settings/preferences."""
    voice_enabled: bool = True
    tts_voice: str = "en-US-GuyNeural"
    tts_speed: float = 1.0
    wake_word_enabled: bool = True
    notifications_enabled: bool = True
    dark_mode: bool = True
    language: str = "en"


class UpdateSettingsRequest(BaseModel):
    """Update settings request."""
    voice_enabled: Optional[bool] = None
    tts_voice: Optional[str] = None
    tts_speed: Optional[float] = Field(None, ge=0.5, le=2.0)
    wake_word_enabled: Optional[bool] = None
    notifications_enabled: Optional[bool] = None
    dark_mode: Optional[bool] = None
    language: Optional[str] = None


# ============================================================================
# Cache Models
# ============================================================================

class CacheStatsResponse(BaseModel):
    """Cache statistics response."""
    enabled: bool
    memory_cache: Dict[str, Any]
    sqlite_cache: Optional[Dict[str, Any]] = None
    semantic_cache: Optional[Dict[str, Any]] = None
    total_hits: int
    total_misses: int
    hit_ratio: float


class ClearCacheRequest(BaseModel):
    """Clear cache request."""
    cache_type: Optional[str] = Field(None, pattern="^(memory|sqlite|semantic|all)$")


# ============================================================================
# WebSocket Models
# ============================================================================

class WSMessageType(str, Enum):
    """WebSocket message types."""
    # Server -> Client
    RESPONSE_CHUNK = "response_chunk"
    RESPONSE_COMPLETE = "response_complete"
    TTS_READY = "tts_ready"
    DEVICE_STATE_CHANGED = "device_state_changed"
    NOTIFICATION = "notification"
    HEALTH_ALERT = "health_alert"
    ERROR = "error"
    PONG = "pong"
    
    # Client -> Server
    AUDIO_CHUNK = "audio_chunk"
    COMMAND = "command"
    CANCEL = "cancel"
    PING = "ping"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"


class WSMessage(BaseModel):
    """WebSocket message format."""
    type: WSMessageType
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message_id: Optional[str] = None


# ============================================================================
# Notification Models
# ============================================================================

class NotificationType(str, Enum):
    """Notification types."""
    COMMAND_RESPONSE = "command_response"
    IOT_ALERT = "iot_alert"
    REMINDER = "reminder"
    SYSTEM_ALERT = "system_alert"


class NotificationRequest(BaseModel):
    """Send notification request."""
    title: str = Field(..., max_length=100)
    message: str = Field(..., max_length=500)
    notification_type: NotificationType = NotificationType.SYSTEM_ALERT
    priority: int = Field(3, ge=1, le=5)  # 1=min, 5=max
    tags: Optional[List[str]] = None


# ============================================================================
# Error Models
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Validation error response."""
    error: str = "Validation Error"
    detail: List[Dict[str, Any]]
