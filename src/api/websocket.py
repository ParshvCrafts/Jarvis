"""
WebSocket Handler for Real-Time Communication.

Provides bidirectional real-time communication between mobile app and JARVIS.

Server → Client Events:
- response_chunk: Streaming LLM response
- response_complete: Full response ready
- tts_ready: TTS audio available
- device_state_changed: IoT device update
- notification: System notification
- health_alert: Performance/health warning

Client → Server Events:
- audio_chunk: Streaming voice input
- command: Text command
- cancel: Cancel current operation
- ping: Keep-alive
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from loguru import logger

from .auth import get_auth_manager
from .models import WSMessage, WSMessageType


websocket_router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """
    Manages WebSocket connections.
    
    Handles:
    - Connection lifecycle
    - Message broadcasting
    - User-specific messaging
    - Connection health monitoring
    """
    
    def __init__(self):
        # Active connections: user_id -> set of WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
        # Connection metadata: WebSocket -> metadata dict
        self._metadata: Dict[WebSocket, Dict[str, Any]] = {}
        # Subscriptions: topic -> set of WebSocket connections
        self._subscriptions: Dict[str, Set[WebSocket]] = {}
        # Message queue for offline users
        self._message_queue: Dict[str, List[WSMessage]] = {}
        # Last ping times
        self._last_ping: Dict[WebSocket, float] = {}
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        device_id: Optional[str] = None,
    ) -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        
        # Add to connections
        if user_id not in self._connections:
            self._connections[user_id] = set()
        self._connections[user_id].add(websocket)
        
        # Store metadata
        self._metadata[websocket] = {
            "user_id": user_id,
            "device_id": device_id,
            "connected_at": datetime.utcnow(),
        }
        
        self._last_ping[websocket] = time.time()
        
        logger.info(f"WebSocket connected: user={user_id}, device={device_id}")
        
        # Send queued messages
        await self._send_queued_messages(websocket, user_id)
    
    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        metadata = self._metadata.get(websocket, {})
        user_id = metadata.get("user_id")
        
        # Remove from connections
        if user_id and user_id in self._connections:
            self._connections[user_id].discard(websocket)
            if not self._connections[user_id]:
                del self._connections[user_id]
        
        # Remove from subscriptions
        for topic in list(self._subscriptions.keys()):
            self._subscriptions[topic].discard(websocket)
            if not self._subscriptions[topic]:
                del self._subscriptions[topic]
        
        # Clean up metadata
        self._metadata.pop(websocket, None)
        self._last_ping.pop(websocket, None)
        
        logger.info(f"WebSocket disconnected: user={user_id}")
    
    async def subscribe(self, websocket: WebSocket, topic: str) -> None:
        """Subscribe a connection to a topic."""
        if topic not in self._subscriptions:
            self._subscriptions[topic] = set()
        self._subscriptions[topic].add(websocket)
    
    async def unsubscribe(self, websocket: WebSocket, topic: str) -> None:
        """Unsubscribe a connection from a topic."""
        if topic in self._subscriptions:
            self._subscriptions[topic].discard(websocket)
    
    async def send_personal(
        self,
        websocket: WebSocket,
        message: WSMessage,
    ) -> bool:
        """Send message to a specific connection."""
        try:
            await websocket.send_json(message.model_dump(mode="json"))
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    async def send_to_user(
        self,
        user_id: str,
        message: WSMessage,
        queue_if_offline: bool = True,
    ) -> int:
        """Send message to all connections for a user."""
        sent_count = 0
        
        if user_id in self._connections:
            for websocket in self._connections[user_id].copy():
                if await self.send_personal(websocket, message):
                    sent_count += 1
        
        # Queue if user offline and queueing enabled
        if sent_count == 0 and queue_if_offline:
            if user_id not in self._message_queue:
                self._message_queue[user_id] = []
            self._message_queue[user_id].append(message)
            # Limit queue size
            if len(self._message_queue[user_id]) > 100:
                self._message_queue[user_id] = self._message_queue[user_id][-100:]
        
        return sent_count
    
    async def broadcast_to_topic(
        self,
        topic: str,
        message: WSMessage,
    ) -> int:
        """Broadcast message to all subscribers of a topic."""
        sent_count = 0
        
        if topic in self._subscriptions:
            for websocket in self._subscriptions[topic].copy():
                if await self.send_personal(websocket, message):
                    sent_count += 1
        
        return sent_count
    
    async def broadcast_all(self, message: WSMessage) -> int:
        """Broadcast message to all connected users."""
        sent_count = 0
        
        for connections in self._connections.values():
            for websocket in connections.copy():
                if await self.send_personal(websocket, message):
                    sent_count += 1
        
        return sent_count
    
    async def _send_queued_messages(
        self,
        websocket: WebSocket,
        user_id: str,
    ) -> None:
        """Send queued messages to a newly connected user."""
        if user_id in self._message_queue:
            messages = self._message_queue.pop(user_id)
            for message in messages:
                await self.send_personal(websocket, message)
    
    def update_ping(self, websocket: WebSocket) -> None:
        """Update last ping time for a connection."""
        self._last_ping[websocket] = time.time()
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self._connections.values())
    
    def get_user_count(self) -> int:
        """Get number of connected users."""
        return len(self._connections)


# Global connection manager
manager = ConnectionManager()


# Reference to JARVIS instance
_jarvis_instance = None


def set_websocket_jarvis(jarvis):
    """Set JARVIS instance for WebSocket handlers."""
    global _jarvis_instance
    _jarvis_instance = jarvis


@websocket_router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time communication.
    
    Connect with: ws://host:port/api/v1/ws?token=<jwt_token>
    
    Message format (JSON):
    {
        "type": "command|audio_chunk|cancel|ping|subscribe|unsubscribe",
        "data": { ... },
        "message_id": "optional-uuid"
    }
    """
    # Verify token
    auth = get_auth_manager()
    payload = auth.verify_token(token, token_type="access")
    
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    user_id = payload.get("sub")
    device_id = payload.get("device_id")
    
    # Connect
    await manager.connect(websocket, user_id, device_id)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            # Parse message
            try:
                msg_type = WSMessageType(data.get("type", ""))
                msg_data = data.get("data", {})
                msg_id = data.get("message_id", str(uuid.uuid4()))
            except ValueError:
                await manager.send_personal(websocket, WSMessage(
                    type=WSMessageType.ERROR,
                    data={"error": f"Unknown message type: {data.get('type')}"},
                ))
                continue
            
            # Handle message
            await handle_message(
                websocket=websocket,
                user_id=user_id,
                msg_type=msg_type,
                msg_data=msg_data,
                msg_id=msg_id,
            )
    
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


