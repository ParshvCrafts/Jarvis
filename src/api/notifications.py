"""
Push Notifications Module for Mobile API.

Uses ntfy.sh for push notifications - free, self-hostable, no account required.

Features:
- Send notifications to mobile devices
- Support for different priority levels
- Action buttons in notifications
- Topic-based subscription
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class NotificationPriority(Enum):
    """Notification priority levels."""
    MIN = 1
    LOW = 2
    DEFAULT = 3
    HIGH = 4
    MAX = 5


@dataclass
class NotificationAction:
    """Action button for notification."""
    action: str  # "view", "http", "broadcast"
    label: str
    url: Optional[str] = None
    clear: bool = False


@dataclass
class Notification:
    """Notification to send."""
    topic: str
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.DEFAULT
    tags: List[str] = field(default_factory=list)
    click_url: Optional[str] = None
    actions: List[NotificationAction] = field(default_factory=list)
    attachment_url: Optional[str] = None
    icon_url: Optional[str] = None


@dataclass
class NotificationConfig:
    """Notification service configuration."""
    enabled: bool = True
    server_url: str = "https://ntfy.sh"  # Can be self-hosted
    default_topic: str = "jarvis-notifications"
    timeout: float = 10.0


class NotificationService:
    """
    Push notification service using ntfy.sh.
    
    ntfy.sh is a simple HTTP-based pub-sub notification service.
    - Free to use (or self-host)
    - No account required
    - Works on iOS and Android
    - Simple REST API
    
    Usage:
        service = NotificationService()
        await service.send(
            topic="jarvis-user123",
            title="JARVIS Alert",
            message="Your command has completed",
        )
    """
    
    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or NotificationConfig()
        self._client: Optional[httpx.AsyncClient] = None
        
        if not HTTPX_AVAILABLE:
            logger.warning("httpx not available. Push notifications disabled.")
    
    async def _get_client(self) -> Optional[httpx.AsyncClient]:
        """Get or create HTTP client."""
        if not HTTPX_AVAILABLE:
            return None
        
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.config.timeout)
        
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def send(
        self,
        topic: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.DEFAULT,
        tags: Optional[List[str]] = None,
        click_url: Optional[str] = None,
        actions: Optional[List[NotificationAction]] = None,
    ) -> bool:
        """
        Send a push notification.
        
        Args:
            topic: Topic to publish to (users subscribe to topics)
            title: Notification title
            message: Notification body
            priority: Priority level (1-5)
            tags: Emoji tags (e.g., ["warning", "robot"])
            click_url: URL to open when notification is clicked
            actions: Action buttons
        
        Returns:
            True if sent successfully.
        """
        if not self.config.enabled:
            return False
        
        client = await self._get_client()
        if not client:
            return False
        
        # Build headers
        headers = {
            "Title": title,
            "Priority": str(priority.value),
        }
        
        if tags:
            headers["Tags"] = ",".join(tags)
        
        if click_url:
            headers["Click"] = click_url
        
        if actions:
            action_strs = []
            for action in actions:
                if action.action == "view" and action.url:
                    action_strs.append(f"view, {action.label}, {action.url}")
                elif action.action == "http" and action.url:
                    action_strs.append(f"http, {action.label}, {action.url}")
            if action_strs:
                headers["Actions"] = "; ".join(action_strs)
        
        # Send notification
        url = f"{self.config.server_url}/{topic}"
        
        try:
            response = await client.post(url, content=message, headers=headers)
            
            if response.status_code == 200:
                logger.debug(f"Notification sent to {topic}: {title}")
                return True
            else:
                logger.warning(f"Notification failed: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Notification error: {e}")
            return False
    
    async def send_notification(self, notification: Notification) -> bool:
        """Send a Notification object."""
        return await self.send(
            topic=notification.topic,
            title=notification.title,
            message=notification.message,
            priority=notification.priority,
            tags=notification.tags,
            click_url=notification.click_url,
            actions=notification.actions,
        )
    
    async def send_command_response(
        self,
        user_topic: str,
        command: str,
        response: str,
    ) -> bool:
        """Send notification for command response."""
        # Truncate long responses
        if len(response) > 200:
            response = response[:197] + "..."
        
        return await self.send(
            topic=user_topic,
            title="JARVIS Response",
            message=response,
            priority=NotificationPriority.DEFAULT,
            tags=["robot", "speech_balloon"],
        )
    
    async def send_iot_alert(
        self,
        user_topic: str,
        device_name: str,
        event: str,
        details: Optional[str] = None,
    ) -> bool:
        """Send IoT device alert."""
        message = f"{device_name}: {event}"
        if details:
            message += f"\n{details}"
        
        # Choose tag based on event
        tags = ["house"]
        if "door" in device_name.lower():
            tags.append("door")
        elif "light" in device_name.lower():
            tags.append("bulb")
        
        if "open" in event.lower() or "unlock" in event.lower():
            tags.append("warning")
        
        return await self.send(
            topic=user_topic,
            title="IoT Alert",
            message=message,
            priority=NotificationPriority.HIGH,
            tags=tags,
        )
    
    async def send_reminder(
        self,
        user_topic: str,
        reminder_text: str,
        due_time: Optional[datetime] = None,
    ) -> bool:
        """Send reminder notification."""
        message = reminder_text
        if due_time:
            message += f"\nDue: {due_time.strftime('%I:%M %p')}"
        
        return await self.send(
            topic=user_topic,
            title="Reminder",
            message=message,
            priority=NotificationPriority.HIGH,
            tags=["bell", "clock"],
        )
    
    async def send_system_alert(
        self,
        user_topic: str,
        alert_type: str,
        message: str,
        severity: str = "warning",
    ) -> bool:
        """Send system alert notification."""
        priority = NotificationPriority.HIGH
        tags = ["computer"]
        
        if severity == "error":
            priority = NotificationPriority.MAX
            tags.append("x")
        elif severity == "warning":
            tags.append("warning")
        else:
            priority = NotificationPriority.DEFAULT
            tags.append("information_source")
        
        return await self.send(
            topic=user_topic,
            title=f"JARVIS {alert_type}",
            message=message,
            priority=priority,
            tags=tags,
        )


# ============================================================================
# User Topic Management
# ============================================================================

class UserTopicManager:
    """
    Manages user notification topics.
    
    Each user gets a unique topic for their notifications.
    Topics are derived from user ID to ensure privacy.
    """
    
    def __init__(self, topic_prefix: str = "jarvis"):
        self.topic_prefix = topic_prefix
        self._user_topics: Dict[str, str] = {}
    
    def get_user_topic(self, user_id: str) -> str:
        """Get notification topic for a user."""
        if user_id not in self._user_topics:
            # Generate topic from user ID
            import hashlib
            topic_hash = hashlib.sha256(user_id.encode()).hexdigest()[:12]
            self._user_topics[user_id] = f"{self.topic_prefix}-{topic_hash}"
        
        return self._user_topics[user_id]
    
    def set_user_topic(self, user_id: str, topic: str) -> None:
        """Set custom topic for a user."""
        self._user_topics[user_id] = topic


# ============================================================================
# Singleton Instances
# ============================================================================

_notification_service: Optional[NotificationService] = None
_topic_manager: Optional[UserTopicManager] = None


def get_notification_service(config: Optional[NotificationConfig] = None) -> NotificationService:
    """Get or create the global notification service."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService(config)
    return _notification_service


