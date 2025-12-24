"""System control modules for JARVIS."""

from loguru import logger

# Core system controller
try:
    from .controller import SystemController
except ImportError as e:
    logger.warning(f"System controller not available: {e}")
    SystemController = None

# Browser automation - with graceful fallback
try:
    from .browser import BrowserController, BrowserManager, GoogleDocsController, WebResearcher
except ImportError as e:
    logger.warning(f"Browser automation not available: {e}")
    BrowserController = None
    BrowserManager = None
    GoogleDocsController = None
    WebResearcher = None

# Dev tools - with graceful fallback
try:
    from .dev_tools import GitController, VSCodeController, TerminalController, DevToolsManager
except ImportError as e:
    logger.warning(f"Dev tools not available: {e}")
    GitController = None
    VSCodeController = None
    TerminalController = None
    DevToolsManager = None

# Quick Launch system
try:
    from .quick_launch import (
        QuickLaunchManager,
        QuickLaunchDB,
        ApplicationLauncher,
        WebLauncher,
        YouTubeLauncher,
        Application,
        Bookmark,
        LaunchResult,
        LaunchType,
        get_quick_launch_manager,
    )
    QUICK_LAUNCH_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Quick Launch not available: {e}")
    QUICK_LAUNCH_AVAILABLE = False
    QuickLaunchManager = None
    QuickLaunchDB = None
    ApplicationLauncher = None
    WebLauncher = None
    YouTubeLauncher = None
    Application = None
    Bookmark = None
    LaunchResult = None
    LaunchType = None
    get_quick_launch_manager = None

__all__ = [
    "SystemController",
    # Browser
    "BrowserController",
    "BrowserManager",
    "GoogleDocsController",
    "WebResearcher",
    # Dev Tools
    "GitController",
    "VSCodeController",
    "TerminalController",
    "DevToolsManager",
    # Quick Launch
    "QUICK_LAUNCH_AVAILABLE",
    "QuickLaunchManager",
    "QuickLaunchDB",
    "ApplicationLauncher",
    "WebLauncher",
    "YouTubeLauncher",
    "Application",
    "Bookmark",
    "LaunchResult",
    "LaunchType",
    "get_quick_launch_manager",
]
