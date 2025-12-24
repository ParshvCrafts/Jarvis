"""
Voice Journal for JARVIS.

Audio diary with transcription:
- Record voice entries
- Auto-transcribe
- Tag and categorize
- Mood tracking
- Searchable transcripts
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import random

from loguru import logger


class Mood(Enum):
    GREAT = "great"
    GOOD = "good"
    OKAY = "okay"
    LOW = "low"
    STRESSED = "stressed"


@dataclass
class JournalEntry:
    id: Optional[int] = None
    date: date = field(default_factory=date.today)
    content: str = ""
    mood: Optional[Mood] = None
    tags: List[str] = field(default_factory=list)
    audio_path: Optional[str] = None
    is_transcribed: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "JournalEntry":
        import json
        return cls(
            id=row["id"],
            date=date.fromisoformat(row["date"]),
            content=row["content"] or "",
            mood=Mood(row["mood"]) if row["mood"] else None,
            tags=json.loads(row["tags"]) if row["tags"] else [],
            audio_path=row["audio_path"],
            is_transcribed=bool(row["is_transcribed"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
        )


class VoiceJournal:
    """
    Voice-enabled journaling system.
    
    Features:
    - Text and voice entries
    - Mood tracking
    - Daily prompts
    - Search and reflection
    """
    
    # Daily prompts for reflection
    DAILY_PROMPTS = [
        "What's one thing you're grateful for today?",
        "What did you accomplish today?",
        "What's challenging you right now?",
        "What did you learn today?",
        "How are you feeling right now?",
        "What's one thing you want to improve?",
        "Who made a positive impact on you today?",
        "What's something you're looking forward to?",
        "What would make tomorrow great?",
        "What's one small win from today?",
        "How did you take care of yourself today?",
        "What's on your mind right now?",
        "What made you smile today?",
        "What's a goal you're working towards?",
        "How did you grow today?",
    ]
    
    # Mood keywords for auto-detection
    MOOD_KEYWORDS = {
        Mood.GREAT: ["amazing", "fantastic", "excellent", "wonderful", "excited", "thrilled", "awesome"],
        Mood.GOOD: ["good", "happy", "nice", "pleased", "satisfied", "content", "positive"],
        Mood.OKAY: ["okay", "fine", "alright", "neutral", "so-so", "meh"],
        Mood.LOW: ["sad", "down", "disappointed", "tired", "exhausted", "frustrated"],
        Mood.STRESSED: ["stressed", "anxious", "worried", "overwhelmed", "nervous", "pressure"],
    }
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "voice_journal.db"
        self.audio_dir = self.data_dir / "journal_audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
        logger.info("Voice Journal initialized")
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    content TEXT,
                    mood TEXT,
                    tags TEXT,
                    audio_path TEXT,
                    is_transcribed INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
    
    def _detect_mood(self, content: str) -> Optional[Mood]:
        """Auto-detect mood from content."""
        content_lower = content.lower()
        
        for mood, keywords in self.MOOD_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content_lower:
                    return mood
        
        return None
    
    def _extract_tags(self, content: str) -> List[str]:
        """Extract hashtags from content."""
        import re
        tags = re.findall(r'#(\w+)', content)
        return tags
    
    def add_entry(
        self,
        content: str,
        mood: Optional[str] = None,
        tags: Optional[List[str]] = None,
        entry_date: Optional[str] = None,
    ) -> JournalEntry:
        """Add a journal entry."""
        import json
        
        # Parse mood
        entry_mood = None
        if mood:
            try:
                entry_mood = Mood(mood.lower())
            except ValueError:
                entry_mood = self._detect_mood(content)
        else:
            entry_mood = self._detect_mood(content)
        
        # Extract tags from content if not provided
        entry_tags = tags or self._extract_tags(content)
        
        # Parse date
        entry_dt = date.fromisoformat(entry_date) if entry_date else date.today()
        
        entry = JournalEntry(
            date=entry_dt,
            content=content,
            mood=entry_mood,
            tags=entry_tags,
        )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO entries (date, content, mood, tags, is_transcribed, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entry.date.isoformat(),
                entry.content,
                entry.mood.value if entry.mood else None,
                json.dumps(entry.tags),
                1,
                entry.created_at.isoformat()
            ))
            entry.id = cursor.lastrowid
            conn.commit()
        
        logger.info(f"Added journal entry for {entry.date}")
        return entry
    
    def get_daily_prompt(self) -> str:
        """Get a random daily prompt."""
        return random.choice(self.DAILY_PROMPTS)
    
    def get_today_entries(self) -> List[JournalEntry]:
        """Get today's journal entries."""
        return self.get_entries_by_date(date.today())
    
    def get_entries_by_date(self, entry_date: date) -> List[JournalEntry]:
        """Get entries for a specific date."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM entries WHERE date = ? ORDER BY created_at DESC",
                (entry_date.isoformat(),)
            ).fetchall()
        
        return [JournalEntry.from_row(row) for row in rows]
    
    def get_recent_entries(self, days: int = 7) -> List[JournalEntry]:
        """Get entries from the last N days."""
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM entries WHERE date >= ? ORDER BY date DESC, created_at DESC",
                (cutoff,)
            ).fetchall()
        
        return [JournalEntry.from_row(row) for row in rows]
    
    def search_entries(self, query: str) -> List[JournalEntry]:
        """Search journal entries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM entries 
                WHERE LOWER(content) LIKE ? OR tags LIKE ?
                ORDER BY date DESC
                LIMIT 20
            """, (f"%{query.lower()}%", f"%{query.lower()}%")).fetchall()
        
        return [JournalEntry.from_row(row) for row in rows]
    
    def get_entries_by_mood(self, mood: str) -> List[JournalEntry]:
        """Get entries by mood."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM entries WHERE mood = ? ORDER BY date DESC LIMIT 20",
                (mood.lower(),)
            ).fetchall()
        
        return [JournalEntry.from_row(row) for row in rows]
    
    def get_entries_by_tag(self, tag: str) -> List[JournalEntry]:
        """Get entries by tag."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM entries WHERE tags LIKE ? ORDER BY date DESC LIMIT 20",
                (f"%{tag.lower()}%",)
            ).fetchall()
        
        return [JournalEntry.from_row(row) for row in rows]
    
    def format_entry(self, entry: JournalEntry) -> str:
        """Format a single entry for display."""
        mood_emoji = {
            Mood.GREAT: "🌟",
            Mood.GOOD: "😊",
            Mood.OKAY: "😐",
            Mood.LOW: "😔",
            Mood.STRESSED: "😰",
        }
        
        lines = [f"📅 **{entry.date.strftime('%B %d, %Y')}**"]
        
        if entry.mood:
            emoji = mood_emoji.get(entry.mood, "")
            lines.append(f"Mood: {emoji} {entry.mood.value.title()}")
        
        lines.append(f"\n{entry.content}")
        
        if entry.tags:
            lines.append(f"\n🏷️ {' '.join('#' + tag for tag in entry.tags)}")
        
        return "\n".join(lines)
    
    def format_entries(self, entries: List[JournalEntry]) -> str:
        """Format multiple entries for display."""
        if not entries:
            return "No journal entries found."
        
        lines = ["📔 **Journal Entries**\n"]
        
        current_date = None
        for entry in entries:
            if entry.date != current_date:
                current_date = entry.date
                lines.append(f"\n**{entry.date.strftime('%B %d, %Y')}**")
            
            mood_str = ""
            if entry.mood:
                mood_emoji = {"great": "🌟", "good": "😊", "okay": "😐", "low": "😔", "stressed": "😰"}
                mood_str = f" {mood_emoji.get(entry.mood.value, '')}"
            
            # Truncate long content
            content = entry.content[:100] + "..." if len(entry.content) > 100 else entry.content
            lines.append(f"  •{mood_str} {content}")
        
        return "\n".join(lines)
    
    def get_mood_summary(self, days: int = 30) -> str:
        """Get mood summary for the last N days."""
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT mood, COUNT(*) as count 
                FROM entries 
                WHERE date >= ? AND mood IS NOT NULL
                GROUP BY mood
            """, (cutoff,)).fetchall()
            
            total = conn.execute(
                "SELECT COUNT(*) FROM entries WHERE date >= ?",
                (cutoff,)
            ).fetchone()[0]
        
        if not rows:
            return "No mood data available yet. Start journaling to track your mood!"
        
        mood_emoji = {"great": "🌟", "good": "😊", "okay": "😐", "low": "😔", "stressed": "😰"}
        
        lines = [
            f"📊 **Mood Summary (Last {days} Days)**\n",
            f"Total Entries: {total}\n",
        ]
        
        for mood, count in sorted(rows, key=lambda x: x[1], reverse=True):
            emoji = mood_emoji.get(mood, "")
            pct = (count / total * 100) if total > 0 else 0
            lines.append(f"  {emoji} {mood.title()}: {count} ({pct:.0f}%)")
        
        return "\n".join(lines)
    
    def get_streak(self) -> int:
        """Get current journaling streak (consecutive days)."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT date FROM entries ORDER BY date DESC"
            ).fetchall()
        
        if not rows:
            return 0
        
        dates = [date.fromisoformat(row[0]) for row in rows]
        
        streak = 0
        expected = date.today()
        
        for d in dates:
            if d == expected:
                streak += 1
                expected -= timedelta(days=1)
            elif d < expected:
                break
        
        return streak
    
    def get_stats(self) -> str:
        """Get journaling statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
            
            this_week = conn.execute("""
                SELECT COUNT(*) FROM entries 
                WHERE date >= ?
            """, ((date.today() - timedelta(days=7)).isoformat(),)).fetchone()[0]
            
            this_month = conn.execute("""
                SELECT COUNT(*) FROM entries 
                WHERE date >= ?
            """, ((date.today() - timedelta(days=30)).isoformat(),)).fetchone()[0]
        
        streak = self.get_streak()
        
        return f"""📔 **Journal Stats**

Total Entries: {total}
This Week: {this_week}
This Month: {this_month}
Current Streak: {streak} days 🔥"""