def get_topic_manager() -> UserTopicManager:
    """Get or create the global topic manager."""
    global _topic_manager
    if _topic_manager is None:
        _topic_manager = UserTopicManager()
    return _topic_manager


# ============================================================================
# Convenience Functions
# ============================================================================

async def notify_user(
    user_id: str,
    title: str,
    message: str,
    priority: NotificationPriority = NotificationPriority.DEFAULT,
    tags: Optional[List[str]] = None,
) -> bool:
    """Send notification to a user by their ID."""
    service = get_notification_service()
    topic_manager = get_topic_manager()
    
    topic = topic_manager.get_user_topic(user_id)
    
    return await service.send(
        topic=topic,
        title=title,
        message=message,
        priority=priority,
        tags=tags,
    )


async def notify_command_complete(
    user_id: str,
    command: str,
    response: str,
) -> bool:
    """Notify user that their command completed."""
    service = get_notification_service()
    topic_manager = get_topic_manager()
    
    topic = topic_manager.get_user_topic(user_id)
    
    return await service.send_command_response(topic, command, response)


async def notify_iot_event(
    user_id: str,
    device_name: str,
    event: str,
) -> bool:
    """Notify user of IoT event."""
    service = get_notification_service()
    topic_manager = get_topic_manager()
    
    topic = topic_manager.get_user_topic(user_id)
    
    return await service.send_iot_alert(topic, device_name, event)
