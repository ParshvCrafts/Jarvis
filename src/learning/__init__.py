"""
JARVIS Learning & Personalization Module - Phase 7 Part F

Provides user preference learning and adaptive personalization:
- User preference storage and retrieval
- Usage pattern detection
- Adaptive response customization
"""

from __future__ import annotations

from loguru import logger

try:
    from .preferences import (
        UserPreferences,
        PreferenceManager,
        get_preference_manager,
    )
    PREFERENCES_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Preferences not available: {e}")
    PREFERENCES_AVAILABLE = False
    UserPreferences = None
    PreferenceManager = None
    get_preference_manager = None

try:
    from .patterns import (
        UsagePattern,
        PatternDetector,
        get_pattern_detector,
    )
    PATTERNS_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Patterns not available: {e}")
    PATTERNS_AVAILABLE = False
    UsagePattern = None
    PatternDetector = None
    get_pattern_detector = None

try:
    from .personalization import (
        PersonalizationEngine,
        get_personalization_engine,
    )
    PERSONALIZATION_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Personalization not available: {e}")
    PERSONALIZATION_AVAILABLE = False
    PersonalizationEngine = None
    get_personalization_engine = None


__all__ = [
    "PREFERENCES_AVAILABLE",
    "PATTERNS_AVAILABLE", 
    "PERSONALIZATION_AVAILABLE",
    "UserPreferences",
    "PreferenceManager",
    "get_preference_manager",
    "UsagePattern",
    "PatternDetector",
    "get_pattern_detector",
    "PersonalizationEngine",
    "get_personalization_engine",
]
