"""
JARVIS - Unified Main Application Module (Phase 3)

Integrates ALL enhanced modules with proper:
- Startup sequence with validation
- Graceful shutdown
- Audio feedback
- Configuration validation
- All enhanced features enabled
"""

from __future__ import annotations

import asyncio
import signal
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

# Enable nested event loops (required for LangGraph agents in async context)
try:
    import nest_asyncio
    nest_asyncio.apply()
    logger.debug("nest_asyncio applied for nested event loop support")
except ImportError:
    logger.warning("nest_asyncio not available - nested async calls may fail")

# Core imports
from .core.config import config, env, ensure_directories, PROJECT_ROOT, DATA_DIR
from .core.logger import setup_logging
from .core.llm_router import IntelligentLLMRouter, create_intelligent_router, TaskType

# Performance Integration (Phase 5)
try:
    from .core.performance_integration import (
        PerformanceIntegration,
        IntegrationConfig,
        get_performance_integration,
        init_performance_integration,
    )
    from .core.cache import CacheCategory
    PERFORMANCE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Performance integration not available: {e}")
    PERFORMANCE_AVAILABLE = False
    PerformanceIntegration = None
    IntegrationConfig = None
    CacheCategory = None

# Authentication (optional - requires cv2, numpy)
AUTH_AVAILABLE = False
try:
    from .auth import AuthenticationManager
    AUTH_AVAILABLE = AuthenticationManager is not None
except ImportError as e:
    logger.warning(f"Authentication not available: {e}")
    AuthenticationManager = None

# Enhanced Voice Pipeline (optional - requires numpy, sounddevice)
VOICE_AVAILABLE = False
try:
    from .voice.pipeline_enhanced import EnhancedVoicePipeline, PipelineState, VoiceCommand, ConversationState
    from .voice.stt_enhanced import EnhancedSpeechToText, STTProvider
    from .voice.wake_word_enhanced import EnhancedWakeWordDetector
    from .voice.tts import TextToSpeech
    VOICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Voice pipeline not available: {e}")
    EnhancedVoicePipeline = None
    PipelineState = None
    VoiceCommand = None
    ConversationState = None
    EnhancedSpeechToText = None
    STTProvider = None
    EnhancedWakeWordDetector = None
    TextToSpeech = None

# Memory Systems
try:
    from .memory.conversation import ConversationMemory
    from .memory.vector_store import VectorMemory
    from .memory.episodic import EpisodicMemory
    MEMORY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Memory systems not available: {e}")
    ConversationMemory = None
    VectorMemory = None
    EpisodicMemory = None
    MEMORY_AVAILABLE = False

# Agent System
try:
    from .agents.supervisor import SupervisorAgent
    from .agents.supervisor_enhanced import EnhancedSupervisorAgent
    from .agents.specialized import create_all_agents
    from .agents.tools_enhanced import create_default_registry, ToolRegistry
    AGENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Agent system not available: {e}")
    SupervisorAgent = None
    EnhancedSupervisorAgent = None
    create_all_agents = None
    create_default_registry = None
    ToolRegistry = None
    AGENTS_AVAILABLE = False

# System Control (optional - requires pyautogui, etc.)
SYSTEM_CONTROL_AVAILABLE = False
try:
    from .system.controller import SystemController
    from .system.browser import BrowserManager
    from .system.dev_tools import GitController, VSCodeController, DevToolsManager
    SYSTEM_CONTROL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"System control not available: {e}")
    SystemController = None
    BrowserManager = None
    GitController = None
    VSCodeController = None
    DevToolsManager = None

# Quick Launch (optional)
QUICK_LAUNCH_AVAILABLE = False
try:
    from .system.quick_launch import QuickLaunchManager, get_quick_launch_manager
    QUICK_LAUNCH_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Quick Launch not available: {e}")
    QuickLaunchManager = None
    get_quick_launch_manager = None

# Communication (optional)
COMMUNICATION_AVAILABLE = False
try:
    from .communication import (
        ContactsManager,
        WhatsAppService,
        CommunicationRouter,
        HotkeyListener,
        ActivationManager,
        CONTACTS_AVAILABLE,
        WHATSAPP_AVAILABLE,
        HOTKEY_AVAILABLE,
    )
    COMMUNICATION_AVAILABLE = CONTACTS_AVAILABLE
except ImportError as e:
    logger.debug(f"Communication not available: {e}")
    ContactsManager = None
    WhatsAppService = None
    CommunicationRouter = None
    HotkeyListener = None
    ActivationManager = None
    CONTACTS_AVAILABLE = False
    WHATSAPP_AVAILABLE = False
    HOTKEY_AVAILABLE = False

# IoT (optional - requires zeroconf)
IOT_AVAILABLE = False
try:
    from .iot.esp32_enhanced import EnhancedESP32Controller, DeviceType
    IOT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"IoT control not available: {e}")
    EnhancedESP32Controller = None
    DeviceType = None

# Proactive Intelligence (optional)
PROACTIVE_AVAILABLE = False
try:
    from .proactive.intelligence import ProactiveIntelligence
    PROACTIVE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Proactive intelligence not available: {e}")
    ProactiveIntelligence = None

# Academic Features (optional)
ACADEMIC_AVAILABLE = False
try:
    from .academic import AcademicManager, CANVAS_AVAILABLE, POMODORO_AVAILABLE
    ACADEMIC_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Academic features not available: {e}")
    AcademicManager = None
    CANVAS_AVAILABLE = False
    POMODORO_AVAILABLE = False

# Productivity Features (Phase 2)
PRODUCTIVITY_AVAILABLE = False
try:
    from .productivity import ProductivityManager, MUSIC_AVAILABLE, JOURNAL_AVAILABLE
    PRODUCTIVITY_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Productivity features not available: {e}")
    ProductivityManager = None
    MUSIC_AVAILABLE = False
    JOURNAL_AVAILABLE = False

# Career Features (Phase 3)
CAREER_AVAILABLE = False
try:
    from .career import CareerManager, CAREER_MANAGER_AVAILABLE
    CAREER_AVAILABLE = CAREER_MANAGER_AVAILABLE
except ImportError as e:
    logger.debug(f"Career features not available: {e}")
    CareerManager = None

# Finance Features (Investment Advisor)
FINANCE_AVAILABLE = False
try:
    from .finance import FinanceManager, FINANCE_MANAGER_AVAILABLE
    FINANCE_AVAILABLE = FINANCE_MANAGER_AVAILABLE
except ImportError as e:
    logger.debug(f"Finance features not available: {e}")
    FinanceManager = None

# Research Features (Advanced Paper Writing)
RESEARCH_AVAILABLE = False
try:
    from .research import ResearchManager, RESEARCH_AVAILABLE as _RESEARCH_AVAILABLE
    RESEARCH_AVAILABLE = _RESEARCH_AVAILABLE
except ImportError as e:
    logger.debug(f"Research features not available: {e}")
    ResearchManager = None

# Scholarship Features (Essay Generation & Application Tracking)
SCHOLARSHIP_AVAILABLE = False
try:
    from .scholarship import ScholarshipManager, ScholarshipConfig, SCHOLARSHIP_AVAILABLE as _SCHOLARSHIP_AVAILABLE
    SCHOLARSHIP_AVAILABLE = _SCHOLARSHIP_AVAILABLE
except ImportError as e:
    logger.debug(f"Scholarship features not available: {e}")
    ScholarshipManager = None
    ScholarshipConfig = None

# Telegram (imported conditionally)
TELEGRAM_AVAILABLE = False
try:
    from .telegram.bot_enhanced import EnhancedTelegramBot
    TELEGRAM_AVAILABLE = True
except ImportError:
    pass

# Mobile API (Phase 6)
MOBILE_API_AVAILABLE = False
try:
    from .api import create_app, API_AVAILABLE
    from .api.routes import set_jarvis_instance
    from .api.websocket import set_websocket_jarvis
    from .api.voice import set_voice_jarvis
    MOBILE_API_AVAILABLE = API_AVAILABLE
except ImportError as e:
    logger.warning(f"Mobile API not available: {e}")


class StartupState(Enum):
    """Application startup states."""
    INITIALIZING = "initializing"
    LOADING_CONFIG = "loading_config"
    VALIDATING_CONFIG = "validating_config"
    INITIALIZING_LLM = "initializing_llm"
    INITIALIZING_AUTH = "initializing_auth"
    INITIALIZING_VOICE = "initializing_voice"
    INITIALIZING_AGENTS = "initializing_agents"
    INITIALIZING_IOT = "initializing_iot"
    INITIALIZING_TELEGRAM = "initializing_telegram"
    READY = "ready"
    ERROR = "error"


