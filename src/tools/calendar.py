"""
Google Calendar Service for JARVIS - Phase 7

Provides calendar integration using Google Calendar API (FREE for personal use).

Features:
- List upcoming events
- Create new events
- Update existing events
- Delete events
- Check availability
- Natural language date parsing

Setup:
1. Go to Google Cloud Console (https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download credentials.json to config/google_credentials.json
6. Run JARVIS - it will prompt for authorization on first use

API Documentation: https://developers.google.com/calendar/api/v3/reference
"""

from __future__ import annotations

import asyncio
import json
import os
import pickle
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from loguru import logger

# Google API imports (optional)
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    logger.debug("Google API libraries not installed. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")


# OAuth scopes for Calendar API
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
]


@dataclass
class CalendarEvent:
    """Represents a calendar event."""
    id: str
    summary: str
    start: datetime
    end: datetime
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: List[str] = field(default_factory=list)
    is_all_day: bool = False
    status: str = "confirmed"
    html_link: Optional[str] = None
    
    @classmethod
    def from_google_event(cls, event: Dict[str, Any]) -> "CalendarEvent":
        """Create CalendarEvent from Google Calendar API response."""
        # Handle all-day events vs timed events
        start_data = event.get("start", {})
        end_data = event.get("end", {})
        
        if "date" in start_data:
            # All-day event
            start = datetime.fromisoformat(start_data["date"])
            end = datetime.fromisoformat(end_data["date"])
            is_all_day = True
        else:
            # Timed event
            start = datetime.fromisoformat(start_data.get("dateTime", "").replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_data.get("dateTime", "").replace("Z", "+00:00"))
            is_all_day = False
        
        attendees = []
        for attendee in event.get("attendees", []):
            email = attendee.get("email", "")
            if email:
                attendees.append(email)
        
        return cls(
            id=event.get("id", ""),
            summary=event.get("summary", "No Title"),
            start=start,
            end=end,
            description=event.get("description"),
            location=event.get("location"),
            attendees=attendees,
            is_all_day=is_all_day,
            status=event.get("status", "confirmed"),
            html_link=event.get("htmlLink"),
        )
    
    def to_google_event(self) -> Dict[str, Any]:
        """Convert to Google Calendar API format."""
        event = {
            "summary": self.summary,
        }
        
        if self.description:
            event["description"] = self.description
        if self.location:
            event["location"] = self.location
        
        if self.is_all_day:
            event["start"] = {"date": self.start.strftime("%Y-%m-%d")}
            event["end"] = {"date": self.end.strftime("%Y-%m-%d")}
        else:
            event["start"] = {
                "dateTime": self.start.isoformat(),
                "timeZone": str(self.start.tzinfo) if self.start.tzinfo else "UTC",
            }
            event["end"] = {
                "dateTime": self.end.isoformat(),
                "timeZone": str(self.end.tzinfo) if self.end.tzinfo else "UTC",
            }
        
        if self.attendees:
            event["attendees"] = [{"email": email} for email in self.attendees]
        
        return event
    
    def format_display(self) -> str:
        """Format event for display."""
        if self.is_all_day:
            time_str = "All day"
        else:
            time_str = f"{self.start.strftime('%I:%M %p')} - {self.end.strftime('%I:%M %p')}"
        
        lines = [f"📅 **{self.summary}**"]
        lines.append(f"   {self.start.strftime('%A, %B %d, %Y')}")
        lines.append(f"   {time_str}")
        
        if self.location:
            lines.append(f"   📍 {self.location}")
        
        return "\n".join(lines)


