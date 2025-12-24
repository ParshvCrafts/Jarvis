"""
Focus Mode for JARVIS.

Block distractions during study sessions:
- Awareness-based distraction blocking
- Site blocklist management
- Integration with Pomodoro
- Focus session tracking
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from loguru import logger


@dataclass
class FocusSession:
    """A focus session record."""
    id: Optional[int] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_minutes: int = 0
    distractions_blocked: int = 0
    completed: bool = False


class FocusMode:
    """
    Focus mode manager.
    
    Provides awareness-based distraction blocking:
    - Maintains blocklist of distracting sites
    - Tracks focus sessions
    - Warns when accessing blocked sites
    
    Note: This is awareness-based, not system-level blocking.
    For actual blocking, use browser extensions or system tools.
    
    Usage:
        focus = FocusMode()
        focus.start()
        is_blocked = focus.check_url("twitter.com")
        focus.stop()
    """
    
    # Default blocked sites
    DEFAULT_BLOCKLIST = {
        "twitter.com",
        "x.com",
        "facebook.com",
        "instagram.com",
        "reddit.com",
        "tiktok.com",
        "youtube.com",  # Can be whitelisted for educational content
        "netflix.com",
        "twitch.tv",
        "discord.com",
        "snapchat.com",
        "pinterest.com",
        "tumblr.com",
    }
    
    # Educational sites that should never be blocked
    WHITELIST = {
        "github.com",
        "stackoverflow.com",
        "docs.python.org",
        "numpy.org",
        "pandas.pydata.org",
        "scikit-learn.org",
        "pytorch.org",
        "tensorflow.org",
        "kaggle.com",
        "arxiv.org",
        "scholar.google.com",
        "bcourses.berkeley.edu",
        "piazza.com",
        "gradescope.com",
        "edstem.org",
        "coursera.org",
        "edx.org",
        "khanacademy.org",
        "wikipedia.org",
        "wolframalpha.com",
        "desmos.com",
    }
    
    def __init__(
        self,
        db_path: str = "data/focus.db",
        custom_blocklist: Optional[Set[str]] = None,
    ):
        """
        Initialize focus mode.
        
        Args:
            db_path: Path to SQLite database
            custom_blocklist: Additional sites to block
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.blocklist = set(self.DEFAULT_BLOCKLIST)
        if custom_blocklist:
            self.blocklist.update(custom_blocklist)
        
        self._active = False
        self._session_start: Optional[datetime] = None
        self._distractions_blocked = 0
        
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS focus_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    duration_minutes INTEGER DEFAULT 0,
                    distractions_blocked INTEGER DEFAULT 0,
                    completed BOOLEAN DEFAULT FALSE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS blocklist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL UNIQUE,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS distraction_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id INTEGER,
                    FOREIGN KEY (session_id) REFERENCES focus_sessions(id)
                )
            """)
            conn.commit()
            
            # Load custom blocklist from database
            rows = conn.execute("SELECT domain FROM blocklist").fetchall()
            for row in rows:
                self.blocklist.add(row[0])
    
    @property
    def is_active(self) -> bool:
        """Check if focus mode is active."""
        return self._active
    
    def start(self, duration_minutes: Optional[int] = None) -> str:
        """
        Start focus mode.
        
        Args:
            duration_minutes: Optional duration (for auto-stop)
            
        Returns:
            Status message
        """
        if self._active:
            return "Focus mode is already active."
        
        self._active = True
        self._session_start = datetime.now()
        self._distractions_blocked = 0
        
        logger.info("Focus mode started")
        
        blocked_count = len(self.blocklist)
        return f"🎯 Focus mode activated! {blocked_count} distracting sites will be flagged."
    
    def stop(self) -> str:
        """Stop focus mode and save session."""
        if not self._active:
            return "Focus mode is not active."
        
        end_time = datetime.now()
        duration = int((end_time - self._session_start).total_seconds() / 60)
        
        # Save session
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO focus_sessions 
                (start_time, end_time, duration_minutes, distractions_blocked, completed)
                VALUES (?, ?, ?, ?, TRUE)
            """, (self._session_start, end_time, duration, self._distractions_blocked))
            conn.commit()
        
        self._active = False
        blocked = self._distractions_blocked
        self._session_start = None
        self._distractions_blocked = 0
        
        logger.info(f"Focus mode ended: {duration} min, {blocked} distractions blocked")
        
        return f"🏁 Focus session complete!\n⏱️ Duration: {duration} minutes\n🚫 Distractions blocked: {blocked}"
    
    def check_url(self, url: str) -> tuple:
        """
        Check if a URL should be blocked.
        
        Args:
            url: URL or domain to check
            
        Returns:
            (is_blocked, message)
        """
        # Extract domain from URL
        domain = self._extract_domain(url)
        
        # Check whitelist first
        for whitelisted in self.WHITELIST:
            if whitelisted in domain:
                return False, None
        
        # Check blocklist
        for blocked in self.blocklist:
            if blocked in domain:
                if self._active:
                    self._distractions_blocked += 1
                    self._log_distraction(domain)
                    return True, f"⚠️ {domain} is blocked during focus mode. Stay focused!"
                return True, f"💡 {domain} is on your blocklist. Consider staying focused."
        
        return False, None
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        url = url.lower().strip()
        
        # Remove protocol
        for prefix in ["https://", "http://", "www."]:
            if url.startswith(prefix):
                url = url[len(prefix):]
        
        # Get domain part
        domain = url.split("/")[0]
        return domain
    
    def _log_distraction(self, domain: str):
        """Log a blocked distraction."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO distraction_log (domain, blocked_at)
                VALUES (?, CURRENT_TIMESTAMP)
            """, (domain,))
            conn.commit()
    
    def add_to_blocklist(self, domain: str) -> str:
        """Add a site to the blocklist."""
        domain = self._extract_domain(domain)
        
        if domain in self.WHITELIST:
            return f"Cannot block {domain} - it's on the educational whitelist."
        
        self.blocklist.add(domain)
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute(
                    "INSERT INTO blocklist (domain) VALUES (?)",
                    (domain,)
                )
                conn.commit()
            except sqlite3.IntegrityError:
                pass  # Already exists
        
        return f"Added {domain} to blocklist."
    
    def remove_from_blocklist(self, domain: str) -> str:
        """Remove a site from the blocklist."""
        domain = self._extract_domain(domain)
        
        if domain in self.blocklist:
            self.blocklist.discard(domain)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "DELETE FROM blocklist WHERE domain = ?",
                    (domain,)
                )
                conn.commit()
            
            return f"Removed {domain} from blocklist."
        
        return f"{domain} is not in your blocklist."
    
    def get_blocklist(self) -> List[str]:
        """Get current blocklist."""
        return sorted(self.blocklist)
    
    def get_status(self) -> str:
        """Get current focus mode status."""
        if not self._active:
            return "Focus mode is not active."
        
        duration = int((datetime.now() - self._session_start).total_seconds() / 60)
        
        return f"""🎯 Focus Mode Active
⏱️ Duration: {duration} minutes
🚫 Distractions blocked: {self._distractions_blocked}"""
    
    def get_today_stats(self) -> str:
        """Get today's focus statistics."""
        today = datetime.now().date()
        
        with sqlite3.connect(self.db_path) as conn:
            # Total focus time today
            row = conn.execute("""
                SELECT COALESCE(SUM(duration_minutes), 0), COUNT(*)
                FROM focus_sessions
                WHERE DATE(start_time) = DATE(?)
            """, (today,)).fetchone()
            
            total_minutes = row[0]
            session_count = row[1]
            
            # Distractions blocked today
            row = conn.execute("""
                SELECT COUNT(*) FROM distraction_log
                WHERE DATE(blocked_at) = DATE(?)
            """, (today,)).fetchone()
            
            distractions = row[0]
        
        hours = total_minutes // 60
        mins = total_minutes % 60
        
        return f"""📊 Today's Focus Stats
⏱️ Total focus time: {hours}h {mins}m
🎯 Sessions: {session_count}
🚫 Distractions blocked: {distractions}"""
    
    def get_weekly_stats(self) -> str:
        """Get this week's focus statistics."""
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT COALESCE(SUM(duration_minutes), 0), COUNT(*),
                       COALESCE(SUM(distractions_blocked), 0)
                FROM focus_sessions
                WHERE DATE(start_time) >= DATE(?)
            """, (week_start,)).fetchone()
            
            total_minutes = row[0]
            session_count = row[1]
            distractions = row[2]
        
        hours = total_minutes // 60
        mins = total_minutes % 60
        
        return f"""📊 Weekly Focus Stats
⏱️ Total focus time: {hours}h {mins}m
🎯 Sessions: {session_count}
🚫 Distractions blocked: {distractions}"""
    
    def format_blocklist(self) -> str:
        """Format blocklist for display."""
        sites = self.get_blocklist()
        
        if not sites:
            return "Blocklist is empty."
        
        lines = ["🚫 Blocked Sites:", ""]
        for site in sites:
            lines.append(f"  • {site}")
        
        lines.append("")
        lines.append(f"Total: {len(sites)} sites")
        
        return "\n".join(lines)
