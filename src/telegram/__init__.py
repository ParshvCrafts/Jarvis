"""Telegram bot modules for JARVIS."""

from loguru import logger

# Enhanced module (canonical) - with graceful fallback
try:
    from .bot_enhanced import (
        EnhancedTelegramBot,
        RateLimiter,
        ConfirmationType,
        PendingAction,
    )
except ImportError as e:
    logger.warning(f"Enhanced Telegram bot not available: {e}")
    EnhancedTelegramBot = None
    RateLimiter = None
    ConfirmationType = None
    PendingAction = None

# Legacy alias for backwards compatibility
try:
    from .bot import JarvisTelegramBot as LegacyTelegramBot
except ImportError:
    LegacyTelegramBot = None

__all__ = [
    # Enhanced (use these)
    "EnhancedTelegramBot",
    "RateLimiter",
    "ConfirmationType",
    "PendingAction",
    # Legacy (deprecated)
    "LegacyTelegramBot",
]