class CalendarService:
    """
    Google Calendar service for JARVIS.
    
    Provides full calendar management capabilities using the Google Calendar API.
    Free for personal use with OAuth 2.0 authentication.
    """
    
    def __init__(
        self,
        credentials_file: str = "config/google_credentials.json",
        token_file: str = "config/calendar_token.pickle",
        default_calendar: str = "primary",
    ):
        """
        Initialize calendar service.
        
        Args:
            credentials_file: Path to Google OAuth credentials JSON
            token_file: Path to store OAuth token
            default_calendar: Default calendar ID (usually "primary")
        """
        self.credentials_file = Path(credentials_file)
        self.token_file = Path(token_file)
        self.default_calendar = default_calendar
        self._service = None
        self._credentials = None
    
    def _get_credentials(self) -> Optional[Credentials]:
        """Get or refresh OAuth credentials."""
        if not GOOGLE_API_AVAILABLE:
            logger.error("Google API libraries not installed")
            return None
        
        creds = None
        
        # Load existing token
        if self.token_file.exists():
            try:
                with open(self.token_file, "rb") as f:
                    creds = pickle.load(f)
            except Exception as e:
                logger.warning(f"Failed to load token: {e}")
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Failed to refresh token: {e}")
                    creds = None
            
            if not creds:
                if not self.credentials_file.exists():
                    logger.error(f"Credentials file not found: {self.credentials_file}")
                    return None
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_file), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    logger.error(f"Failed to get credentials: {e}")
                    return None
            
            # Save token for future use
            try:
                self.token_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.token_file, "wb") as f:
                    pickle.dump(creds, f)
            except Exception as e:
                logger.warning(f"Failed to save token: {e}")
        
        return creds
    
    def _get_service(self):
        """Get or create Calendar API service."""
        if self._service is None:
            creds = self._get_credentials()
            if creds is None:
                return None
            
            try:
                self._service = build("calendar", "v3", credentials=creds)
            except Exception as e:
                logger.error(f"Failed to build calendar service: {e}")
                return None
        
        return self._service
    
    def is_available(self) -> bool:
        """Check if calendar service is available."""
        if not GOOGLE_API_AVAILABLE:
            return False
        return self._get_service() is not None
    
    async def list_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_results: int = 10,
        calendar_id: Optional[str] = None,
    ) -> List[CalendarEvent]:
        """
        List calendar events.
        
        Args:
            start_date: Start of time range (default: now)
            end_date: End of time range (default: 7 days from now)
            max_results: Maximum number of events to return
            calendar_id: Calendar ID (default: primary)
            
        Returns:
            List of CalendarEvent objects
        """
        service = self._get_service()
        if service is None:
            return []
        
        if start_date is None:
            start_date = datetime.now(ZoneInfo("UTC"))
        if end_date is None:
            end_date = start_date + timedelta(days=7)
        
        calendar_id = calendar_id or self.default_calendar
        
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            events_result = await loop.run_in_executor(
                None,
                lambda: service.events().list(
                    calendarId=calendar_id,
                    timeMin=start_date.isoformat(),
                    timeMax=end_date.isoformat(),
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                ).execute()
            )
            
            events = []
            for event in events_result.get("items", []):
                try:
                    events.append(CalendarEvent.from_google_event(event))
                except Exception as e:
                    logger.warning(f"Failed to parse event: {e}")
            
            return events
            
        except HttpError as e:
            logger.error(f"Calendar API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to list events: {e}")
            return []
    
    async def get_today_events(self) -> List[CalendarEvent]:
        """Get all events for today."""
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return await self.list_events(start_date=start, end_date=end, max_results=20)
    
    async def get_week_events(self) -> List[CalendarEvent]:
        """Get all events for the current week."""
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # Get to start of week (Monday)
        start = start - timedelta(days=start.weekday())
        end = start + timedelta(days=7)
        return await self.list_events(start_date=start, end_date=end, max_results=50)
    
    async def create_event(
        self,
        summary: str,
        start: datetime,
        end: Optional[datetime] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        all_day: bool = False,
        calendar_id: Optional[str] = None,
    ) -> Optional[CalendarEvent]:
        """
        Create a new calendar event.
        
        Args:
            summary: Event title
            start: Start time
            end: End time (default: 1 hour after start)
            description: Event description
            location: Event location
            attendees: List of attendee emails
            all_day: Whether this is an all-day event
            calendar_id: Calendar ID
            
        Returns:
            Created CalendarEvent or None on failure
        """
        service = self._get_service()
        if service is None:
            return None
        
        if end is None:
            end = start + timedelta(hours=1)
        
        event = CalendarEvent(
            id="",
            summary=summary,
            start=start,
            end=end,
            description=description,
            location=location,
            attendees=attendees or [],
            is_all_day=all_day,
        )
        
        calendar_id = calendar_id or self.default_calendar
        
        try:
            loop = asyncio.get_event_loop()
            created = await loop.run_in_executor(
                None,
                lambda: service.events().insert(
                    calendarId=calendar_id,
                    body=event.to_google_event(),
                ).execute()
            )
            
            return CalendarEvent.from_google_event(created)
            
        except HttpError as e:
            logger.error(f"Failed to create event: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            return None
    
    async def update_event(
        self,
        event_id: str,
        summary: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        calendar_id: Optional[str] = None,
    ) -> Optional[CalendarEvent]:
        """
        Update an existing calendar event.
        
        Args:
            event_id: ID of event to update
            summary: New title (optional)
            start: New start time (optional)
            end: New end time (optional)
            description: New description (optional)
            location: New location (optional)
            calendar_id: Calendar ID
            
        Returns:
            Updated CalendarEvent or None on failure
        """
        service = self._get_service()
        if service is None:
            return None
        
        calendar_id = calendar_id or self.default_calendar
        
        try:
            # Get existing event
            loop = asyncio.get_event_loop()
            existing = await loop.run_in_executor(
                None,
                lambda: service.events().get(
                    calendarId=calendar_id,
                    eventId=event_id,
                ).execute()
            )
            
            # Update fields
            if summary:
                existing["summary"] = summary
            if description:
                existing["description"] = description
            if location:
                existing["location"] = location
            if start:
                existing["start"] = {"dateTime": start.isoformat()}
            if end:
                existing["end"] = {"dateTime": end.isoformat()}
            
            # Save changes
            updated = await loop.run_in_executor(
                None,
                lambda: service.events().update(
                    calendarId=calendar_id,
                    eventId=event_id,
                    body=existing,
                ).execute()
            )
            
            return CalendarEvent.from_google_event(updated)
            
        except HttpError as e:
            logger.error(f"Failed to update event: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to update event: {e}")
            return None
    
    async def delete_event(
        self,
        event_id: str,
        calendar_id: Optional[str] = None,
    ) -> bool:
        """
        Delete a calendar event.
        
        Args:
            event_id: ID of event to delete
            calendar_id: Calendar ID
            
        Returns:
            True if deleted successfully
        """
        service = self._get_service()
        if service is None:
            return False
        
        calendar_id = calendar_id or self.default_calendar
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: service.events().delete(
                    calendarId=calendar_id,
                    eventId=event_id,
                ).execute()
            )
            return True
            
        except HttpError as e:
            logger.error(f"Failed to delete event: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete event: {e}")
            return False
    
    async def check_availability(
        self,
        start: datetime,
        end: datetime,
        calendar_id: Optional[str] = None,
    ) -> Tuple[bool, List[CalendarEvent]]:
        """
        Check if a time slot is available.
        
        Args:
            start: Start of time slot
            end: End of time slot
            calendar_id: Calendar ID
            
        Returns:
            Tuple of (is_available, conflicting_events)
        """
        events = await self.list_events(
            start_date=start,
            end_date=end,
            max_results=10,
            calendar_id=calendar_id,
        )
        
        conflicts = []
        for event in events:
            # Check for overlap
            if event.start < end and event.end > start:
                conflicts.append(event)
        
        return len(conflicts) == 0, conflicts
    
    async def find_free_slots(
        self,
        date: datetime,
        duration_minutes: int = 60,
        work_start: int = 9,
        work_end: int = 17,
        calendar_id: Optional[str] = None,
    ) -> List[Tuple[datetime, datetime]]:
        """
        Find free time slots on a given date.
        
        Args:
            date: Date to check
            duration_minutes: Required duration in minutes
            work_start: Work day start hour (default 9 AM)
            work_end: Work day end hour (default 5 PM)
            calendar_id: Calendar ID
            
        Returns:
            List of (start, end) tuples for free slots
        """
        # Get events for the day
        day_start = date.replace(hour=work_start, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=work_end, minute=0, second=0, microsecond=0)
        
        events = await self.list_events(
            start_date=day_start,
            end_date=day_end,
            max_results=50,
            calendar_id=calendar_id,
        )
        
        # Sort events by start time
        events.sort(key=lambda e: e.start)
        
        # Find gaps
        free_slots = []
        current = day_start
        duration = timedelta(minutes=duration_minutes)
        
        for event in events:
            if event.start > current:
                # There's a gap
                gap_end = event.start
                if gap_end - current >= duration:
                    free_slots.append((current, gap_end))
            current = max(current, event.end)
        
        # Check remaining time
        if day_end - current >= duration:
            free_slots.append((current, day_end))
        
        return free_slots


