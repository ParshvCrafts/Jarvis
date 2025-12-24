"""
Centralized Error Handling for JARVIS.

Provides:
- User-friendly error messages
- Configuration guidance
- Graceful degradation helpers
"""

from typing import Dict, Optional
from loguru import logger


class ConfigurationError(Exception):
    """Raised when a required configuration is missing."""
    pass


class ServiceUnavailableError(Exception):
    """Raised when an external service is unavailable."""
    pass


# User-friendly error messages with setup instructions
ERROR_MESSAGES: Dict[str, Dict[str, str]] = {
    "canvas_token": {
        "short": "Canvas not configured",
        "detailed": """Canvas LMS is not configured.

To enable Canvas integration:
1. Go to bCourses (bcourses.berkeley.edu)
2. Click Account → Settings → New Access Token
3. Add to your .env file:
   CANVAS_API_TOKEN=your_token_here

Then restart JARVIS.""",
    },
    "github_token": {
        "short": "GitHub not configured",
        "detailed": """GitHub integration is not configured.

To enable GitHub features:
1. Go to github.com/settings/tokens
2. Generate a new token with 'repo' scope
3. Add to your .env file:
   GITHUB_TOKEN=your_token_here

Then restart JARVIS.""",
    },
    "notion_token": {
        "short": "Notion not configured",
        "detailed": """Notion integration is not configured.

To enable Notion features:
1. Go to notion.so/my-integrations
2. Create a new integration
3. Add to your .env file:
   NOTION_API_KEY=your_key_here

Then restart JARVIS.""",
    },
    "groq_key": {
        "short": "Groq API not configured",
        "detailed": """Groq LLM provider is not configured.

To enable Groq (recommended, fast & free):
1. Go to console.groq.com
2. Create an API key
3. Add to your .env file:
   GROQ_API_KEY=your_key_here

Then restart JARVIS.""",
    },
    "gemini_key": {
        "short": "Gemini API not configured",
        "detailed": """Google Gemini is not configured.

To enable Gemini:
1. Go to makersuite.google.com/app/apikey
2. Create an API key
3. Add to your .env file:
   GEMINI_API_KEY=your_key_here

Then restart JARVIS.""",
    },
    "telegram_token": {
        "short": "Telegram bot not configured",
        "detailed": """Telegram bot is not configured.

To enable Telegram:
1. Message @BotFather on Telegram
2. Create a new bot with /newbot
3. Add to your .env file:
   TELEGRAM_BOT_TOKEN=your_token_here
4. Add your Telegram user ID to settings.yaml:
   telegram:
     allowed_users:
       - your_user_id

Then restart JARVIS.""",
    },
    "yfinance": {
        "short": "Stock data unavailable",
        "detailed": """Stock market data is unavailable.

yfinance library is not installed. To enable:
   pip install yfinance

Then restart JARVIS.""",
    },
    "voice_dependencies": {
        "short": "Voice features unavailable",
        "detailed": """Voice features require additional dependencies.

To enable voice:
   pip install sounddevice numpy openwakeword faster-whisper edge-tts

Then restart JARVIS.""",
    },
    "network_error": {
        "short": "Network error",
        "detailed": """Unable to connect to the service.

Please check:
1. Your internet connection
2. The service might be temporarily down
3. Your firewall settings

Try again in a few moments.""",
    },
}


def get_error_message(error_key: str, detailed: bool = False) -> str:
    """
    Get user-friendly error message.
    
    Args:
        error_key: Key for the error type
        detailed: Whether to return detailed message with setup instructions
        
    Returns:
        User-friendly error message
    """
    if error_key not in ERROR_MESSAGES:
        return f"An error occurred: {error_key}"
    
    msg = ERROR_MESSAGES[error_key]
    return msg["detailed"] if detailed else msg["short"]


def handle_missing_config(
    service_name: str,
    config_key: str,
    env_var: str,
) -> str:
    """
    Handle missing configuration gracefully.
    
    Args:
        service_name: Name of the service (e.g., "Canvas", "GitHub")
        config_key: Key in ERROR_MESSAGES
        env_var: Environment variable name
        
    Returns:
        User-friendly error message
    """
    logger.warning(f"{service_name} not configured: {env_var} not set")
    return get_error_message(config_key, detailed=True)


def handle_api_error(
    service_name: str,
    error: Exception,
    fallback_message: Optional[str] = None,
) -> str:
    """
    Handle API errors gracefully.
    
    Args:
        service_name: Name of the service
        error: The exception that occurred
        fallback_message: Optional fallback message
        
    Returns:
        User-friendly error message
    """
    error_str = str(error).lower()
    
    # Check for common error patterns
    if "401" in error_str or "unauthorized" in error_str:
        return f"{service_name} authentication failed. Please check your API token/key."
    
    if "403" in error_str or "forbidden" in error_str:
        return f"{service_name} access denied. Your token may not have the required permissions."
    
    if "404" in error_str or "not found" in error_str:
        return f"{service_name} resource not found. Please check the URL or ID."
    
    if "429" in error_str or "rate limit" in error_str:
        return f"{service_name} rate limit exceeded. Please wait a moment and try again."
    
    if "timeout" in error_str or "timed out" in error_str:
        return f"{service_name} request timed out. Please check your connection and try again."
    
    if "connection" in error_str or "network" in error_str:
        return get_error_message("network_error")
    
    # Log the actual error for debugging
    logger.error(f"{service_name} error: {error}")
    
    return fallback_message or f"{service_name} encountered an error. Please try again."


def check_service_available(
    service_name: str,
    is_configured: bool,
    config_key: str,
) -> Optional[str]:
    """
    Check if a service is available and return error message if not.
    
    Args:
        service_name: Name of the service
        is_configured: Whether the service is configured
        config_key: Key in ERROR_MESSAGES for setup instructions
        
    Returns:
        Error message if not available, None if available
    """
    if not is_configured:
        return get_error_message(config_key, detailed=False)
    return None


class GracefulDegradation:
    """
    Helper for graceful degradation when services are unavailable.
    
    Usage:
        with GracefulDegradation("Canvas", "canvas_token") as gd:
            if gd.available:
                result = await canvas.get_assignments()
            else:
                result = gd.fallback_message
    """
    
    def __init__(
        self,
        service_name: str,
        config_key: str,
        is_available: bool = True,
    ):
        self.service_name = service_name
        self.config_key = config_key
        self.available = is_available
        self.fallback_message = get_error_message(config_key, detailed=False)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"{self.service_name} error: {exc_val}")
            return True  # Suppress the exception
        return False
