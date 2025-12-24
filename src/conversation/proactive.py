"""
Proactive Assistant for JARVIS - Phase 7 Part G

Provides proactive suggestions and assistance:
- Follow-up suggestions after queries
- Time-based recommendations
- Context-aware assistance
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from loguru import logger


class SuggestionType(Enum):
    """Types of proactive suggestions."""
    FOLLOWUP = "followup"  # Follow-up to current query
    TIME_BASED = "time_based"  # Based on time of day
    PATTERN_BASED = "pattern_based"  # Based on usage patterns
    CONTEXT_BASED = "context_based"  # Based on conversation context
    REMINDER = "reminder"  # Reminder about something


@dataclass
class ProactiveSuggestion:
    """A proactive suggestion for the user."""
    suggestion_type: SuggestionType
    message: str
    action: Optional[str] = None  # Query to execute if accepted
    priority: int = 5  # 1-10, higher = more important
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if suggestion has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def format_suggestion(self) -> str:
        """Format suggestion for display."""
        return self.message


class ProactiveAssistant:
    """
    Generates proactive suggestions and assistance.
    
    Analyzes context and patterns to offer helpful
    suggestions without being intrusive.
    """
    
    # Follow-up suggestions by intent
    FOLLOWUP_SUGGESTIONS = {
        "weather": [
            ("Would you like the forecast for tomorrow?", "What's the weather forecast for tomorrow?"),
            ("Should I check if you need an umbrella?", "Will it rain today?"),
            ("Want to see the weekly forecast?", "What's the 7-day forecast?"),
        ],
        "calendar": [
            ("Would you like to schedule something?", "Schedule a meeting"),
            ("Should I check tomorrow's schedule?", "What's on my calendar tomorrow?"),
            ("Want me to send meeting invites?", None),
        ],
        "email": [
            ("Would you like to compose a reply?", "Reply to this email"),
            ("Should I mark these as read?", None),
            ("Want to see emails from this sender?", None),
        ],
        "smart_home": [
            ("Should I adjust any other devices?", "List smart home devices"),
            ("Want me to create a scene for this?", None),
        ],
        "documents": [
            ("Would you like me to search for more?", None),
            ("Should I summarize the key points?", "Summarize the document"),
        ],
    }
    
    # Time-based suggestions
    TIME_SUGGESTIONS = {
        "morning": [  # 6-10 AM
            ("Good morning! Would you like a weather update?", "What's the weather today?"),
            ("Ready to check your schedule for today?", "What's on my calendar today?"),
            ("Want to see your unread emails?", "Check my unread emails"),
        ],
        "midday": [  # 11 AM - 1 PM
            ("Time for a lunch break? I can check nearby restaurants.", None),
            ("Want me to check your afternoon schedule?", "What's on my calendar this afternoon?"),
        ],
        "afternoon": [  # 2-5 PM
            ("Would you like to review tomorrow's schedule?", "What's on my calendar tomorrow?"),
            ("Should I check for any urgent emails?", "Check my unread emails"),
        ],
        "evening": [  # 6-9 PM
            ("Would you like tomorrow's weather forecast?", "What's the weather forecast for tomorrow?"),
            ("Ready to review tomorrow's schedule?", "What's on my calendar tomorrow?"),
        ],
    }
    
    def __init__(
        self,
        max_suggestions_per_turn: int = 2,
        cooldown_minutes: int = 5,
    ):
        """
        Initialize proactive assistant.
        
        Args:
            max_suggestions_per_turn: Max suggestions to show at once
            cooldown_minutes: Minutes between similar suggestions
        """
        self.max_suggestions = max_suggestions_per_turn
        self.cooldown_minutes = cooldown_minutes
        self._last_suggestions: Dict[str, datetime] = {}
        self._suggestion_counts: Dict[str, int] = {}
    
    def get_followup_suggestions(
        self,
        intent: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ProactiveSuggestion]:
        """
        Get follow-up suggestions for an intent.
        
        Args:
            intent: Current query intent
            context: Additional context
            
        Returns:
            List of ProactiveSuggestion objects
        """
        suggestions = []
        intent_lower = intent.lower()
        
        # Find matching suggestions
        for key, suggestion_list in self.FOLLOWUP_SUGGESTIONS.items():
            if key in intent_lower:
                for message, action in suggestion_list:
                    # Check cooldown
                    suggestion_key = f"followup_{key}_{message[:20]}"
                    if self._is_on_cooldown(suggestion_key):
                        continue
                    
                    suggestions.append(ProactiveSuggestion(
                        suggestion_type=SuggestionType.FOLLOWUP,
                        message=message,
                        action=action,
                        priority=7,
                        expires_at=datetime.now() + timedelta(minutes=5),
                        metadata={"intent": intent, "key": suggestion_key},
                    ))
                break
        
        # Limit and record
        suggestions = suggestions[:self.max_suggestions]
        for s in suggestions:
            self._record_suggestion(s.metadata.get("key", ""))
        
        return suggestions
    
    def get_time_based_suggestions(self) -> List[ProactiveSuggestion]:
        """
        Get suggestions based on current time.
        
        Returns:
            List of time-appropriate suggestions
        """
        hour = datetime.now().hour
        suggestions = []
        
        # Determine time period
        if 6 <= hour < 10:
            period = "morning"
        elif 11 <= hour < 14:
            period = "midday"
        elif 14 <= hour < 18:
            period = "afternoon"
        elif 18 <= hour < 22:
            period = "evening"
        else:
            return []  # No suggestions late night/early morning
        
        suggestion_list = self.TIME_SUGGESTIONS.get(period, [])
        
        for message, action in suggestion_list:
            suggestion_key = f"time_{period}_{message[:20]}"
            if self._is_on_cooldown(suggestion_key):
                continue
            
            suggestions.append(ProactiveSuggestion(
                suggestion_type=SuggestionType.TIME_BASED,
                message=message,
                action=action,
                priority=5,
                expires_at=datetime.now() + timedelta(hours=1),
                metadata={"period": period, "key": suggestion_key},
            ))
        
        suggestions = suggestions[:1]  # Only one time-based suggestion
        for s in suggestions:
            self._record_suggestion(s.metadata.get("key", ""))
        
        return suggestions
    
    def get_context_suggestions(
        self,
        context: Dict[str, Any],
    ) -> List[ProactiveSuggestion]:
        """
        Get suggestions based on conversation context.
        
        Args:
            context: Current conversation context
            
        Returns:
            List of context-aware suggestions
        """
        suggestions = []
        
        # Check for location context
        location = context.get("location")
        if location:
            suggestion_key = f"context_location_{location}"
            if not self._is_on_cooldown(suggestion_key):
                suggestions.append(ProactiveSuggestion(
                    suggestion_type=SuggestionType.CONTEXT_BASED,
                    message=f"Would you like directions to {location}?",
                    action=None,
                    priority=4,
                    metadata={"key": suggestion_key},
                ))
        
        # Check for event context
        event = context.get("event")
        if event:
            suggestion_key = f"context_event_{str(event)[:20]}"
            if not self._is_on_cooldown(suggestion_key):
                suggestions.append(ProactiveSuggestion(
                    suggestion_type=SuggestionType.CONTEXT_BASED,
                    message="Should I set a reminder for this event?",
                    action=None,
                    priority=6,
                    metadata={"key": suggestion_key},
                ))
        
        suggestions = suggestions[:self.max_suggestions]
        for s in suggestions:
            self._record_suggestion(s.metadata.get("key", ""))
        
        return suggestions
    
    def _is_on_cooldown(self, suggestion_key: str) -> bool:
        """Check if a suggestion is on cooldown."""
        if suggestion_key not in self._last_suggestions:
            return False
        
        last_time = self._last_suggestions[suggestion_key]
        elapsed = (datetime.now() - last_time).total_seconds() / 60
        return elapsed < self.cooldown_minutes
    
    def _record_suggestion(self, suggestion_key: str):
        """Record that a suggestion was shown."""
        self._last_suggestions[suggestion_key] = datetime.now()
        self._suggestion_counts[suggestion_key] = self._suggestion_counts.get(suggestion_key, 0) + 1
    
    def format_suggestions(
        self,
        suggestions: List[ProactiveSuggestion],
    ) -> Optional[str]:
        """
        Format suggestions for display.
        
        Args:
            suggestions: List of suggestions
            
        Returns:
            Formatted string or None if no suggestions
        """
        if not suggestions:
            return None
        
        if len(suggestions) == 1:
            return f"\n💡 {suggestions[0].message}"
        
        lines = ["\n💡 Suggestions:"]
        for i, s in enumerate(suggestions, 1):
            lines.append(f"   {i}. {s.message}")
        
        return "\n".join(lines)
    
    def should_show_suggestions(
        self,
        turn_count: int,
        last_suggestion_turn: int,
    ) -> bool:
        """
        Determine if suggestions should be shown.
        
        Args:
            turn_count: Current conversation turn
            last_suggestion_turn: Turn when last suggestion was shown
            
        Returns:
            True if suggestions should be shown
        """
        # Don't show on every turn
        if turn_count - last_suggestion_turn < 2:
            return False
        
        # Don't overwhelm with suggestions
        if turn_count < 2:
            return False
        
        return True
    
    def get_greeting_with_suggestions(
        self,
        user_name: Optional[str] = None,
    ) -> str:
        """
        Generate a greeting with optional suggestions.
        
        Args:
            user_name: User's name if known
            
        Returns:
            Greeting string
        """
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            greeting = "Good morning"
        elif 12 <= hour < 17:
            greeting = "Good afternoon"
        elif 17 <= hour < 21:
            greeting = "Good evening"
        else:
            greeting = "Hello"
        
        if user_name:
            greeting = f"{greeting}, {user_name}"
        
        greeting += "!"
        
        # Add time-based suggestion
        time_suggestions = self.get_time_based_suggestions()
        if time_suggestions:
            greeting += f" {time_suggestions[0].message}"
        
        return greeting


# Singleton instance
_proactive_assistant: Optional[ProactiveAssistant] = None


def get_proactive_assistant() -> ProactiveAssistant:
    """Get or create proactive assistant singleton."""
    global _proactive_assistant
    if _proactive_assistant is None:
        _proactive_assistant = ProactiveAssistant()
    return _proactive_assistant