# Singleton instance
_calendar_service: Optional[CalendarService] = None


def get_calendar_service(
    credentials_file: str = "config/google_credentials.json",
) -> CalendarService:
    """Get or create calendar service singleton."""
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = CalendarService(credentials_file=credentials_file)
    return _calendar_service


# =============================================================================
# Natural Language Date Parsing
# =============================================================================

def parse_natural_date(text: str, reference: Optional[datetime] = None) -> Optional[datetime]:
    """
    Parse natural language date/time expressions.
    
    Examples:
    - "today", "tomorrow", "yesterday"
    - "next Monday", "this Friday"
    - "in 2 hours", "in 30 minutes"
    - "at 3pm", "at 15:00"
    - "tomorrow at 2pm"
    
    Args:
        text: Natural language date string
        reference: Reference datetime (default: now)
        
    Returns:
        Parsed datetime or None
    """
    if reference is None:
        reference = datetime.now()
    
    text = text.lower().strip()
    
    # Simple patterns
    if text == "today":
        return reference.replace(hour=9, minute=0, second=0, microsecond=0)
    elif text == "tomorrow":
        return (reference + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    elif text == "yesterday":
        return (reference - timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Day of week
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, day in enumerate(days):
        if day in text:
            current_day = reference.weekday()
            days_ahead = i - current_day
            if "next" in text:
                days_ahead += 7
            elif days_ahead <= 0:
                days_ahead += 7
            target = reference + timedelta(days=days_ahead)
            return target.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Relative time ("in X hours/minutes")
    import re
    
    hours_match = re.search(r"in\s+(\d+)\s+hours?", text)
    if hours_match:
        hours = int(hours_match.group(1))
        return reference + timedelta(hours=hours)
    
    minutes_match = re.search(r"in\s+(\d+)\s+minutes?", text)
    if minutes_match:
        minutes = int(minutes_match.group(1))
        return reference + timedelta(minutes=minutes)
    
    days_match = re.search(r"in\s+(\d+)\s+days?", text)
    if days_match:
        days = int(days_match.group(1))
        return (reference + timedelta(days=days)).replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Time of day ("at 3pm", "at 15:00")
    time_12h = re.search(r"at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)", text)
    if time_12h:
        hour = int(time_12h.group(1))
        minute = int(time_12h.group(2) or 0)
        period = time_12h.group(3)
        
        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0
        
        # Check if there's a date component
        if "tomorrow" in text:
            base = reference + timedelta(days=1)
        else:
            base = reference
        
        return base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    time_24h = re.search(r"at\s+(\d{1,2}):(\d{2})", text)
    if time_24h:
        hour = int(time_24h.group(1))
        minute = int(time_24h.group(2))
        
        if "tomorrow" in text:
            base = reference + timedelta(days=1)
        else:
            base = reference
        
        return base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    return None


# =============================================================================
# Tool Functions for Agent Integration
# =============================================================================

async def list_calendar_events(time_range: str = "today") -> str:
    """
    List calendar events for a time range.
    
    Args:
        time_range: "today", "tomorrow", "week", or natural language
        
    Returns:
        Formatted list of events
    """
    try:
        service = get_calendar_service()
        if not service.is_available():
            return "Calendar service not available. Please configure Google Calendar credentials."
        
        time_range = time_range.lower()
        
        if time_range == "today":
            events = await service.get_today_events()
            header = "Today's Events"
        elif time_range == "tomorrow":
            tomorrow = datetime.now() + timedelta(days=1)
            start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            events = await service.list_events(start_date=start, end_date=end)
            header = "Tomorrow's Events"
        elif time_range == "week" or time_range == "this week":
            events = await service.get_week_events()
            header = "This Week's Events"
        else:
            # Try to parse natural language
            date = parse_natural_date(time_range)
            if date:
                start = date.replace(hour=0, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=1)
                events = await service.list_events(start_date=start, end_date=end)
                header = f"Events for {date.strftime('%A, %B %d')}"
            else:
                events = await service.get_today_events()
                header = "Today's Events"
        
        if not events:
            return f"**{header}**\n\nNo events scheduled."
        
        lines = [f"**{header}** ({len(events)} events)\n"]
        for event in events:
            lines.append(event.format_display())
            lines.append("")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Failed to list events: {e}")
        return f"Failed to get calendar events: {e}"


async def create_calendar_event(
    title: str,
    when: str,
    duration_minutes: int = 60,
    location: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    """
    Create a new calendar event.
    
    Args:
        title: Event title
        when: When to schedule (natural language)
        duration_minutes: Event duration in minutes
        location: Event location (optional)
        description: Event description (optional)
        
    Returns:
        Confirmation message
    """
    try:
        service = get_calendar_service()
        if not service.is_available():
            return "Calendar service not available. Please configure Google Calendar credentials."
        
        # Parse the date/time
        start = parse_natural_date(when)
        if start is None:
            return f"I couldn't understand the time '{when}'. Try something like 'tomorrow at 2pm' or 'next Monday at 10am'."
        
        end = start + timedelta(minutes=duration_minutes)
        
        # Check availability
        is_free, conflicts = await service.check_availability(start, end)
        if not is_free:
            conflict_names = [c.summary for c in conflicts]
            return f"That time slot conflicts with: {', '.join(conflict_names)}. Would you like to schedule anyway or choose a different time?"
        
        # Create the event
        event = await service.create_event(
            summary=title,
            start=start,
            end=end,
            location=location,
            description=description,
        )
        
        if event:
            return f"✅ Created event: **{event.summary}**\n{event.start.strftime('%A, %B %d at %I:%M %p')}"
        else:
            return "Failed to create event. Please try again."
        
    except Exception as e:
        logger.error(f"Failed to create event: {e}")
        return f"Failed to create event: {e}"


async def check_calendar_availability(when: str, duration_minutes: int = 60) -> str:
    """
    Check if a time slot is available.
    
    Args:
        when: Time to check (natural language)
        duration_minutes: Duration to check
        
    Returns:
        Availability status
    """
    try:
        service = get_calendar_service()
        if not service.is_available():
            return "Calendar service not available. Please configure Google Calendar credentials."
        
        start = parse_natural_date(when)
        if start is None:
            return f"I couldn't understand the time '{when}'."
        
        end = start + timedelta(minutes=duration_minutes)
        
        is_free, conflicts = await service.check_availability(start, end)
        
        if is_free:
            return f"✅ You're free {start.strftime('%A, %B %d from %I:%M %p')} to {end.strftime('%I:%M %p')}."
        else:
            lines = [f"❌ You have {len(conflicts)} conflict(s) at that time:"]
            for conflict in conflicts:
                lines.append(f"  - {conflict.summary} ({conflict.start.strftime('%I:%M %p')} - {conflict.end.strftime('%I:%M %p')})")
            return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Failed to check availability: {e}")
        return f"Failed to check availability: {e}"


async def delete_calendar_event(event_name: str) -> str:
    """
    Delete a calendar event by name.
    
    Args:
        event_name: Name/title of the event to delete
        
    Returns:
        Confirmation message
    """
    try:
        service = get_calendar_service()
        if not service.is_available():
            return "Calendar service not available. Please configure Google Calendar credentials."
        
        # Find matching events
        events = await service.list_events(max_results=50)
        matches = [e for e in events if event_name.lower() in e.summary.lower()]
        
        if not matches:
            return f"No events found matching '{event_name}'."
        
        if len(matches) > 1:
            lines = [f"Found {len(matches)} events matching '{event_name}':"]
            for i, event in enumerate(matches, 1):
                lines.append(f"  {i}. {event.summary} - {event.start.strftime('%B %d at %I:%M %p')}")
            lines.append("\nPlease be more specific about which event to delete.")
            return "\n".join(lines)
        
        # Delete the single match
        event = matches[0]
        success = await service.delete_event(event.id)
        
        if success:
            return f"✅ Deleted event: **{event.summary}** ({event.start.strftime('%B %d at %I:%M %p')})"
        else:
            return "Failed to delete event. Please try again."
        
    except Exception as e:
        logger.error(f"Failed to delete event: {e}")
        return f"Failed to delete event: {e}"


# Calendar tool definitions for agent system
CALENDAR_TOOLS = [
    {
        "name": "list_calendar_events",
        "description": "List calendar events for today, tomorrow, this week, or a specific date. Use this when the user asks about their schedule or calendar.",
        "parameters": {
            "type": "object",
            "properties": {
                "time_range": {
                    "type": "string",
                    "description": "Time range: 'today', 'tomorrow', 'week', or a date like 'next Monday'"
                }
            },
            "required": ["time_range"]
        },
        "function": list_calendar_events,
    },
    {
        "name": "create_calendar_event",
        "description": "Create a new calendar event. Use this when the user wants to schedule something.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Event title/name"
                },
                "when": {
                    "type": "string",
                    "description": "When to schedule: 'tomorrow at 2pm', 'next Monday at 10am', etc."
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Event duration in minutes (default 60)",
                    "default": 60
                },
                "location": {
                    "type": "string",
                    "description": "Event location (optional)"
                },
                "description": {
                    "type": "string",
                    "description": "Event description (optional)"
                }
            },
            "required": ["title", "when"]
        },
        "function": create_calendar_event,
    },
    {
        "name": "check_calendar_availability",
        "description": "Check if a time slot is available on the calendar. Use this when the user asks if they're free at a certain time.",
        "parameters": {
            "type": "object",
            "properties": {
                "when": {
                    "type": "string",
                    "description": "Time to check: 'tomorrow at 2pm', 'Friday afternoon', etc."
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Duration to check in minutes (default 60)",
                    "default": 60
                }
            },
            "required": ["when"]
        },
        "function": check_calendar_availability,
    },
    {
        "name": "delete_calendar_event",
        "description": "Delete/cancel a calendar event by name. Use this when the user wants to cancel an appointment.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_name": {
                    "type": "string",
                    "description": "Name or partial name of the event to delete"
                }
            },
            "required": ["event_name"]
        },
        "function": delete_calendar_event,
    },
]
