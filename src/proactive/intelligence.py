"""
Proactive Intelligence Module for JARVIS.

Features:
- Geofencing with OwnTracks integration
- Routine learning from command patterns
- Context-aware suggestions
- Time-based automations
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from math import radians, sin, cos, sqrt, atan2
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class Location:
    """A geographic location."""
    latitude: float
    longitude: float
    accuracy: float = 0.0
    timestamp: float = field(default_factory=time.time)
    
    def distance_to(self, other: "Location") -> float:
        """Calculate distance to another location in meters (Haversine formula)."""
        R = 6371000  # Earth's radius in meters
        
        lat1, lon1 = radians(self.latitude), radians(self.longitude)
        lat2, lon2 = radians(other.latitude), radians(other.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c


@dataclass
class GeoZone:
    """A geographic zone for geofencing."""
    zone_id: str
    name: str
    center: Location
    radius: float  # meters
    
    def contains(self, location: Location) -> bool:
        """Check if location is within this zone."""
        return self.center.distance_to(location) <= self.radius


class ZoneEvent(Enum):
    """Geofencing zone events."""
    ENTER = "enter"
    EXIT = "exit"
    DWELL = "dwell"


@dataclass
class ZoneTransition:
    """A zone transition event."""
    zone: GeoZone
    event: ZoneEvent
    timestamp: float
    location: Location


class GeofenceManager:
    """
    Geofencing manager with OwnTracks integration.
    
    Features:
    - Define geographic zones
    - Track zone entry/exit
    - Trigger automations on transitions
    """
    
    def __init__(self, db_path: Path):
        """
        Initialize geofence manager.
        
        Args:
            db_path: Path to SQLite database.
        """
        self.db_path = db_path
        self.zones: Dict[str, GeoZone] = {}
        self.current_location: Optional[Location] = None
        self.current_zones: set = set()
        
        self._callbacks: Dict[str, List[Callable[[ZoneTransition], None]]] = defaultdict(list)
        
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _init_db(self) -> None:
        """Initialize database tables."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS zones (
                    zone_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    radius REAL NOT NULL,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS location_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    accuracy REAL,
                    timestamp REAL NOT NULL,
                    source TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS zone_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    zone_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    latitude REAL,
                    longitude REAL
                )
            """)
        
        self._load_zones()
    
    def _load_zones(self) -> None:
        """Load zones from database."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM zones")
            for row in cursor:
                zone = GeoZone(
                    zone_id=row["zone_id"],
                    name=row["name"],
                    center=Location(row["latitude"], row["longitude"]),
                    radius=row["radius"],
                )
                self.zones[zone.zone_id] = zone
    
    def add_zone(
        self,
        zone_id: str,
        name: str,
        latitude: float,
        longitude: float,
        radius: float,
    ) -> GeoZone:
        """Add a geofence zone."""
        zone = GeoZone(
            zone_id=zone_id,
            name=name,
            center=Location(latitude, longitude),
            radius=radius,
        )
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO zones (zone_id, name, latitude, longitude, radius)
                VALUES (?, ?, ?, ?, ?)
            """, (zone_id, name, latitude, longitude, radius))
        
        self.zones[zone_id] = zone
        logger.info(f"Added zone: {name} ({radius}m radius)")
        return zone
    
    def remove_zone(self, zone_id: str) -> bool:
        """Remove a zone."""
        if zone_id in self.zones:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM zones WHERE zone_id = ?", (zone_id,))
            del self.zones[zone_id]
            return True
        return False
    
    def on_zone_event(
        self,
        zone_id: str,
        callback: Callable[[ZoneTransition], None],
    ) -> None:
        """Register callback for zone events."""
        self._callbacks[zone_id].append(callback)
    
    def update_location(self, location: Location, source: str = "manual") -> List[ZoneTransition]:
        """
        Update current location and check for zone transitions.
        
        Args:
            location: New location.
            source: Location source (owntracks, gps, etc.).
            
        Returns:
            List of zone transitions.
        """
        self.current_location = location
        
        # Log location
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO location_history (latitude, longitude, accuracy, timestamp, source)
                VALUES (?, ?, ?, ?, ?)
            """, (location.latitude, location.longitude, location.accuracy, location.timestamp, source))
        
        # Check zone transitions
        transitions = []
        new_zones = set()
        
        for zone_id, zone in self.zones.items():
            if zone.contains(location):
                new_zones.add(zone_id)
                
                # Check for entry
                if zone_id not in self.current_zones:
                    transition = ZoneTransition(
                        zone=zone,
                        event=ZoneEvent.ENTER,
                        timestamp=location.timestamp,
                        location=location,
                    )
                    transitions.append(transition)
                    self._log_event(transition)
                    self._trigger_callbacks(transition)
        
        # Check for exits
        for zone_id in self.current_zones - new_zones:
            zone = self.zones.get(zone_id)
            if zone:
                transition = ZoneTransition(
                    zone=zone,
                    event=ZoneEvent.EXIT,
                    timestamp=location.timestamp,
                    location=location,
                )
                transitions.append(transition)
                self._log_event(transition)
                self._trigger_callbacks(transition)
        
        self.current_zones = new_zones
        return transitions
    
    def _log_event(self, transition: ZoneTransition) -> None:
        """Log zone event to database."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO zone_events (zone_id, event, timestamp, latitude, longitude)
                VALUES (?, ?, ?, ?, ?)
            """, (
                transition.zone.zone_id,
                transition.event.value,
                transition.timestamp,
                transition.location.latitude,
                transition.location.longitude,
            ))
    
    def _trigger_callbacks(self, transition: ZoneTransition) -> None:
        """Trigger callbacks for zone event."""
        for callback in self._callbacks.get(transition.zone.zone_id, []):
            try:
                callback(transition)
            except Exception as e:
                logger.error(f"Callback error: {e}")
        
        # Also trigger wildcard callbacks
        for callback in self._callbacks.get("*", []):
            try:
                callback(transition)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def process_owntracks(self, payload: Dict[str, Any]) -> Optional[List[ZoneTransition]]:
        """
        Process OwnTracks location update.
        
        Args:
            payload: OwnTracks JSON payload.
            
        Returns:
            List of zone transitions if location update.
        """
        msg_type = payload.get("_type")
        
        if msg_type == "location":
            location = Location(
                latitude=payload.get("lat", 0),
                longitude=payload.get("lon", 0),
                accuracy=payload.get("acc", 0),
                timestamp=payload.get("tst", time.time()),
            )
            return self.update_location(location, source="owntracks")
        
        return None
    
    def is_in_zone(self, zone_id: str) -> bool:
        """Check if currently in a zone."""
        return zone_id in self.current_zones
    
    def get_current_zones(self) -> List[GeoZone]:
        """Get list of zones currently in."""
        return [self.zones[zid] for zid in self.current_zones if zid in self.zones]


