"""
JARVIS Communication Module

Provides:
- Contacts management system
- WhatsApp automation
- Global keyboard shortcut activation
- Unified communication routing
"""

from loguru import logger

# Contacts Management
try:
    from .contacts import (
        Contact,
        ContactsDatabase,
        ContactsManager,
    )
    CONTACTS_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Contacts not available: {e}")
    CONTACTS_AVAILABLE = False
    Contact = None
    ContactsDatabase = None
    ContactsManager = None

# WhatsApp Automation
try:
    from .whatsapp import (
        WhatsAppService,
        WhatsAppResult,
        WhatsAppCommandParser,
        CommunicationRouter,
    )
    WHATSAPP_AVAILABLE = True
except ImportError as e:
    logger.debug(f"WhatsApp not available: {e}")
    WHATSAPP_AVAILABLE = False
    WhatsAppService = None
    WhatsAppResult = None
    WhatsAppCommandParser = None
    CommunicationRouter = None

# Hotkey Activation
try:
    from .hotkey import (
        HotkeyListener,
        ActivationManager,
        KEYBOARD_AVAILABLE,
        get_available_hotkeys,
        validate_hotkey,
    )
    HOTKEY_AVAILABLE = KEYBOARD_AVAILABLE
except ImportError as e:
    logger.debug(f"Hotkey not available: {e}")
    HOTKEY_AVAILABLE = False
    HotkeyListener = None
    ActivationManager = None
    KEYBOARD_AVAILABLE = False
    get_available_hotkeys = None
    validate_hotkey = None

__all__ = [
    # Contacts
    "CONTACTS_AVAILABLE",
    "Contact",
    "ContactsDatabase",
    "ContactsManager",
    # WhatsApp
    "WHATSAPP_AVAILABLE",
    "WhatsAppService",
    "WhatsAppResult",
    "WhatsAppCommandParser",
    "CommunicationRouter",
    # Hotkey
    "HOTKEY_AVAILABLE",
    "HotkeyListener",
    "ActivationManager",
    "KEYBOARD_AVAILABLE",
    "get_available_hotkeys",
    "validate_hotkey",
]
