"""
Mobile API Module for JARVIS.

Provides RESTful API and WebSocket endpoints for mobile app integration.

Components:
- auth: JWT authentication and device registration
- routes: API endpoint handlers
- websocket: Real-time communication
- notifications: Push notification support (ntfy.sh)
- voice: Speech-to-text and text-to-speech endpoints
"""

try:
    from .app import create_app, get_app, run_api_server
    from .auth import AuthManager, AuthConfig, get_auth_manager
    from .websocket import (
        manager as websocket_manager,
        notify_device_state_change,
        send_notification as ws_send_notification,
        send_health_alert,
    )
    from .notifications import (
        NotificationService,
        NotificationConfig,
        get_notification_service,
        notify_user,
        notify_command_complete,
        notify_iot_event,
    )
    
    API_AVAILABLE = True
except ImportError as e:
    API_AVAILABLE = False
    create_app = None
    get_app = None

__all__ = [
    "API_AVAILABLE",
    "create_app",
    "get_app",
    "run_api_server",
    "AuthManager",
    "AuthConfig",
    "get_auth_manager",
    "websocket_manager",
    "notify_device_state_change",
    "ws_send_notification",
    "send_health_alert",
    "NotificationService",
    "NotificationConfig",
    "get_notification_service",
    "notify_user",
    "notify_command_complete",
    "notify_iot_event",
]
