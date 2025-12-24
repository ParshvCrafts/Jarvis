"""
Conversation Memory Module for JARVIS.

Provides short-term conversation memory with sliding window
and message summarization.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class Message:
    """A conversation message."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Conversation:
    """A conversation session."""
    id: str
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    summary: Optional[str] = None
    
    def add_message(self, role: str, content: str, **metadata) -> Message:
        """Add a message to the conversation."""
        message = Message(role=role, content=content, metadata=metadata)
        self.messages.append(message)
        self.updated_at = datetime.now()
        return message
    
    def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """Get messages, optionally limited to most recent."""
        if limit is None:
            return self.messages
        return self.messages[-limit:]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "summary": self.summary,
        }


class ConversationMemory:
    """
    Short-term conversation memory with sliding window.
    
    Features:
    - Configurable message limit
    - Sliding window for context management
    - Conversation summarization
    - Multiple conversation support
    """
    
    def __init__(
        self,
        max_messages: int = 20,
        window_size: int = 10,
        llm_manager: Any = None,
    ):
        """
        Initialize conversation memory.
        
        Args:
            max_messages: Maximum messages to store per conversation.
            window_size: Number of recent messages to include in context.
            llm_manager: LLM manager for summarization.
        """
        self.max_messages = max_messages
        self.window_size = window_size
        self.llm_manager = llm_manager
        
        self._conversations: Dict[str, Conversation] = {}
        self._active_conversation_id: Optional[str] = None
    
    def create_conversation(self, conversation_id: Optional[str] = None) -> Conversation:
        """Create a new conversation."""
        import uuid
        
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())
        
        conversation = Conversation(id=conversation_id)
        self._conversations[conversation_id] = conversation
        self._active_conversation_id = conversation_id
        
        logger.debug(f"Created conversation: {conversation_id}")
        return conversation
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        return self._conversations.get(conversation_id)
    
    def get_active_conversation(self) -> Optional[Conversation]:
        """Get the active conversation."""
        if self._active_conversation_id:
            return self._conversations.get(self._active_conversation_id)
        return None
    
    def set_active_conversation(self, conversation_id: str) -> bool:
        """Set the active conversation."""
        if conversation_id in self._conversations:
            self._active_conversation_id = conversation_id
            return True
        return False
    
    def add_message(
        self,
        role: str,
        content: str,
        conversation_id: Optional[str] = None,
        **metadata,
    ) -> Optional[Message]:
        """
        Add a message to a conversation.
        
        Args:
            role: Message role ("user", "assistant", "system").
            content: Message content.
            conversation_id: Conversation ID (uses active if not specified).
            **metadata: Additional message metadata.
            
        Returns:
            The created message, or None if no conversation.
        """
        if conversation_id is None:
            conversation_id = self._active_conversation_id
        
        if conversation_id is None:
            # Create new conversation
            conversation = self.create_conversation()
            conversation_id = conversation.id
        
        conversation = self._conversations.get(conversation_id)
        if conversation is None:
            return None
        
        message = conversation.add_message(role, content, **metadata)
        
        # Check if we need to trim messages
        if len(conversation.messages) > self.max_messages:
            self._trim_conversation(conversation)
        
        return message
    
    def _trim_conversation(self, conversation: Conversation) -> None:
        """Trim conversation to max_messages, optionally summarizing."""
        if len(conversation.messages) <= self.max_messages:
            return
        
        # Keep the most recent messages
        messages_to_remove = len(conversation.messages) - self.max_messages
        old_messages = conversation.messages[:messages_to_remove]
        conversation.messages = conversation.messages[messages_to_remove:]
        
        # Optionally summarize removed messages
        if self.llm_manager and old_messages:
            self._summarize_messages(conversation, old_messages)
    
    def _summarize_messages(
        self,
        conversation: Conversation,
        messages: List[Message],
    ) -> None:
        """Summarize messages and update conversation summary."""
        try:
            from ..core.llm import Message as LLMMessage
            
            # Build summarization prompt
            messages_text = "\n".join([
                f"{m.role}: {m.content}" for m in messages
            ])
            
            prompt = f"""Summarize the following conversation excerpt concisely, 
preserving key information, decisions, and context:

{messages_text}

Summary:"""
            
            response = self.llm_manager.generate([
                LLMMessage(role="user", content=prompt)
            ])
            
            new_summary = response.content.strip()
            
            # Combine with existing summary
            if conversation.summary:
                conversation.summary = f"{conversation.summary}\n\n{new_summary}"
            else:
                conversation.summary = new_summary
            
            logger.debug(f"Summarized {len(messages)} messages")
        
        except Exception as e:
            logger.error(f"Failed to summarize messages: {e}")
    
    def get_context_messages(
        self,
        conversation_id: Optional[str] = None,
        include_summary: bool = True,
    ) -> List[Dict[str, str]]:
        """
        Get messages for LLM context.
        
        Args:
            conversation_id: Conversation ID (uses active if not specified).
            include_summary: Include conversation summary as system message.
            
        Returns:
            List of message dictionaries for LLM.
        """
        if conversation_id is None:
            conversation_id = self._active_conversation_id
        
        if conversation_id is None:
            return []
        
        conversation = self._conversations.get(conversation_id)
        if conversation is None:
            return []
        
        messages = []
        
        # Add summary as context
        if include_summary and conversation.summary:
            messages.append({
                "role": "system",
                "content": f"Previous conversation summary:\n{conversation.summary}",
            })
        
        # Add recent messages (within window)
        for msg in conversation.get_messages(self.window_size):
            messages.append({
                "role": msg.role,
                "content": msg.content,
            })
        
        return messages
    
    def clear_conversation(self, conversation_id: Optional[str] = None) -> bool:
        """Clear a conversation's messages."""
        if conversation_id is None:
            conversation_id = self._active_conversation_id
        
        if conversation_id and conversation_id in self._conversations:
            self._conversations[conversation_id].messages = []
            self._conversations[conversation_id].summary = None
            return True
        return False
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            if self._active_conversation_id == conversation_id:
                self._active_conversation_id = None
            return True
        return False
    
    def list_conversations(self) -> List[Dict[str, Any]]:
        """List all conversations."""
        return [
            {
                "id": conv.id,
                "message_count": len(conv.messages),
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
            }
            for conv in self._conversations.values()
        ]
    
    def export_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Export a conversation to dictionary."""
        conversation = self._conversations.get(conversation_id)
        if conversation:
            return conversation.to_dict()
        return None
    
    def import_conversation(self, data: Dict[str, Any]) -> Optional[Conversation]:
        """Import a conversation from dictionary."""
        try:
            conversation = Conversation(
                id=data["id"],
                messages=[Message.from_dict(m) for m in data.get("messages", [])],
                created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
                updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
                metadata=data.get("metadata", {}),
                summary=data.get("summary"),
            )
            self._conversations[conversation.id] = conversation
            return conversation
        except Exception as e:
            logger.error(f"Failed to import conversation: {e}")
            return None
