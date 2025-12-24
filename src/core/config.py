"""
Configuration management for JARVIS.

This module handles loading and validating configuration from YAML files
and environment variables using Pydantic for type safety.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"


class FaceRecognitionConfig(BaseModel):
    """Face recognition configuration."""
    enabled: bool = True
    tolerance: float = Field(default=0.5, ge=0.0, le=1.0)
    num_jitters: int = Field(default=1, ge=1)
    model: str = Field(default="hog", pattern="^(hog|cnn)$")


class LivenessConfig(BaseModel):
    """Liveness detection configuration."""
    enabled: bool = True
    ear_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    consec_frames: int = Field(default=3, ge=1)
    head_movement_enabled: bool = True
    timeout: int = Field(default=10, ge=1)


class VoiceVerificationConfig(BaseModel):
    """Voice verification configuration."""
    enabled: bool = True
    similarity_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    min_audio_duration: float = Field(default=1.5, ge=0.5)
    sample_rate: int = Field(default=16000, ge=8000)


class AuthorizationLevels(BaseModel):
    """Command authorization levels."""
    low: List[str] = Field(default_factory=lambda: ["query", "search", "weather", "time", "reminder"])
    medium: List[str] = Field(default_factory=lambda: ["app_control", "file_operations", "browser", "email"])
    high: List[str] = Field(default_factory=lambda: ["door_unlock", "system_settings", "delete_files", "iot_control"])


class AuthConfig(BaseModel):
    """Authentication configuration."""
    session_timeout: int = Field(default=1800, ge=60)
    max_failed_attempts: int = Field(default=3, ge=1)
    lockout_duration: int = Field(default=300, ge=60)
    face_recognition: FaceRecognitionConfig = Field(default_factory=FaceRecognitionConfig)
    liveness_detection: LivenessConfig = Field(default_factory=LivenessConfig)
    voice_verification: VoiceVerificationConfig = Field(default_factory=VoiceVerificationConfig)
    authorization_levels: AuthorizationLevels = Field(default_factory=AuthorizationLevels)


class LLMProviderConfig(BaseModel):
    """LLM provider configuration."""
    provider: str
    model: str
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1)
    timeout: int = Field(default=30, ge=1)
    base_url: Optional[str] = None


class FallbackConfig(BaseModel):
    """LLM fallback configuration."""
    enabled: bool = True
    retry_attempts: int = Field(default=2, ge=1)
    retry_delay: float = Field(default=1.0, ge=0.0)


class LLMConfig(BaseModel):
    """LLM configuration."""
    # Make provider configs optional with sensible defaults
    primary: Optional[LLMProviderConfig] = None
    secondary: Optional[LLMProviderConfig] = None
    tertiary: Optional[LLMProviderConfig] = None
    fallback: FallbackConfig = Field(default_factory=FallbackConfig)
    
    # New-style provider configs (from settings.yaml)
    intelligent_routing: bool = True
    cache: Optional[dict] = None
    providers: Optional[dict] = None
    retry: Optional[dict] = None


class WakeWordConfig(BaseModel):
    """Wake word configuration."""
    enabled: bool = True
    phrase: str = "hey jarvis"
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    model_path: str = ""


class STTConfig(BaseModel):
    """Speech-to-text configuration."""
    engine: str = Field(default="faster_whisper", pattern="^(faster_whisper|whisper)$")
    model: str = "base.en"
    device: str = Field(default="cpu", pattern="^(cpu|cuda)$")
    compute_type: str = Field(default="int8", pattern="^(float16|int8|float32)$")
    language: str = "en"


class VADConfig(BaseModel):
    """Voice activity detection configuration."""
    enabled: bool = True
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    min_speech_duration: float = Field(default=0.25, ge=0.0)
    silence_duration: float = Field(default=1.0, ge=0.0)


class TTSConfig(BaseModel):
    """Text-to-speech configuration."""
    engine: str = Field(default="edge_tts", pattern="^(edge_tts|piper|kokoro)$")
    voice: str = "en-US-GuyNeural"
    rate: float = Field(default=1.0, ge=0.5, le=2.0)
    volume: float = Field(default=1.0, ge=0.0, le=1.0)


class AudioConfig(BaseModel):
    """Audio configuration."""
    sample_rate: int = Field(default=16000, ge=8000)
    channels: int = Field(default=1, ge=1, le=2)
    chunk_size: int = Field(default=1024, ge=256)
    input_device: Optional[int] = None
    output_device: Optional[int] = None


class VoiceConfig(BaseModel):
    """Voice pipeline configuration."""
    wake_word: WakeWordConfig = Field(default_factory=WakeWordConfig)
    speech_to_text: STTConfig = Field(default_factory=STTConfig)
    voice_activity_detection: VADConfig = Field(default_factory=VADConfig)
    text_to_speech: TTSConfig = Field(default_factory=TTSConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)


class ConversationMemoryConfig(BaseModel):
    """Conversation memory configuration."""
    max_messages: int = Field(default=20, ge=1)
    window_size: int = Field(default=10, ge=1)


class VectorStoreConfig(BaseModel):
    """Vector store configuration."""
    provider: str = Field(default="chromadb", pattern="^(chromadb|lancedb)$")
    collection_name: str = "jarvis_memory"
    embedding_model: str = "all-MiniLM-L6-v2"
    max_results: int = Field(default=5, ge=1)


class EpisodicMemoryConfig(BaseModel):
    """Episodic memory configuration."""
    db_path: str = "data/episodic.db"
    consolidation_enabled: bool = True
    consolidation_interval: int = Field(default=24, ge=1)


class MemoryConfig(BaseModel):
    """Memory configuration."""
    conversation: ConversationMemoryConfig = Field(default_factory=ConversationMemoryConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    episodic: EpisodicMemoryConfig = Field(default_factory=EpisodicMemoryConfig)


class AgentConfig(BaseModel):
    """Individual agent configuration."""
    enabled: bool = True
    max_iterations: Optional[int] = None
    max_results: Optional[int] = None
    timeout: Optional[int] = None
    execution_timeout: Optional[int] = None
    sandbox: Optional[bool] = None
    allowed_apps: Optional[List[str]] = None
    discovery_timeout: Optional[int] = None
    email_provider: Optional[str] = None


class AgentsConfig(BaseModel):
    """Agents configuration."""
    supervisor: AgentConfig = Field(default_factory=lambda: AgentConfig(max_iterations=10))
    research: AgentConfig = Field(default_factory=lambda: AgentConfig(max_results=5, timeout=30))
    coding: AgentConfig = Field(default_factory=lambda: AgentConfig(execution_timeout=30, sandbox=True))
    system: AgentConfig = Field(default_factory=lambda: AgentConfig(
        allowed_apps=["notepad", "calculator", "browser", "vscode", "terminal"]
    ))
    iot: AgentConfig = Field(default_factory=lambda: AgentConfig(discovery_timeout=10))
    communication: AgentConfig = Field(default_factory=lambda: AgentConfig(email_provider="gmail"))


class IoTDeviceConfig(BaseModel):
    """IoT device configuration."""
    enabled: bool = False
    hostname: str = ""
    port: int = Field(default=80, ge=1, le=65535)
    servo_on_position: Optional[int] = None
    servo_off_position: Optional[int] = None
    servo_unlock_position: Optional[int] = None
    servo_lock_position: Optional[int] = None
    auto_release_timeout: Optional[int] = None
    auth_level: Optional[str] = None


class IoTDevicesConfig(BaseModel):
    """IoT devices configuration."""
    light_switch: IoTDeviceConfig = Field(default_factory=IoTDeviceConfig)
    door_lock: IoTDeviceConfig = Field(default_factory=IoTDeviceConfig)


class IoTConfig(BaseModel):
    """IoT configuration."""
    mdns_enabled: bool = True
    service_type: str = "_jarvis._tcp.local."
    heartbeat_interval: int = Field(default=30, ge=1)
    command_timeout: int = Field(default=10, ge=1)
    devices: IoTDevicesConfig = Field(default_factory=IoTDevicesConfig)


class TelegramConfig(BaseModel):
    """Telegram bot configuration."""
    enabled: bool = False
    allowed_users: List[int] = Field(default_factory=list)
    voice_notes_enabled: bool = True
    location_tracking: bool = False


class ProactiveConfig(BaseModel):
    """Proactive features configuration."""
    enabled: bool = True
    calendar_enabled: bool = False
    weather_enabled: bool = True
    location: str = "Berkeley, CA"
    learning_enabled: bool = True


class SystemConfig(BaseModel):
    """System control configuration."""
    screenshot_enabled: bool = True
    clipboard_enabled: bool = True
    file_operations_enabled: bool = True
    allowed_directories: List[str] = Field(default_factory=lambda: ["~/Documents", "~/Downloads", "~/Desktop"])
    browser_automation_enabled: bool = True
    default_browser: str = "chrome"


class GeneralConfig(BaseModel):
    """General configuration."""
    name: str = "JARVIS"
    version: str = "1.0.0"
    debug: bool = False
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    data_dir: str = "data"
    models_dir: str = "models"


class JarvisConfig(BaseModel):
    """Main JARVIS configuration."""
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    llm: Optional[LLMConfig] = None
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    iot: IoTConfig = Field(default_factory=IoTConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    proactive: ProactiveConfig = Field(default_factory=ProactiveConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)


class EnvSettings(BaseSettings):
    """Environment variables settings."""
    
    # LLM API Keys (FREE TIERS ONLY)
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    
    # Telegram
    telegram_bot_token: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_user_id: Optional[str] = Field(default=None, alias="TELEGRAM_USER_ID")  # String to handle placeholder
    
    @field_validator("telegram_user_id", mode="before")
    @classmethod
    def validate_telegram_user_id(cls, v):
        """Convert telegram_user_id to int if valid, else None."""
        if v is None:
            return None
        if isinstance(v, int):
            return str(v)
        if isinstance(v, str):
            # Check if it's a placeholder or invalid
            if v.startswith("your_") or not v.isdigit():
                return None
            return v
        return None
    
    # IoT
    iot_shared_secret: Optional[str] = Field(default=None, alias="IOT_SHARED_SECRET")
    
    # Email
    gmail_app_password: Optional[str] = Field(default=None, alias="GMAIL_APP_PASSWORD")
    gmail_address: Optional[str] = Field(default=None, alias="GMAIL_ADDRESS")
    
    # Security
    jwt_secret: Optional[str] = Field(default=None, alias="JWT_SECRET")
    encryption_key: Optional[str] = Field(default=None, alias="ENCRYPTION_KEY")
    
    # Optional Services
    openweather_api_key: Optional[str] = Field(default=None, alias="OPENWEATHER_API_KEY")
    google_calendar_credentials_path: Optional[str] = Field(default=None, alias="GOOGLE_CALENDAR_CREDENTIALS_PATH")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def load_yaml_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = CONFIG_DIR / "settings.yaml"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        return {}
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_config(config_path: Path | str | None = None) -> JarvisConfig:
    """
    Load and return the JARVIS configuration.
    
    Merges YAML configuration with environment variables.
    """
    yaml_config = load_yaml_config(config_path)
    return JarvisConfig(**yaml_config)


def get_env_settings() -> EnvSettings:
    """Get environment settings."""
    return EnvSettings()


# Global configuration instances (lazy loaded)
_config: Optional[JarvisConfig] = None
_env_settings: Optional[EnvSettings] = None


def config() -> JarvisConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = get_config()
    return _config


def env() -> EnvSettings:
    """Get the global environment settings instance."""
    global _env_settings
    if _env_settings is None:
        _env_settings = get_env_settings()
    return _env_settings


def ensure_directories() -> None:
    """Ensure required directories exist."""
    directories = [
        DATA_DIR,
        MODELS_DIR,
        DATA_DIR / "face_encodings",
        DATA_DIR / "voice_prints",
        DATA_DIR / "logs",
        DATA_DIR / "recordings",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
