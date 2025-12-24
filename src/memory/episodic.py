"""
Episodic Memory Module for JARVIS.

Provides structured storage for user preferences, routines,
and historical data using SQLite.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


class EpisodicMemory:
    """
    Structured episodic memory using SQLite.
    
    Stores:
    - User preferences
    - Learned routines
    - Command history
    - Interaction patterns
    """
    
    def __init__(self, db_path: Path | str):
        """
        Initialize episodic memory.
        
        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_database(self) -> None:
        """Initialize database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # User preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Command history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS command_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    response TEXT,
                    success INTEGER DEFAULT 1,
                    execution_time REAL,
                    context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Routines table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS routines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    trigger_type TEXT NOT NULL,
                    trigger_value TEXT NOT NULL,
                    actions TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    last_run TIMESTAMP,
                    run_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Learned patterns table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT NOT NULL,
                    pattern_data TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    occurrences INTEGER DEFAULT 1,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Events/reminders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    event_time TIMESTAMP NOT NULL,
                    reminder_time TIMESTAMP,
                    recurring TEXT,
                    completed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_command_created ON command_history(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_time ON events(event_time)")
            
            logger.debug("Episodic memory database initialized")
    
    # =========================================================================
    # Preferences
    # =========================================================================
    
    def set_preference(
        self,
        key: str,
        value: Any,
        category: str = "general",
    ) -> bool:
        """
        Set a user preference.
        
        Args:
            key: Preference key.
            value: Preference value (will be JSON serialized).
            category: Preference category.
            
        Returns:
            True if successful.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO preferences (key, value, category, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (key, json.dumps(value), category))
            return True
        except Exception as e:
            logger.error(f"Failed to set preference: {e}")
            return False
    
    def get_preference(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Get a user preference.
        
        Args:
            key: Preference key.
            default: Default value if not found.
            
        Returns:
            Preference value or default.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
                row = cursor.fetchone()
                
                if row:
                    return json.loads(row["value"])
                return default
        except Exception as e:
            logger.error(f"Failed to get preference: {e}")
            return default
    
    def get_preferences_by_category(self, category: str) -> Dict[str, Any]:
        """Get all preferences in a category."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT key, value FROM preferences WHERE category = ?",
                    (category,)
                )
                
                return {
                    row["key"]: json.loads(row["value"])
                    for row in cursor.fetchall()
                }
        except Exception as e:
            logger.error(f"Failed to get preferences: {e}")
            return {}
    
    def delete_preference(self, key: str) -> bool:
        """Delete a preference."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM preferences WHERE key = ?", (key,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete preference: {e}")
            return False
    
    # =========================================================================
    # Command History
    # =========================================================================
    
    def log_command(
        self,
        command: str,
        response: Optional[str] = None,
        success: bool = True,
        execution_time: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """
        Log a command execution.
        
        Args:
            command: The command text.
            response: The response given.
            success: Whether execution was successful.
            execution_time: Time taken in seconds.
            context: Additional context.
            
        Returns:
            Command ID if successful.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO command_history 
                    (command, response, success, execution_time, context)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    command,
                    response,
                    1 if success else 0,
                    execution_time,
                    json.dumps(context) if context else None,
                ))
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to log command: {e}")
            return None
    
    def get_command_history(
        self,
        limit: int = 50,
        offset: int = 0,
        success_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get command history."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM command_history"
                params = []
                
                if success_only:
                    query += " WHERE success = 1"
                
                query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                
                return [
                    {
                        "id": row["id"],
                        "command": row["command"],
                        "response": row["response"],
                        "success": bool(row["success"]),
                        "execution_time": row["execution_time"],
                        "context": json.loads(row["context"]) if row["context"] else None,
                        "created_at": row["created_at"],
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Failed to get command history: {e}")
            return []
    
    def search_commands(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search command history."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM command_history
                    WHERE command LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (f"%{query}%", limit))
                
                return [
                    {
                        "id": row["id"],
                        "command": row["command"],
                        "response": row["response"],
                        "success": bool(row["success"]),
                        "created_at": row["created_at"],
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Failed to search commands: {e}")
            return []
    
    # =========================================================================
    # Routines
    # =========================================================================
    
    def create_routine(
        self,
        name: str,
        trigger_type: str,
        trigger_value: str,
        actions: List[Dict[str, Any]],
    ) -> Optional[int]:
        """
        Create a new routine.
        
        Args:
            name: Routine name.
            trigger_type: Type of trigger ("time", "location", "command", "event").
            trigger_value: Trigger value (e.g., "08:00", "home", "good morning").
            actions: List of actions to perform.
            
        Returns:
            Routine ID if successful.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO routines (name, trigger_type, trigger_value, actions)
                    VALUES (?, ?, ?, ?)
                """, (name, trigger_type, trigger_value, json.dumps(actions)))
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to create routine: {e}")
            return None
    
    def get_routine(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a routine by name."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM routines WHERE name = ?", (name,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        "id": row["id"],
                        "name": row["name"],
                        "trigger_type": row["trigger_type"],
                        "trigger_value": row["trigger_value"],
                        "actions": json.loads(row["actions"]),
                        "enabled": bool(row["enabled"]),
                        "last_run": row["last_run"],
                        "run_count": row["run_count"],
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to get routine: {e}")
            return None
    
    def get_routines_by_trigger(
        self,
        trigger_type: str,
        trigger_value: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get routines by trigger type."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if trigger_value:
                    cursor.execute("""
                        SELECT * FROM routines 
                        WHERE trigger_type = ? AND trigger_value = ? AND enabled = 1
                    """, (trigger_type, trigger_value))
                else:
                    cursor.execute("""
                        SELECT * FROM routines 
                        WHERE trigger_type = ? AND enabled = 1
                    """, (trigger_type,))
                
                return [
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "trigger_type": row["trigger_type"],
                        "trigger_value": row["trigger_value"],
                        "actions": json.loads(row["actions"]),
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Failed to get routines: {e}")
            return []
    
    def update_routine_run(self, routine_id: int) -> bool:
        """Update routine last run time and count."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE routines 
                    SET last_run = CURRENT_TIMESTAMP, run_count = run_count + 1
                    WHERE id = ?
                """, (routine_id,))
            return True
        except Exception as e:
            logger.error(f"Failed to update routine: {e}")
            return False
    
    def toggle_routine(self, name: str, enabled: bool) -> bool:
        """Enable or disable a routine."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE routines SET enabled = ? WHERE name = ?",
                    (1 if enabled else 0, name)
                )
            return True
        except Exception as e:
            logger.error(f"Failed to toggle routine: {e}")
            return False
    
    def delete_routine(self, name: str) -> bool:
        """Delete a routine."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM routines WHERE name = ?", (name,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete routine: {e}")
            return False
    
    # =========================================================================
    # Patterns
    # =========================================================================
    
    def record_pattern(
        self,
        pattern_type: str,
        pattern_data: Dict[str, Any],
        confidence: float = 0.5,
    ) -> Optional[int]:
        """
        Record a learned pattern.
        
        Args:
            pattern_type: Type of pattern (e.g., "time_preference", "command_sequence").
            pattern_data: Pattern data.
            confidence: Initial confidence score.
            
        Returns:
            Pattern ID if successful.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if similar pattern exists
                cursor.execute("""
                    SELECT id, occurrences, confidence FROM patterns
                    WHERE pattern_type = ? AND pattern_data = ?
                """, (pattern_type, json.dumps(pattern_data)))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing pattern
                    new_confidence = min(1.0, existing["confidence"] + 0.1)
                    cursor.execute("""
                        UPDATE patterns 
                        SET occurrences = occurrences + 1,
                            confidence = ?,
                            last_seen = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (new_confidence, existing["id"]))
                    return existing["id"]
                else:
                    # Create new pattern
                    cursor.execute("""
                        INSERT INTO patterns (pattern_type, pattern_data, confidence)
                        VALUES (?, ?, ?)
                    """, (pattern_type, json.dumps(pattern_data), confidence))
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to record pattern: {e}")
            return None
    
    def get_patterns(
        self,
        pattern_type: Optional[str] = None,
        min_confidence: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Get learned patterns."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if pattern_type:
                    cursor.execute("""
                        SELECT * FROM patterns
                        WHERE pattern_type = ? AND confidence >= ?
                        ORDER BY confidence DESC
                    """, (pattern_type, min_confidence))
                else:
                    cursor.execute("""
                        SELECT * FROM patterns
                        WHERE confidence >= ?
                        ORDER BY confidence DESC
                    """, (min_confidence,))
                
                return [
                    {
                        "id": row["id"],
                        "pattern_type": row["pattern_type"],
                        "pattern_data": json.loads(row["pattern_data"]),
                        "confidence": row["confidence"],
                        "occurrences": row["occurrences"],
                        "last_seen": row["last_seen"],
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Failed to get patterns: {e}")
            return []
    
    # =========================================================================
    # Events/Reminders
    # =========================================================================
    
    def create_event(
        self,
        title: str,
        event_time: datetime,
        description: Optional[str] = None,
        reminder_time: Optional[datetime] = None,
        recurring: Optional[str] = None,
    ) -> Optional[int]:
        """
        Create an event or reminder.
        
        Args:
            title: Event title.
            event_time: When the event occurs.
            description: Event description.
            reminder_time: When to remind (before event).
            recurring: Recurrence pattern (e.g., "daily", "weekly").
            
        Returns:
            Event ID if successful.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO events 
                    (title, description, event_time, reminder_time, recurring)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    title,
                    description,
                    event_time.isoformat(),
                    reminder_time.isoformat() if reminder_time else None,
                    recurring,
                ))
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            return None
    
    def get_upcoming_events(
        self,
        hours: int = 24,
        include_completed: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get upcoming events."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM events
                    WHERE event_time <= datetime('now', '+{} hours')
                    AND event_time >= datetime('now')
                """.format(hours)
                
                if not include_completed:
                    query += " AND completed = 0"
                
                query += " ORDER BY event_time ASC"
                
                cursor.execute(query)
                
                return [
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "description": row["description"],
                        "event_time": row["event_time"],
                        "reminder_time": row["reminder_time"],
                        "recurring": row["recurring"],
                        "completed": bool(row["completed"]),
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            return []
    
    def get_pending_reminders(self) -> List[Dict[str, Any]]:
        """Get reminders that should be triggered now."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM events
                    WHERE reminder_time <= datetime('now')
                    AND completed = 0
                    ORDER BY reminder_time ASC
                """)
                
                return [
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "description": row["description"],
                        "event_time": row["event_time"],
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Failed to get reminders: {e}")
            return []
    
    def complete_event(self, event_id: int) -> bool:
        """Mark an event as completed."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE events SET completed = 1 WHERE id = ?",
                    (event_id,)
                )
            return True
        except Exception as e:
            logger.error(f"Failed to complete event: {e}")
            return False
    
    def delete_event(self, event_id: int) -> bool:
        """Delete an event."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete event: {e}")
            return False
