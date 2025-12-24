"""
Conversation Context Management for JARVIS - Phase 7 Part G

Manages conversation state across multiple turns:
- Message history tracking
- Topic detection and continuity
- Pronoun and reference resolution
- Context summarization for long conversations
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from loguru import logger


class MessageRole(Enum):
    """Role of message sender."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class ConversationMessage:
    """A single message in the conversation."""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def age_seconds(self) -> float:
        """Get message age in seconds."""
        return (datetime.now() - self.timestamp).total_seconds()


@dataclass
class ConversationTopic:
    """Represents a conversation topic."""
    name: str
    started_at: datetime
    last_mentioned: datetime
    message_count: int = 1
    entities: Dict[str, Any] = field(default_factory=dict)
    
    def is_active(self, timeout_minutes: int = 5) -> bool:
        """Check if topic is still active."""
        age = (datetime.now() - self.last_mentioned).total_seconds() / 60
        return age < timeout_minutes


@dataclass
class ConversationContext:
    """Current conversation context."""
    session_id: str
    user_id: str = "default"
    current_topic: Optional[ConversationTopic] = None
    active_entities: Dict[str, Any] = field(default_factory=dict)
    pending_clarification: Optional[str] = None
    last_intent: Optional[str] = None
    turn_count: int = 0
    
    def get_entity(self, entity_type: str) -> Optional[Any]:
        """Get an active entity by type."""
        return self.active_entities.get(entity_type)
    
    def set_entity(self, entity_type: str, value: Any):
        """Set an active entity."""
        self.active_entities[entity_type] = value
    
    def clear_entity(self, entity_type: str):
        """Clear an active entity."""
        self.active_entities.pop(entity_type, None)