@dataclass
class ConfigValidationResult:
    """Result of configuration validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    features_enabled: Dict[str, bool] = field(default_factory=dict)
    
    def __str__(self) -> str:
        lines = []
        if self.valid:
            lines.append("✅ Configuration valid")
        else:
            lines.append("❌ Configuration invalid")
        
        if self.errors:
            lines.append("\nErrors:")
            for e in self.errors:
                lines.append(f"  ❌ {e}")
        
        if self.warnings:
            lines.append("\nWarnings:")
            for w in self.warnings:
                lines.append(f"  ⚠️ {w}")
        
        lines.append("\nFeatures:")
        for feature, enabled in self.features_enabled.items():
            status = "✅" if enabled else "❌"
            lines.append(f"  {status} {feature}")
        
        return "\n".join(lines)


class JarvisUnified:
    """
    Unified JARVIS application with all enhanced features.
    
    Features:
    - Intelligent LLM routing with 5 providers
    - Enhanced voice pipeline with conversation mode
    - Interruptible TTS
    - Proactive intelligence
    - Browser automation
    - Git/VS Code integration
    - Enhanced Telegram bot
    - IoT with mDNS discovery
    """
    
    VERSION = "2.0.0"
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize JARVIS.
        
        Args:
            config_path: Optional path to configuration file.
        """
        self._startup_state = StartupState.INITIALIZING
        
        # Load configuration
        self._config = config()
        self._env = env()
        
        # Ensure directories exist
        ensure_directories()
        
        # Setup logging
        setup_logging(self._config)
        
        logger.info("=" * 60)
        logger.info(f"JARVIS v{self.VERSION} - Initializing...")
        logger.info("=" * 60)
        
        # Component references (lazy loaded)
        self._llm_router: Optional[IntelligentLLMRouter] = None
        self._auth_manager: Optional[AuthenticationManager] = None
        self._voice_pipeline: Optional[EnhancedVoicePipeline] = None
        self._tts: Optional[TextToSpeech] = None
        self._supervisor: Optional[SupervisorAgent] = None
        self._tool_registry: Optional[ToolRegistry] = None
        self._conversation_memory: Optional[ConversationMemory] = None
        self._vector_memory: Optional[VectorMemory] = None
        self._episodic_memory: Optional[EpisodicMemory] = None
        self._system_controller: Optional[SystemController] = None
        self._browser: Optional[BrowserManager] = None
        self._git_manager: Optional[GitController] = None
        self._vscode: Optional[VSCodeController] = None
        self._quick_launch: Optional[QuickLaunchManager] = None
        self._iot_controller: Optional[EnhancedESP32Controller] = None
        self._proactive: Optional[ProactiveIntelligence] = None
        self._telegram_bot: Optional[EnhancedTelegramBot] = None
        
        # Communication (contacts, WhatsApp, hotkey)
        self._contacts_manager: Optional[ContactsManager] = None
        self._whatsapp_service: Optional[WhatsAppService] = None
        self._communication_router: Optional[CommunicationRouter] = None
        self._hotkey_listener: Optional[HotkeyListener] = None
        
        # Performance Integration (Phase 5)
        self._performance: Optional[PerformanceIntegration] = None
        
        # Academic Features
        self._academic: Optional[AcademicManager] = None
        
        # Productivity Features (Phase 2)
        self._productivity: Optional[ProductivityManager] = None
        
        # Career Features (Phase 3)
        self._career: Optional[CareerManager] = None
        
        # Finance Features (Investment Advisor)
        self._finance: Optional[FinanceManager] = None
        
        # Research Features (Advanced Paper Writing)
        self._research: Optional[ResearchManager] = None
        
        # Scholarship Features (Essay Generation & Application Tracking)
        self._scholarship: Optional[ScholarshipManager] = None
        
        # Mobile API (Phase 6)
        self._api_app = None
        self._api_server = None
        self._api_task = None
        
        # State
        self._running = False
        self._authenticated = False
        self._current_user: Optional[str] = None
        self._current_language: str = "en"  # Multilingual support
        self._streaming_enabled = True  # Can be toggled
    
    # =========================================================================
    # Configuration Validation
    # =========================================================================
    
    def validate_config(self) -> ConfigValidationResult:
        """
        Validate configuration and check available features.
        
        Returns:
            ConfigValidationResult with validation status.
        """
        self._startup_state = StartupState.VALIDATING_CONFIG
        
        result = ConfigValidationResult(valid=True)
        
        # Check LLM providers
        llm_available = False
        
        if self._env.groq_api_key:
            result.features_enabled["LLM: Groq"] = True
            llm_available = True
        else:
            result.features_enabled["LLM: Groq"] = False
            result.warnings.append("GROQ_API_KEY not set - Groq provider disabled")
        
        if self._env.gemini_api_key:
            result.features_enabled["LLM: Gemini"] = True
            llm_available = True
        else:
            result.features_enabled["LLM: Gemini"] = False
        
        # Ollama is always potentially available (local)
        result.features_enabled["LLM: Ollama (local)"] = True
        llm_available = True
        
        if not llm_available:
            result.valid = False
            result.errors.append("No LLM providers available - at least one API key required")
        
        # Check Telegram
        if self._env.telegram_bot_token and self._config.telegram.enabled:
            if self._config.telegram.allowed_users:
                result.features_enabled["Telegram Bot"] = True
            else:
                result.features_enabled["Telegram Bot"] = False
                result.warnings.append("Telegram enabled but no allowed_users configured")
        else:
            result.features_enabled["Telegram Bot"] = False
        
        # Check IoT
        if self._env.iot_shared_secret:
            result.features_enabled["IoT Control"] = True
        else:
            result.features_enabled["IoT Control"] = False
            result.warnings.append("IOT_SHARED_SECRET not set - IoT disabled")
        
        # Check authentication
        if self._env.jwt_secret:
            result.features_enabled["Authentication"] = True
        else:
            result.features_enabled["Authentication"] = False
            result.warnings.append("JWT_SECRET not set - using default (insecure)")
        
        # Voice features (always available if dependencies installed)
        result.features_enabled["Voice Pipeline"] = True
        result.features_enabled["Wake Word Detection"] = True
        result.features_enabled["Speech-to-Text"] = True
        result.features_enabled["Text-to-Speech"] = True
        
        # System features
        result.features_enabled["System Control"] = True
        result.features_enabled["Browser Automation"] = True
        result.features_enabled["Git Integration"] = True
        result.features_enabled["Proactive Intelligence"] = True
        
        # Performance features (Phase 5)
        if PERFORMANCE_AVAILABLE:
            perf_config = getattr(self._config, 'performance', None)
            if perf_config:
                result.features_enabled["LLM Streaming"] = getattr(perf_config.streaming, 'enabled', True)
                result.features_enabled["Intelligent Cache"] = getattr(self._config.cache, 'enabled', True)
                result.features_enabled["Performance Dashboard"] = getattr(self._config.dashboard, 'enabled', True)
            else:
                result.features_enabled["LLM Streaming"] = True
                result.features_enabled["Intelligent Cache"] = True
                result.features_enabled["Performance Dashboard"] = True
        else:
            result.features_enabled["LLM Streaming"] = False
            result.features_enabled["Intelligent Cache"] = False
            result.features_enabled["Performance Dashboard"] = False
            result.warnings.append("Performance optimization modules not available")
        
        return result
    
    # =========================================================================
    # Component Initialization
    # =========================================================================
    
    def _init_llm(self) -> IntelligentLLMRouter:
        """Initialize intelligent LLM router."""
        if self._llm_router is None:
            self._startup_state = StartupState.INITIALIZING_LLM
            logger.info("Initializing intelligent LLM router...")
            
            self._llm_router = create_intelligent_router(
                groq_api_key=self._env.groq_api_key,
                gemini_api_key=self._env.gemini_api_key,
                ollama_base_url=self._env.ollama_base_url,
                cache_dir=DATA_DIR / "llm_cache",
            )
            
            status = self._llm_router.get_status()
            available = [name for name, info in status["providers"].items() if info["available"]]
            logger.info(f"Available LLM providers: {available}")
        
        return self._llm_router
    
    def _init_auth(self) -> AuthenticationManager:
        """Initialize authentication manager."""
        if self._auth_manager is None:
            self._startup_state = StartupState.INITIALIZING_AUTH
            logger.info("Initializing authentication manager...")
            
            auth_config = self._config.auth
            
            self._auth_manager = AuthenticationManager(
                data_dir=DATA_DIR,
                face_config={
                    "tolerance": auth_config.face_recognition.tolerance,
                    "model": auth_config.face_recognition.model,
                    "num_jitters": auth_config.face_recognition.num_jitters,
                },
                voice_config={
                    "similarity_threshold": auth_config.voice_verification.similarity_threshold,
                    "min_audio_duration": auth_config.voice_verification.min_audio_duration,
                },
                liveness_config={
                    "ear_threshold": auth_config.liveness_detection.ear_threshold,
                    "consec_frames": auth_config.liveness_detection.consec_frames,
                    "head_movement_enabled": auth_config.liveness_detection.head_movement_enabled,
                    "timeout": auth_config.liveness_detection.timeout,
                },
                session_config={
                    "session_timeout": auth_config.session_timeout,
                    "max_failed_attempts": auth_config.max_failed_attempts,
                    "lockout_duration": auth_config.lockout_duration,
                    "jwt_secret": self._env.jwt_secret or "default-insecure-secret",
                    "authorization_levels": {
                        "low": auth_config.authorization_levels.low,
                        "medium": auth_config.authorization_levels.medium,
                        "high": auth_config.authorization_levels.high,
                    },
                },
            )
            
            status = self._auth_manager.get_enrollment_status()
            logger.info(f"Auth status: {status}")
        
        return self._auth_manager
    
    def _init_voice(self) -> EnhancedVoicePipeline:
        """Initialize enhanced voice pipeline."""
        if self._voice_pipeline is None:
            self._startup_state = StartupState.INITIALIZING_VOICE
            logger.info("Initializing enhanced voice pipeline...")
            
            voice_config = self._config.voice
            
            # Initialize TTS separately for direct access
            self._tts = TextToSpeech(
                voice=voice_config.text_to_speech.voice,
                rate=voice_config.text_to_speech.rate,
            )
            
            # Create enhanced pipeline with dict configs
            self._voice_pipeline = EnhancedVoicePipeline(
                wake_word_config={
                    "phrase": voice_config.wake_word.phrase,
                    "threshold": voice_config.wake_word.threshold,
                    "model_path": voice_config.wake_word.model_path or None,
                    "min_consecutive": 2,  # Require 2 consecutive detections
                },
                stt_config={
                    "model": voice_config.speech_to_text.model,
                    "device": voice_config.speech_to_text.device,
                    "language": voice_config.speech_to_text.language,
                },
                tts_config={
                    "engine": voice_config.text_to_speech.engine,
                    "voice": voice_config.text_to_speech.voice,
                    "rate": voice_config.text_to_speech.rate,
                },
                conversation_timeout=30.0,  # Stay listening for 30s
                groq_api_key=self._env.groq_api_key,
            )
            
            # Set callbacks
            self._voice_pipeline.set_callbacks(
                on_wake_word=self._on_wake_word,
                on_command=self._on_voice_command,
                on_state_change=self._on_pipeline_state_change,
                on_error=self._on_pipeline_error,
            )
            
            logger.info("Enhanced voice pipeline initialized")
        
        return self._voice_pipeline
    
    def _init_memory(self) -> None:
        """Initialize memory systems."""
        logger.info("Initializing memory systems...")
        
        memory_config = self._config.memory
        
        # Conversation memory
        self._conversation_memory = ConversationMemory(
            max_messages=memory_config.conversation.max_messages,
            window_size=memory_config.conversation.window_size,
            llm_manager=self._init_llm(),
        )
        
        # Vector memory
        self._vector_memory = VectorMemory(
            persist_directory=DATA_DIR / "chroma_db",
            collection_name=memory_config.vector_store.collection_name,
            embedding_model=memory_config.vector_store.embedding_model,
            max_results=memory_config.vector_store.max_results,
        )
        
        # Episodic memory
        self._episodic_memory = EpisodicMemory(
            db_path=DATA_DIR / memory_config.episodic.db_path,
        )
        
        logger.info("Memory systems initialized")
    
    def _init_agents(self) -> SupervisorAgent:
        """Initialize agent system with enhanced supervisor and tools."""
        if self._supervisor is None:
            self._startup_state = StartupState.INITIALIZING_AGENTS
            logger.info("Initializing agent system...")
            
            llm = self._init_llm()
            
            # Create enhanced tool registry
            self._tool_registry = create_default_registry()
            
            # Create specialized agents
            agents = create_all_agents(llm)
            
            # Initialize memory for context engineering
            self._init_memory()
            
            # Use enhanced supervisor with context engineering
            self._supervisor = EnhancedSupervisorAgent(
                llm_manager=llm,
                agents=agents,
                max_iterations=self._config.agents.supervisor.max_iterations or 10,
                memory_store=self._vector_memory,  # For long-term recall
            )
            
            logger.info(f"Initialized enhanced supervisor with {len(agents)} specialized agents")
        
        return self._supervisor
    
    def _init_system(self) -> None:
        """Initialize system control components."""
        logger.info("Initializing system control...")
        
        # System controller
        self._system_controller = SystemController(
            allowed_apps=self._config.agents.system.allowed_apps,
            screenshot_dir=DATA_DIR / "screenshots",
        )
        
        # Browser automation
        self._browser = BrowserManager(
            headless=False,
            user_data_dir=DATA_DIR / "browser_data",
        )
        
        # Git manager
        self._git_manager = GitController()
        
        # VS Code integration
        self._vscode = VSCodeController()
        
        # Quick Launch system
        if QUICK_LAUNCH_AVAILABLE:
            quick_launch_config = getattr(self._config, 'quick_launch', None)
            if quick_launch_config and getattr(quick_launch_config, 'enabled', True):
                db_path = getattr(quick_launch_config, 'db_path', 'data/quick_launch.db')
                youtube_config = getattr(quick_launch_config, 'youtube', None)
                auto_play = getattr(youtube_config, 'auto_play', False) if youtube_config else False
                
                self._quick_launch = QuickLaunchManager(
                    db_path=DATA_DIR.parent / db_path,
                    youtube_auto_play=auto_play,
                )
                logger.info("Quick Launch system initialized")
        
        # Communication system (contacts, WhatsApp, hotkey)
        self._init_communication()
        
        # Academic features (Canvas, Pomodoro, etc.)
        self._init_academic()
        
        logger.info("System control initialized")
    
    def _init_communication(self) -> None:
        """Initialize communication system (contacts, WhatsApp, hotkey)."""
        if not COMMUNICATION_AVAILABLE:
            return
        
        comm_config = getattr(self._config, 'communication', None)
        if not comm_config:
            return
        
        # Contacts Manager
        contacts_config = getattr(comm_config, 'contacts', None)
        if contacts_config and getattr(contacts_config, 'enabled', True):
            db_path = getattr(contacts_config, 'db_path', 'data/contacts.db')
            country_code = getattr(contacts_config, 'default_country_code', '+1')
            
            self._contacts_manager = ContactsManager(
                db_path=DATA_DIR.parent / db_path,
                default_country_code=country_code,
            )
            logger.info(f"Contacts manager initialized ({self._contacts_manager.get_contact_count()} contacts)")
        
        # WhatsApp Service
        whatsapp_config = getattr(comm_config, 'whatsapp', None)
        if whatsapp_config and getattr(whatsapp_config, 'enabled', True) and self._contacts_manager:
            auto_send = getattr(whatsapp_config, 'auto_send', False)
            use_web = getattr(whatsapp_config, 'use_web_whatsapp', True)
            confirm = getattr(whatsapp_config, 'confirm_before_send', True)
            
            self._whatsapp_service = WhatsAppService(
                contacts_manager=self._contacts_manager,
                auto_send=auto_send,
                use_web_whatsapp=use_web,
            )
            
            # Communication Router
            self._communication_router = CommunicationRouter(
                contacts_manager=self._contacts_manager,
                whatsapp_service=self._whatsapp_service,
                confirm_before_send=confirm,
            )
            logger.info("WhatsApp service initialized")
        
        # Hotkey Listener
        hotkey_config = getattr(comm_config, 'hotkey', None)
        if hotkey_config and getattr(hotkey_config, 'enabled', True) and HOTKEY_AVAILABLE:
            key_combo = getattr(hotkey_config, 'key_combination', 'win+j')
            
            self._hotkey_listener = HotkeyListener(
                hotkey=key_combo,
                callback=self._on_hotkey_activation,
                enabled=True,
            )
            logger.info(f"Hotkey listener configured: {key_combo}")
    
    def _init_academic(self) -> None:
        """Initialize academic features (Canvas, Pomodoro, etc.)."""
        if not ACADEMIC_AVAILABLE:
            return
        
        academic_config = getattr(self._config, 'academic', None)
        if not academic_config or not getattr(academic_config, 'enabled', True):
            return
        
        # Convert config to dict for AcademicManager
        config_dict = {
            'canvas': {
                'enabled': getattr(getattr(academic_config, 'canvas', None), 'enabled', True),
                'base_url': getattr(getattr(academic_config, 'canvas', None), 'base_url', None),
            } if hasattr(academic_config, 'canvas') else {},
            'pomodoro': {
                'work_duration': getattr(getattr(academic_config, 'pomodoro', None), 'work_duration', 25),
                'short_break': getattr(getattr(academic_config, 'pomodoro', None), 'short_break', 5),
                'long_break': getattr(getattr(academic_config, 'pomodoro', None), 'long_break', 15),
                'sessions_before_long_break': getattr(getattr(academic_config, 'pomodoro', None), 'sessions_before_long_break', 4),
            } if hasattr(academic_config, 'pomodoro') else {},
            'github': {
                'enabled': getattr(getattr(academic_config, 'github', None), 'enabled', True),
            } if hasattr(academic_config, 'github') else {},
            'arxiv': {
                'enabled': getattr(getattr(academic_config, 'arxiv', None), 'enabled', True),
            } if hasattr(academic_config, 'arxiv') else {},
        }
        
        self._academic = AcademicManager(
            config=config_dict,
            llm_router=self._llm_router,
            data_dir=str(DATA_DIR),
            on_timer_end=self._on_pomodoro_end,
            on_pomodoro_music=self._on_pomodoro_music,
        )
        logger.info("Academic features initialized (Canvas, Pomodoro, Notes, GitHub, arXiv)")
        
        # Initialize productivity features after academic (they share some components)
        self._init_productivity()
    
    def _init_productivity(self) -> None:
        """Initialize productivity features (Music, Journal, Habits, etc.)."""
        if not PRODUCTIVITY_AVAILABLE:
            return
        
        productivity_config = getattr(self._config, 'productivity', None)
        if not productivity_config:
            return
        
        # Convert config to dict for ProductivityManager
        config_dict = {
            'music': {
                'enabled': getattr(getattr(productivity_config, 'music', None), 'enabled', True),
                'preferred_service': getattr(getattr(productivity_config, 'music', None), 'preferred_service', 'youtube_music'),
                'auto_play_on_pomodoro': getattr(getattr(productivity_config, 'music', None), 'auto_play_on_pomodoro', True),
            } if hasattr(productivity_config, 'music') else {},
            'habits': {
                'enabled': getattr(getattr(productivity_config, 'habits', None), 'enabled', True),
                'add_defaults': getattr(getattr(productivity_config, 'habits', None), 'add_defaults', True),
            } if hasattr(productivity_config, 'habits') else {},
            'snippets': {
                'enabled': getattr(getattr(productivity_config, 'snippets', None), 'enabled', True),
                'load_defaults': getattr(getattr(productivity_config, 'snippets', None), 'load_defaults', True),
            } if hasattr(productivity_config, 'snippets') else {},
            'focus_mode': {
                'enabled': getattr(getattr(productivity_config, 'focus_mode', None), 'enabled', True),
                'blocked_sites': getattr(getattr(productivity_config, 'focus_mode', None), 'blocked_sites', []),
            } if hasattr(productivity_config, 'focus_mode') else {},
            'breaks': {
                'enabled': getattr(getattr(productivity_config, 'breaks', None), 'enabled', True),
                'work_duration': getattr(getattr(productivity_config, 'breaks', None), 'work_duration', 50),
                'short_break': getattr(getattr(productivity_config, 'breaks', None), 'short_break', 5),
                'long_break': getattr(getattr(productivity_config, 'breaks', None), 'long_break', 15),
            } if hasattr(productivity_config, 'breaks') else {},
        }
        
        # Get pomodoro timer from academic module if available
        pomodoro_timer = self._academic.pomodoro if self._academic else None
        canvas_client = self._academic.canvas if self._academic else None
        assignment_tracker = self._academic.assignments if self._academic else None
        
        self._productivity = ProductivityManager(
            config=config_dict,
            data_dir=str(DATA_DIR),
            pomodoro_timer=pomodoro_timer,
            canvas_client=canvas_client,
            assignment_tracker=assignment_tracker,
            on_break_due=self._on_break_due,
        )
        logger.info("Productivity features initialized (Music, Journal, Habits, Projects, Snippets, Focus, Breaks)")
        
        # Initialize career features after productivity
        self._init_career()
    
    def _init_career(self) -> None:
        """Initialize career features (Interview, Resume, Applications, etc.)."""
        if not CAREER_AVAILABLE:
            return
        
        # Build config dict from settings
        config_dict = {}
        
        # Career config
        career_config = getattr(self._config, 'career', None)
        if career_config:
            config_dict['interview_prep'] = {
                'enabled': getattr(getattr(career_config, 'interview_prep', None), 'enabled', True),
                'default_difficulty': getattr(getattr(career_config, 'interview_prep', None), 'default_difficulty', 'medium'),
            } if hasattr(career_config, 'interview_prep') else {}
            
            config_dict['resume'] = {
                'enabled': getattr(getattr(career_config, 'resume', None), 'enabled', True),
                'name': getattr(getattr(career_config, 'resume', None), 'name', ''),
                'university': getattr(getattr(career_config, 'resume', None), 'university', 'UC Berkeley'),
                'major': getattr(getattr(career_config, 'resume', None), 'major', 'Data Science'),
                'graduation': getattr(getattr(career_config, 'resume', None), 'graduation', '2028'),
            } if hasattr(career_config, 'resume') else {}
            
            config_dict['applications'] = {
                'enabled': getattr(getattr(career_config, 'applications', None), 'enabled', True),
                'reminder_days': getattr(getattr(career_config, 'applications', None), 'reminder_days', 3),
            } if hasattr(career_config, 'applications') else {}
            
            config_dict['networking'] = {
                'enabled': getattr(getattr(career_config, 'networking', None), 'enabled', True),
                'follow_up_days': getattr(getattr(career_config, 'networking', None), 'follow_up_days', 14),
            } if hasattr(career_config, 'networking') else {}
        
        # Finance config
        finance_config = getattr(self._config, 'finance', None)
        if finance_config:
            expense_config = getattr(finance_config, 'expense_tracker', None)
            config_dict['finance'] = {
                'expense_tracker': {
                    'enabled': getattr(expense_config, 'enabled', True) if expense_config else True,
                    'currency': getattr(expense_config, 'currency', 'USD') if expense_config else 'USD',
                    'monthly_budget': getattr(expense_config, 'monthly_budget', 1000) if expense_config else 1000,
                    'budget_threshold': getattr(expense_config, 'budget_threshold', 80) if expense_config else 80,
                }
            }
        
        # Notion config
        notion_config = getattr(self._config, 'notion', None)
        if notion_config:
            config_dict['notion'] = {
                'enabled': getattr(notion_config, 'enabled', True),
                'integration_type': getattr(notion_config, 'integration_type', 'url'),
                'api_key': self._env.notion_api_key if hasattr(self._env, 'notion_api_key') else None,
            }
        
        self._career = CareerManager(
            config=config_dict,
            data_dir=str(DATA_DIR),
        )
        logger.info("Career features initialized (Interview, Resume, Applications, Expense, Notion, Networking, Journal, Learning)")
        
        # Initialize finance features after career
        self._init_finance()
    
    def _init_finance(self) -> None:
        """Initialize finance features (Investment Advisor, Portfolio, etc.)."""
        if not FINANCE_AVAILABLE:
            return
        
        # Build config dict from settings
        config_dict = {}
        
        finance_config = getattr(self._config, 'finance', None)
        if finance_config:
            investment_config = getattr(finance_config, 'investment', None)
            if investment_config:
                config_dict['investment'] = {
                    'enabled': getattr(investment_config, 'enabled', True),
                    'default_watchlist': getattr(investment_config, 'default_watchlist', []),
                }
            
            portfolio_config = getattr(finance_config, 'portfolio', None)
            if portfolio_config:
                config_dict['portfolio'] = {
                    'enabled': getattr(portfolio_config, 'enabled', True),
                }
        
        self._finance = FinanceManager(
            config=config_dict,
            data_dir=str(DATA_DIR),
        )
        logger.info("Finance features initialized (Stocks, Education, Retirement, Savings, Tax, Credit, Debt, Tips, Dashboard, Portfolio)")
        
        # Update academic briefing with cross-module services
        self._update_briefing_services()
        
        # Initialize research features
        self._init_research()
        
        # Initialize scholarship features
        self._init_scholarship()
    
    def _init_research(self) -> None:
        """Initialize research and paper writing features."""
        if not RESEARCH_AVAILABLE:
            return
        
        research_config = getattr(self._config, 'research', None)
        if not research_config or not getattr(research_config, 'enabled', True):
            return
        
        # Convert config to dict
        config_dict = {
            'apis': {},
            'defaults': {},
            'google_docs': {},
            'writing': {},
        }
        
        if hasattr(research_config, 'apis'):
            apis = research_config.apis
            config_dict['apis'] = {
                'semantic_scholar': {'enabled': getattr(getattr(apis, 'semantic_scholar', None), 'enabled', True)} if hasattr(apis, 'semantic_scholar') else {},
                'openalex': {
                    'enabled': getattr(getattr(apis, 'openalex', None), 'enabled', True),
                    'email': getattr(getattr(apis, 'openalex', None), 'email', ''),
                } if hasattr(apis, 'openalex') else {},
                'arxiv': {'enabled': getattr(getattr(apis, 'arxiv', None), 'enabled', True)} if hasattr(apis, 'arxiv') else {},
                'crossref': {'enabled': getattr(getattr(apis, 'crossref', None), 'enabled', True)} if hasattr(apis, 'crossref') else {},
            }
        
        if hasattr(research_config, 'defaults'):
            defaults = research_config.defaults
            config_dict['defaults'] = {
                'citation_style': getattr(defaults, 'citation_style', 'apa'),
                'min_sources': getattr(defaults, 'min_sources', 8),
                'max_sources': getattr(defaults, 'max_sources', 15),
                'recent_years': getattr(defaults, 'recent_years', 5),
            }
        
        if hasattr(research_config, 'google_docs'):
            config_dict['google_docs'] = {
                'enabled': getattr(research_config.google_docs, 'enabled', True),
            }
        
        self._research = ResearchManager(
            config=config_dict,
            llm_router=self._llm_router,
            data_dir=str(DATA_DIR),
            progress_callback=self._on_research_progress,
        )
        logger.info("Research features initialized (Scholarly Search, Paper Writing, Google Docs)")
    
    def _on_research_progress(self, message: str) -> None:
        """Handle research progress updates."""
        logger.info(f"Research: {message}")
        if self._tts and "complete" in message.lower():
            asyncio.create_task(self._speak_async(message))
    
    def _init_scholarship(self) -> None:
        """Initialize scholarship features (Essay Generation, Application Tracking)."""
        if not SCHOLARSHIP_AVAILABLE:
            return
        
        scholarship_config = getattr(self._config, 'scholarship', None)
        if scholarship_config and not getattr(scholarship_config, 'enabled', True):
            return
        
        # Build config
        config = ScholarshipConfig(
            tavily_api_key=getattr(self._env, 'tavily_api_key', None),
            serper_api_key=getattr(self._env, 'serper_api_key', None),
            supabase_url=getattr(self._env, 'supabase_url', None),
            supabase_key=getattr(self._env, 'supabase_key', None),
            db_path=str(DATA_DIR / "scholarship_applications.db"),
        )
        
        # Set profile from config if available
        if scholarship_config and hasattr(scholarship_config, 'profile'):
            from .scholarship import EligibilityProfile
            profile_cfg = scholarship_config.profile
            config.profile = EligibilityProfile(
                name=getattr(profile_cfg, 'name', 'User'),
                major=getattr(profile_cfg, 'major', 'Undeclared'),
                university=getattr(profile_cfg, 'university', ''),
                year=getattr(profile_cfg, 'year', 'Freshman'),
            )
        
        self._scholarship = ScholarshipManager(
            config=config,
            llm_router=self._llm_router,
        )
        logger.info("Scholarship features initialized (Discovery, Essay Generation, Application Tracking)")
    
    def _update_briefing_services(self) -> None:
        """Update academic briefing with cross-module services after all modules initialized."""
        if not self._academic:
            return
        
        # Get habit tracker from productivity
        habit_tracker = None
        if self._productivity and hasattr(self._productivity, 'habits'):
            habit_tracker = self._productivity.habits
        
        # Get application tracker from career
        application_tracker = None
        if self._career and hasattr(self._career, 'applications'):
            application_tracker = self._career.applications
        
        # Update briefing with cross-module services
        self._academic.update_briefing_services(
            habit_tracker=habit_tracker,
            application_tracker=application_tracker,
            finance_manager=self._finance,
        )
        logger.debug("Briefing services updated with cross-module integrations")
    
    def _on_break_due(self, message: str) -> None:
        """Handle break reminder."""
        logger.info(f"Break reminder: {message}")
        if self._tts:
            asyncio.create_task(self._speak_async(message))
    
    def _on_pomodoro_end(self, message: str) -> None:
        """Handle pomodoro timer completion."""
        logger.info(f"Pomodoro: {message}")
        # Speak the message if TTS is available
        if self._tts:
            asyncio.create_task(self._speak_async(message))
    
    def _on_pomodoro_music(self, playlist: str) -> str:
        """Play music when Pomodoro starts with music request."""
        if not self._productivity:
            return ""
        
        # Handle special cases
        playlist_lower = playlist.lower()
        if "my mix" in playlist_lower:
            return self._productivity.music.play_my_mix()
        elif "liked" in playlist_lower:
            return self._productivity.music.play_liked_songs()
        else:
            return self._productivity.music.play(playlist)
    
    def _init_iot(self) -> Optional[EnhancedESP32Controller]:
        """Initialize IoT controller."""
        if self._iot_controller is None and self._env.iot_shared_secret:
            self._startup_state = StartupState.INITIALIZING_IOT
            logger.info("Initializing IoT controller...")
            
            self._iot_controller = EnhancedESP32Controller(
                shared_secret=self._env.iot_shared_secret,
                auto_discover=True,
                heartbeat_interval=30,
            )
            
            logger.info("IoT controller initialized")
        
        return self._iot_controller
    
    def _init_proactive(self) -> ProactiveIntelligence:
        """Initialize proactive intelligence."""
        if self._proactive is None:
            logger.info("Initializing proactive intelligence...")
            
            self._proactive = ProactiveIntelligence(DATA_DIR / "proactive")
            
            # Register automation callback
            self._proactive.on_automation(self._on_automation_trigger)
            
            logger.info("Proactive intelligence initialized")
        
        return self._proactive
    
    async def _init_performance(self) -> Optional[PerformanceIntegration]:
        """Initialize performance integration (Phase 5)."""
        if not PERFORMANCE_AVAILABLE:
            logger.warning("Performance integration not available")
            return None
        
        if self._performance is None:
            logger.info("Initializing performance integration...")
            
            # Build config from settings
            perf_config = getattr(self._config, 'performance', None)
            cache_config = getattr(self._config, 'cache', None)
            dashboard_config = getattr(self._config, 'dashboard', None)
            
            integration_config = IntegrationConfig(
                # Streaming
                streaming_enabled=getattr(perf_config.streaming, 'enabled', True) if perf_config else True,
                min_sentence_length=getattr(perf_config.streaming, 'min_sentence_length', 10) if perf_config else 10,
                max_buffer_sentences=getattr(perf_config.streaming, 'max_buffer_sentences', 5) if perf_config else 5,
                
                # Caching
                cache_enabled=getattr(cache_config, 'enabled', True) if cache_config else True,
                cache_dir=DATA_DIR / "cache",
                semantic_cache_enabled=getattr(cache_config.semantic, 'enabled', True) if cache_config else True,
                semantic_threshold=getattr(cache_config.semantic, 'threshold', 0.92) if cache_config else 0.92,
                
                # Parallel
                parallel_enabled=getattr(perf_config.parallel, 'enabled', True) if perf_config else True,
                max_parallel_tasks=getattr(perf_config.parallel, 'max_tasks', 5) if perf_config else 5,
                
                # Dashboard
                dashboard_enabled=getattr(dashboard_config, 'enabled', True) if dashboard_config else True,
                dashboard_host=getattr(dashboard_config, 'host', '127.0.0.1') if dashboard_config else '127.0.0.1',
                dashboard_port=getattr(dashboard_config, 'port', 8080) if dashboard_config else 8080,
                
                # Predictive
                predictive_enabled=True,
                prediction_db_path=DATA_DIR / "predictions.db",
                
                # Resources
                max_memory_mb=getattr(perf_config.resources, 'max_memory_mb', 1024) if perf_config else 1024,
                gc_threshold_mb=getattr(perf_config.resources, 'gc_threshold_mb', 512) if perf_config else 512,
            )
            
            self._performance = get_performance_integration(integration_config)
            await self._performance.start()
            
            self._streaming_enabled = integration_config.streaming_enabled
            
            logger.info("Performance integration initialized")
            if integration_config.dashboard_enabled:
                logger.info(f"Dashboard available at http://{integration_config.dashboard_host}:{integration_config.dashboard_port}/dashboard")
        
        return self._performance
    
    async def _init_mobile_api(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        """Initialize Mobile API server (Phase 6)."""
        if not MOBILE_API_AVAILABLE:
            logger.warning("Mobile API not available (missing dependencies)")
            return
        
        try:
            import uvicorn
            
            logger.info("Initializing Mobile API...")
            
            # Create FastAPI app with JARVIS instance
            self._api_app = create_app(jarvis_instance=self)
            
            # Set JARVIS instance for all API modules
            set_jarvis_instance(self)
            set_websocket_jarvis(self)
            set_voice_jarvis(self)
            
            # Create uvicorn config
            config = uvicorn.Config(
                app=self._api_app,
                host=host,
                port=port,
                log_level="warning",  # Reduce noise
            )
            
            self._api_server = uvicorn.Server(config)
            
            # Start server in background task
            self._api_task = asyncio.create_task(self._api_server.serve())
            
            logger.info(f"Mobile API started at http://{host}:{port}")
            logger.info(f"API docs available at http://{host}:{port}/api/docs")
            
        except Exception as e:
            logger.error(f"Failed to start Mobile API: {e}")
    
    async def _stop_mobile_api(self) -> None:
        """Stop Mobile API server."""
        if self._api_server:
            self._api_server.should_exit = True
            if self._api_task:
                try:
                    await asyncio.wait_for(self._api_task, timeout=5.0)
                except asyncio.TimeoutError:
                    self._api_task.cancel()
            logger.info("Mobile API stopped")
    
    async def _init_telegram(self) -> Optional[EnhancedTelegramBot]:
        """Initialize enhanced Telegram bot."""
        if not TELEGRAM_AVAILABLE:
            logger.warning("Telegram bot not available (missing dependencies)")
            return None
        
        if not self._config.telegram.enabled:
            logger.info("Telegram bot disabled in configuration")
            return None
        
        if not self._env.telegram_bot_token:
            logger.warning("Telegram bot token not configured")
            return None
        
        self._startup_state = StartupState.INITIALIZING_TELEGRAM
        logger.info("Initializing enhanced Telegram bot...")
        
        self._telegram_bot = EnhancedTelegramBot(
            token=self._env.telegram_bot_token,
            allowed_users=self._config.telegram.allowed_users,
            command_handler=self.chat,
            iot_controller=self._iot_controller,
        )
        
        await self._telegram_bot.start()
        logger.info("Enhanced Telegram bot started")
        
        return self._telegram_bot
    
    # =========================================================================
    # Callbacks
    # =========================================================================
    
    def _on_wake_word(self, detection: Any) -> None:
        """Handle wake word detection."""
        logger.info("Wake word detected!")
        
        # Check if authentication required
        if self._config.auth.require_auth_on_wake:
            # Trigger authentication flow
            self._handle_authentication_flow()
        else:
            # Just acknowledge
            self.say("Yes?", blocking=False)
    
    def _on_voice_command(self, command: VoiceCommand) -> str:
        """Handle voice command."""
        # Get language from command (multilingual support)
        language = getattr(command, 'language', 'en')
        lang_prob = getattr(command, 'language_probability', 1.0)
        logger.info(f"Processing command: {command.text} (lang={language}, prob={lang_prob:.2f})")
        
        # Log to proactive intelligence for routine learning
        if self._proactive:
            self._proactive.log_command(command.text)
        
        # Add to conversation memory
        if self._conversation_memory:
            self._conversation_memory.add_message("user", command.text)
        
        # Log command
        if self._episodic_memory:
            self._episodic_memory.log_command(command.text)
        
        # Process command with language context
        try:
            response = self._process_command(command.text, language=language)
            
            # Add response to memory
            if self._conversation_memory:
                self._conversation_memory.add_message("assistant", response)
            
            return response
        
        except Exception as e:
            logger.error(f"Command processing error: {e}")
            return f"I encountered an error: {e}"
    
    def _on_pipeline_state_change(self, state: PipelineState) -> None:
        """Handle voice pipeline state changes."""
        logger.debug(f"Pipeline state: {state.value}")
        
        # Provide audio feedback for certain states
        if state == PipelineState.CONVERSATION_MODE:
            logger.info("Entered conversation mode")
    
    def _on_pipeline_error(self, error: Exception) -> None:
        """Handle voice pipeline errors."""
        logger.error(f"Pipeline error: {error}")
    
    def _on_automation_trigger(self, action: str) -> None:
        """Handle proactive automation trigger."""
        logger.info(f"Automation triggered: {action}")
        self.chat(action)
    
    def _on_hotkey_activation(self) -> None:
        """Handle hotkey activation (Win+J)."""
        logger.info("JARVIS activated via hotkey")
        
        # Play activation sound
        try:
            from .voice.audio_utils import play_activation_sound
            play_activation_sound()
        except Exception:
            pass
        
        # If voice pipeline is available, enter conversation mode
        if self._voice_pipeline:
            self._voice_pipeline.enter_conversation_mode()
            self.say("Yes?", blocking=False)
        else:
            # Text mode - just acknowledge
            print("\n[JARVIS activated via hotkey - ready for input]")
    
    # =========================================================================
    # Command Processing
    # =========================================================================
    
    def _process_command(self, text: str, language: str = "en") -> str:
        """Process a command through the agent system."""
        text_lower = text.lower()
        
        # Check for language switching commands
        language_switch = self._check_language_switch(text_lower)
        if language_switch:
            return language_switch
        
        # Handle special commands (not cached)
        if "authenticate" in text_lower:
            return self._handle_authentication()
        
        if "enroll" in text_lower and "face" in text_lower:
            return self._handle_face_enrollment()
        
        if "enroll" in text_lower and "voice" in text_lower:
            return self._handle_voice_enrollment()
        
        if "logout" in text_lower or "sign out" in text_lower:
            return self._handle_logout()
        
        if "status" in text_lower and ("system" in text_lower or "jarvis" in text_lower):
            return self._get_system_status()
        
        if text_lower in ["status", "jarvis status", "system status", "health check"]:
            return self._get_system_status()
        
        if "what can you do" in text_lower or "help" in text_lower:
            # Check for category-specific help
            import re
            help_match = re.search(r'help\s+(?:with\s+)?(\w+)', text_lower)
            if help_match:
                category = help_match.group(1)
                return self._get_help(category)
            return self._get_help()
        
        # Exit phrases for conversation mode
        if text_lower in ["that's all", "thanks jarvis", "goodbye", "nevermind", "cancel"]:
            if self._voice_pipeline:
                self._voice_pipeline.exit_conversation_mode()
            return "Alright, let me know if you need anything else."
        
        # Communication commands (WhatsApp, contacts)
        comm_result = self._handle_communication(text_lower, text)
        if comm_result:
            return comm_result
        
        # Quick Launch commands (open, play, add app/bookmark, list)
        quick_launch_result = self._handle_quick_launch(text_lower, text)
        if quick_launch_result:
            return quick_launch_result
        
        # Academic commands (Canvas, Pomodoro, Notes, GitHub, arXiv, etc.)
        academic_result = self._handle_academic(text_lower, text)
        if academic_result:
            return academic_result
        
        # Productivity commands (Music, Journal, Habits, Projects, etc.)
        productivity_result = self._handle_productivity(text_lower, text)
        if productivity_result:
            return productivity_result
        
        # Career commands (Interview, Resume, Applications, Expense, etc.)
        career_result = self._handle_career(text_lower, text)
        if career_result:
            return career_result
        
        # Finance commands (Stocks, Investment, Savings, Tax, Credit, etc.)
        finance_result = self._handle_finance(text_lower, text)
        if finance_result:
            return finance_result
        
        # Research commands (Paper Writing, Scholarly Search, Citations)
        research_result = self._handle_research(text_lower, text)
        if research_result:
            return research_result
        
        # Scholarship commands (Find scholarships, Generate essays, Track applications)
        scholarship_result = self._handle_scholarship(text_lower, text)
        if scholarship_result:
            return scholarship_result
        
        # Log command for prediction (Phase 5)
        if self._performance:
            self._performance.log_command(text)
        
        # Add language context to the query for multilingual responses
        query_with_context = text
        if language != "en":
            lang_instruction = self._get_language_instruction(language)
            query_with_context = f"{text}\n\n[Language Context: {lang_instruction}]"
        
        # Process through supervisor agent with caching (Phase 5)
        supervisor = self._init_agents()
        
        if self._performance and PERFORMANCE_AVAILABLE:
            # Use cached agent call
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(
                self._process_command_async(query_with_context, supervisor)
            )
        else:
            # Fallback to direct call
            response = supervisor.run_sync(query_with_context)
        
        return response
    
    async def _process_command_async(self, text: str, supervisor) -> str:
        """Process command asynchronously with caching and streaming."""
        if not self._performance:
            return supervisor.run_sync(text)
        
        # Define the agent call
        async def agent_call():
            # Run supervisor in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, supervisor.run_sync, text)
        
        # Use cached agent call
        response = await self._performance.cached_agent_call(
            query=text,
            agent_func=agent_call,
        )
        
        return response
    
    def _handle_authentication(self) -> str:
        """Handle authentication request."""
        auth = self._init_auth()
        
        if not auth.is_enrolled:
            return "No biometrics enrolled. Please enroll your face first by saying 'enroll my face'."
        
        result = auth.authenticate(
            require_face=True,
            require_voice=False,
            require_liveness=True,
        )
        
        if result.success:
            self._authenticated = True
            self._current_user = result.user_id
            return f"Authentication successful! Welcome back, {result.user_id}."
        else:
            return f"Authentication failed. {result.message}"
    
    def _handle_authentication_flow(self) -> None:
        """Handle authentication flow on wake word."""
        auth = self._init_auth()
        
        if not auth.is_enrolled:
            self.say("Please enroll your face first.")
            return
        
        self.say("Authenticating...")
        
        result = auth.authenticate(
            require_face=True,
            require_voice=False,
            require_liveness=True,
        )
        
        if result.success:
            self._authenticated = True
            self._current_user = result.user_id
            self.say(f"Welcome back! How can I help you?")
        else:
            self.say("I don't recognize you. Access denied.")
    
    def _handle_face_enrollment(self) -> str:
        """Handle face enrollment request."""
        auth = self._init_auth()
        success, message = auth.enroll_face_from_camera(num_samples=5)
        return message
    
    def _handle_voice_enrollment(self) -> str:
        """Handle voice enrollment request."""
        auth = self._init_auth()
        success, message = auth.enroll_voice_from_microphone(num_samples=3)
        return message
    
    def _handle_logout(self) -> str:
        """Handle logout request."""
        auth = self._init_auth()
        auth.logout()
        self._authenticated = False
        self._current_user = None
        return "You have been logged out. Goodbye!"
    
    def _get_system_status(self) -> str:
        """Get comprehensive system status report."""
        lines = [f"📊 **JARVIS v{self.VERSION} Status Report**", ""]
        
        # ===== Core Systems =====
        lines.append("**🔧 Core Systems:**")
        
        # LLM status
        if self._llm_router:
            status = self._llm_router.get_status()
            available = [name for name, info in status["providers"].items() if info["available"]]
            lines.append(f"  ✅ LLM Providers: {', '.join(available)}")
        else:
            lines.append("  ❌ LLM: Not initialized")
        
        # Voice status
        if VOICE_AVAILABLE:
            if self._voice_pipeline:
                lines.append("  ✅ Voice Pipeline: Active")
            else:
                lines.append("  ⚠️ Voice Pipeline: Available but not started")
        else:
            lines.append("  ❌ Voice: Dependencies not installed")
        
        # Auth status
        if self._authenticated:
            lines.append(f"  ✅ Authenticated: {self._current_user or 'Yes'}")
        else:
            lines.append("  ⚠️ Not authenticated")
        
        # ===== Feature Modules =====
        lines.append("")
        lines.append("**📚 Feature Modules:**")
        
        # Academic
        if self._academic:
            canvas_status = "✅" if self._academic.canvas and self._academic.canvas.is_configured else "⚠️ No token"
            lines.append(f"  ✅ Academic: Active (Canvas: {canvas_status})")
        else:
            lines.append("  ❌ Academic: Not initialized")
        
        # Productivity
        if self._productivity:
            lines.append("  ✅ Productivity: Active (Music, Journal, Habits, Projects)")
        else:
            lines.append("  ❌ Productivity: Not initialized")
        
        # Career
        if self._career:
            lines.append("  ✅ Career: Active (Interview, Resume, Applications)")
        else:
            lines.append("  ❌ Career: Not initialized")
        
        # Finance
        if self._finance:
            lines.append("  ✅ Finance: Active (Stocks, Portfolio, Dashboard)")
        else:
            lines.append("  ❌ Finance: Not initialized")
        
        # Research
        if self._research:
            lines.append("  ✅ Research: Active (Paper Writing, Scholarly Search)")
        else:
            lines.append("  ⚠️ Research: Not initialized")
        
        # Scholarship
        if self._scholarship:
            stats = self._scholarship.get_statistics()
            lines.append(f"  ✅ Scholarship: Active ({stats.get('total', 0)} apps, ${stats.get('won_amount', 0):,.0f} won)")
        else:
            lines.append("  ⚠️ Scholarship: Not initialized")
        
        # ===== Integrations =====
        lines.append("")
        lines.append("**🔗 Integrations:**")
        
        # Quick Launch
        if self._quick_launch:
            apps = self._quick_launch.list_applications()
            bookmarks = self._quick_launch.list_bookmarks()
            lines.append(f"  ✅ Quick Launch: {len(apps)} apps, {len(bookmarks)} bookmarks")
        else:
            lines.append("  ❌ Quick Launch: Not initialized")
        
        # Communication
        if self._contacts_manager:
            count = self._contacts_manager.get_contact_count()
            lines.append(f"  ✅ Contacts: {count} contacts")
        if self._whatsapp_service:
            lines.append("  ✅ WhatsApp: Ready")
        if self._hotkey_listener and self._hotkey_listener.is_running:
            lines.append(f"  ✅ Hotkey: {self._hotkey_listener.hotkey}")
        
        # IoT
        if self._iot_controller:
            devices = self._iot_controller.get_online_devices()
            lines.append(f"  ✅ IoT Devices: {len(devices)} online")
        else:
            lines.append("  ⚠️ IoT: Not configured")
        
        # Telegram
        if self._telegram_bot:
            lines.append("  ✅ Telegram Bot: Active")
        else:
            lines.append("  ⚠️ Telegram: Not configured")
        
        # ===== API Keys Status =====
        lines.append("")
        lines.append("**🔑 API Keys:**")
        
        # Check various API keys
        api_keys = [
            ("GROQ_API_KEY", self._env.groq_api_key, "Groq LLM"),
            ("GEMINI_API_KEY", self._env.gemini_api_key, "Google Gemini"),
            ("MISTRAL_API_KEY", getattr(self._env, 'mistral_api_key', None), "Mistral"),
            ("CANVAS_API_TOKEN", getattr(self._env, 'canvas_api_token', None), "Canvas LMS"),
            ("GITHUB_TOKEN", getattr(self._env, 'github_token', None), "GitHub"),
            ("CORE_API_KEY", getattr(self._env, 'core_api_key', None), "CORE Academic"),
            ("TAVILY_API_KEY", getattr(self._env, 'tavily_api_key', None), "Tavily Search"),
        ]
        
        for env_var, value, name in api_keys:
            if value:
                lines.append(f"  ✅ {name}: Configured")
            else:
                lines.append(f"  ⚠️ {name}: Not set ({env_var})")
        
        # Google Docs status
        google_creds_path = Path("config/google_credentials.json")
        google_token_path = Path("config/google_token.json")
        if google_creds_path.exists():
            if google_token_path.exists():
                lines.append("  ✅ Google Docs: Configured")
            else:
                lines.append("  ⚠️ Google Docs: Credentials found, needs authorization")
        else:
            lines.append("  ⚠️ Google Docs: Not configured (see docs/GOOGLE_DOCS_SETUP.md)")
        
        # Performance
        if self._performance:
            lines.append("")
            lines.append("  ✅ Performance Dashboard: Active")
        
        lines.append("")
        lines.append("*Say 'help' or 'what can you do' for available commands.*")
        
        return "\n".join(lines)
    
    def _get_help(self, category: Optional[str] = None) -> str:
        """Get comprehensive help message, optionally filtered by category."""
        
        help_sections = {
            "academic": """📚 **Academic Commands:**
- "Good morning" / "Daily briefing" - Get your morning summary
- "What's due today/this week?" - Check assignments
- "Start pomodoro" / "Start 25 minute focus session"
- "Start pomodoro with focus music" - Timer + music
- "Pomodoro status" / "How much time left?"
- "Take a note: [content]" - Quick notes
- "Show my notes" / "Recent notes"
- "Add assignment [name] due [date]"
- "GitHub status" / "My repositories"
- "Search arXiv for [topic]"
- "Explain [concept]" - AI-powered explanations""",

            "productivity": """🎵 **Productivity Commands:**
- "Play focus music" / "Play lo-fi"
- "Play my liked songs" / "Play my library"
- "Search [song] on YouTube Music"
- "Log learning: [what you learned]"
- "What did I learn this week?"
- "Complete habit [name]" / "My habits"
- "Add habit [name]"
- "Show my projects" / "Project status"
- "Add project [name]"
- "Show snippet [name]" - Code snippets
- "Weekly review" - Productivity summary
- "Start focus mode" / "End focus mode"
- "Take a break" - Break reminders""",

            "career": """💼 **Career Commands:**
- "Practice interview" / "Give me a coding question"
- "Interview stats" - Your practice history
- "Add experience [title] at [company]"
- "Show my resume" / "My skills"
- "Add job application [company] for [role]"
- "Application status" / "Pending applications"
- "Add expense $[amount] for [category]"
- "Monthly spending" / "Budget status"
- "Add contact [name]" - Networking
- "Follow-up reminders" - Who to contact
- "Journal entry: [content]" - Voice journal
- "Start learning path [topic]" - ML, NLP, etc.""",

            "finance": """💰 **Finance Commands:**
- "Stock price of [symbol]" / "How's VTI?"
- "Should I buy VTI right now?" - Real-time analysis
- "Market update" / "How's the market?"
- "Should I invest now?" - Current market advice
- "Market summary" / "My watchlist"
- "Compare VTI vs VOO"
- "Investment advice" / "Why index funds?"
- "Explain 401k matching" / "Roth vs Traditional"
- "Best savings rates" / "Compare SoFi vs Ally"
- "Tax tips for students"
- "How to build credit" / "Best student cards"
- "Good debt vs bad debt"
- "Student discounts" / "Free stuff for students"
- "My financial health" / "Am I on track?"
- "Add 10 shares VTI at $220" - Portfolio tracking
- "My portfolio" / "Asset allocation\"""",

            "research": """📝 **Research & Paper Writing:**
- "Write a research paper on [topic]"
- "10 page paper on [topic] in APA format"
- "Research paper about [topic] for my class"
- "Find papers about [topic]" - Quick scholarly search
- "Search for scholarly articles on [topic]"
- "Latest research on [topic]"
- "Show my research projects"
- "Resume my [topic] paper"
- "Research status"
- "Use APA format" / "Use MLA format"
- "How do I cite in APA?"
- "Generate bibliography\"""",

            "scholarship": """🎓 **Scholarship Automation:**
- "Find scholarships" / "Search scholarships"
- "Scholarships due soon" / "Due this week"
- "Scholarship status" / "Application stats"
- "Generate essay for [scholarship]"
- "Mark [scholarship] submitted"
- "Mark [scholarship] won" / "Mark [scholarship] lost"
- "Import winning essays from [folder]"
- "Import essay" - Add past essay to RAG
- "STEM scholarships" / "Data science scholarships\"""",

            "system": """⚙️ **System Commands:**
- "Open [app]" / "Launch Chrome"
- "Play [video] on YouTube"
- "Add bookmark [name] at [url]"
- "List my apps" / "My bookmarks"
- "JARVIS status" - System health check
- "What can you do?" - This help menu
- "Help with [category]" - Category-specific help

**Communication:**
- "Send WhatsApp to [contact]: [message]"
- "Add contact [name] [phone]"
- "My contacts"

**Languages:**
- "Switch to Hindi" / "Switch to Gujarati"
- "Switch to English\"""",
        }
        
        # Check if asking for specific category help
        if category:
            category_lower = category.lower()
            for key in help_sections:
                if key in category_lower or category_lower in key:
                    return help_sections[key]
        
        # Return overview
        overview = """🤖 **JARVIS - Your Personal AI Assistant**

I can help you with academics, productivity, career, finance, and more!

**Quick Commands:**
- "Good morning" - Daily briefing with all your info
- "JARVIS status" - Check system health
- "Start pomodoro with focus music" - Study session
- "What's due this week?" - Assignment overview
- "My financial health" - Finance dashboard

**Get Detailed Help:**
- "Help with academic" - Academic commands
- "Help with productivity" - Music, habits, projects
- "Help with career" - Interview prep, resume, jobs
- "Help with finance" - Stocks, savings, credit
- "Help with research" - Paper writing, citations
- "Help with scholarship" - Essay generation, tracking
- "Help with system" - Apps, bookmarks, settings

**Tips:**
- Speak naturally - I understand context
- Say "That's all" to end conversation
- Use Win+J hotkey for quick access

*Say "help with [category]" for detailed commands!*"""
        
        return overview
    
    # =========================================================================
    # Public Interface
    # =========================================================================
    
    def chat(self, message: str) -> str:
        """Send a text message to JARVIS."""
        command = VoiceCommand(
            text=message,
            confidence=1.0,
            duration=0.0,
            timestamp=time.time(),
        )
        return self._on_voice_command(command)
    
    def _check_language_switch(self, text_lower: str) -> Optional[str]:
        """Check if text is a language switching command."""
        # Language switching commands
        switch_commands = {
            # English commands
            "switch to hindi": ("hi", "हिंदी में बदल गया। अब मैं हिंदी में जवाब दूंगा।"),
            "speak in hindi": ("hi", "हिंदी में बदल गया। अब मैं हिंदी में जवाब दूंगा।"),
            "hindi mode": ("hi", "हिंदी मोड सक्रिय।"),
            "switch to gujarati": ("gu", "ગુજરાતીમાં બદલાયું. હવે હું ગુજરાતીમાં જવાબ આપીશ."),
            "speak in gujarati": ("gu", "ગુજરાતીમાં બદલાયું. હવે હું ગુજરાતીમાં જવાબ આપીશ."),
            "gujarati mode": ("gu", "ગુજરાતી મોડ સક્રિય."),
            "switch to english": ("en", "Switched to English. I'll now respond in English."),
            "speak in english": ("en", "Switched to English. I'll now respond in English."),
            "english mode": ("en", "English mode activated."),
            # Hindi commands
            "हिंदी में बात करो": ("hi", "ठीक है, अब मैं हिंदी में बात करूंगा।"),
            "अंग्रेजी में बोलो": ("en", "Okay, I'll speak in English now."),
            # Gujarati commands
            "ગુજરાતીમાં બોલો": ("gu", "ઠીક છે, હવે હું ગુજરાતીમાં બોલીશ."),
            "અંગ્રેજીમાં બોલો": ("en", "Okay, I'll speak in English now."),
        }
        
        for command, (lang, response) in switch_commands.items():
            if command in text_lower:
                self._current_language = lang
                logger.info(f"Language switched to: {lang}")
                return response
        
        return None
    
    def _get_language_instruction(self, language: str) -> str:
        """Get LLM instruction for responding in a specific language."""
        instructions = {
            "hi": "Respond in Hindi (हिंदी) using Devanagari script. Use natural Hindi expressions.",
            "gu": "Respond in Gujarati (ગુજરાતી) using Gujarati script. Use natural Gujarati expressions.",
            "en": "Respond in English.",
        }
        return instructions.get(language, "Respond in the same language as the user's query.")
    
    def _handle_communication(self, text_lower: str, text: str) -> Optional[str]:
        """Handle communication commands (WhatsApp, contacts)."""
        if not self._communication_router:
            return None
        
        # Check if this is a communication-related command
        comm_keywords = [
            "whatsapp", "contact", "call", "message", "text",
            "what's", "number", "phone", "add contact", "delete contact",
            "list contacts", "my contacts",
        ]
        
        if not any(kw in text_lower for kw in comm_keywords):
            return None
        
        # Route through communication router
        response, needs_confirmation = self._communication_router.handle_command(text)
        
        if response:
            return response
        
        return None
    
    def _handle_quick_launch(self, text_lower: str, text: str) -> Optional[str]:
        """Handle Quick Launch commands (open, play, add app/bookmark, list)."""
        if not self._quick_launch:
            return None
        
        import re
        
        # YouTube/media patterns
        youtube_patterns = [
            r"play (.+) on youtube",
            r"search youtube for (.+)",
            r"youtube (.+)",
            r"play (.+) on yt",
        ]
        for pattern in youtube_patterns:
            match = re.search(pattern, text_lower)
            if match:
                query = match.group(1).strip()
                result = self._quick_launch.play_youtube(query)
                return result.message
        
        # Open patterns (apps, bookmarks, websites)
        open_patterns = [
            r"^open (.+)$",
            r"^launch (.+)$",
            r"^start (.+)$",
        ]
        for pattern in open_patterns:
            match = re.search(pattern, text_lower)
            if match:
                target = match.group(1).strip()
                result = self._quick_launch.open(target)
                return result.message
        
        # Add application patterns
        add_app_patterns = [
            r"add (?:application|app) (.+?) (?:at|path) (.+)",
            r"register (?:application|app) (.+?) (?:at|path) (.+)",
        ]
        for pattern in add_app_patterns:
            match = re.search(pattern, text_lower)
            if match:
                name = match.group(1).strip()
                path = match.group(2).strip()
                success, msg = self._quick_launch.add_application(name, path=path)
                return msg
        
        # Add bookmark patterns
        add_bookmark_patterns = [
            r"add bookmark (.+?) (?:at|url) (.+)",
            r"bookmark (.+?) (?:at|url) (.+)",
            r"save bookmark (.+?) (?:at|url) (.+)",
        ]
        for pattern in add_bookmark_patterns:
            match = re.search(pattern, text_lower)
            if match:
                name = match.group(1).strip()
                url = match.group(2).strip()
                success, msg = self._quick_launch.add_bookmark(name, url)
                return msg
        
        # List applications
        if any(p in text_lower for p in ["list apps", "list applications", "my apps", "what apps", "show apps"]):
            apps = self._quick_launch.list_applications()
            if apps:
                names = [app.name for app in apps[:10]]  # Limit to 10
                return f"You have {len(apps)} registered applications: {', '.join(names)}"
            return "No applications registered yet. Add one with 'add application [name] at [path]'"
        
        # List bookmarks
        if any(p in text_lower for p in ["list bookmarks", "my bookmarks", "show bookmarks", "what bookmarks"]):
            bookmarks = self._quick_launch.list_bookmarks()
            if bookmarks:
                names = [b.name for b in bookmarks[:10]]  # Limit to 10
                return f"You have {len(bookmarks)} bookmarks: {', '.join(names)}"
            return "No bookmarks saved yet. Add one with 'add bookmark [name] at [url]'"
        
        # Remove application
        remove_app_match = re.search(r"remove (?:application|app) (.+)", text_lower)
        if remove_app_match:
            name = remove_app_match.group(1).strip()
            success, msg = self._quick_launch.remove_application(name)
            return msg
        
        # Remove bookmark
        remove_bookmark_match = re.search(r"remove bookmark (.+)", text_lower)
        if remove_bookmark_match:
            name = remove_bookmark_match.group(1).strip()
            success, msg = self._quick_launch.remove_bookmark(name)
            return msg
        
        return None
    
    def _handle_academic(self, text_lower: str, text: str) -> Optional[str]:
        """Handle academic commands (Canvas, Pomodoro, Notes, GitHub, arXiv, etc.)."""
        if not self._academic:
            return None
        
        # Run async handler in event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new task if loop is already running
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._academic.handle_command(text)
                    )
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(self._academic.handle_command(text))
        except Exception as e:
            logger.error(f"Academic command error: {e}")
            return None
    
    def _handle_productivity(self, text_lower: str, text: str) -> Optional[str]:
        """Handle productivity commands (Music, Journal, Habits, Projects, etc.)."""
        if not self._productivity:
            return None
        
        # Run async handler in event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._productivity.handle_command(text)
                    )
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(self._productivity.handle_command(text))
        except Exception as e:
            logger.error(f"Productivity command error: {e}")
            return None
    
    def _handle_career(self, text_lower: str, text: str) -> Optional[str]:
        """Handle career commands (Interview, Resume, Applications, Expense, etc.)."""
        if not self._career:
            return None
        
        # Run async handler in event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._career.handle_command(text)
                    )
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(self._career.handle_command(text))
        except Exception as e:
            logger.error(f"Career command error: {e}")
            return None
    
    def _handle_finance(self, text_lower: str, text: str) -> Optional[str]:
        """Handle finance commands (Stocks, Investment, Savings, Tax, Credit, etc.)."""
        if not self._finance:
            return None
        
        # Run async handler in event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._finance.handle_command(text)
                    )
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(self._finance.handle_command(text))
        except Exception as e:
            logger.error(f"Finance command error: {e}")
            return None
    
    def _handle_research(self, text_lower: str, text: str) -> Optional[str]:
        """Handle research commands (Paper Writing, Scholarly Search, Citations)."""
        if not self._research:
            return None
        
        # Check if this is a research command
        research_patterns = [
            "research paper", "write a paper", "write paper",
            "find papers", "search for papers", "scholarly search",
            "research projects", "resume my", "research status",
            "citation", "cite", "bibliography", "works cited",
            "apa format", "mla format", "chicago format", "ieee format",
        ]
        
        if not any(p in text_lower for p in research_patterns):
            return None
        
        # Run async handler in event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._research.handle_command(text)
                    )
                    return future.result(timeout=120)  # Longer timeout for research
            else:
                return loop.run_until_complete(self._research.handle_command(text))
        except Exception as e:
            logger.error(f"Research command error: {e}")
            return None
    
    def _handle_scholarship(self, text_lower: str, text: str) -> Optional[str]:
        """Handle scholarship commands (Discovery, Essay Generation, Application Tracking)."""
        if not self._scholarship:
            return None
        
        # Check if this is a scholarship command
        scholarship_patterns = [
            "scholarship", "find scholarship", "search scholarship",
            "scholarship due", "due soon", "application status",
            "generate essay", "write essay", "essay for",
            "mark submitted", "mark won", "mark lost",
            "import essay", "import winning", "past essay",
            "scholarship stats", "scholarship status",
        ]
        
        if not any(p in text_lower for p in scholarship_patterns):
            return None
        
        # Run async handler in event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._scholarship.handle_voice_command(text)
                    )
                    return future.result(timeout=60)
            else:
                return loop.run_until_complete(self._scholarship.handle_voice_command(text))
        except Exception as e:
            logger.error(f"Scholarship command error: {e}")
            return None
    
    def say(self, text: str, blocking: bool = True) -> None:
        """Speak text."""
        if self._tts:
            self._tts.speak(text, blocking=blocking)
        else:
            logger.info(f"JARVIS: {text}")
    
    def start_voice(self) -> bool:
        """Start the voice pipeline."""
        pipeline = self._init_voice()
        return pipeline.start()
    
    def stop_voice(self) -> None:
        """Stop the voice pipeline."""
        if self._voice_pipeline:
            self._voice_pipeline.stop()
    
    # =========================================================================
    # Main Run Methods
    # =========================================================================
    
    def _play_startup_sound(self) -> None:
        """Play JARVIS startup sound if enabled."""
        try:
            from .core.audio import play_startup_sound
            
            # Get audio config
            audio_config = getattr(self._config, 'audio', None)
            if audio_config:
                startup_config = getattr(audio_config, 'startup_sound', None)
                if startup_config:
                    config_dict = {
                        'enabled': getattr(startup_config, 'enabled', True),
                        'file': getattr(startup_config, 'file', 'assets/audio/startup.wav'),
                        'volume': getattr(startup_config, 'volume', 0.7),
                    }
                    if config_dict['enabled']:
                        play_startup_sound(config_dict)
                        logger.debug("Startup sound played")
                    return
            
            # Default: play startup sound
            play_startup_sound({'enabled': True})
            
        except Exception as e:
            logger.debug(f"Startup sound skipped: {e}")
    
    def run(self) -> None:
        """Run JARVIS with full voice interface."""
        logger.info("Starting JARVIS...")
        
        # Run first-time setup if needed
        try:
            from .core.setup_wizard import is_first_run, run_first_time_setup
            if is_first_run():
                logger.info("First run detected, running setup wizard...")
                run_first_time_setup(interactive=False)
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"First-run setup skipped: {e}")
        
        # Play startup sound
        self._play_startup_sound()
        
        # Validate configuration
        validation = self.validate_config()
        if not validation.valid:
            logger.error("Configuration validation failed:")
            for error in validation.errors:
                logger.error(f"  {error}")
            print(validation)
            sys.exit(1)
        
        logger.info("Configuration validated")
        
        # Initialize components in order
        self._init_llm()
        self._init_auth()
        self._init_memory()
        self._init_agents()
        self._init_system()
        self._init_iot()
        self._init_proactive()
        
        # Setup signal handlers
        def signal_handler(sig, frame):
            logger.info("Shutdown signal received")
            self._running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start hotkey listener
        if self._hotkey_listener:
            self._hotkey_listener.start()
            logger.info(f"Hotkey listener started: {self._hotkey_listener.hotkey}")
        
        # Start voice pipeline
        self._running = True
        self._startup_state = StartupState.READY
        
        if self.start_voice():
            logger.info("Voice pipeline started")
            self.say("JARVIS online and ready.")
        else:
            logger.warning("Voice pipeline failed to start. Running in text mode.")
            self.run_text_mode()
            return
        
        # Start async components in background
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Initialize performance integration (Phase 5)
        try:
            loop.run_until_complete(self._init_performance())
        except Exception as e:
            logger.warning(f"Performance integration failed to start: {e}")
        
        # Initialize Telegram bot
        try:
            loop.run_until_complete(self._init_telegram())
        except Exception as e:
            logger.warning(f"Telegram bot failed to start: {e}")
        
        # Initialize Mobile API (Phase 6)
        try:
            api_port = getattr(getattr(self._config, 'api', None), 'port', 8000) or 8000
            loop.run_until_complete(self._init_mobile_api(port=api_port))
        except Exception as e:
            logger.warning(f"Mobile API failed to start: {e}")
        
        # Main loop
        try:
            while self._running:
                loop.run_until_complete(asyncio.sleep(0.1))
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()
    
    def run_text_mode(self) -> None:
        """Run JARVIS in text-only mode."""
        logger.info("Starting JARVIS in text mode...")
        
        # Run first-time setup if needed
        try:
            from .core.setup_wizard import is_first_run, run_first_time_setup
            if is_first_run():
                logger.info("First run detected, running setup wizard...")
                run_first_time_setup(interactive=False)
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"First-run setup skipped: {e}")
        
        # Play startup sound
        self._play_startup_sound()
        
        # Validate configuration
        validation = self.validate_config()
        if not validation.valid:
            logger.error("Configuration validation failed")
            print(validation)
            sys.exit(1)
        
        # Initialize components
        self._init_llm()
        self._init_memory()
        self._init_agents()
        self._init_system()
        self._init_proactive()
        
        # Initialize performance integration (Phase 5)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._init_performance())
        except Exception as e:
            logger.warning(f"Performance integration failed to start: {e}")
        
        # Initialize Mobile API (Phase 6)
        try:
            api_port = getattr(getattr(self._config, 'api', None), 'port', 8000) or 8000
            loop.run_until_complete(self._init_mobile_api(port=api_port))
        except Exception as e:
            logger.warning(f"Mobile API failed to start: {e}")
        
        self._startup_state = StartupState.READY
        
        print("\n" + "=" * 60)
        print(f"JARVIS v{self.VERSION} - Text Mode")
        print("Type 'quit' or 'exit' to stop")
        print("Type 'status' for system status")
        print("Type 'help' for available commands")
        if self._performance:
            print(f"Dashboard: http://127.0.0.1:8080/dashboard")
        if MOBILE_API_AVAILABLE:
            print(f"Mobile API: http://0.0.0.0:{api_port}/api/docs")
        print("=" * 60 + "\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ["quit", "exit", "bye"]:
                    print("\nJARVIS: Goodbye!")
                    break
                
                response = self.chat(user_input)
                print(f"\nJARVIS: {response}\n")
            
            except KeyboardInterrupt:
                print("\n\nJARVIS: Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                print(f"\nJARVIS: I encountered an error: {e}\n")
        
        self.shutdown()
    
    def shutdown(self) -> None:
        """Shutdown JARVIS gracefully."""
        logger.info("Shutting down JARVIS...")
        
        self._running = False
        
        # Say goodbye
        if self._tts:
            try:
                self._tts.speak("Goodbye, shutting down.", blocking=True)
            except Exception:
                pass
        
        # Stop voice pipeline
        self.stop_voice()
        
        # Stop performance integration (Phase 5)
        if self._performance:
            try:
                asyncio.get_event_loop().run_until_complete(self._performance.stop())
            except Exception:
                pass
        
        # Stop Mobile API (Phase 6)
        if self._api_server:
            try:
                asyncio.get_event_loop().run_until_complete(self._stop_mobile_api())
            except Exception:
                pass
        
        # Close browser sessions
        if self._browser:
            try:
                asyncio.get_event_loop().run_until_complete(self._browser.close())
            except Exception:
                pass
        
        # Stop Telegram bot
        if self._telegram_bot:
            try:
                asyncio.get_event_loop().run_until_complete(self._telegram_bot.stop())
            except Exception:
                pass
        
        # Stop IoT heartbeat
        if self._iot_controller:
            self._iot_controller.stop_heartbeat()
        
        logger.info("JARVIS shutdown complete")


def check_config() -> None:
    """Check configuration and print status."""
    print("\n" + "=" * 60)
    print("JARVIS Configuration Check")
    print("=" * 60 + "\n")
    
    jarvis = JarvisUnified()
    result = jarvis.validate_config()
    print(result)
    
    if result.valid:
        print("\n✅ Configuration is valid. JARVIS is ready to run.")
        sys.exit(0)
    else:
        print("\n❌ Configuration has errors. Please fix them before running.")
        sys.exit(1)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS - Advanced Personal AI Assistant")
    parser.add_argument("--text", action="store_true", help="Run in text-only mode")
    parser.add_argument("--check-config", action="store_true", help="Validate configuration and exit")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    
    args = parser.parse_args()
    
    if args.check_config:
        check_config()
        return
    
    jarvis = JarvisUnified(config_path=Path(args.config) if args.config else None)
    
    if args.text:
        jarvis.run_text_mode()
    else:
        jarvis.run()


if __name__ == "__main__":
    main()
