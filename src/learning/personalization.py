"""
Personalization Engine for JARVIS - Phase 7 Part F

Combines preferences and patterns to provide adaptive responses:
- Applies user preferences to responses
- Suggests proactive actions
- Personalizes response format and content
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from .preferences import PreferenceManager, get_preference_manager, Verbosity
from .patterns import PatternDetector, get_pattern_detector, PatternType


@dataclass
class PersonalizedContext:
    """Context for personalized response generation."""
    user_id: str
    default_location: Optional[str] = None
    temperature_unit: str = "fahrenheit"
    time_format: str = "12h"
    verbosity: str = "normal"
    use_emojis: bool = True
    formal_tone: bool = False
    nickname: Optional[str] = None
    suggested_followups: List[str] = None
    proactive_suggestions: List[str] = None
    
    def __post_init__(self):
        if self.suggested_followups is None:
            self.suggested_followups = []
        if self.proactive_suggestions is None:
            self.proactive_suggestions = []


class PersonalizationEngine:
    """
    Engine for personalizing JARVIS responses.
    
    Combines user preferences and detected patterns to:
    - Apply formatting preferences
    - Provide default values
    - Suggest follow-up actions
    - Generate proactive recommendations
    """
    
    def __init__(
        self,
        preference_manager: Optional[PreferenceManager] = None,
        pattern_detector: Optional[PatternDetector] = None,
    ):
        """
        Initialize personalization engine.
        
        Args:
            preference_manager: User preference manager
            pattern_detector: Usage pattern detector
        """
        self.preferences = preference_manager or get_preference_manager()
        self.patterns = pattern_detector or get_pattern_detector()
    
    def get_context(self, user_id: str = "default") -> PersonalizedContext:
        """
        Get personalized context for response generation.
        
        Args:
            user_id: User identifier
            
        Returns:
            PersonalizedContext with user preferences and suggestions
        """
        prefs = self.preferences.get_preferences(user_id)
        
        # Get time-based suggestions
        time_suggestions = self.patterns.get_time_based_suggestions(user_id)
        
        return PersonalizedContext(
            user_id=user_id,
            default_location=self.preferences.get_default_location("weather", user_id),
            temperature_unit=prefs.temperature_unit.value,
            time_format=prefs.time_format.value,
            verbosity=prefs.verbosity.value,
            use_emojis=prefs.use_emojis,
            formal_tone=prefs.formal_tone,
            nickname=prefs.nickname,
            proactive_suggestions=time_suggestions,
        )
    
    def personalize_response(
        self,
        response: str,
        user_id: str = "default",
    ) -> str:
        """
        Apply personalization to a response.
        
        Args:
            response: Original response text
            user_id: User identifier
            
        Returns:
            Personalized response
        """
        context = self.get_context(user_id)
        
        # Apply verbosity preference
        if context.verbosity == "brief":
            response = self._make_brief(response)
        elif context.verbosity == "detailed":
            response = self._make_detailed(response)
        
        # Apply emoji preference
        if not context.use_emojis:
            response = self._remove_emojis(response)
        
        # Apply formality
        if context.formal_tone:
            response = self._make_formal(response)
        
        # Add nickname if set
        if context.nickname and response.startswith("Here"):
            response = response.replace("Here", f"Here you go, {context.nickname}. Here", 1)
        
        return response
    
    def _make_brief(self, text: str) -> str:
        """Shorten response for brief preference."""
        lines = text.split("\n")
        
        # Keep first few lines and summary
        if len(lines) > 5:
            # Keep header and first few content lines
            brief_lines = lines[:4]
            brief_lines.append("...")
            return "\n".join(brief_lines)
        
        return text
    
    def _make_detailed(self, text: str) -> str:
        """Response is already detailed, just return as-is."""
        return text
    
    def _remove_emojis(self, text: str) -> str:
        """Remove emojis from text."""
        import re
        # Remove common weather/UI emojis
        emoji_pattern = re.compile(
            "["
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F680-\U0001F6FF"  # transport & map
            "\U0001F700-\U0001F77F"  # alchemical
            "\U0001F780-\U0001F7FF"  # geometric
            "\U0001F800-\U0001F8FF"  # supplemental arrows
            "\U0001F900-\U0001F9FF"  # supplemental symbols
            "\U0001FA00-\U0001FA6F"  # chess
            "\U0001FA70-\U0001FAFF"  # symbols
            "\U00002702-\U000027B0"  # dingbats
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        return emoji_pattern.sub("", text).strip()
    
    def _make_formal(self, text: str) -> str:
        """Make response more formal."""
        # Simple replacements for more formal tone
        replacements = {
            "Hey": "Hello",
            "hey": "hello",
            "Yeah": "Yes",
            "yeah": "yes",
            "Nope": "No",
            "nope": "no",
            "gonna": "going to",
            "wanna": "want to",
            "gotta": "have to",
            "kinda": "somewhat",
            "pretty": "quite",
            "awesome": "excellent",
            "cool": "good",
        }
        
        for informal, formal in replacements.items():
            text = text.replace(informal, formal)
        
        return text
    
    def get_followup_suggestions(
        self,
        current_intent: str,
        user_id: str = "default",
    ) -> List[str]:
        """
        Get suggested follow-up queries.
        
        Args:
            current_intent: Current query intent
            user_id: User identifier
            
        Returns:
            List of suggested follow-up queries
        """
        suggestions = []
        
        # Get pattern-based suggestions
        pattern_suggestions = self.patterns.get_suggested_actions(current_intent, user_id)
        
        # Convert intents to natural language suggestions
        intent_to_suggestion = {
            "weather": "Would you like the forecast for tomorrow?",
            "calendar": "Should I check your calendar?",
            "email": "Want me to check your email?",
            "research": "Would you like me to search for more information?",
            "iot": "Should I adjust any other devices?",
        }
        
        for intent in pattern_suggestions:
            if intent in intent_to_suggestion:
                suggestions.append(intent_to_suggestion[intent])
        
        # Add context-specific suggestions
        if current_intent == "weather":
            suggestions.append("Would you like the forecast for the week?")
        elif current_intent == "calendar":
            suggestions.append("Should I schedule something?")
        elif current_intent == "email":
            suggestions.append("Would you like to compose a reply?")
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    def get_proactive_greeting(self, user_id: str = "default") -> Optional[str]:
        """
        Generate a proactive greeting based on time and patterns.
        
        Args:
            user_id: User identifier
            
        Returns:
            Proactive greeting or None
        """
        now = datetime.now()
        hour = now.hour
        context = self.get_context(user_id)
        
        # Determine greeting based on time
        if 5 <= hour < 12:
            greeting = "Good morning"
        elif 12 <= hour < 17:
            greeting = "Good afternoon"
        elif 17 <= hour < 21:
            greeting = "Good evening"
        else:
            greeting = "Hello"
        
        # Add nickname if available
        if context.nickname:
            greeting = f"{greeting}, {context.nickname}"
        
        # Add proactive suggestions if available
        if context.proactive_suggestions:
            actions = context.proactive_suggestions[:2]
            if "weather" in actions:
                greeting += ". Would you like a weather update?"
            elif "calendar" in actions:
                greeting += ". Would you like to review your schedule?"
        
        return greeting
    
    def learn_from_interaction(
        self,
        query: str,
        response: str,
        intent: str,
        success: bool = True,
        user_id: str = "default",
    ):
        """
        Learn from a query-response interaction.
        
        Args:
            query: User query
            response: JARVIS response
            intent: Detected intent
            success: Whether interaction was successful
            user_id: User identifier
        """
        # Log query for pattern detection
        self.patterns.log_query(
            query=query,
            intent=intent,
            response_type="success" if success else "error",
            success=success,
            user_id=user_id,
        )
        
        # Learn preferences from query
        self.preferences.learn_from_query(query, response, user_id)
        
        # Extract and track locations
        location = self._extract_location(query)
        if location:
            context = "weather" if "weather" in intent.lower() else "general"
            self.preferences.increment_location_usage(location, context, user_id)
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from text."""
        import re
        
        patterns = [
            r"(?:in|at|for)\s+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z]{2})?)",
            r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+weather",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                location = match.group(1).strip()
                stop_words = ["the", "today", "tomorrow", "this", "next", "week"]
                if location.lower() not in stop_words:
                    return location
        
        return None
    
    def should_ask_for_location(
        self,
        query: str,
        user_id: str = "default",
    ) -> bool:
        """
        Check if we should ask for location (no location in query and no default).
        
        Args:
            query: User query
            user_id: User identifier
            
        Returns:
            True if should ask for location
        """
        # Check if location is in query
        location = self._extract_location(query)
        if location:
            return False
        
        # Check if we have a default
        default = self.preferences.get_default_location("weather", user_id)
        if default:
            return False
        
        return True
    
    def get_default_or_ask(
        self,
        query: str,
        user_id: str = "default",
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Get location from query, default, or return clarification question.
        
        Args:
            query: User query
            user_id: User identifier
            
        Returns:
            Tuple of (location, clarification_question)
            If location found, clarification is None
            If no location, returns (None, question_to_ask)
        """
        # Try to extract from query
        location = self._extract_location(query)
        if location:
            return location, None
        
        # Try default
        default = self.preferences.get_default_location("weather", user_id)
        if default:
            return default, None
        
        # Need to ask
        return None, "For which city would you like the weather? (I'll remember your answer for next time)"


# Singleton instance
_personalization_engine: Optional[PersonalizationEngine] = None


def get_personalization_engine() -> PersonalizationEngine:
    """Get or create personalization engine singleton."""
    global _personalization_engine
    if _personalization_engine is None:
        _personalization_engine = PersonalizationEngine()
    return _personalization_engine
