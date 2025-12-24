"""
User Preferences System for JARVIS - Phase 7 Part F

Tracks and stores user preferences for personalized responses:
- Location preferences (home city, work location)
- Unit preferences (temperature, time format)
- Response style (verbosity, formality)
- Common contacts and entities
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

from loguru import logger


class TemperatureUnit(Enum):
    """Temperature unit preference."""
    FAHRENHEIT = "fahrenheit"
    CELSIUS = "celsius"


class TimeFormat(Enum):
    """Time format preference."""
    TWELVE_HOUR = "12h"
    TWENTY_FOUR_HOUR = "24h"


class Verbosity(Enum):
    """Response verbosity preference."""
    BRIEF = "brief"
    NORMAL = "normal"
    DETAILED = "detailed"


@dataclass
class UserPreferences:
    """User preference settings."""
    user_id: str = "default"
    
    # Location preferences
    home_city: Optional[str] = None
    work_location: Optional[str] = None
    default_location: Optional[str] = None
    
    # Unit preferences
    temperature_unit: TemperatureUnit = TemperatureUnit.FAHRENHEIT
    time_format: TimeFormat = TimeFormat.TWELVE_HOUR
    
    # Response style
    verbosity: Verbosity = Verbosity.NORMAL
    use_emojis: bool = True
    formal_tone: bool = False
    
    # Common entities
    nickname: Optional[str] = None
    common_contacts: Dict[str, str] = field(default_factory=dict)  # name -> email
    
    # Learned defaults
    default_calendar: str = "primary"
    default_reminder_time: int = 30  # minutes before
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = {
            "user_id": self.user_id,
            "home_city": self.home_city,
            "work_location": self.work_location,
            "default_location": self.default_location,
            "temperature_unit": self.temperature_unit.value,
            "time_format": self.time_format.value,
            "verbosity": self.verbosity.value,
            "use_emojis": self.use_emojis,
            "formal_tone": self.formal_tone,
            "nickname": self.nickname,
            "common_contacts": json.dumps(self.common_contacts),
            "default_calendar": self.default_calendar,
            "default_reminder_time": self.default_reminder_time,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserPreferences":
        """Create from dictionary."""
        return cls(
            user_id=data.get("user_id", "default"),
            home_city=data.get("home_city"),
            work_location=data.get("work_location"),
            default_location=data.get("default_location"),
            temperature_unit=TemperatureUnit(data.get("temperature_unit", "fahrenheit")),
            time_format=TimeFormat(data.get("time_format", "12h")),
            verbosity=Verbosity(data.get("verbosity", "normal")),
            use_emojis=data.get("use_emojis", True),
            formal_tone=data.get("formal_tone", False),
            nickname=data.get("nickname"),
            common_contacts=json.loads(data.get("common_contacts", "{}")),
            default_calendar=data.get("default_calendar", "primary"),
            default_reminder_time=data.get("default_reminder_time", 30),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class LocationFrequency:
    """Tracks frequency of location mentions."""
    location: str
    count: int = 0
    last_used: datetime = field(default_factory=datetime.now)
    context: str = ""  # "weather", "calendar", etc.


class PreferenceManager:
    """
    Manages user preferences with SQLite persistence.
    
    Tracks preferences, learns from interactions, and provides
    personalized defaults for JARVIS responses.
    """
    
    def __init__(self, db_path: str = "data/preferences.db"):
        """
        Initialize preference manager.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._preferences_cache: Dict[str, UserPreferences] = {}
        self._location_frequencies: Dict[str, Dict[str, LocationFrequency]] = {}
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    home_city TEXT,
                    work_location TEXT,
                    default_location TEXT,
                    temperature_unit TEXT DEFAULT 'fahrenheit',
                    time_format TEXT DEFAULT '12h',
                    verbosity TEXT DEFAULT 'normal',
                    use_emojis INTEGER DEFAULT 1,
                    formal_tone INTEGER DEFAULT 0,
                    nickname TEXT,
                    common_contacts TEXT DEFAULT '{}',
                    default_calendar TEXT DEFAULT 'primary',
                    default_reminder_time INTEGER DEFAULT 30,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS location_frequency (
                    user_id TEXT,
                    location TEXT,
                    count INTEGER DEFAULT 0,
                    last_used TEXT,
                    context TEXT,
                    PRIMARY KEY (user_id, location, context)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS preference_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    preference_key TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    reason TEXT,
                    timestamp TEXT
                )
            """)
            
            conn.commit()
    
    def get_preferences(self, user_id: str = "default") -> UserPreferences:
        """
        Get user preferences.
        
        Args:
            user_id: User identifier
            
        Returns:
            UserPreferences object
        """
        # Check cache
        if user_id in self._preferences_cache:
            return self._preferences_cache[user_id]
        
        # Load from database
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM user_preferences WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            
            if row:
                prefs = UserPreferences.from_dict(dict(row))
            else:
                # Create default preferences
                prefs = UserPreferences(user_id=user_id)
                self._save_preferences(prefs)
            
            self._preferences_cache[user_id] = prefs
            return prefs
    
    def _save_preferences(self, prefs: UserPreferences):
        """Save preferences to database."""
        prefs.updated_at = datetime.now()
        data = prefs.to_dict()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_preferences (
                    user_id, home_city, work_location, default_location,
                    temperature_unit, time_format, verbosity, use_emojis,
                    formal_tone, nickname, common_contacts, default_calendar,
                    default_reminder_time, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["user_id"], data["home_city"], data["work_location"],
                data["default_location"], data["temperature_unit"],
                data["time_format"], data["verbosity"], data["use_emojis"],
                data["formal_tone"], data["nickname"], data["common_contacts"],
                data["default_calendar"], data["default_reminder_time"],
                data["created_at"], data["updated_at"]
            ))
            conn.commit()
    
    def set_preference(
        self,
        key: str,
        value: Any,
        user_id: str = "default",
        reason: str = "user_request",
    ) -> bool:
        """
        Set a user preference.
        
        Args:
            key: Preference key (e.g., "home_city", "verbosity")
            value: New value
            user_id: User identifier
            reason: Reason for change (for history)
            
        Returns:
            True if successful
        """
        try:
            prefs = self.get_preferences(user_id)
            
            # Get old value for history
            old_value = getattr(prefs, key, None)
            if isinstance(old_value, Enum):
                old_value = old_value.value
            
            # Handle enum conversions
            if key == "temperature_unit":
                value = TemperatureUnit(value) if isinstance(value, str) else value
            elif key == "time_format":
                value = TimeFormat(value) if isinstance(value, str) else value
            elif key == "verbosity":
                value = Verbosity(value) if isinstance(value, str) else value
            
            # Set new value
            setattr(prefs, key, value)
            self._save_preferences(prefs)
            
            # Record history
            new_value_str = value.value if isinstance(value, Enum) else str(value)
            self._record_preference_change(
                user_id, key, str(old_value), new_value_str, reason
            )
            
            logger.info(f"Set preference {key}={value} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set preference: {e}")
            return False
    
    def _record_preference_change(
        self,
        user_id: str,
        key: str,
        old_value: str,
        new_value: str,
        reason: str,
    ):
        """Record preference change in history."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO preference_history (
                    user_id, preference_key, old_value, new_value, reason, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, key, old_value, new_value, reason, datetime.now().isoformat()))
            conn.commit()
    
    def get_preference(
        self,
        key: str,
        default: Any = None,
        user_id: str = "default",
    ) -> Any:
        """
        Get a specific preference value.
        
        Args:
            key: Preference key
            default: Default value if not set
            user_id: User identifier
            
        Returns:
            Preference value
        """
        prefs = self.get_preferences(user_id)
        value = getattr(prefs, key, default)
        
        # Return enum values as strings for easier use
        if isinstance(value, Enum):
            return value.value
        return value
    
    def increment_location_usage(
        self,
        location: str,
        context: str = "general",
        user_id: str = "default",
    ):
        """
        Increment location usage count for learning.
        
        Args:
            location: Location name
            context: Usage context (weather, calendar, etc.)
            user_id: User identifier
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO location_frequency (user_id, location, count, last_used, context)
                VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(user_id, location, context) DO UPDATE SET
                    count = count + 1,
                    last_used = ?
            """, (user_id, location, datetime.now().isoformat(), context, datetime.now().isoformat()))
            conn.commit()
        
        # Check if should become default
        self._check_location_default(location, context, user_id)
    
    def _check_location_default(
        self,
        location: str,
        context: str,
        user_id: str,
        threshold: int = 3,
    ):
        """Check if a location should become the default."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT count FROM location_frequency
                WHERE user_id = ? AND location = ? AND context = ?
            """, (user_id, location, context))
            row = cursor.fetchone()
            
            if row and row[0] >= threshold:
                prefs = self.get_preferences(user_id)
                
                # Set as default based on context
                if context == "weather" and not prefs.default_location:
                    self.set_preference(
                        "default_location", location, user_id,
                        reason=f"learned_from_{row[0]}_uses"
                    )
                    logger.info(f"Learned default location: {location}")
    
    def get_frequent_locations(
        self,
        context: str = "general",
        user_id: str = "default",
        limit: int = 5,
    ) -> List[LocationFrequency]:
        """Get most frequently used locations."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT location, count, last_used, context
                FROM location_frequency
                WHERE user_id = ? AND (context = ? OR context = 'general')
                ORDER BY count DESC
                LIMIT ?
            """, (user_id, context, limit))
            
            return [
                LocationFrequency(
                    location=row["location"],
                    count=row["count"],
                    last_used=datetime.fromisoformat(row["last_used"]),
                    context=row["context"],
                )
                for row in cursor.fetchall()
            ]
    
    def get_default_location(
        self,
        context: str = "weather",
        user_id: str = "default",
    ) -> Optional[str]:
        """
        Get the default location for a context.
        
        Args:
            context: Usage context
            user_id: User identifier
            
        Returns:
            Default location or None
        """
        prefs = self.get_preferences(user_id)
        
        # Check explicit default
        if prefs.default_location:
            return prefs.default_location
        
        # Check home city
        if prefs.home_city:
            return prefs.home_city
        
        # Check most frequent
        frequent = self.get_frequent_locations(context, user_id, limit=1)
        if frequent:
            return frequent[0].location
        
        return None
    
    def learn_from_query(
        self,
        query: str,
        response: str,
        user_id: str = "default",
    ):
        """
        Learn preferences from a query-response pair.
        
        Args:
            query: User query
            response: JARVIS response
            user_id: User identifier
        """
        query_lower = query.lower()
        
        # Learn verbosity preference
        if "be brief" in query_lower or "shorter" in query_lower:
            self.set_preference("verbosity", "brief", user_id, "learned_from_query")
        elif "more detail" in query_lower or "explain more" in query_lower:
            self.set_preference("verbosity", "detailed", user_id, "learned_from_query")
        
        # Learn temperature unit preference
        if "celsius" in query_lower or "°c" in query_lower:
            self.set_preference("temperature_unit", "celsius", user_id, "learned_from_query")
        elif "fahrenheit" in query_lower or "°f" in query_lower:
            self.set_preference("temperature_unit", "fahrenheit", user_id, "learned_from_query")
        
        # Learn emoji preference
        if "no emoji" in query_lower or "without emoji" in query_lower:
            self.set_preference("use_emojis", False, user_id, "learned_from_query")
        
        # Learn formality preference
        if "be formal" in query_lower or "professional" in query_lower:
            self.set_preference("formal_tone", True, user_id, "learned_from_query")
        elif "be casual" in query_lower or "informal" in query_lower:
            self.set_preference("formal_tone", False, user_id, "learned_from_query")


# Singleton instance
_preference_manager: Optional[PreferenceManager] = None


def get_preference_manager(db_path: str = "data/preferences.db") -> PreferenceManager:
    """Get or create preference manager singleton."""
    global _preference_manager
    if _preference_manager is None:
        _preference_manager = PreferenceManager(db_path=db_path)
    return _preference_manager
