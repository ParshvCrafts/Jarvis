"""
Weekly Review Generator for JARVIS.

Automated weekly summary and reflection:
- Study time summary
- Assignments completed
- Projects worked on
- Learning highlights
- Habit completion
- Next week priorities
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class WeeklyStats:
    """Weekly statistics."""
    study_minutes: int = 0
    pomodoros_completed: int = 0
    assignments_completed: int = 0
    projects_worked_on: int = 0
    learning_entries: int = 0
    habits_completed: int = 0
    habits_total: int = 0
    code_snippets_used: int = 0
    focus_sessions: int = 0


class WeeklyReview:
    """
    Weekly review generator.
    
    Aggregates data from all productivity modules to generate
    comprehensive weekly summaries.
    
    Usage:
        review = WeeklyReview(pomodoro, journal, habits, projects)
        summary = review.generate()
    """
    
    def __init__(
        self,
        pomodoro_timer=None,
        learning_journal=None,
        habit_tracker=None,
        project_tracker=None,
        assignment_tracker=None,
        canvas_client=None,
    ):
        """
        Initialize weekly review.
        
        Args:
            pomodoro_timer: Pomodoro timer for study stats
            learning_journal: Learning journal for entries
            habit_tracker: Habit tracker for completion rates
            project_tracker: Project tracker for project stats
            assignment_tracker: Assignment tracker for completions
            canvas_client: Canvas client for assignment data
        """
        self.pomodoro = pomodoro_timer
        self.journal = learning_journal
        self.habits = habit_tracker
        self.projects = project_tracker
        self.assignments = assignment_tracker
        self.canvas = canvas_client
    
    def get_week_range(self) -> tuple:
        """Get current week's date range (Monday to Sunday)."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        return week_start, week_end
    
    def get_stats(self) -> WeeklyStats:
        """Gather weekly statistics from all sources."""
        stats = WeeklyStats()
        week_start, week_end = self.get_week_range()
        
        # Pomodoro stats
        if self.pomodoro:
            try:
                pomo_stats = self.pomodoro.get_stats()
                stats.study_minutes = pomo_stats.week_minutes
                stats.pomodoros_completed = pomo_stats.week_sessions
            except Exception as e:
                logger.debug(f"Failed to get pomodoro stats: {e}")
        
        # Learning journal entries
        if self.journal:
            try:
                entries = self.journal.get_this_week()
                stats.learning_entries = len(entries)
            except Exception as e:
                logger.debug(f"Failed to get journal entries: {e}")
        
        # Habit completion
        if self.habits:
            try:
                habits = self.habits.get_all_habits()
                stats.habits_total = len(habits) * 7  # Assuming daily habits
                
                # Count completions this week
                for habit in habits:
                    habit_stats = self.habits.get_stats(habit.name)
                    if habit_stats:
                        # Simplified: count based on streak
                        stats.habits_completed += min(7, habit_stats.current_streak)
            except Exception as e:
                logger.debug(f"Failed to get habit stats: {e}")
        
        # Projects worked on
        if self.projects:
            try:
                projects = self.projects.get_all()
                for project in projects:
                    time_this_week = self.projects.get_time_this_week(project.id)
                    if time_this_week > 0:
                        stats.projects_worked_on += 1
            except Exception as e:
                logger.debug(f"Failed to get project stats: {e}")
        
        # Assignments completed
        if self.assignments:
            try:
                # This would need a method to get completed assignments this week
                pass
            except Exception as e:
                logger.debug(f"Failed to get assignment stats: {e}")
        
        return stats
    
    def generate(self, include_details: bool = True) -> str:
        """
        Generate weekly review.
        
        Args:
            include_details: Include detailed breakdowns
            
        Returns:
            Formatted weekly review
        """
        week_start, week_end = self.get_week_range()
        stats = self.get_stats()
        
        lines = [
            "📊 Weekly Review",
            f"Week of {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}",
            "=" * 50,
            "",
        ]
        
        # Study Time
        hours = stats.study_minutes // 60
        mins = stats.study_minutes % 60
        lines.append("📚 **Study Time**")
        lines.append(f"   Total: {hours}h {mins}m")
        lines.append(f"   Pomodoros: {stats.pomodoros_completed} sessions")
        lines.append("")
        
        # Learning
        lines.append("🧠 **Learning**")
        lines.append(f"   Journal entries: {stats.learning_entries}")
        
        if include_details and self.journal:
            try:
                entries = self.journal.get_this_week()
                if entries:
                    subjects = {}
                    for e in entries:
                        subjects[e.subject] = subjects.get(e.subject, 0) + 1
                    
                    lines.append("   Topics covered:")
                    for subject, count in sorted(subjects.items(), key=lambda x: -x[1])[:5]:
                        lines.append(f"     • {subject}: {count} entries")
            except Exception:
                pass
        lines.append("")
        
        # Habits
        if stats.habits_total > 0:
            completion_rate = (stats.habits_completed / stats.habits_total) * 100
            lines.append("✅ **Habits**")
            lines.append(f"   Completion: {stats.habits_completed}/{stats.habits_total} ({completion_rate:.0f}%)")
            
            if include_details and self.habits:
                try:
                    habits = self.habits.get_all_habits()
                    for habit in habits[:5]:
                        streak = self.habits.get_streak(habit.name)
                        lines.append(f"     • {habit.name}: {streak} day streak 🔥")
                except Exception:
                    pass
            lines.append("")
        
        # Projects
        if stats.projects_worked_on > 0:
            lines.append("🚀 **Projects**")
            lines.append(f"   Active projects: {stats.projects_worked_on}")
            
            if include_details and self.projects:
                try:
                    projects = self.projects.get_all()
                    for project in projects:
                        time_this_week = self.projects.get_time_this_week(project.id)
                        if time_this_week > 0:
                            h = time_this_week // 60
                            m = time_this_week % 60
                            lines.append(f"     • {project.name}: {h}h {m}m")
                except Exception:
                    pass
            lines.append("")
        
        # Achievements
        lines.append("🏆 **Achievements**")
        achievements = self._get_achievements(stats)
        if achievements:
            for achievement in achievements:
                lines.append(f"   {achievement}")
        else:
            lines.append("   Keep working towards your goals!")
        lines.append("")
        
        # Areas for improvement
        lines.append("📈 **Areas for Improvement**")
        improvements = self._get_improvements(stats)
        for improvement in improvements:
            lines.append(f"   • {improvement}")
        lines.append("")
        
        # Next week priorities
        lines.append("🎯 **Next Week Priorities**")
        priorities = self._get_priorities()
        for priority in priorities:
            lines.append(f"   • {priority}")
        
        return "\n".join(lines)
    
    def _get_achievements(self, stats: WeeklyStats) -> List[str]:
        """Get achievements based on stats."""
        achievements = []
        
        if stats.study_minutes >= 1200:  # 20+ hours
            achievements.append("🌟 Study Champion: 20+ hours of focused study!")
        elif stats.study_minutes >= 600:  # 10+ hours
            achievements.append("⭐ Dedicated Learner: 10+ hours of study!")
        
        if stats.pomodoros_completed >= 20:
            achievements.append("🍅 Pomodoro Master: 20+ sessions completed!")
        
        if stats.learning_entries >= 7:
            achievements.append("📝 Daily Learner: Logged learning every day!")
        
        if stats.habits_total > 0:
            rate = stats.habits_completed / stats.habits_total
            if rate >= 0.9:
                achievements.append("💪 Habit Hero: 90%+ habit completion!")
            elif rate >= 0.7:
                achievements.append("👍 Habit Builder: 70%+ habit completion!")
        
        return achievements
    
    def _get_improvements(self, stats: WeeklyStats) -> List[str]:
        """Get areas for improvement."""
        improvements = []
        
        if stats.study_minutes < 300:  # Less than 5 hours
            improvements.append("Increase study time - aim for at least 1 hour daily")
        
        if stats.learning_entries < 3:
            improvements.append("Log your learning more often - helps retention!")
        
        if stats.habits_total > 0:
            rate = stats.habits_completed / stats.habits_total
            if rate < 0.5:
                improvements.append("Focus on building consistent habits")
        
        if not improvements:
            improvements.append("Keep up the great work! Consider setting stretch goals.")
        
        return improvements
    
    def _get_priorities(self) -> List[str]:
        """Get suggested priorities for next week."""
        priorities = []
        
        # Check for upcoming deadlines
        if self.canvas:
            try:
                # Would check for assignments due next week
                priorities.append("Review upcoming assignment deadlines")
            except Exception:
                pass
        
        if self.assignments:
            try:
                upcoming = self.assignments.get_upcoming(days=7)
                if upcoming:
                    priorities.append(f"Complete {len(upcoming)} upcoming assignments")
            except Exception:
                pass
        
        # Default priorities
        if not priorities:
            priorities = [
                "Set specific study goals for each day",
                "Maintain habit streaks",
                "Review and consolidate this week's learning",
            ]
        
        return priorities[:5]
    
    def compare_to_last_week(self) -> str:
        """Compare this week to last week."""
        # This would require storing historical data
        # For now, return a placeholder
        return "📊 Week-over-week comparison coming soon!"