class ConversationManager:
    """
    Manages conversation context and history.
    
    Tracks messages, detects topics, resolves references,
    and maintains context across conversation turns.
    """
    
    # Patterns for reference detection
    PRONOUN_PATTERNS = {
        "it": r"\b(it|this|that)\b",
        "they": r"\b(they|them|those|these)\b",
        "there": r"\b(there)\b",
        "then": r"\b(then|that time)\b",
    }
    
    # Topic keywords for detection
    TOPIC_KEYWORDS = {
        "weather": ["weather", "temperature", "forecast", "rain", "snow", "sunny", "cloudy"],
        "calendar": ["calendar", "schedule", "meeting", "appointment", "event"],
        "email": ["email", "message", "inbox", "send", "reply"],
        "smart_home": ["light", "switch", "thermostat", "device", "turn on", "turn off"],
        "documents": ["document", "file", "pdf", "search", "find"],
        "general": [],
    }
    
    def __init__(
        self,
        max_history: int = 20,
        context_timeout_minutes: int = 30,
    ):
        """
        Initialize conversation manager.
        
        Args:
            max_history: Maximum messages to keep in history
            context_timeout_minutes: Minutes before context expires
        """
        self.max_history = max_history
        self.context_timeout = context_timeout_minutes
        self._sessions: Dict[str, ConversationContext] = {}
        self._histories: Dict[str, deque] = {}
    
    def get_or_create_session(
        self,
        session_id: str,
        user_id: str = "default",
    ) -> ConversationContext:
        """
        Get or create a conversation session.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            
        Returns:
            ConversationContext for the session
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationContext(
                session_id=session_id,
                user_id=user_id,
            )
            self._histories[session_id] = deque(maxlen=self.max_history)
        
        return self._sessions[session_id]
    
    def add_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
    ) -> ConversationMessage:
        """
        Add a message to the conversation.
        
        Args:
            session_id: Session identifier
            role: Message role (user/assistant)
            content: Message content
            intent: Detected intent
            entities: Extracted entities
            
        Returns:
            Created ConversationMessage
        """
        context = self.get_or_create_session(session_id)
        history = self._histories[session_id]
        
        message = ConversationMessage(
            role=role,
            content=content,
            intent=intent,
            entities=entities or {},
        )
        
        history.append(message)
        
        # Update context
        if role == MessageRole.USER:
            context.turn_count += 1
            context.last_intent = intent
            
            # Update active entities
            if entities:
                for key, value in entities.items():
                    context.set_entity(key, value)
            
            # Detect and update topic
            topic = self._detect_topic(content, intent)
            if topic:
                if context.current_topic and context.current_topic.name == topic:
                    context.current_topic.last_mentioned = datetime.now()
                    context.current_topic.message_count += 1
                else:
                    context.current_topic = ConversationTopic(
                        name=topic,
                        started_at=datetime.now(),
                        last_mentioned=datetime.now(),
                    )
        
        return message
    
    def _detect_topic(self, content: str, intent: Optional[str] = None) -> Optional[str]:
        """Detect conversation topic from content."""
        content_lower = content.lower()
        
        # Use intent if available
        if intent:
            intent_lower = intent.lower()
            for topic in self.TOPIC_KEYWORDS:
                if topic in intent_lower:
                    return topic
        
        # Check keywords
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content_lower:
                    return topic
        
        return None
    
    def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[ConversationMessage]:
        """
        Get conversation history.
        
        Args:
            session_id: Session identifier
            limit: Maximum messages to return
            
        Returns:
            List of messages (oldest first)
        """
        if session_id not in self._histories:
            return []
        
        history = list(self._histories[session_id])
        if limit:
            history = history[-limit:]
        return history
    
    def resolve_references(
        self,
        session_id: str,
        query: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Resolve pronouns and references in a query.
        
        Args:
            session_id: Session identifier
            query: User query with potential references
            
        Returns:
            Tuple of (resolved query, resolved entities)
        """
        context = self.get_or_create_session(session_id)
        resolved_entities = {}
        resolved_query = query
        
        # Check for "what about X" pattern (topic continuation)
        what_about_match = re.search(r"what about\s+(.+?)(?:\?|$)", query.lower())
        if what_about_match:
            new_subject = what_about_match.group(1).strip()
            
            # If current topic is weather, assume new location
            if context.current_topic and context.current_topic.name == "weather":
                resolved_entities["location"] = new_subject.title()
                resolved_query = f"What's the weather in {new_subject.title()}?"
                return resolved_query, resolved_entities
        
        # Check for "tomorrow" / "next week" with weather context
        if context.current_topic and context.current_topic.name == "weather":
            if "tomorrow" in query.lower() and "weather" not in query.lower():
                location = context.get_entity("location")
                if location:
                    resolved_query = f"What's the weather forecast for tomorrow in {location}?"
                    resolved_entities["location"] = location
                    return resolved_query, resolved_entities
        
        # Check for pronoun references
        for pronoun_type, pattern in self.PRONOUN_PATTERNS.items():
            if re.search(pattern, query.lower()):
                # Try to resolve from context
                if pronoun_type == "it" or pronoun_type == "there":
                    # Could refer to location
                    location = context.get_entity("location")
                    if location and context.current_topic:
                        if context.current_topic.name == "weather":
                            resolved_entities["location"] = location
                
                elif pronoun_type == "they":
                    # Could refer to people/events
                    events = context.get_entity("events")
                    if events:
                        resolved_entities["events"] = events
        
        return resolved_query, resolved_entities
    
    def get_context_summary(self, session_id: str) -> str:
        """
        Get a summary of current conversation context.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Context summary string
        """
        context = self.get_or_create_session(session_id)
        history = self.get_history(session_id, limit=5)
        
        parts = []
        
        # Current topic
        if context.current_topic and context.current_topic.is_active():
            parts.append(f"Current topic: {context.current_topic.name}")
        
        # Active entities
        if context.active_entities:
            entities_str = ", ".join([f"{k}={v}" for k, v in context.active_entities.items()])
            parts.append(f"Active entities: {entities_str}")
        
        # Recent messages summary
        if history:
            recent = history[-3:]
            messages_str = " | ".join([
                f"{m.role.value}: {m.content[:50]}..."
                for m in recent
            ])
            parts.append(f"Recent: {messages_str}")
        
        return " | ".join(parts) if parts else "No active context"
    
    def should_continue_topic(
        self,
        session_id: str,
        new_query: str,
    ) -> bool:
        """
        Check if query continues current topic.
        
        Args:
            session_id: Session identifier
            new_query: New user query
            
        Returns:
            True if query continues current topic
        """
        context = self.get_or_create_session(session_id)
        
        if not context.current_topic:
            return False
        
        if not context.current_topic.is_active():
            return False
        
        # Check for continuation patterns
        continuation_patterns = [
            r"^(and|also|what about|how about|what else)",
            r"^(tomorrow|next|later|then)",
            r"^(it|that|this|there)",
        ]
        
        query_lower = new_query.lower().strip()
        for pattern in continuation_patterns:
            if re.match(pattern, query_lower):
                return True
        
        # Check if same topic keywords
        new_topic = self._detect_topic(new_query)
        if new_topic and new_topic == context.current_topic.name:
            return True
        
        return False
    
    def clear_session(self, session_id: str):
        """Clear a conversation session."""
        self._sessions.pop(session_id, None)
        self._histories.pop(session_id, None)
    
    def get_last_location(self, session_id: str) -> Optional[str]:
        """Get the last mentioned location from context."""
        context = self.get_or_create_session(session_id)
        return context.get_entity("location")
    
    def set_location(self, session_id: str, location: str):
        """Set the current location in context."""
        context = self.get_or_create_session(session_id)
        context.set_entity("location", location)


# Singleton instance
_conversation_manager: Optional[ConversationManager] = None


def get_conversation_manager() -> ConversationManager:
    """Get or create conversation manager singleton."""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager
