"""
Break Reminders for JARVIS.

Prevent burnout with smart break reminders:
- Configurable work/break intervals
- Break activity suggestions
- Compliance tracking
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


@dataclass
class BreakSuggestion:
    """A break activity suggestion."""
    activity: str
    duration_minutes: int
    category: str  # stretch, hydrate, walk, eyes, mindfulness
    description: Optional[str] = None


class BreakReminder:
    """
    Smart break reminder system.
    
    Reminds users to take breaks during long work sessions.
    Suggests healthy break activities.
    
    Usage:
        reminder = BreakReminder(on_break_due=callback)
        await reminder.start()
        reminder.take_break()
        reminder.skip_break()
    """
    
    # Break activity suggestions
    BREAK_ACTIVITIES = [
        # Stretches
        BreakSuggestion("Neck rolls", 1, "stretch", "Roll your neck slowly in circles"),
        BreakSuggestion("Shoulder shrugs", 1, "stretch", "Raise shoulders to ears, hold, release"),
        BreakSuggestion("Wrist stretches", 1, "stretch", "Extend arm, pull fingers back gently"),
        BreakSuggestion("Standing stretch", 2, "stretch", "Stand up and stretch arms overhead"),
        BreakSuggestion("Back twist", 1, "stretch", "Sit and twist torso left and right"),
        
        # Hydration
        BreakSuggestion("Drink water", 1, "hydrate", "Have a glass of water"),
        BreakSuggestion("Refill water bottle", 2, "hydrate", "Walk to refill your water"),
        BreakSuggestion("Make tea", 3, "hydrate", "Brew a cup of tea"),
        
        # Walking
        BreakSuggestion("Short walk", 5, "walk", "Walk around your room or hallway"),
        BreakSuggestion("Stair climb", 3, "walk", "Walk up and down stairs once"),
        BreakSuggestion("Step outside", 5, "walk", "Get some fresh air outside"),
        
        # Eye care
        BreakSuggestion("20-20-20 rule", 1, "eyes", "Look at something 20 feet away for 20 seconds"),
        BreakSuggestion("Eye circles", 1, "eyes", "Roll your eyes in circles"),
        BreakSuggestion("Palm your eyes", 1, "eyes", "Cover eyes with palms, relax"),
        BreakSuggestion("Look away", 1, "eyes", "Focus on a distant object"),
        
        # Mindfulness
        BreakSuggestion("Deep breaths", 2, "mindfulness", "Take 5 slow, deep breaths"),
        BreakSuggestion("Body scan", 3, "mindfulness", "Notice tension in your body"),
        BreakSuggestion("Gratitude moment", 2, "mindfulness", "Think of 3 things you're grateful for"),
        BreakSuggestion("Mini meditation", 5, "mindfulness", "Close eyes and focus on breathing"),
    ]
    
    def __init__(
        self,
        work_duration_minutes: int = 50,
        short_break_minutes: int = 5,
        long_break_minutes: int = 15,
        long_break_interval: int = 4,  # Long break after every N work sessions
        on_break_due: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize break reminder.
        
        Args:
            work_duration_minutes: Minutes of work before break reminder
            short_break_minutes: Duration of short breaks
            long_break_minutes: Duration of long breaks
            long_break_interval: Work sessions before long break
            on_break_due: Callback when break is due
        """
        self.work_duration = work_duration_minutes
        self.short_break = short_break_minutes
        self.long_break = long_break_minutes
        self.long_break_interval = long_break_interval
        self.on_break_due = on_break_due
        
        self._active = False
        self._work_start: Optional[datetime] = None
        self._sessions_since_long_break = 0
        self._breaks_taken = 0
        self._breaks_skipped = 0
        self._monitor_task: Optional[asyncio.Task] = None
    
    @property
    def is_active(self) -> bool:
        """Check if break reminders are active."""
        return self._active
    
    async def start(self) -> str:
        """Start break reminder monitoring."""
        if self._active:
            return "Break reminders are already active."
        
        self._active = True
        self._work_start = datetime.now()
        
        # Start monitoring task
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        logger.info(f"Break reminders started (every {self.work_duration} min)")
        return f"⏰ Break reminders enabled! I'll remind you every {self.work_duration} minutes."
    
    def stop(self) -> str:
        """Stop break reminder monitoring."""
        if not self._active:
            return "Break reminders are not active."
        
        self._active = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            self._monitor_task = None
        
        logger.info("Break reminders stopped")
        return "Break reminders disabled."
    
    async def _monitor_loop(self):
        """Background monitoring loop."""
        try:
            while self._active:
                await asyncio.sleep(self.work_duration * 60)
                
                if self._active:
                    self._trigger_break_reminder()
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Break monitor error: {e}")
    
    def _trigger_break_reminder(self):
        """Trigger a break reminder."""
        self._sessions_since_long_break += 1
        
        # Determine break type
        if self._sessions_since_long_break >= self.long_break_interval:
            is_long_break = True
            duration = self.long_break
            self._sessions_since_long_break = 0
        else:
            is_long_break = False
            duration = self.short_break
        
        # Get suggestion
        suggestion = self.get_suggestion(is_long_break)
        
        # Build message
        break_type = "long" if is_long_break else "short"
        message = f"""⏰ Time for a {break_type} break!

You've been working for {self.work_duration} minutes.
Take a {duration}-minute break.

💡 Suggestion: {suggestion.activity}
{suggestion.description}

Say 'Take a break' or 'Skip break'."""
        
        logger.info(f"Break reminder triggered: {break_type} break")
        
        if self.on_break_due:
            self.on_break_due(message)
    
    def take_break(self, duration_minutes: Optional[int] = None) -> str:
        """
        Acknowledge taking a break.
        
        Args:
            duration_minutes: Override break duration
            
        Returns:
            Break message with suggestion
        """
        duration = duration_minutes or self.short_break
        suggestion = self.get_suggestion(duration >= self.long_break)
        
        self._breaks_taken += 1
        self._work_start = datetime.now()  # Reset work timer
        
        return f"""🧘 Taking a {duration}-minute break!

💡 {suggestion.activity}
{suggestion.description}

Enjoy your break! I'll be here when you're ready."""
    
    def skip_break(self) -> str:
        """Skip the current break reminder."""
        self._breaks_skipped += 1
        self._work_start = datetime.now()  # Reset work timer
        
        return "⏭️ Break skipped. I'll remind you again later. Remember to take care of yourself!"
    
    def get_suggestion(self, is_long_break: bool = False) -> BreakSuggestion:
        """Get a random break activity suggestion."""
        if is_long_break:
            # For long breaks, prefer walks and longer activities
            suitable = [s for s in self.BREAK_ACTIVITIES if s.duration_minutes >= 3]
        else:
            # For short breaks, prefer quick activities
            suitable = [s for s in self.BREAK_ACTIVITIES if s.duration_minutes <= 3]
        
        if not suitable:
            suitable = self.BREAK_ACTIVITIES
        
        return random.choice(suitable)
    
    def get_suggestions_by_category(self, category: str) -> List[BreakSuggestion]:
        """Get suggestions by category."""
        return [s for s in self.BREAK_ACTIVITIES if s.category == category]
    
    def time_since_last_break(self) -> Optional[int]:
        """Get minutes since last break/start."""
        if not self._work_start:
            return None
        
        return int((datetime.now() - self._work_start).total_seconds() / 60)
    
    def get_status(self) -> str:
        """Get current break reminder status."""
        if not self._active:
            return "Break reminders are not active."
        
        minutes_worked = self.time_since_last_break() or 0
        minutes_until_break = max(0, self.work_duration - minutes_worked)
        
        sessions_until_long = self.long_break_interval - self._sessions_since_long_break
        
        return f"""⏰ Break Reminder Status

🟢 Active: Yes
⏱️ Time worked: {minutes_worked} minutes
⏳ Next break in: {minutes_until_break} minutes
📊 Sessions until long break: {sessions_until_long}

Today's stats:
✅ Breaks taken: {self._breaks_taken}
⏭️ Breaks skipped: {self._breaks_skipped}"""
    
    def get_stats(self) -> str:
        """Get break statistics."""
        total = self._breaks_taken + self._breaks_skipped
        compliance = (self._breaks_taken / total * 100) if total > 0 else 0
        
        return f"""📊 Break Statistics

✅ Breaks taken: {self._breaks_taken}
⏭️ Breaks skipped: {self._breaks_skipped}
📈 Compliance rate: {compliance:.0f}%

Keep taking breaks to stay healthy and productive!"""
    
    def suggest_stretch(self) -> str:
        """Get a stretch suggestion."""
        stretches = self.get_suggestions_by_category("stretch")
        suggestion = random.choice(stretches)
        return f"🧘 Stretch: {suggestion.activity}\n{suggestion.description}"
    
    def suggest_hydration(self) -> str:
        """Get a hydration suggestion."""
        hydration = self.get_suggestions_by_category("hydrate")
        suggestion = random.choice(hydration)
        return f"💧 Hydration: {suggestion.activity}\n{suggestion.description}"
    
    def suggest_eye_care(self) -> str:
        """Get an eye care suggestion."""
        eye_care = self.get_suggestions_by_category("eyes")
        suggestion = random.choice(eye_care)
        return f"👁️ Eye care: {suggestion.activity}\n{suggestion.description}"
