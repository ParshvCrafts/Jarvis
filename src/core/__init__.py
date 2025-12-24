"""Core modules for JARVIS."""

from loguru import logger

# Configuration
try:
    from .config import config, env, ensure_directories, DATA_DIR, PROJECT_ROOT
except ImportError as e:
    logger.warning(f"Config not available: {e}")
    config = None
    env = None

# Logging
try:
    from .logger import setup_logging
except ImportError as e:
    logger.warning(f"Logger setup not available: {e}")
    setup_logging = None

# LLM
try:
    from .llm import LLMManager, Message, LLMResponse
except ImportError as e:
    logger.warning(f"LLM not available: {e}")
    LLMManager = None
    Message = None
    LLMResponse = None

# LLM Router
try:
    from .llm_router import IntelligentLLMRouter, create_intelligent_router
except ImportError as e:
    logger.warning(f"LLM router not available: {e}")
    IntelligentLLMRouter = None
    create_intelligent_router = None

# Internal API
try:
    from .internal_api import (
        InternalAPI,
        EventBus,
        ServiceRegistry,
        Event,
        EventType,
        get_internal_api,
        get_event_bus,
        get_service_registry,
    )
except ImportError as e:
    logger.warning(f"Internal API not available: {e}")
    InternalAPI = None
    EventBus = None
    ServiceRegistry = None
    Event = None
    EventType = None
    get_internal_api = None
    get_event_bus = None
    get_service_registry = None

# Help System
try:
    from .help_system import (
        HelpSystem,
        HelpTopic,
        HelpCategory,
        get_help_system,
        get_help,
    )
except ImportError as e:
    logger.warning(f"Help system not available: {e}")
    HelpSystem = None
    HelpTopic = None
    HelpCategory = None
    get_help_system = None
    get_help = None

# Health Monitor
try:
    from .health_monitor import (
        HealthMonitor,
        HealthCheck,
        ComponentStatus,
        Alert,
        AlertLevel,
        get_health_monitor,
        check_llm_health,
        check_voice_health,
        check_memory_health,
        check_disk_health,
    )
except ImportError as e:
    logger.warning(f"Health monitor not available: {e}")
    HealthMonitor = None
    HealthCheck = None
    ComponentStatus = None
    Alert = None
    AlertLevel = None
    get_health_monitor = None
    check_llm_health = None
    check_voice_health = None
    check_memory_health = None
    check_disk_health = None

# Streaming Response Handler
try:
    from .streaming import (
        StreamingResponseHandler,
        StreamingTTSQueue,
        StreamMetrics,
        SentenceChunk,
        SentenceDetector,
        StreamState,
        create_streaming_response,
    )
except ImportError as e:
    logger.warning(f"Streaming not available: {e}")
    StreamingResponseHandler = None
    StreamingTTSQueue = None
    StreamMetrics = None
    SentenceChunk = None
    SentenceDetector = None
    StreamState = None
    create_streaming_response = None

# Performance Optimization
try:
    from .performance import (
        PerformanceOptimizer,
        PerformanceConfig,
        ParallelExecutor,
        ResourceMonitor,
        ResourceMetrics,
        ConnectionPool,
        get_performance_optimizer,
        init_performance_optimizer,
    )
except ImportError as e:
    logger.warning(f"Performance optimizer not available: {e}")
    PerformanceOptimizer = None
    PerformanceConfig = None
    ParallelExecutor = None
    ResourceMonitor = None
    ResourceMetrics = None
    ConnectionPool = None
    get_performance_optimizer = None
    init_performance_optimizer = None

# Intelligent Cache
try:
    from .cache import (
        IntelligentCache,
        CacheConfig,
        CacheCategory,
        CacheEntry,
        CacheStats,
        LRUCache,
        SQLiteCache,
        SemanticCache,
        ResponseTemplates,
        get_cache,
        cached_response,
    )