async def handle_message(
    websocket: WebSocket,
    user_id: str,
    msg_type: WSMessageType,
    msg_data: Dict[str, Any],
    msg_id: str,
) -> None:
    """Handle incoming WebSocket message."""
    
    if msg_type == WSMessageType.PING:
        # Respond with pong
        manager.update_ping(websocket)
        await manager.send_personal(websocket, WSMessage(
            type=WSMessageType.PONG,
            data={"timestamp": time.time()},
            message_id=msg_id,
        ))
    
    elif msg_type == WSMessageType.COMMAND:
        # Process text command
        text = msg_data.get("text", "")
        if not text:
            await manager.send_personal(websocket, WSMessage(
                type=WSMessageType.ERROR,
                data={"error": "No command text provided"},
                message_id=msg_id,
            ))
            return
        
        # Process command (with streaming if available)
        await process_command_streaming(websocket, user_id, text, msg_id)
    
    elif msg_type == WSMessageType.AUDIO_CHUNK:
        # Handle audio chunk for STT
        audio_data = msg_data.get("audio")
        if audio_data:
            await handle_audio_chunk(websocket, user_id, audio_data, msg_id)
    
    elif msg_type == WSMessageType.CANCEL:
        # Cancel current operation
        await handle_cancel(websocket, user_id, msg_id)
    
    elif msg_type == WSMessageType.SUBSCRIBE:
        # Subscribe to topic
        topic = msg_data.get("topic")
        if topic:
            await manager.subscribe(websocket, topic)
            await manager.send_personal(websocket, WSMessage(
                type=WSMessageType.NOTIFICATION,
                data={"message": f"Subscribed to {topic}"},
                message_id=msg_id,
            ))
    
    elif msg_type == WSMessageType.UNSUBSCRIBE:
        # Unsubscribe from topic
        topic = msg_data.get("topic")
        if topic:
            await manager.unsubscribe(websocket, topic)


