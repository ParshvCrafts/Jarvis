"""
Daily Briefing for JARVIS.

Provides comprehensive morning briefings and evening summaries:
- Weather
- Calendar events
- Assignments due
- Unread emails
- Study statistics
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class BriefingData:
    """Data for a daily briefing."""
    greeting: str = ""
    date_str: str = ""
    weather: Optional[str] = None
    calendar_events: List[str] = field(default_factory=list)
    assignments_due_today: List[str] = field(default_factory=list)
    assignments_due_tomorrow: List[str] = field(default_factory=list)
    assignments_this_week: List[str] = field(default_factory=list)
    unread_emails: int = 0
    study_time_today: int = 0  # minutes
    study_time_yesterday: int = 0  # minutes
    pomodoros_today: int = 0
    habit_streaks: List[str] = field(default_factory=list)
    application_updates: List[str] = field(default_factory=list)
    financial_tip: Optional[str] = None
    motivational_quote: Optional[str] = None


class DailyBriefing:
    """
    Daily briefing generator.
    
    Aggregates data from various sources to provide
    comprehensive morning briefings and evening summaries.
    
    Usage:
        briefing = DailyBriefing(canvas_client, pomodoro_timer, ...)
        message = await briefing.get_morning_briefing()
        summary = await briefing.get_evening_summary()
    """
    
    MOTIVATIONAL_QUOTES = [
        "The only way to do great work is to love what you do. - Steve Jobs",
        "Success is not final, failure is not fatal: it is the courage to continue that counts. - Winston Churchill",
        "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
        "It does not matter how slowly you go as long as you do not stop. - Confucius",
        "Believe you can and you're halfway there. - Theodore Roosevelt",
        "The best time to plant a tree was 20 years ago. The second best time is now. - Chinese Proverb",
        "Your limitation—it's only your imagination.",
        "Push yourself, because no one else is going to do it for you.",
        "Great things never come from comfort zones.",
        "Dream it. Wish it. Do it.",
        "Success doesn't just find you. You have to go out and get it.",
        "The harder you work for something, the greater you'll feel when you achieve it.",
        "Dream bigger. Do bigger.",
        "Don't stop when you're tired. Stop when you're done.",
        "Wake up with determination. Go to bed with satisfaction.",
    ]
    
    # Financial tips for students
    FINANCIAL_TIPS = [
        "💰 Tip: Max out your Roth IRA early - time in market beats timing the market!",
        "💰 Tip: Check if you're getting all your student discounts (Spotify, Amazon Prime, Adobe).",
        "💰 Tip: Keep your credit utilization under 30% to build a strong credit score.",
        "💰 Tip: Even $50/month invested now could be $100K+ by retirement thanks to compound interest.",
        "💰 Tip: Always get your employer's full 401k match - it's free money!",
        "💰 Tip: High-yield savings accounts offer 4%+ APY - don't leave money in a 0.01% account.",
        "💰 Tip: Tax-loss harvesting can save you money - sell losers to offset gains.",
        "💰 Tip: Index funds beat 90% of actively managed funds over time.",
        "💰 Tip: Build a $1,000 emergency fund before investing.",
        "💰 Tip: The best time to start investing was yesterday. The second best is today.",
    ]
    
    def __init__(
        self,
        canvas_client=None,
        pomodoro_timer=None,
        assignment_tracker=None,
        notes_manager=None,
        weather_service=None,
        calendar_service=None,
        email_service=None,
        habit_tracker=None,
        application_tracker=None,
        finance_manager=None,
    ):
        """
        Initialize daily briefing.
        
        Args:
            canvas_client: Canvas LMS client
            pomodoro_timer: Pomodoro timer instance
            assignment_tracker: Assignment tracker instance
            notes_manager: Notes manager instance
            weather_service: Weather service (optional)
            calendar_service: Calendar service (optional)
            email_service: Email service (optional)
            habit_tracker: Habit tracker for streaks (optional)
            application_tracker: Job application tracker (optional)
            finance_manager: Finance manager for tips (optional)
        """
        self.canvas = canvas_client
        self.pomodoro = pomodoro_timer
        self.assignments = assignment_tracker
        self.notes = notes_manager
        self.weather = weather_service
        self.calendar = calendar_service
        self.email = email_service
        self.habits = habit_tracker
        self.applications = application_tracker
        self.finance = finance_manager
    
    def _get_greeting(self) -> str:
        """Get time-appropriate greeting."""
        hour = datetime.now().hour
        
        if hour < 12:
            return "Good morning"
        elif hour < 17:
            return "Good afternoon"
        else:
            return "Good evening"
    
    def _get_random_quote(self) -> str:
        """Get a random motivational quote."""
        import random
        return random.choice(self.MOTIVATIONAL_QUOTES)
    
    async def _get_weather(self) -> Optional[str]:
        """Get weather information."""
        if not self.weather:
            return None
        
        try:
            # Assuming weather service has a get_current method
            if hasattr(self.weather, 'get_current'):
                weather_data = await self.weather.get_current()
                if weather_data:
                    temp = weather_data.get('temperature', 'N/A')
                    condition = weather_data.get('condition', 'Unknown')
                    return f"{temp}°F, {condition}"
        except Exception as e:
            logger.error(f"Failed to get weather: {e}")
        
        return None
    
    async def _get_calendar_events(self) -> List[str]:
        """Get today's calendar events."""
        if not self.calendar:
            return []
        
        try:
            if hasattr(self.calendar, 'get_today_events'):
                events = await self.calendar.get_today_events()
                return [f"{e.get('time', '')} - {e.get('title', 'Event')}" for e in events]
        except Exception as e:
            logger.error(f"Failed to get calendar events: {e}")
        
        return []
    
    async def _get_canvas_assignments(self) -> tuple:
        """Get Canvas assignments."""
        due_today = []
        due_tomorrow = []
        due_week = []
        
        if not self.canvas:
            return due_today, due_tomorrow, due_week
        
        try:
            if self.canvas.is_configured:
                # Due today
                today_assignments = await self.canvas.get_assignments_due_today()
                due_today = [f"{a.name} ({a.course_name}) - {a.due_at.strftime('%I:%M %p')}" 
                            for a in today_assignments if a.due_at]
                
                # Due tomorrow
                tomorrow_assignments = await self.canvas.get_assignments_due_tomorrow()
                due_tomorrow = [f"{a.name} ({a.course_name})" for a in tomorrow_assignments]
                
                # Due this week (excluding today/tomorrow)
                week_assignments = await self.canvas.get_upcoming_assignments(days=7)
                for a in week_assignments:
                    if a.due_at and not a.is_due_today and not a.is_due_tomorrow:
                        due_week.append(f"{a.name} ({a.course_name}) - {a.due_at.strftime('%A')}")
        except Exception as e:
            logger.error(f"Failed to get Canvas assignments: {e}")
        
        return due_today, due_tomorrow, due_week
    
    async def _get_local_assignments(self) -> tuple:
        """Get local tracked assignments."""
        due_today = []
        due_tomorrow = []
        due_week = []
        
        if not self.assignments:
            return due_today, due_tomorrow, due_week
        
        try:
            # Due today
            today = self.assignments.get_due_today()
            due_today = [f"{a.name} ({a.course or 'No course'})" for a in today]
            
            # Due tomorrow
            tomorrow = self.assignments.get_due_tomorrow()
            due_tomorrow = [f"{a.name} ({a.course or 'No course'})" for a in tomorrow]
            
            # Due this week
            week = self.assignments.get_upcoming(days=7)
            for a in week:
                if not a.is_due_today and not a.is_due_tomorrow and a.due_date:
                    due_week.append(f"{a.name} - {a.due_date.strftime('%A')}")
        except Exception as e:
            logger.error(f"Failed to get local assignments: {e}")
        
        return due_today, due_tomorrow, due_week
    
    async def _get_unread_emails(self) -> int:
        """Get unread email count."""
        if not self.email:
            return 0
        
        try:
            if hasattr(self.email, 'get_unread_count'):
                return await self.email.get_unread_count()
        except Exception as e:
            logger.error(f"Failed to get unread emails: {e}")
        
        return 0
    
    def _get_study_stats(self) -> tuple:
        """Get today's study statistics."""
        if not self.pomodoro:
            return 0, 0
        
        try:
            stats = self.pomodoro.get_stats()
            return stats.today_minutes, stats.today_sessions
        except Exception as e:
            logger.error(f"Failed to get study stats: {e}")
        
        return 0, 0
    
    def _get_yesterday_study_time(self) -> int:
        """Get yesterday's study time in minutes."""
        if not self.pomodoro:
            return 0
        
        try:
            if hasattr(self.pomodoro, 'get_yesterday_stats'):
                stats = self.pomodoro.get_yesterday_stats()
                return stats.total_minutes if stats else 0
        except Exception as e:
            logger.debug(f"Failed to get yesterday stats: {e}")
        
        return 0
    
    def _get_habit_streaks(self) -> List[str]:
        """Get current habit streaks."""
        if not self.habits:
            return []
        
        try:
            if hasattr(self.habits, 'get_active_habits'):
                habits = self.habits.get_active_habits()
                streaks = []
                for habit in habits:
                    if hasattr(habit, 'current_streak') and habit.current_streak > 0:
                        streaks.append(f"{habit.name}: {habit.current_streak} days 🔥")
                return streaks
        except Exception as e:
            logger.debug(f"Failed to get habit streaks: {e}")
        
        return []
    
    def _get_application_updates(self) -> List[str]:
        """Get recent job application updates."""
        if not self.applications:
            return []
        
        try:
            updates = []
            
            # Check for applications needing follow-up
            if hasattr(self.applications, 'get_pending_followups'):
                followups = self.applications.get_pending_followups()
                for app in followups[:3]:
                    updates.append(f"📋 Follow up with {app.company}")
            
            # Check for upcoming deadlines
            if hasattr(self.applications, 'get_upcoming_deadlines'):
                deadlines = self.applications.get_upcoming_deadlines(days=7)
                for app in deadlines[:2]:
                    updates.append(f"⏰ {app.company} deadline approaching")
            
            return updates
        except Exception as e:
            logger.debug(f"Failed to get application updates: {e}")
        
        return []
    
    def _get_financial_tip(self) -> str:
        """Get a random financial tip."""
        import random
        return random.choice(self.FINANCIAL_TIPS)
    
    # =========================================================================
    # Briefings
    # =========================================================================
    
    async def get_morning_briefing(self, include_quote: bool = True, include_finance_tip: bool = True) -> str:
        """
        Generate comprehensive morning briefing.
        
        Args:
            include_quote: Include motivational quote
            include_finance_tip: Include financial tip
            
        Returns:
            Formatted briefing message
        """
        greeting = self._get_greeting()
        today = datetime.now()
        date_str = today.strftime("%A, %B %d")
        
        lines = [f"🌅 {greeting}! Here's your briefing for {date_str}:"]
        lines.append("")
        
        # Weather
        weather = await self._get_weather()
        if weather:
            lines.append(f"🌤️ **Weather:** {weather}")
        
        # Calendar
        events = await self._get_calendar_events()
        if events:
            lines.append("")
            lines.append(f"📅 **Today's Schedule:**")
            for event in events[:5]:
                lines.append(f"   • {event}")
        
        # Assignments
        canvas_today, canvas_tomorrow, canvas_week = await self._get_canvas_assignments()
        local_today, local_tomorrow, local_week = await self._get_local_assignments()
        
        # Combine and deduplicate
        all_today = list(set(canvas_today + local_today))
        all_tomorrow = list(set(canvas_tomorrow + local_tomorrow))
        all_week = list(set(canvas_week + local_week))
        
        if all_today:
            lines.append("")
            lines.append(f"🔴 **Due TODAY:**")
            for a in all_today:
                lines.append(f"   • {a}")
        
        if all_tomorrow:
            lines.append("")
            lines.append(f"🟡 **Due Tomorrow:**")
            for a in all_tomorrow:
                lines.append(f"   • {a}")
        
        if all_week:
            lines.append("")
            lines.append(f"📋 **This Week:**")
            for a in all_week[:5]:
                lines.append(f"   • {a}")
        
        # Emails
        unread = await self._get_unread_emails()
        if unread > 0:
            lines.append("")
            lines.append(f"📧 You have {unread} unread email{'s' if unread > 1 else ''}.")
        
        # Habit streaks
        streaks = self._get_habit_streaks()
        if streaks:
            lines.append("")
            lines.append(f"🔥 **Habit Streaks:**")
            for streak in streaks[:5]:
                lines.append(f"   • {streak}")
        
        # Yesterday's study time
        yesterday_minutes = self._get_yesterday_study_time()
        if yesterday_minutes > 0:
            hours = yesterday_minutes // 60
            mins = yesterday_minutes % 60
            time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins} minutes"
            lines.append("")
            lines.append(f"📚 Yesterday's study time: {time_str}")
        
        # Job application updates
        app_updates = self._get_application_updates()
        if app_updates:
            lines.append("")
            lines.append(f"💼 **Job Applications:**")
            for update in app_updates:
                lines.append(f"   • {update}")
        
        # Financial tip
        if include_finance_tip:
            lines.append("")
            lines.append(self._get_financial_tip())
        
        # Motivational quote
        if include_quote:
            lines.append("")
            lines.append(f"💡 \"{self._get_random_quote()}\"")
        
        lines.append("")
        lines.append("Have a productive day! 🚀")
        
        return "\n".join(lines)
    
    async def get_evening_summary(self) -> str:
        """
        Generate evening summary.
        
        Returns:
            Formatted summary message
        """
        today = datetime.now()
        date_str = today.strftime("%A, %B %d")
        
        lines = [f"📊 Day Summary for {date_str}:"]
        lines.append("")
        
        # Study stats
        study_minutes, pomodoros = self._get_study_stats()
        if study_minutes > 0:
            hours = study_minutes // 60
            mins = study_minutes % 60
            time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins} minutes"
            lines.append(f"📚 Study time: {time_str}")
            lines.append(f"🍅 Pomodoros completed: {pomodoros}")
        else:
            lines.append("📚 No study sessions recorded today.")
        
        # Notes taken
        if self.notes:
            try:
                recent = self.notes.get_recent(limit=100)
                today_notes = [n for n in recent if n.created_at.date() == today.date()]
                if today_notes:
                    lines.append(f"📝 Notes taken: {len(today_notes)}")
            except Exception:
                pass
        
        # Assignments completed (would need tracking)
        # TODO: Track completed assignments
        
        # Tomorrow preview
        lines.append("")
        lines.append("📅 Tomorrow:")
        
        canvas_today, canvas_tomorrow, _ = await self._get_canvas_assignments()
        local_today, local_tomorrow, _ = await self._get_local_assignments()
        all_tomorrow = list(set(canvas_tomorrow + local_tomorrow))
        
        if all_tomorrow:
            for a in all_tomorrow[:3]:
                lines.append(f"   • {a}")
        else:
            lines.append("   No assignments due tomorrow.")
        
        lines.append("")
        lines.append("Rest well! 🌙")
        
        return "\n".join(lines)
    
    async def get_quick_status(self) -> str:
        """
        Get a quick status update.
        
        Returns:
            Brief status message
        """
        canvas_today, canvas_tomorrow, _ = await self._get_canvas_assignments()
        local_today, local_tomorrow, _ = await self._get_local_assignments()
        
        all_today = list(set(canvas_today + local_today))
        all_tomorrow = list(set(canvas_tomorrow + local_tomorrow))
        
        parts = []
        
        if all_today:
            parts.append(f"{len(all_today)} due today")
        if all_tomorrow:
            parts.append(f"{len(all_tomorrow)} due tomorrow")
        
        # Study status
        if self.pomodoro and self.pomodoro.state.value != "idle":
            parts.append(self.pomodoro.get_status())
        
        if parts:
            return "Status: " + ", ".join(parts)
        else:
            return "All clear! No immediate deadlines."
    
    def format_day_overview(self) -> str:
        """Format a simple day overview (sync version for quick access)."""
        today = datetime.now()
        greeting = self._get_greeting()
        
        lines = [
            f"{greeting}!",
            f"Today is {today.strftime('%A, %B %d, %Y')}.",
        ]
        
        # Add study stats if available
        if self.pomodoro:
            stats = self.pomodoro.get_stats()
            if stats.today_sessions > 0:
                lines.append(f"You've completed {stats.today_sessions} pomodoros today.")
        
        return " ".join(lines)
