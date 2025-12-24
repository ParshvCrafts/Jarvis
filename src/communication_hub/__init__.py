"""
JARVIS Communication Hub Module.

Email templates, meeting scheduling, and LinkedIn content generation.
"""

from loguru import logger

COMMUNICATION_AVAILABLE = False

try:
    from .models import (
        EmailTemplate,
        EmailDraft,
        EmailCategory,
        Meeting,
        MeetingType,
        MeetingPreferences,
        TimeSlot,
        LinkedInContent,
        LinkedInContentType,
        ContactInfo,
        EMAIL_TEMPLATES,
        LINKEDIN_TEMPLATES,
    )
    
    from .manager import (
        CommunicationManager,
        CommunicationConfig,
    )
    
    COMMUNICATION_AVAILABLE = True
    logger.info("Communication Hub module loaded successfully")
    
except ImportError as e:
    logger.warning(f"Communication Hub module not fully available: {e}")

__all__ = [
    "COMMUNICATION_AVAILABLE",
    # Models
    "EmailTemplate",
    "EmailDraft",
    "EmailCategory",
    "Meeting",
    "MeetingType",
    "MeetingPreferences",
    "TimeSlot",
    "LinkedInContent",
    "LinkedInContentType",
    "ContactInfo",
    "EMAIL_TEMPLATES",
    "LINKEDIN_TEMPLATES",
    # Manager
    "CommunicationManager",
    "CommunicationConfig",
]