async def process_command_streaming(
    websocket: WebSocket,
    user_id: str,
    text: str,
    msg_id: str,
) -> None:
    """Process command with streaming response."""
    start_time = time.time()
    
    if _jarvis_instance:
        try:
            # Check if streaming is available
            if hasattr(_jarvis_instance, '_performance') and _jarvis_instance._performance:
                perf = _jarvis_instance._performance
                
                # Try streaming response
                if hasattr(perf, '_streaming') and perf._streaming:
                    # Stream chunks
                    full_response = ""
                    
                    # For now, process synchronously and send as single response
                    # TODO: Implement true streaming when LLM supports it
                    response = _jarvis_instance._process_command(text)
                    
                    # Send response in chunks for demo
                    words = response.split()
                    chunk = ""
                    for i, word in enumerate(words):
                        chunk += word + " "
                        if len(chunk) > 50 or i == len(words) - 1:
                            await manager.send_personal(websocket, WSMessage(
                                type=WSMessageType.RESPONSE_CHUNK,
                                data={"chunk": chunk.strip(), "index": i},
                                message_id=msg_id,
                            ))
                            chunk = ""
                            await asyncio.sleep(0.05)  # Small delay for streaming effect
                    
                    full_response = response
                else:
                    # Non-streaming
                    full_response = _jarvis_instance._process_command(text)
            else:
                full_response = _jarvis_instance._process_command(text)
            
            # Send complete response
            processing_time = (time.time() - start_time) * 1000
            await manager.send_personal(websocket, WSMessage(
                type=WSMessageType.RESPONSE_COMPLETE,
                data={
                    "response": full_response,
                    "processing_time_ms": processing_time,
                    "command": text,
                },
                message_id=msg_id,
            ))
            
        except Exception as e:
            logger.error(f"Command processing error: {e}")
            await manager.send_personal(websocket, WSMessage(
                type=WSMessageType.ERROR,
                data={"error": str(e)},
                message_id=msg_id,
            ))
    else:
        await manager.send_personal(websocket, WSMessage(
            type=WSMessageType.ERROR,
            data={"error": "JARVIS not available"},
            message_id=msg_id,
        ))


# Audio buffer for streaming STT
_audio_buffers: Dict[str, bytes] = {}


async def handle_audio_chunk(
    websocket: WebSocket,
    user_id: str,
    audio_data: str,  # Base64 encoded
    msg_id: str,
) -> None:
    """Handle incoming audio chunk for STT."""
    import base64
    
    try:
        # Decode audio
        audio_bytes = base64.b64decode(audio_data)
        
        # Add to buffer
        if user_id not in _audio_buffers:
            _audio_buffers[user_id] = b""
        _audio_buffers[user_id] += audio_bytes
        
        # Check if we have enough audio (e.g., 1 second at 16kHz 16-bit = 32000 bytes)
        if len(_audio_buffers[user_id]) >= 32000:
            # Process audio
            audio = _audio_buffers[user_id]
            _audio_buffers[user_id] = b""
            
            # Transcribe
            if _jarvis_instance and hasattr(_jarvis_instance, '_voice_pipeline'):
                voice = _jarvis_instance._voice_pipeline
                if voice and hasattr(voice, 'transcribe'):
                    text = await asyncio.to_thread(voice.transcribe, audio)
                    
                    if text:
                        await manager.send_personal(websocket, WSMessage(
                            type=WSMessageType.NOTIFICATION,
                            data={"transcript": text, "final": False},
                            message_id=msg_id,
                        ))
    
    except Exception as e:
        logger.error(f"Audio processing error: {e}")


async def handle_cancel(
    websocket: WebSocket,
    user_id: str,
    msg_id: str,
) -> None:
    """Handle cancel request."""
    # Clear audio buffer
    if user_id in _audio_buffers:
        del _audio_buffers[user_id]
    
    # Interrupt streaming if active
    if _jarvis_instance and hasattr(_jarvis_instance, '_performance'):
        perf = _jarvis_instance._performance
        if perf and hasattr(perf, 'interrupt_streaming'):
            perf.interrupt_streaming()
    
    await manager.send_personal(websocket, WSMessage(
        type=WSMessageType.NOTIFICATION,
        data={"message": "Operation cancelled"},
        message_id=msg_id,
    ))


# ============================================================================
# Utility Functions for External Use
# ============================================================================

async def notify_device_state_change(
    device_id: str,
    new_state: Dict[str, Any],
) -> None:
    """Notify all connected clients of device state change."""
    message = WSMessage(
        type=WSMessageType.DEVICE_STATE_CHANGED,
        data={
            "device_id": device_id,
            "state": new_state,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
    await manager.broadcast_to_topic("devices", message)
    await manager.broadcast_to_topic(f"device:{device_id}", message)


async def send_notification(
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "info",
) -> None:
    """Send notification to a specific user."""
    ws_message = WSMessage(
        type=WSMessageType.NOTIFICATION,
        data={
            "title": title,
            "message": message,
            "notification_type": notification_type,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
    await manager.send_to_user(user_id, ws_message, queue_if_offline=True)


async def send_health_alert(
    alert_type: str,
    message: str,
    severity: str = "warning",
) -> None:
    """Broadcast health alert to all connected clients."""
    ws_message = WSMessage(
        type=WSMessageType.HEALTH_ALERT,
        data={
            "alert_type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
    await manager.broadcast_all(ws_message)


def get_connection_stats() -> Dict[str, Any]:
    """Get WebSocket connection statistics."""
    return {
        "total_connections": manager.get_connection_count(),
        "unique_users": manager.get_user_count(),
    }
