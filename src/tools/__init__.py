"""
JARVIS Tools Module - Phase 7: Agentic Tools & Intelligence

Provides real-world tool integrations for JARVIS:
- Weather: Open-Meteo (FREE, no API key)
- Calendar: Google Calendar API (FREE)
- Email: Gmail API (FREE)
- Smart Home: MQTT / Home Assistant (FREE)
- Documents: RAG with vector search (FREE)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

# Weather tool (always available - no API key needed)
try:
    from .weather import WeatherService, get_weather_service
    WEATHER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Weather service not available: {e}")
    WEATHER_AVAILABLE = False
    WeatherService = None
    get_weather_service = None

# Calendar tool (requires Google credentials)
try:
    from .calendar import CalendarService, get_calendar_service
    CALENDAR_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Calendar service not available: {e}")
    CALENDAR_AVAILABLE = False
    CalendarService = None
    get_calendar_service = None

# Email tool (requires Gmail credentials)
try:
    from .email import EmailService, get_email_service
    EMAIL_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Email service not available: {e}")
    EMAIL_AVAILABLE = False
    EmailService = None
    get_email_service = None

# Smart home tools
try:
    from .mqtt import MQTTService, get_mqtt_service
    MQTT_AVAILABLE = True
except ImportError as e:
    logger.debug(f"MQTT service not available: {e}")
    MQTT_AVAILABLE = False
    MQTTService = None
    get_mqtt_service = None

try:
    from .home_assistant import HomeAssistantService, get_home_assistant_service
    HOME_ASSISTANT_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Home Assistant service not available: {e}")
    HOME_ASSISTANT_AVAILABLE = False
    HomeAssistantService = None
    get_home_assistant_service = None

# Document/RAG tools
try:
    from .documents import DocumentService, get_document_service
    DOCUMENTS_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Document service not available: {e}")
    DOCUMENTS_AVAILABLE = False
    DocumentService = None
    get_document_service = None


__all__ = [
    # Availability flags
    "WEATHER_AVAILABLE",
    "CALENDAR_AVAILABLE", 
    "EMAIL_AVAILABLE",
    "MQTT_AVAILABLE",
    "HOME_ASSISTANT_AVAILABLE",
    "DOCUMENTS_AVAILABLE",
    # Services
    "WeatherService",
    "CalendarService",
    "EmailService",
    "MQTTService",
    "HomeAssistantService",
    "DocumentService",
    # Factory functions
    "get_weather_service",
    "get_calendar_service",
    "get_email_service",
    "get_mqtt_service",
    "get_home_assistant_service",
    "get_document_service",
]
