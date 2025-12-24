"""
Pomodoro Study Timer for JARVIS.

Provides voice-controlled study sessions with:
- Standard Pomodoro (25 min work, 5 min break)
- Customizable durations
- Long breaks after 4 sessions
- Study statistics tracking
"""

from __future__ import annotations

import asyncio
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

# Audio support
try:
    from ..core.audio import AudioPlayer
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    AudioPlayer = None


class TimerState(str, Enum):
    """Timer state."""
    IDLE = "idle"
    WORKING = "working"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"
    PAUSED = "paused"


@dataclass
class StudySession:
    """A completed study session."""
    id: Optional[int] = None
    subject: Optional[str] = None
    duration_minutes: int = 25
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    completed: bool = False
    
    @property
    def actual_duration(self) -> timedelta:
        """Get actual duration of session."""
        end = self.ended_at or datetime.now()
        return end - self.started_at


@dataclass
class PomodoroStats:
    """Pomodoro statistics."""
    today_sessions: int = 0
    today_minutes: int = 0
    week_sessions: int = 0
    week_minutes: int = 0
    total_sessions: int = 0
    total_minutes: int = 0
    current_streak: int = 0
    longest_streak: int = 0


class PomodoroTimer:
    """
    Pomodoro study timer with voice control.
    
    Usage:
        timer = PomodoroTimer()
        await timer.start()  # Start 25-min work session
        await timer.start(duration=45, subject="Data 8")  # Custom session
        timer.pause()
        timer.resume()
        timer.stop()
    """
    
    def __init__(
        self,
        db_path: str = "data/pomodoro.db",
        work_duration: int = 25,
        short_break: int = 5,
        long_break: int = 15,
        sessions_before_long_break: int = 4,
        on_timer_end: Optional[Callable[[str], None]] = None,
        on_tick: Optional[Callable[[int], None]] = None,
    ):
        """
        Initialize Pomodoro timer.
        
        Args:
            db_path: Path to SQLite database for session tracking
            work_duration: Default work session duration (minutes)
            short_break: Short break duration (minutes)
            long_break: Long break duration (minutes)
            sessions_before_long_break: Sessions before long break
            on_timer_end: Callback when timer ends (receives message)
            on_tick: Callback every second (receives remaining seconds)
        """
        self.db_path = Path(db_path)
        self.work_duration = work_duration
        self.short_break = short_break
        self.long_break = long_break
        self.sessions_before_long_break = sessions_before_long_break
        self.on_timer_end = on_timer_end
        self.on_tick = on_tick
        
        # Audio player for notifications
        self._audio: Optional[AudioPlayer] = None
        if AUDIO_AVAILABLE:
            try:
                self._audio = AudioPlayer()
            except Exception as e:
                logger.debug(f"Audio player init failed: {e}")
        
        # Timer state
        self.state = TimerState.IDLE
        self.current_session: Optional[StudySession] = None
        self.remaining_seconds: int = 0
        self.sessions_completed: int = 0
        self._timer_task: Optional[asyncio.Task] = None
        self._paused_at: Optional[datetime] = None
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS study_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT,
                    duration_minutes INTEGER NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    ended_at TIMESTAMP,
                    completed BOOLEAN DEFAULT FALSE
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_started 
                ON study_sessions(started_at)
            """)
            conn.commit()
    
    # =========================================================================
    # Timer Control
    # =========================================================================
    
    async def start(
        self,
        duration: Optional[int] = None,
        subject: Optional[str] = None,
    ) -> str:
        """
        Start a work session.
        
        Args:
            duration: Session duration in minutes (default: work_duration)
            subject: Optional subject/topic for the session
            
        Returns:
            Status message
        """
        if self.state in (TimerState.WORKING, TimerState.SHORT_BREAK, TimerState.LONG_BREAK):
            return f"Timer already running. {self.get_status()}"
        
        if self.state == TimerState.PAUSED:
            return await self.resume()
        
        # Create new session
        duration = duration or self.work_duration
        self.current_session = StudySession(
            subject=subject,
            duration_minutes=duration,
            started_at=datetime.now(),
        )
        
        self.remaining_seconds = duration * 60
        self.state = TimerState.WORKING
        
        # Start timer task
        self._timer_task = asyncio.create_task(self._run_timer())
        
        subject_str = f" for {subject}" if subject else ""
        return f"Starting {duration}-minute focus session{subject_str}. I'll notify you when it's time for a break."
    
    async def start_break(self, long_break: bool = False) -> str:
        """
        Start a break.
        
        Args:
            long_break: Whether to take a long break
            
        Returns:
            Status message
        """
        if self.state in (TimerState.SHORT_BREAK, TimerState.LONG_BREAK):
            return f"Already on break. {self.get_status()}"
        
        if long_break:
            self.remaining_seconds = self.long_break * 60
            self.state = TimerState.LONG_BREAK
            duration = self.long_break
        else:
            self.remaining_seconds = self.short_break * 60
            self.state = TimerState.SHORT_BREAK
            duration = self.short_break
        
        # Start timer task
        self._timer_task = asyncio.create_task(self._run_timer())
        
        return f"Starting {duration}-minute break. Relax and recharge!"
    
    def pause(self) -> str:
        """Pause the timer."""
        if self.state == TimerState.IDLE:
            return "No timer running."
        
        if self.state == TimerState.PAUSED:
            return "Timer already paused."
        
        self._paused_at = datetime.now()
        self.state = TimerState.PAUSED
        
        if self._timer_task:
            self._timer_task.cancel()
            self._timer_task = None
        
        return f"Timer paused. {self._format_time(self.remaining_seconds)} remaining."
    
    async def resume(self) -> str:
        """Resume a paused timer."""
        if self.state != TimerState.PAUSED:
            return "Timer is not paused."
        
        self.state = TimerState.WORKING
        self._paused_at = None
        
        # Restart timer task
        self._timer_task = asyncio.create_task(self._run_timer())
        
        return f"Timer resumed. {self._format_time(self.remaining_seconds)} remaining."
    
    def stop(self) -> str:
        """Stop the timer."""
        if self.state == TimerState.IDLE:
            return "No timer running."
        
        # Cancel timer task
        if self._timer_task:
            self._timer_task.cancel()
            self._timer_task = None
        
        # Save incomplete session if it was a work session
        if self.current_session:
            self.current_session.ended_at = datetime.now()
            self.current_session.completed = False
            self._save_session(self.current_session)
        
        self.state = TimerState.IDLE
        self.current_session = None
        self.remaining_seconds = 0
        
        return "Study session ended."
    
    async def _run_timer(self):
        """Run the timer countdown."""
        try:
            while self.remaining_seconds > 0:
                await asyncio.sleep(1)
                self.remaining_seconds -= 1
                
                if self.on_tick:
                    self.on_tick(self.remaining_seconds)
            
            # Timer completed
            await self._on_timer_complete()
            
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Timer error: {e}")
    
    async def _on_timer_complete(self):
        """Handle timer completion."""
        if self.state == TimerState.WORKING:
            # Work session completed
            if self.current_session:
                self.current_session.ended_at = datetime.now()
                self.current_session.completed = True
                self._save_session(self.current_session)
            
            self.sessions_completed += 1
            
            # Determine break type
            if self.sessions_completed % self.sessions_before_long_break == 0:
                message = f"Great work! You've completed {self.sessions_completed} pomodoros. Time for a {self.long_break}-minute long break!"
                self.state = TimerState.IDLE
            else:
                message = f"Focus session complete! Time for a {self.short_break}-minute break."
                self.state = TimerState.IDLE
            
            self.current_session = None
            
        elif self.state in (TimerState.SHORT_BREAK, TimerState.LONG_BREAK):
            message = "Break's over! Ready to start another focus session?"
            self.state = TimerState.IDLE
        else:
            message = "Timer complete!"
            self.state = TimerState.IDLE
        
        # Play audio notification
        self._play_notification_sound()
        
        if self.on_timer_end:
            self.on_timer_end(message)
        
        logger.info(f"Pomodoro: {message}")
    
    def _play_notification_sound(self):
        """Play audio notification when timer ends."""
        if not self._audio or not self._audio.available:
            # Fallback to system beep on Windows
            try:
                import winsound
                winsound.Beep(800, 500)  # 800Hz for 500ms
                winsound.Beep(1000, 500)  # 1000Hz for 500ms
            except Exception:
                pass
            return
        
        try:
            # Try to play success sound
            self._audio.play_success()
        except Exception as e:
            logger.debug(f"Audio notification failed: {e}")
    
    # =========================================================================
    # Status & Statistics
    # =========================================================================
    
    def get_status(self) -> str:
        """Get current timer status."""
        if self.state == TimerState.IDLE:
            return "No timer running."
        
        time_str = self._format_time(self.remaining_seconds)
        
        if self.state == TimerState.WORKING:
            subject = f" ({self.current_session.subject})" if self.current_session and self.current_session.subject else ""
            return f"Focus session{subject}: {time_str} remaining"
        elif self.state == TimerState.SHORT_BREAK:
            return f"Short break: {time_str} remaining"
        elif self.state == TimerState.LONG_BREAK:
            return f"Long break: {time_str} remaining"
        elif self.state == TimerState.PAUSED:
            return f"Paused: {time_str} remaining"
        
        return f"Timer: {time_str}"
    
    def get_time_remaining(self) -> Optional[int]:
        """Get remaining time in seconds."""
        if self.state == TimerState.IDLE:
            return None
        return self.remaining_seconds
    
    def _format_time(self, seconds: int) -> str:
        """Format seconds as MM:SS or HH:MM:SS."""
        if seconds >= 3600:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}:{secs:02d}"
    
    def get_stats(self) -> PomodoroStats:
        """Get study statistics."""
        stats = PomodoroStats()
        
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Today's stats
            row = conn.execute("""
                SELECT COUNT(*) as count, COALESCE(SUM(duration_minutes), 0) as minutes
                FROM study_sessions
                WHERE DATE(started_at) = DATE(?) AND completed = TRUE
            """, (today,)).fetchone()
            stats.today_sessions = row["count"]
            stats.today_minutes = row["minutes"]
            
            # Week stats
            row = conn.execute("""
                SELECT COUNT(*) as count, COALESCE(SUM(duration_minutes), 0) as minutes
                FROM study_sessions
                WHERE DATE(started_at) >= DATE(?) AND completed = TRUE
            """, (week_start,)).fetchone()
            stats.week_sessions = row["count"]
            stats.week_minutes = row["minutes"]
            
            # Total stats
            row = conn.execute("""
                SELECT COUNT(*) as count, COALESCE(SUM(duration_minutes), 0) as minutes
                FROM study_sessions
                WHERE completed = TRUE
            """).fetchone()
            stats.total_sessions = row["count"]
            stats.total_minutes = row["minutes"]
            
            # Streak calculation (consecutive days with at least one session)
            rows = conn.execute("""
                SELECT DISTINCT DATE(started_at) as session_date
                FROM study_sessions
                WHERE completed = TRUE
                ORDER BY session_date DESC
            """).fetchall()
            
            if rows:
                dates = [datetime.strptime(r["session_date"], "%Y-%m-%d").date() for r in rows]
                
                # Current streak
                current_streak = 0
                check_date = today
                for d in dates:
                    if d == check_date:
                        current_streak += 1
                        check_date -= timedelta(days=1)
                    elif d == check_date - timedelta(days=1):
                        # Allow for yesterday if today hasn't started yet
                        current_streak += 1
                        check_date = d - timedelta(days=1)
                    else:
                        break
                stats.current_streak = current_streak
                
                # Longest streak
                longest = 1
                current = 1
                for i in range(1, len(dates)):
                    if dates[i] == dates[i-1] - timedelta(days=1):
                        current += 1
                        longest = max(longest, current)
                    else:
                        current = 1
                stats.longest_streak = longest
        
        return stats
    
    def format_stats(self) -> str:
        """Format statistics as readable string."""
        stats = self.get_stats()
        
        lines = [
            f"📊 Study Statistics:",
            f"",
            f"Today: {stats.today_sessions} sessions ({stats.today_minutes} minutes)",
            f"This week: {stats.week_sessions} sessions ({stats.week_minutes} minutes)",
            f"Total: {stats.total_sessions} sessions ({stats.total_minutes} minutes)",
            f"",
            f"🔥 Current streak: {stats.current_streak} days",
            f"🏆 Longest streak: {stats.longest_streak} days",
        ]
        
        return "\n".join(lines)
    
    def get_today_summary(self) -> str:
        """Get today's study summary."""
        stats = self.get_stats()
        
        if stats.today_sessions == 0:
            return "You haven't completed any study sessions today. Ready to start?"
        
        hours = stats.today_minutes // 60
        minutes = stats.today_minutes % 60
        
        time_str = f"{hours} hours and {minutes} minutes" if hours > 0 else f"{minutes} minutes"
        
        return f"Today you've completed {stats.today_sessions} pomodoros, totaling {time_str} of focused study time."
    
    # =========================================================================
    # Database Operations
    # =========================================================================
    
    def _save_session(self, session: StudySession):
        """Save a study session to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO study_sessions (subject, duration_minutes, started_at, ended_at, completed)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session.subject,
                session.duration_minutes,
                session.started_at.isoformat(),
                session.ended_at.isoformat() if session.ended_at else None,
                session.completed,
            ))
            conn.commit()
    
    def get_recent_sessions(self, limit: int = 10) -> List[StudySession]:
        """Get recent study sessions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM study_sessions
                ORDER BY started_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
            
            sessions = []
            for row in rows:
                session = StudySession(
                    id=row["id"],
                    subject=row["subject"],
                    duration_minutes=row["duration_minutes"],
                    started_at=datetime.fromisoformat(row["started_at"]),
                    ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
                    completed=bool(row["completed"]),
                )
                sessions.append(session)
            
            return sessions
