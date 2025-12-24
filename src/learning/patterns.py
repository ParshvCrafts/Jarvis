"""
Usage Pattern Detection for JARVIS - Phase 7 Part F

Detects and tracks user behavior patterns:
- Frequently asked queries
- Time-based patterns (morning routine, etc.)
- Command sequences
- Topic preferences
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from loguru import logger


class PatternType(Enum):
    """Types of usage patterns."""
    TIME_BASED = "time_based"  # Morning routine, evening check
    QUERY_SEQUENCE = "query_sequence"  # Weather then calendar
    TOPIC_PREFERENCE = "topic_preference"  # Frequently asks about X
    LOCATION_BASED = "location_based"  # Different behavior at home/work
    PERIODIC = "periodic"  # Weekly reports, daily summaries


@dataclass
class UsagePattern:
    """Represents a detected usage pattern."""
    pattern_id: str
    pattern_type: PatternType
    description: str
    frequency: int = 0
    confidence: float = 0.0
    triggers: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    time_window: Optional[Tuple[int, int]] = None  # Hour range (start, end)
    last_triggered: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def matches_time(self, dt: datetime) -> bool:
        """Check if pattern matches given time."""
        if self.time_window is None:
            return True
        start, end = self.time_window
        hour = dt.hour
        if start <= end:
            return start <= hour <= end
        else:  # Wraps around midnight
            return hour >= start or hour <= end


@dataclass
class QueryLog:
    """Log entry for a user query."""
    query: str
    intent: str
    timestamp: datetime
    response_type: str
    success: bool
    duration_ms: int = 0


class PatternDetector:
    """
    Detects usage patterns from query history.
    
    Analyzes user behavior to identify:
    - Time-based routines
    - Common query sequences
    - Topic preferences
    """
    
    def __init__(self, db_path: str = "data/patterns.db"):
        """
        Initialize pattern detector.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._patterns_cache: Dict[str, List[UsagePattern]] = {}
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    query TEXT,
                    intent TEXT,
                    timestamp TEXT,
                    response_type TEXT,
                    success INTEGER,
                    duration_ms INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS detected_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    pattern_type TEXT,
                    description TEXT,
                    frequency INTEGER DEFAULT 0,
                    confidence REAL DEFAULT 0.0,
                    triggers TEXT,
                    actions TEXT,
                    time_window_start INTEGER,
                    time_window_end INTEGER,
                    last_triggered TEXT,
                    metadata TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_log_user_time 
                ON query_log(user_id, timestamp)
            """)
            
            conn.commit()
    
    def log_query(
        self,
        query: str,
        intent: str,
        response_type: str = "success",
        success: bool = True,
        duration_ms: int = 0,
        user_id: str = "default",
    ):
        """
        Log a user query for pattern analysis.
        
        Args:
            query: User query text
            intent: Detected intent type
            response_type: Type of response given
            success: Whether query was successful
            duration_ms: Response time in milliseconds
            user_id: User identifier
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO query_log (
                    user_id, query, intent, timestamp, response_type, success, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, query, intent, datetime.now().isoformat(),
                response_type, int(success), duration_ms
            ))
            conn.commit()
        
        # Trigger pattern analysis periodically
        self._maybe_analyze_patterns(user_id)
    
    def _maybe_analyze_patterns(self, user_id: str, threshold: int = 10):
        """Analyze patterns if enough new queries."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM query_log WHERE user_id = ?
            """, (user_id,))
            count = cursor.fetchone()[0]
            
            if count % threshold == 0:
                self.analyze_patterns(user_id)
    
    def analyze_patterns(self, user_id: str = "default") -> List[UsagePattern]:
        """
        Analyze query history to detect patterns.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of detected patterns
        """
        patterns = []
        
        # Analyze time-based patterns
        patterns.extend(self._detect_time_patterns(user_id))
        
        # Analyze query sequences
        patterns.extend(self._detect_sequence_patterns(user_id))
        
        # Analyze topic preferences
        patterns.extend(self._detect_topic_patterns(user_id))
        
        # Save patterns
        for pattern in patterns:
            self._save_pattern(pattern, user_id)
        
        self._patterns_cache[user_id] = patterns
        return patterns
    
    def _detect_time_patterns(self, user_id: str) -> List[UsagePattern]:
        """Detect time-based usage patterns."""
        patterns = []
        
        with sqlite3.connect(self.db_path) as conn:
            # Get queries by hour
            cursor = conn.execute("""
                SELECT 
                    CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                    intent,
                    COUNT(*) as count
                FROM query_log
                WHERE user_id = ?
                GROUP BY hour, intent
                HAVING count >= 3
                ORDER BY count DESC
            """, (user_id,))
            
            hour_intents = {}
            for row in cursor.fetchall():
                hour, intent, count = row
                if hour not in hour_intents:
                    hour_intents[hour] = []
                hour_intents[hour].append((intent, count))
            
            # Detect morning routine (6-9 AM)
            morning_intents = []
            for hour in range(6, 10):
                if hour in hour_intents:
                    morning_intents.extend(hour_intents[hour])
            
            if morning_intents:
                top_intents = [i[0] for i in sorted(morning_intents, key=lambda x: -x[1])[:3]]
                if top_intents:
                    patterns.append(UsagePattern(
                        pattern_id=f"morning_routine_{user_id}",
                        pattern_type=PatternType.TIME_BASED,
                        description="Morning routine pattern",
                        frequency=sum(i[1] for i in morning_intents),
                        confidence=0.7,
                        triggers=["morning", "wake up", "good morning"],
                        actions=top_intents,
                        time_window=(6, 9),
                    ))
            
            # Detect evening routine (6-10 PM)
            evening_intents = []
            for hour in range(18, 23):
                if hour in hour_intents:
                    evening_intents.extend(hour_intents[hour])
            
            if evening_intents:
                top_intents = [i[0] for i in sorted(evening_intents, key=lambda x: -x[1])[:3]]
                if top_intents:
                    patterns.append(UsagePattern(
                        pattern_id=f"evening_routine_{user_id}",
                        pattern_type=PatternType.TIME_BASED,
                        description="Evening routine pattern",
                        frequency=sum(i[1] for i in evening_intents),
                        confidence=0.7,
                        triggers=["evening", "night", "good evening"],
                        actions=top_intents,
                        time_window=(18, 22),
                    ))
        
        return patterns
    
    def _detect_sequence_patterns(self, user_id: str) -> List[UsagePattern]:
        """Detect query sequence patterns."""
        patterns = []
        
        with sqlite3.connect(self.db_path) as conn:
            # Get recent queries in order
            cursor = conn.execute("""
                SELECT intent, timestamp FROM query_log
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 100
            """, (user_id,))
            
            intents = [row[0] for row in cursor.fetchall()]
            
            # Find common bigrams (two-query sequences)
            bigrams = []
            for i in range(len(intents) - 1):
                bigrams.append((intents[i+1], intents[i]))  # Reversed for chronological order
            
            bigram_counts = Counter(bigrams)
            
            for bigram, count in bigram_counts.most_common(5):
                if count >= 3:
                    patterns.append(UsagePattern(
                        pattern_id=f"sequence_{bigram[0]}_{bigram[1]}_{user_id}",
                        pattern_type=PatternType.QUERY_SEQUENCE,
                        description=f"Often asks {bigram[1]} after {bigram[0]}",
                        frequency=count,
                        confidence=min(0.9, count / 10),
                        triggers=[bigram[0]],
                        actions=[bigram[1]],
                        metadata={"sequence": list(bigram)},
                    ))
        
        return patterns
    
    def _detect_topic_patterns(self, user_id: str) -> List[UsagePattern]:
        """Detect topic preference patterns."""
        patterns = []
        
        with sqlite3.connect(self.db_path) as conn:
            # Get intent frequencies
            cursor = conn.execute("""
                SELECT intent, COUNT(*) as count
                FROM query_log
                WHERE user_id = ?
                GROUP BY intent
                ORDER BY count DESC
                LIMIT 10
            """, (user_id,))
            
            total = 0
            intent_counts = []
            for row in cursor.fetchall():
                intent_counts.append((row[0], row[1]))
                total += row[1]
            
            # Create patterns for top topics
            for intent, count in intent_counts[:5]:
                if count >= 5:
                    patterns.append(UsagePattern(
                        pattern_id=f"topic_{intent}_{user_id}",
                        pattern_type=PatternType.TOPIC_PREFERENCE,
                        description=f"Frequently asks about {intent}",
                        frequency=count,
                        confidence=count / total if total > 0 else 0,
                        triggers=[intent],
                        actions=[],
                        metadata={"percentage": round(count / total * 100, 1) if total > 0 else 0},
                    ))
        
        return patterns
    
    def _save_pattern(self, pattern: UsagePattern, user_id: str):
        """Save pattern to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO detected_patterns (
                    pattern_id, user_id, pattern_type, description,
                    frequency, confidence, triggers, actions,
                    time_window_start, time_window_end, last_triggered,
                    metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern.pattern_id, user_id, pattern.pattern_type.value,
                pattern.description, pattern.frequency, pattern.confidence,
                json.dumps(pattern.triggers), json.dumps(pattern.actions),
                pattern.time_window[0] if pattern.time_window else None,
                pattern.time_window[1] if pattern.time_window else None,
                pattern.last_triggered.isoformat() if pattern.last_triggered else None,
                json.dumps(pattern.metadata),
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
            conn.commit()
    
    def get_patterns(self, user_id: str = "default") -> List[UsagePattern]:
        """Get all detected patterns for a user."""
        if user_id in self._patterns_cache:
            return self._patterns_cache[user_id]
        
        patterns = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM detected_patterns WHERE user_id = ?
            """, (user_id,))
            
            for row in cursor.fetchall():
                time_window = None
                if row["time_window_start"] is not None:
                    time_window = (row["time_window_start"], row["time_window_end"])
                
                patterns.append(UsagePattern(
                    pattern_id=row["pattern_id"],
                    pattern_type=PatternType(row["pattern_type"]),
                    description=row["description"],
                    frequency=row["frequency"],
                    confidence=row["confidence"],
                    triggers=json.loads(row["triggers"]),
                    actions=json.loads(row["actions"]),
                    time_window=time_window,
                    last_triggered=datetime.fromisoformat(row["last_triggered"]) if row["last_triggered"] else None,
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                ))
        
        self._patterns_cache[user_id] = patterns
        return patterns
    
    def get_suggested_actions(
        self,
        current_intent: str,
        user_id: str = "default",
    ) -> List[str]:
        """
        Get suggested follow-up actions based on patterns.
        
        Args:
            current_intent: Current query intent
            user_id: User identifier
            
        Returns:
            List of suggested follow-up intents
        """
        patterns = self.get_patterns(user_id)
        suggestions = []
        
        for pattern in patterns:
            if pattern.pattern_type == PatternType.QUERY_SEQUENCE:
                if current_intent in pattern.triggers:
                    suggestions.extend(pattern.actions)
        
        return list(set(suggestions))
    
    def get_time_based_suggestions(
        self,
        user_id: str = "default",
    ) -> List[str]:
        """
        Get suggestions based on current time.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of suggested actions for current time
        """
        now = datetime.now()
        patterns = self.get_patterns(user_id)
        suggestions = []
        
        for pattern in patterns:
            if pattern.pattern_type == PatternType.TIME_BASED:
                if pattern.matches_time(now):
                    suggestions.extend(pattern.actions)
        
        return list(set(suggestions))


# Singleton instance
_pattern_detector: Optional[PatternDetector] = None


def get_pattern_detector(db_path: str = "data/patterns.db") -> PatternDetector:
    """Get or create pattern detector singleton."""
    global _pattern_detector
    if _pattern_detector is None:
        _pattern_detector = PatternDetector(db_path=db_path)
    return _pattern_detector