except ImportError as e:
    logger.warning(f"Cache not available: {e}")
    IntelligentCache = None
    CacheConfig = None
    CacheCategory = None
    CacheEntry = None
    CacheStats = None
    LRUCache = None
    SQLiteCache = None
    SemanticCache = None
    ResponseTemplates = None
    get_cache = None
    cached_response = None

# Performance Dashboard
try:
    from .dashboard import (
        PerformanceDashboard,
        DashboardConfig,
        MetricsCollector,
        get_dashboard,
        init_dashboard,
    )
except ImportError as e:
    logger.warning(f"Dashboard not available: {e}")
    PerformanceDashboard = None
    DashboardConfig = None
    MetricsCollector = None
    get_dashboard = None
    init_dashboard = None

# Performance Integration
try:
    from .performance_integration import (
        PerformanceIntegration,
        IntegrationConfig,
        StreamingLLMIntegration,
        CacheIntegration,
        CommandPredictor,
        get_performance_integration,
        init_performance_integration,
    )
except ImportError as e:
    logger.warning(f"Performance integration not available: {e}")
    PerformanceIntegration = None
    IntegrationConfig = None
    StreamingLLMIntegration = None
    CacheIntegration = None
    CommandPredictor = None
    get_performance_integration = None
    init_performance_integration = None

# Setup Wizard
try:
    from .setup_wizard import (
        run_first_time_setup,
        is_first_run,
        get_system_status,
        print_status,
        validate_configuration,
        populate_default_apps,
        populate_default_bookmarks,
    )
    SETUP_WIZARD_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Setup wizard not available: {e}")
    SETUP_WIZARD_AVAILABLE = False
    run_first_time_setup = None
    is_first_run = None
    get_system_status = None
    print_status = None
    validate_configuration = None
    populate_default_apps = None
    populate_default_bookmarks = None

__all__ = [
    # Config
    "config",
    "env",
    "ensure_directories",
    "DATA_DIR",
    "PROJECT_ROOT",
    # Logging
    "setup_logging",
    # LLM
    "LLMManager",
    "Message",
    "LLMResponse",
    "IntelligentLLMRouter",
    "create_intelligent_router",
    # Internal API
    "InternalAPI",
    "EventBus",
    "ServiceRegistry",
    "Event",
    "EventType",
    "get_internal_api",
    "get_event_bus",
    "get_service_registry",
    # Help System
    "HelpSystem",
    "HelpTopic",
    "HelpCategory",
    "get_help_system",
    "get_help",
    # Health Monitor
    "HealthMonitor",
    "HealthCheck",
    "ComponentStatus",
    "Alert",
    "AlertLevel",
    "get_health_monitor",
    "check_llm_health",
    "check_voice_health",
    "check_memory_health",
    "check_disk_health",
    # Streaming
    "StreamingResponseHandler",
    "StreamingTTSQueue",
    "StreamMetrics",
    "SentenceChunk",
    "SentenceDetector",
    "StreamState",
    "create_streaming_response",
    # Performance
    "PerformanceOptimizer",
    "PerformanceConfig",
    "ParallelExecutor",
    "ResourceMonitor",
    "ResourceMetrics",
    "ConnectionPool",
    "get_performance_optimizer",
    "init_performance_optimizer",
    # Cache
    "IntelligentCache",
    "CacheConfig",
    "CacheCategory",
    "CacheEntry",
    "CacheStats",
    "LRUCache",
    "SQLiteCache",
    "SemanticCache",
    "ResponseTemplates",
    "get_cache",
    "cached_response",
    # Dashboard
    "PerformanceDashboard",
    "DashboardConfig",
    "MetricsCollector",
    "get_dashboard",
    "init_dashboard",
    # Performance Integration
    "PerformanceIntegration",
    "IntegrationConfig",
    "StreamingLLMIntegration",
    "CacheIntegration",
    "CommandPredictor",
    "get_performance_integration",
    "init_performance_integration",
    # Setup Wizard
    "SETUP_WIZARD_AVAILABLE",
    "run_first_time_setup",
    "is_first_run",
    "get_system_status",
    "print_status",
    "validate_configuration",
    "populate_default_apps",
    "populate_default_bookmarks",
]
