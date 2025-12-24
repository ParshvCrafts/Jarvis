"""
Habit Tracker for JARVIS.

Build and maintain good habits:
- Daily habit tracking
- Streak counting
- Weekly reports
- Pre-configured student habits
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

from loguru import logger


class HabitFrequency(str, Enum):
    """Habit frequency."""
    DAILY = "daily"
    WEEKLY = "weekly"
    WEEKDAYS = "weekdays"  # Mon-Fri


@dataclass
class Habit:
    """A habit to track."""
    id: Optional[int] = None
    name: str = ""
    frequency: HabitFrequency = HabitFrequency.DAILY
    target: int = 1  # Target completions per period
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    active: bool = True
    
    def __str__(self) -> str:
        return f"{self.name} ({self.frequency.value})"


@dataclass
class HabitLog:
    """A habit completion log."""
    id: Optional[int] = None
    habit_id: int = 0
    date: date = field(default_factory=date.today)
    completed: bool = True
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class HabitStats:
    """Statistics for a habit."""
    habit: Habit
    current_streak: int = 0
    longest_streak: int = 0
    total_completions: int = 0
    completion_rate: float = 0.0
    last_completed: Optional[date] = None


class HabitTracker:
    """
    Habit tracking system.
    
    Usage:
        tracker = HabitTracker()
        tracker.add_habit("Exercise", frequency=HabitFrequency.DAILY)
        tracker.log_completion("Exercise")
        stats = tracker.get_stats("Exercise")
    """
    
    # Pre-configured habits for students
    DEFAULT_HABITS = [
        ("Study 4 hours", HabitFrequency.DAILY, "Study at least 4 hours"),
        ("Exercise", HabitFrequency.DAILY, "30 minutes of physical activity"),
        ("Review notes", HabitFrequency.DAILY, "Review today's class notes"),
        ("Read 30 min", HabitFrequency.DAILY, "Non-academic reading"),
        ("Meditate", HabitFrequency.DAILY, "5-10 minutes mindfulness"),
        ("Drink water", HabitFrequency.DAILY, "8 glasses of water"),
        ("Sleep 7+ hours", HabitFrequency.DAILY, "Get adequate sleep"),
        ("No social media during study", HabitFrequency.WEEKDAYS, "Focus during study sessions"),
    ]
    
    def __init__(self, db_path: str = "data/habits.db"):
        """
        Initialize habit tracker.
        
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
                CREATE TABLE IF NOT EXISTS habits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    frequency TEXT DEFAULT 'daily',
                    target INTEGER DEFAULT 1,
                    description TEXT,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS habit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    habit_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    completed BOOLEAN DEFAULT TRUE,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (habit_id) REFERENCES habits(id),
                    UNIQUE(habit_id, date)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_habit_logs_date 
                ON habit_logs(date)
            """)
            conn.commit()
    
    def add_habit(
        self,
        name: str,
        frequency: HabitFrequency = HabitFrequency.DAILY,
        description: Optional[str] = None,
        target: int = 1,
    ) -> Habit:
        """
        Add a new habit to track.
        
        Args:
            name: Habit name
            frequency: How often (daily, weekly, weekdays)
            description: Optional description
            target: Target completions per period
            
        Returns:
            Created habit
        """
        habit = Habit(
            name=name,
            frequency=frequency,
            description=description,
            target=target,
        )
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                cursor = conn.execute("""
                    INSERT INTO habits (name, frequency, target, description)
                    VALUES (?, ?, ?, ?)
                """, (habit.name, habit.frequency.value, habit.target, habit.description))
                habit.id = cursor.lastrowid
                conn.commit()
                logger.info(f"Added habit: {habit.name}")
            except sqlite3.IntegrityError:
                # Habit already exists, get it
                row = conn.execute(
                    "SELECT id FROM habits WHERE name = ?", (name,)
                ).fetchone()
                if row:
                    habit.id = row[0]
        
        return habit
    
    def add_default_habits(self) -> List[Habit]:
        """Add pre-configured default habits."""
        habits = []
        for name, freq, desc in self.DEFAULT_HABITS:
            habit = self.add_habit(name, freq, desc)
            habits.append(habit)
        return habits
    
    def get_habit(self, name: str) -> Optional[Habit]:
        """Get a habit by name."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM habits WHERE LOWER(name) LIKE LOWER(?) AND active = TRUE",
                (f"%{name}%",)
            ).fetchone()
            
            if row:
                return self._row_to_habit(row)
        return None
    
    def get_all_habits(self, active_only: bool = True) -> List[Habit]:
        """Get all habits."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM habits"
            if active_only:
                query += " WHERE active = TRUE"
            query += " ORDER BY name"
            
            rows = conn.execute(query).fetchall()
            return [self._row_to_habit(row) for row in rows]
    
    def log_completion(
        self,
        habit_name: str,
        completed: bool = True,
        notes: Optional[str] = None,
        log_date: Optional[date] = None,
    ) -> str:
        """
        Log habit completion.
        
        Args:
            habit_name: Name of habit
            completed: Whether completed
            notes: Optional notes
            log_date: Date to log (default: today)
            
        Returns:
            Status message
        """
        habit = self.get_habit(habit_name)
        if not habit:
            return f"Habit '{habit_name}' not found. Add it first with 'Add habit: {habit_name}'"
        
        log_date = log_date or date.today()
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO habit_logs (habit_id, date, completed, notes)
                    VALUES (?, ?, ?, ?)
                """, (habit.id, log_date, completed, notes))
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to log habit: {e}")
                return f"Failed to log habit: {str(e)}"
        
        streak = self.get_streak(habit.name)
        status = "✅" if completed else "❌"
        
        logger.info(f"Logged habit: {habit.name} = {completed}")
        return f"{status} {habit.name} logged! Current streak: {streak} days 🔥"
    
    def is_completed_today(self, habit_name: str) -> bool:
        """Check if habit is completed today."""
        habit = self.get_habit(habit_name)
        if not habit:
            return False
        
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT completed FROM habit_logs
                WHERE habit_id = ? AND date = ? AND completed = TRUE
            """, (habit.id, date.today())).fetchone()
            
            return row is not None
    
    def get_today_status(self) -> Dict[str, bool]:
        """Get completion status for all habits today."""
        habits = self.get_all_habits()
        status = {}
        
        for habit in habits:
            status[habit.name] = self.is_completed_today(habit.name)
        
        return status
    
    def get_streak(self, habit_name: str) -> int:
        """Get current streak for a habit."""
        habit = self.get_habit(habit_name)
        if not habit:
            return 0
        
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT DISTINCT date FROM habit_logs
                WHERE habit_id = ? AND completed = TRUE
                ORDER BY date DESC
            """, (habit.id,)).fetchall()
            
            if not rows:
                return 0
            
            streak = 0
            expected_date = date.today()
            
            for row in rows:
                log_date = datetime.strptime(row[0], "%Y-%m-%d").date() if isinstance(row[0], str) else row[0]
                
                # For weekday habits, skip weekends
                if habit.frequency == HabitFrequency.WEEKDAYS:
                    while expected_date.weekday() >= 5:  # Saturday or Sunday
                        expected_date -= timedelta(days=1)
                
                if log_date == expected_date:
                    streak += 1
                    expected_date -= timedelta(days=1)
                elif log_date < expected_date:
                    break
            
            return streak
    
    def get_stats(self, habit_name: str) -> Optional[HabitStats]:
        """Get statistics for a habit."""
        habit = self.get_habit(habit_name)
        if not habit:
            return None
        
        with sqlite3.connect(self.db_path) as conn:
            # Total completions
            row = conn.execute("""
                SELECT COUNT(*) FROM habit_logs
                WHERE habit_id = ? AND completed = TRUE
            """, (habit.id,)).fetchone()
            total_completions = row[0] if row else 0
            
            # Last completed
            row = conn.execute("""
                SELECT MAX(date) FROM habit_logs
                WHERE habit_id = ? AND completed = TRUE
            """, (habit.id,)).fetchone()
            last_completed = None
            if row and row[0]:
                last_completed = datetime.strptime(row[0], "%Y-%m-%d").date() if isinstance(row[0], str) else row[0]
            
            # Days since habit created
            days_active = (date.today() - habit.created_at.date()).days + 1
            completion_rate = total_completions / days_active if days_active > 0 else 0
        
        current_streak = self.get_streak(habit_name)
        
        # Calculate longest streak (simplified)
        longest_streak = current_streak  # Would need more complex query for true longest
        
        return HabitStats(
            habit=habit,
            current_streak=current_streak,
            longest_streak=longest_streak,
            total_completions=total_completions,
            completion_rate=min(1.0, completion_rate),
            last_completed=last_completed,
        )
    
    def get_weekly_report(self) -> str:
        """Generate weekly habit report."""
        habits = self.get_all_habits()
        
        if not habits:
            return "No habits tracked yet. Add habits with 'Add habit: [name]'"
        
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        
        lines = ["📊 Weekly Habit Report", ""]
        
        total_possible = 0
        total_completed = 0
        
        for habit in habits:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("""
                    SELECT COUNT(*) FROM habit_logs
                    WHERE habit_id = ? AND date >= ? AND completed = TRUE
                """, (habit.id, week_start)).fetchone()
                completed = row[0] if row else 0
            
            # Calculate possible days
            if habit.frequency == HabitFrequency.DAILY:
                possible = (today - week_start).days + 1
            elif habit.frequency == HabitFrequency.WEEKDAYS:
                possible = min(5, (today - week_start).days + 1)
            else:
                possible = 1
            
            total_possible += possible
            total_completed += completed
            
            streak = self.get_streak(habit.name)
            pct = (completed / possible * 100) if possible > 0 else 0
            
            status = "✅" if completed >= possible else "🔶" if completed > 0 else "❌"
            lines.append(f"{status} {habit.name}: {completed}/{possible} ({pct:.0f}%) | 🔥 {streak} day streak")
        
        overall_pct = (total_completed / total_possible * 100) if total_possible > 0 else 0
        lines.append("")
        lines.append(f"📈 Overall: {total_completed}/{total_possible} ({overall_pct:.0f}%)")
        
        return "\n".join(lines)
    
    def get_today_checklist(self) -> str:
        """Get today's habit checklist."""
        status = self.get_today_status()
        
        if not status:
            return "No habits tracked. Add habits with 'Add habit: [name]'"
        
        lines = ["📋 Today's Habits", ""]
        
        completed = 0
        for habit_name, is_done in status.items():
            icon = "✅" if is_done else "⬜"
            lines.append(f"{icon} {habit_name}")
            if is_done:
                completed += 1
        
        lines.append("")
        lines.append(f"Progress: {completed}/{len(status)} completed")
        
        return "\n".join(lines)
    
    def remove_habit(self, habit_name: str) -> str:
        """Remove (deactivate) a habit."""
        habit = self.get_habit(habit_name)
        if not habit:
            return f"Habit '{habit_name}' not found."
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE habits SET active = FALSE WHERE id = ?",
                (habit.id,)
            )
            conn.commit()
        
        return f"Removed habit: {habit.name}"
    
    def _row_to_habit(self, row: sqlite3.Row) -> Habit:
        """Convert database row to Habit."""
        return Habit(
            id=row["id"],
            name=row["name"],
            frequency=HabitFrequency(row["frequency"]),
            target=row["target"],
            description=row["description"],
            active=bool(row["active"]),
            created_at=datetime.fromisoformat(row["created_at"]) if isinstance(row["created_at"], str) else row["created_at"],
        )
