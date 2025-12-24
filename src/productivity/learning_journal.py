"""
Learning Journal for JARVIS.

Track daily learning for retention and reflection:
- Log what you learned
- Key takeaways
- Questions and confusions
- Understanding ratings
- Weekly/monthly summaries
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class JournalEntry:
    """A learning journal entry."""
    id: Optional[int] = None
    date: datetime = field(default_factory=datetime.now)
    subject: str = ""
    content: str = ""
    takeaways: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)
    rating: int = 3  # 1-5 understanding rating
    time_spent: int = 0  # minutes
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def rating_emoji(self) -> str:
        """Get emoji representation of rating."""
        emojis = {1: "😵", 2: "😕", 3: "😐", 4: "🙂", 5: "🤩"}
        return emojis.get(self.rating, "😐")
    
    def __str__(self) -> str:
        date_str = self.date.strftime("%b %d, %Y")
        return f"[{date_str}] {self.subject}: {self.content[:50]}..."


class LearningJournal:
    """
    Learning journal for tracking daily learning.
    
    Usage:
        journal = LearningJournal()
        journal.log("Learned about gradient descent in Data 8", subject="Data 8")
        entries = journal.get_this_week()
        summary = journal.get_weekly_summary()
    """
    
    def __init__(self, db_path: str = "data/learning_journal.db"):
        """
        Initialize learning journal.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS journal_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TIMESTAMP NOT NULL,
                    subject TEXT,
                    content TEXT NOT NULL,
                    takeaways TEXT,
                    questions TEXT,
                    rating INTEGER DEFAULT 3,
                    time_spent INTEGER DEFAULT 0,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_journal_date 
                ON journal_entries(date)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_journal_subject 
                ON journal_entries(subject)
            """)
            conn.commit()
    
    def log(
        self,
        content: str,
        subject: Optional[str] = None,
        takeaways: Optional[List[str]] = None,
        questions: Optional[List[str]] = None,
        rating: int = 3,
        time_spent: int = 0,
        tags: Optional[List[str]] = None,
    ) -> JournalEntry:
        """
        Log a learning entry.
        
        Args:
            content: What you learned
            subject: Subject/topic (e.g., "Data 8", "ML", "Python")
            takeaways: Key takeaways
            questions: Questions or confusions
            rating: Understanding rating (1-5)
            time_spent: Time spent in minutes
            tags: Tags for categorization
            
        Returns:
            Created journal entry
        """
        entry = JournalEntry(
            date=datetime.now(),
            subject=subject or "General",
            content=content,
            takeaways=takeaways or [],
            questions=questions or [],
            rating=max(1, min(5, rating)),
            time_spent=time_spent,
            tags=tags or [],
        )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO journal_entries 
                (date, subject, content, takeaways, questions, rating, time_spent, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.date,
                entry.subject,
                entry.content,
                "|".join(entry.takeaways),
                "|".join(entry.questions),
                entry.rating,
                entry.time_spent,
                "|".join(entry.tags),
            ))
            entry.id = cursor.lastrowid
            conn.commit()
        
        logger.info(f"Logged learning: {entry.subject} - {content[:50]}")
        return entry
    
    def add_takeaway(self, entry_id: int, takeaway: str) -> bool:
        """Add a takeaway to an existing entry."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT takeaways FROM journal_entries WHERE id = ?",
                (entry_id,)
            ).fetchone()
            
            if not row:
                return False
            
            existing = row[0].split("|") if row[0] else []
            existing.append(takeaway)
            
            conn.execute(
                "UPDATE journal_entries SET takeaways = ? WHERE id = ?",
                ("|".join(existing), entry_id)
            )
            conn.commit()
        return True
    
    def add_question(self, entry_id: int, question: str) -> bool:
        """Add a question to an existing entry."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT questions FROM journal_entries WHERE id = ?",
                (entry_id,)
            ).fetchone()
            
            if not row:
                return False
            
            existing = row[0].split("|") if row[0] else []
            existing.append(question)
            
            conn.execute(
                "UPDATE journal_entries SET questions = ? WHERE id = ?",
                ("|".join(existing), entry_id)
            )
            conn.commit()
        return True
    
    def get_entry(self, entry_id: int) -> Optional[JournalEntry]:
        """Get a specific entry by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM journal_entries WHERE id = ?",
                (entry_id,)
            ).fetchone()
            
            if row:
                return self._row_to_entry(row)
        return None
    
    def get_today(self) -> List[JournalEntry]:
        """Get today's entries."""
        today = datetime.now().date()
        return self._get_entries_by_date(today, today)
    
    def get_this_week(self) -> List[JournalEntry]:
        """Get this week's entries."""
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        return self._get_entries_by_date(week_start, today)
    
    def get_this_month(self) -> List[JournalEntry]:
        """Get this month's entries."""
        today = datetime.now().date()
        month_start = today.replace(day=1)
        return self._get_entries_by_date(month_start, today)
    
    def _get_entries_by_date(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[JournalEntry]:
        """Get entries within date range."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM journal_entries
                WHERE DATE(date) >= DATE(?) AND DATE(date) <= DATE(?)
                ORDER BY date DESC
            """, (start_date, end_date)).fetchall()
            
            return [self._row_to_entry(row) for row in rows]
    
    def get_by_subject(self, subject: str, limit: int = 20) -> List[JournalEntry]:
        """Get entries by subject."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM journal_entries
                WHERE LOWER(subject) LIKE LOWER(?)
                ORDER BY date DESC
                LIMIT ?
            """, (f"%{subject}%", limit)).fetchall()
            
            return [self._row_to_entry(row) for row in rows]
    
    def search(self, query: str, limit: int = 20) -> List[JournalEntry]:
        """Search entries by content."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM journal_entries
                WHERE LOWER(content) LIKE LOWER(?)
                   OR LOWER(subject) LIKE LOWER(?)
                   OR LOWER(takeaways) LIKE LOWER(?)
                ORDER BY date DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%", limit)).fetchall()
            
            return [self._row_to_entry(row) for row in rows]
    
    def get_recent(self, limit: int = 10) -> List[JournalEntry]:
        """Get most recent entries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM journal_entries
                ORDER BY date DESC
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [self._row_to_entry(row) for row in rows]
    
    def get_streak(self) -> int:
        """Get current logging streak (consecutive days)."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT DISTINCT DATE(date) as log_date
                FROM journal_entries
                ORDER BY log_date DESC
            """).fetchall()
            
            if not rows:
                return 0
            
            streak = 0
            expected_date = datetime.now().date()
            
            for row in rows:
                log_date = datetime.strptime(row[0], "%Y-%m-%d").date()
                
                if log_date == expected_date:
                    streak += 1
                    expected_date -= timedelta(days=1)
                elif log_date < expected_date:
                    break
            
            return streak
    
    def get_weekly_summary(self) -> str:
        """Generate weekly learning summary."""
        entries = self.get_this_week()
        
        if not entries:
            return "No learning logged this week. Start logging with 'Log learning: [what you learned]'"
        
        # Aggregate stats
        subjects = {}
        total_time = 0
        total_rating = 0
        all_takeaways = []
        all_questions = []
        
        for entry in entries:
            subject = entry.subject
            if subject not in subjects:
                subjects[subject] = 0
            subjects[subject] += 1
            total_time += entry.time_spent
            total_rating += entry.rating
            all_takeaways.extend(entry.takeaways)
            all_questions.extend(entry.questions)
        
        avg_rating = total_rating / len(entries) if entries else 0
        
        lines = ["📚 Weekly Learning Summary", ""]
        lines.append(f"📝 Total entries: {len(entries)}")
        lines.append(f"⏱️ Total time: {total_time} minutes")
        lines.append(f"📊 Avg understanding: {avg_rating:.1f}/5")
        lines.append(f"🔥 Current streak: {self.get_streak()} days")
        
        lines.append("\n📖 Subjects covered:")
        for subject, count in sorted(subjects.items(), key=lambda x: -x[1]):
            lines.append(f"  • {subject}: {count} entries")
        
        if all_takeaways:
            lines.append("\n💡 Key takeaways:")
            for takeaway in all_takeaways[:5]:
                lines.append(f"  • {takeaway}")
        
        if all_questions:
            lines.append("\n❓ Open questions:")
            for question in all_questions[:3]:
                lines.append(f"  • {question}")
        
        return "\n".join(lines)
    
    def get_monthly_summary(self) -> str:
        """Generate monthly learning summary."""
        entries = self.get_this_month()
        
        if not entries:
            return "No learning logged this month."
        
        subjects = {}
        total_time = 0
        
        for entry in entries:
            subject = entry.subject
            if subject not in subjects:
                subjects[subject] = {"count": 0, "time": 0, "rating_sum": 0}
            subjects[subject]["count"] += 1
            subjects[subject]["time"] += entry.time_spent
            subjects[subject]["rating_sum"] += entry.rating
        
        lines = ["📚 Monthly Learning Summary", ""]
        lines.append(f"📝 Total entries: {len(entries)}")
        lines.append(f"⏱️ Total time: {sum(s['time'] for s in subjects.values())} minutes")
        
        lines.append("\n📖 By subject:")
        for subject, stats in sorted(subjects.items(), key=lambda x: -x[1]["count"]):
            avg = stats["rating_sum"] / stats["count"] if stats["count"] else 0
            lines.append(f"  • {subject}: {stats['count']} entries, {stats['time']} min, {avg:.1f}/5 avg")
        
        return "\n".join(lines)
    
    def format_entries(self, entries: List[JournalEntry], detailed: bool = False) -> str:
        """Format entries for display."""
        if not entries:
            return "No entries found."
        
        lines = []
        for entry in entries:
            date_str = entry.date.strftime("%b %d, %I:%M %p")
            lines.append(f"• [{entry.subject}] {entry.content[:60]}{'...' if len(entry.content) > 60 else ''}")
            lines.append(f"  {date_str} | {entry.rating_emoji} {entry.rating}/5")
            
            if detailed:
                if entry.takeaways:
                    lines.append(f"  💡 Takeaways: {', '.join(entry.takeaways[:2])}")
                if entry.questions:
                    lines.append(f"  ❓ Questions: {', '.join(entry.questions[:2])}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _row_to_entry(self, row: sqlite3.Row) -> JournalEntry:
        """Convert database row to JournalEntry."""
        return JournalEntry(
            id=row["id"],
            date=datetime.fromisoformat(row["date"]) if isinstance(row["date"], str) else row["date"],
            subject=row["subject"] or "",
            content=row["content"],
            takeaways=row["takeaways"].split("|") if row["takeaways"] else [],
            questions=row["questions"].split("|") if row["questions"] else [],
            rating=row["rating"],
            time_spent=row["time_spent"],
            tags=row["tags"].split("|") if row["tags"] else [],
            created_at=datetime.fromisoformat(row["created_at"]) if isinstance(row["created_at"], str) else row["created_at"],
        )