@dataclass
class CommandPattern:
    """A detected command pattern."""
    command: str
    hour: int
    day_of_week: int
    count: int
    last_executed: float
    
    @property
    def time_str(self) -> str:
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        return f"{days[self.day_of_week]} {self.hour:02d}:00"


class RoutineLearner:
    """
    Learn user routines from command patterns.
    
    Features:
    - Track command timing patterns
    - Detect recurring routines
    - Suggest automations
    """
    
    MIN_PATTERN_COUNT = 3  # Minimum occurrences to suggest
    
    def __init__(self, db_path: Path):
        """
        Initialize routine learner.
        
        Args:
            db_path: Path to SQLite database.
        """
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _init_db(self) -> None:
        """Initialize database tables."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS command_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    normalized_command TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    day_of_week INTEGER NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS suggested_routines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    day_of_week INTEGER NOT NULL,
                    suggested_at REAL NOT NULL,
                    accepted INTEGER DEFAULT 0,
                    dismissed INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cmd_time ON command_log(hour, day_of_week)")
    
    def _normalize_command(self, command: str) -> str:
        """Normalize command for pattern matching."""
        # Remove specific details, keep action
        command = command.lower().strip()
        
        # Common normalizations
        normalizations = [
            (r"turn (on|off) the (.+)", r"turn \1 \2"),
            (r"open (.+)", r"open app"),
            (r"search for (.+)", r"search"),
            (r"what('s| is) the (.+)", r"query \2"),
        ]
        
        import re
        for pattern, replacement in normalizations:
            command = re.sub(pattern, replacement, command)
        
        return command
    
    def log_command(self, command: str) -> None:
        """Log a command execution."""
        now = datetime.now()
        normalized = self._normalize_command(command)
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO command_log (command, normalized_command, hour, day_of_week, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (command, normalized, now.hour, now.weekday(), time.time()))
    
    def get_patterns(self, min_count: int = None) -> List[CommandPattern]:
        """Get detected command patterns."""
        min_count = min_count or self.MIN_PATTERN_COUNT
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    normalized_command as command,
                    hour,
                    day_of_week,
                    COUNT(*) as count,
                    MAX(timestamp) as last_executed
                FROM command_log
                WHERE timestamp > ?
                GROUP BY normalized_command, hour, day_of_week
                HAVING count >= ?
                ORDER BY count DESC
            """, (time.time() - 7 * 24 * 3600, min_count))  # Last 7 days
            
            patterns = []
            for row in cursor:
                patterns.append(CommandPattern(
                    command=row["command"],
                    hour=row["hour"],
                    day_of_week=row["day_of_week"],
                    count=row["count"],
                    last_executed=row["last_executed"],
                ))
            
            return patterns
    
    def get_suggestions(self) -> List[Dict[str, Any]]:
        """Get automation suggestions based on patterns."""
        patterns = self.get_patterns()
        suggestions = []
        
        for pattern in patterns:
            # Check if already suggested
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT id FROM suggested_routines
                    WHERE command = ? AND hour = ? AND day_of_week = ?
                    AND (accepted = 1 OR dismissed = 1)
                """, (pattern.command, pattern.hour, pattern.day_of_week))
                
                if cursor.fetchone():
                    continue
            
            suggestions.append({
                "command": pattern.command,
                "time": pattern.time_str,
                "hour": pattern.hour,
                "day_of_week": pattern.day_of_week,
                "occurrences": pattern.count,
                "message": f"You usually '{pattern.command}' at {pattern.time_str}. "
                          f"Would you like me to do this automatically?",
            })
        
        return suggestions
    
    def accept_suggestion(self, command: str, hour: int, day_of_week: int) -> None:
        """Accept a routine suggestion."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO suggested_routines (command, hour, day_of_week, suggested_at, accepted)
                VALUES (?, ?, ?, ?, 1)
            """, (command, hour, day_of_week, time.time()))
    
    def dismiss_suggestion(self, command: str, hour: int, day_of_week: int) -> None:
        """Dismiss a routine suggestion."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO suggested_routines (command, hour, day_of_week, suggested_at, dismissed)
                VALUES (?, ?, ?, ?, 1)
            """, (command, hour, day_of_week, time.time()))


class ContextAwareness:
    """
    Context-aware response adjustment.
    
    Features:
    - Track active application
    - Time-aware greetings
    - Adjust response style based on context
    """
    
    def __init__(self):
        self.current_app: Optional[str] = None
        self.last_interaction: float = 0
    
    def get_greeting(self) -> str:
        """Get time-appropriate greeting."""
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            return "Good morning"
        elif 12 <= hour < 17:
            return "Good afternoon"
        elif 17 <= hour < 21:
            return "Good evening"
        else:
            return "Hello"
    
    def get_context(self) -> Dict[str, Any]:
        """Get current context."""
        now = datetime.now()
        
        return {
            "time_of_day": self._get_time_of_day(),
            "day_of_week": now.strftime("%A"),
            "is_weekend": now.weekday() >= 5,
            "current_app": self.current_app,
            "greeting": self.get_greeting(),
        }
    
    def _get_time_of_day(self) -> str:
        """Get time of day category."""
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"
    
    def update_active_app(self, app_name: str) -> None:
        """Update currently active application."""
        self.current_app = app_name
    
    def get_response_style(self) -> Dict[str, Any]:
        """Get recommended response style based on context."""
        style = {
            "verbosity": "normal",
            "formality": "casual",
            "technical": False,
        }
        
        # Adjust based on active app
        if self.current_app:
            app_lower = self.current_app.lower()
            
            if any(x in app_lower for x in ["code", "visual studio", "pycharm", "intellij"]):
                style["technical"] = True
                style["verbosity"] = "concise"
            elif any(x in app_lower for x in ["slack", "teams", "discord"]):
                style["formality"] = "casual"
            elif any(x in app_lower for x in ["outlook", "gmail"]):
                style["formality"] = "professional"
        
        # Adjust based on time
        hour = datetime.now().hour
        if hour < 7 or hour > 22:
            style["verbosity"] = "concise"  # Be brief late at night
        
        return style


class ProactiveIntelligence:
    """
    Main proactive intelligence manager.
    
    Combines geofencing, routine learning, and context awareness.
    """
    
    def __init__(self, data_dir: Path):
        """
        Initialize proactive intelligence.
        
        Args:
            data_dir: Directory for data storage.
        """
        data_dir.mkdir(parents=True, exist_ok=True)
        
        self.geofence = GeofenceManager(data_dir / "geofence.db")
        self.routines = RoutineLearner(data_dir / "routines.db")
        self.context = ContextAwareness()
        
        self._automation_callbacks: List[Callable[[str], None]] = []
    
    def setup_home_zone(
        self,
        latitude: float,
        longitude: float,
        radius: float = 100,
    ) -> GeoZone:
        """Set up home zone for geofencing."""
        return self.geofence.add_zone(
            zone_id="home",
            name="Home",
            latitude=latitude,
            longitude=longitude,
            radius=radius,
        )
    
    def on_automation(self, callback: Callable[[str], None]) -> None:
        """Register callback for automation triggers."""
        self._automation_callbacks.append(callback)
    
    def _trigger_automation(self, action: str) -> None:
        """Trigger an automation action."""
        for callback in self._automation_callbacks:
            try:
                callback(action)
            except Exception as e:
                logger.error(f"Automation callback error: {e}")
    
    def log_command(self, command: str) -> None:
        """Log a command for routine learning."""
        self.routines.log_command(command)
    
    def get_suggestions(self) -> List[Dict[str, Any]]:
        """Get all proactive suggestions."""
        suggestions = []
        
        # Routine suggestions
        suggestions.extend(self.routines.get_suggestions())
        
        return suggestions
    
    def get_welcome_message(self) -> str:
        """Get contextual welcome message."""
        context = self.context.get_context()
        greeting = context["greeting"]
        
        # Check if returning home
        if self.geofence.is_in_zone("home"):
            return f"{greeting}! Welcome home."
        
        return f"{greeting}! How can I help you?"
    
    def process_location_update(self, latitude: float, longitude: float) -> List[str]:
        """
        Process a location update and return any triggered messages.
        
        Args:
            latitude: Latitude.
            longitude: Longitude.
            
        Returns:
            List of messages to speak/display.
        """
        location = Location(latitude, longitude)
        transitions = self.geofence.update_location(location)
        
        messages = []
        for transition in transitions:
            if transition.zone.zone_id == "home":
                if transition.event == ZoneEvent.ENTER:
                    messages.append("Welcome home! Would you like me to turn on the lights?")
                elif transition.event == ZoneEvent.EXIT:
                    messages.append("Goodbye! I'll keep an eye on things while you're away.")
        
        return messages
