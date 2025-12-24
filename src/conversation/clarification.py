"""
Clarification Handler for JARVIS - Phase 7 Part G

Handles ambiguous queries by:
- Detecting missing required information
- Generating clarification questions
- Integrating user answers into queries
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from loguru import logger


class ClarificationType(Enum):
    """Types of clarification needed."""
    MISSING_LOCATION = "missing_location"
    MISSING_TIME = "missing_time"
    MISSING_RECIPIENT = "missing_recipient"
    MISSING_SUBJECT = "missing_subject"
    AMBIGUOUS_ENTITY = "ambiguous_entity"
    CONFIRMATION_NEEDED = "confirmation_needed"


@dataclass
class ClarificationRequest:
    """A request for clarification from the user."""
    clarification_type: ClarificationType
    question: str
    context: Dict[str, Any] = field(default_factory=dict)
    options: List[str] = field(default_factory=list)
    default_value: Optional[str] = None
    required: bool = True
    callback_intent: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def format_question(self) -> str:
        """Format the clarification question for display."""
        question = self.question
        
        if self.options:
            options_str = ", ".join(self.options)
            question += f"\n(Options: {options_str})"
        
        if self.default_value:
            question += f"\n(Default: {self.default_value})"
        
        return question


@dataclass
class PendingClarification:
    """A pending clarification waiting for user response."""
    request: ClarificationRequest
    original_query: str
    session_id: str
    user_id: str
    expires_at: datetime
    
    def is_expired(self) -> bool:
        """Check if clarification has expired."""
        return datetime.now() > self.expires_at


class ClarificationHandler:
    """
    Handles clarification requests for ambiguous queries.
    
    Detects when queries are missing required information,
    generates appropriate questions, and integrates answers.
    """
    
    # Intent requirements - what info is needed for each intent
    INTENT_REQUIREMENTS = {
        "weather": {
            "required": ["location"],
            "optional": ["time_range"],
        },
        "calendar": {
            "required": [],
            "optional": ["date", "time"],
        },
        "calendar_create": {
            "required": ["title", "time"],
            "optional": ["location", "attendees", "duration"],
        },
        "email_send": {
            "required": ["recipient", "subject", "body"],
            "optional": [],
        },
        "email_read": {
            "required": [],
            "optional": ["sender", "count"],
        },
        "smart_home": {
            "required": ["device", "action"],
            "optional": ["value"],
        },
    }
    
    # Questions for each missing field
    CLARIFICATION_QUESTIONS = {
        "location": "For which city?",
        "time": "What time?",
        "time_range": "For what time period?",
        "date": "For which date?",
        "title": "What should I call this event?",
        "recipient": "Who should I send this to?",
        "subject": "What's the subject?",
        "body": "What would you like the message to say?",
        "device": "Which device?",
        "action": "What would you like me to do with it?",
        "value": "What value should I set?",
        "attendees": "Should I invite anyone?",
        "duration": "How long should it be?",
    }
    
    # Patterns to extract entities
    ENTITY_PATTERNS = {
        "location": [
            r"(?:in|at|for)\s+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z]{2})?)",
            r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+weather",
        ],
        "time": [
            r"(?:at|around)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
            r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))",
        ],
        "date": [
            r"(today|tomorrow|yesterday)",
            r"(next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))",
            r"(this\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))",
            r"(\d{1,2}/\d{1,2}(?:/\d{2,4})?)",
        ],
        "recipient": [
            r"(?:to|for)\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            r"(?:to|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        ],
    }
    
    def __init__(self, expiry_minutes: int = 5):
        """
        Initialize clarification handler.
        
        Args:
            expiry_minutes: Minutes before pending clarification expires
        """
        self.expiry_minutes = expiry_minutes
        self._pending: Dict[str, PendingClarification] = {}
    
    def check_requirements(
        self,
        query: str,
        intent: str,
        extracted_entities: Optional[Dict[str, Any]] = None,
    ) -> Optional[ClarificationRequest]:
        """
        Check if query has all required information.
        
        Args:
            query: User query
            intent: Detected intent
            extracted_entities: Already extracted entities
            
        Returns:
            ClarificationRequest if info is missing, None otherwise
        """
        requirements = self.INTENT_REQUIREMENTS.get(intent, {})
        required_fields = requirements.get("required", [])
        
        if not required_fields:
            return None
        
        # Extract entities from query
        entities = extracted_entities or {}
        for field in required_fields:
            if field not in entities:
                extracted = self._extract_entity(query, field)
                if extracted:
                    entities[field] = extracted
        
        # Check for missing required fields
        for field in required_fields:
            if field not in entities or not entities[field]:
                question = self.CLARIFICATION_QUESTIONS.get(
                    field,
                    f"What {field} would you like?"
                )
                
                return ClarificationRequest(
                    clarification_type=self._get_clarification_type(field),
                    question=question,
                    context={"intent": intent, "field": field, "entities": entities},
                    callback_intent=intent,
                )
        
        return None
    
    def _get_clarification_type(self, field: str) -> ClarificationType:
        """Get clarification type for a field."""
        type_map = {
            "location": ClarificationType.MISSING_LOCATION,
            "time": ClarificationType.MISSING_TIME,
            "time_range": ClarificationType.MISSING_TIME,
            "date": ClarificationType.MISSING_TIME,
            "recipient": ClarificationType.MISSING_RECIPIENT,
            "subject": ClarificationType.MISSING_SUBJECT,
        }
        return type_map.get(field, ClarificationType.AMBIGUOUS_ENTITY)
    
    def _extract_entity(self, text: str, entity_type: str) -> Optional[str]:
        """Extract an entity from text."""
        patterns = self.ENTITY_PATTERNS.get(entity_type, [])
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def create_pending(
        self,
        request: ClarificationRequest,
        original_query: str,
        session_id: str,
        user_id: str = "default",
    ) -> str:
        """
        Create a pending clarification.
        
        Args:
            request: Clarification request
            original_query: Original user query
            session_id: Session identifier
            user_id: User identifier
            
        Returns:
            Clarification ID
        """
        from datetime import timedelta
        import uuid
        
        clarification_id = str(uuid.uuid4())[:8]
        
        self._pending[session_id] = PendingClarification(
            request=request,
            original_query=original_query,
            session_id=session_id,
            user_id=user_id,
            expires_at=datetime.now() + timedelta(minutes=self.expiry_minutes),
        )
        
        return clarification_id
    
    def has_pending(self, session_id: str) -> bool:
        """Check if session has pending clarification."""
        if session_id not in self._pending:
            return False
        
        pending = self._pending[session_id]
        if pending.is_expired():
            del self._pending[session_id]
            return False
        
        return True
    
    def get_pending(self, session_id: str) -> Optional[PendingClarification]:
        """Get pending clarification for session."""
        if not self.has_pending(session_id):
            return None
        return self._pending.get(session_id)
    
    def resolve_clarification(
        self,
        session_id: str,
        answer: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve a pending clarification with user's answer.
        
        Args:
            session_id: Session identifier
            answer: User's answer to clarification question
            
        Returns:
            Dict with resolved query and entities, or None
        """
        pending = self.get_pending(session_id)
        if not pending:
            return None
        
        request = pending.request
        context = request.context
        field = context.get("field")
        entities = context.get("entities", {})
        intent = context.get("intent")
        
        # Add the answer to entities
        entities[field] = answer.strip()
        
        # Build resolved query
        original = pending.original_query
        
        if field == "location":
            if "weather" in original.lower():
                resolved_query = f"What's the weather in {answer}?"
            else:
                resolved_query = f"{original} in {answer}"
        elif field == "time":
            resolved_query = f"{original} at {answer}"
        elif field == "recipient":
            resolved_query = f"{original} to {answer}"
        else:
            resolved_query = f"{original} - {field}: {answer}"
        
        # Clear pending
        del self._pending[session_id]
        
        return {
            "resolved_query": resolved_query,
            "entities": entities,
            "intent": intent,
            "original_query": original,
        }
    
    def cancel_pending(self, session_id: str) -> bool:
        """Cancel a pending clarification."""
        if session_id in self._pending:
            del self._pending[session_id]
            return True
        return False
    
    def generate_confirmation_request(
        self,
        action: str,
        details: Dict[str, Any],
    ) -> ClarificationRequest:
        """
        Generate a confirmation request for an action.
        
        Args:
            action: Action to confirm
            details: Action details
            
        Returns:
            ClarificationRequest for confirmation
        """
        details_str = "\n".join([f"  - {k}: {v}" for k, v in details.items()])
        question = f"I'm about to {action}:\n{details_str}\n\nShould I proceed?"
        
        return ClarificationRequest(
            clarification_type=ClarificationType.CONFIRMATION_NEEDED,
            question=question,
            options=["yes", "no", "cancel"],
            context={"action": action, "details": details},
        )


# Singleton instance
_clarification_handler: Optional[ClarificationHandler] = None


def get_clarification_handler() -> ClarificationHandler:
    """Get or create clarification handler singleton."""
    global _clarification_handler
    if _clarification_handler is None:
        _clarification_handler = ClarificationHandler()
    return _clarification_handler
