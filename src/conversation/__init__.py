"""
JARVIS Conversation Module - Phase 7 Part G

Provides natural conversation capabilities:
- Context management across turns
- Clarification handling for ambiguous queries
- Proactive assistance and suggestions
"""

from __future__ import annotations

from loguru import logger

try:
    from .context import (
        ConversationContext,
        ConversationManager,
        get_conversation_manager,
    )
    CONTEXT_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Context not available: {e}")
    CONTEXT_AVAILABLE = False
    ConversationContext = None
    ConversationManager = None
    get_conversation_manager = None

try:
    from .clarification import (
        ClarificationRequest,
        ClarificationHandler,
        get_clarification_handler,
    )
    CLARIFICATION_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Clarification not available: {e}")
    CLARIFICATION_AVAILABLE = False
    ClarificationRequest = None
    ClarificationHandler = None
    get_clarification_handler = None

try:
    from .proactive import (
        ProactiveSuggestion,
        ProactiveAssistant,
        get_proactive_assistant,
    )
    PROACTIVE_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Proactive not available: {e}")
    PROACTIVE_AVAILABLE = False
    ProactiveSuggestion = None
    ProactiveAssistant = None
    get_proactive_assistant = None


__all__ = [
    "CONTEXT_AVAILABLE",
    "CLARIFICATION_AVAILABLE",
    "PROACTIVE_AVAILABLE",
    "ConversationContext",
    "ConversationManager",
    "get_conversation_manager",
    "ClarificationRequest",
    "ClarificationHandler",
    "get_clarification_handler",
    "ProactiveSuggestion",
    "ProactiveAssistant",
    "get_proactive_assistant",
]
