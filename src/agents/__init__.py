"""Agent modules for JARVIS."""

from loguru import logger

# Core agent imports
try:
    from .supervisor import SupervisorAgent
    from .specialized import create_all_agents
    from .base import BaseAgent
except ImportError as e:
    logger.warning(f"Agent core modules not available: {e}")
    SupervisorAgent = None
    create_all_agents = None
    BaseAgent = None

# Enhanced supervisor with context engineering
try:
    from .supervisor_enhanced import (
        EnhancedSupervisorAgent,
        IntentClassifier,
        ContextEngineer,
        IntentType,
    )
except ImportError as e:
    logger.warning(f"Enhanced supervisor not available: {e}")
    EnhancedSupervisorAgent = None
    IntentClassifier = None
    ContextEngineer = None
    IntentType = None

# Enhanced tools (canonical) - with graceful fallback
try:
    from .tools_enhanced import (
        ToolRegistry,
        ToolResult,
        BaseTool as EnhancedBaseTool,
        WebSearchTool,
        WebFetchTool,
        FileReadTool,
        FileWriteTool,
        CodeExecutionTool,
        AiderTool,
        ResearchTool,
        CalculatorTool,
        create_default_registry,
    )
except ImportError as e:
    logger.warning(f"Enhanced tools not available: {e}")
    ToolRegistry = None
    ToolResult = None
    EnhancedBaseTool = None
    WebSearchTool = None
    WebFetchTool = None
    FileReadTool = None
    FileWriteTool = None
    CodeExecutionTool = None
    AiderTool = None
    ResearchTool = None
    CalculatorTool = None
    create_default_registry = None

# Legacy tools
try:
    from .tools import WebSearchTool as LegacyWebSearchTool
except ImportError:
    LegacyWebSearchTool = None

__all__ = [
    # Core
    "SupervisorAgent",
    "BaseAgent",
    "create_all_agents",
    # Enhanced supervisor
    "EnhancedSupervisorAgent",
    "IntentClassifier",
    "ContextEngineer",
    "IntentType",
    # Enhanced tools (use these)
    "ToolRegistry",
    "ToolResult",
    "EnhancedBaseTool",
    "WebSearchTool",
    "WebFetchTool",
    "FileReadTool",
    "FileWriteTool",
    "CodeExecutionTool",
    "AiderTool",
    "ResearchTool",
    "CalculatorTool",
    "create_default_registry",
    # Legacy
    "LegacyWebSearchTool",
]
