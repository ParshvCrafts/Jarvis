"""
Smart Study Planner for JARVIS.

AI-suggested study schedule based on:
- Upcoming assignments and due dates
- Task difficulty and time estimates
- Available time slots
- Energy patterns
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, date, time
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from loguru import logger


class Priority(str, Enum):
    """Task priority levels."""
    URGENT = "urgent"      # Due within 24 hours
    HIGH = "high"          # Due within 3 days
    MEDIUM = "medium"      # Due within 7 days
    LOW = "low"            # Due later


class Difficulty(str, Enum):
    """Task difficulty levels."""
    EASY = "easy"          # ~30 min
    MEDIUM = "medium"      # ~1-2 hours
    HARD = "hard"          # ~3-4 hours
    COMPLEX = "complex"    # Multiple sessions


@dataclass
class StudyTask:
    """A task to study/complete."""
    name: str
    course: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Priority = Priority.MEDIUM
    difficulty: Difficulty = Difficulty.MEDIUM
    estimated_minutes: int = 60
    completed: bool = False
    source: str = "manual"  # manual, canvas, assignment_tracker
    
    @property
    def urgency_score(self) -> float:
        """Calculate urgency score (higher = more urgent)."""
        if not self.due_date:
            return 0.0
        
        hours_until = (self.due_date - datetime.now()).total_seconds() / 3600
        
        if hours_until <= 0:
            return 100.0  # Overdue
        elif hours_until <= 24:
            return 90.0 + (24 - hours_until) / 24 * 10
        elif hours_until <= 72:
            return 70.0 + (72 - hours_until) / 72 * 20
        elif hours_until <= 168:  # 1 week
            return 40.0 + (168 - hours_until) / 168 * 30
        else:
            return max(0, 40 - hours_until / 168 * 10)


@dataclass
class StudyBlock:
    """A scheduled study block."""
    task: StudyTask
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    notes: Optional[str] = None
    
    def __str__(self) -> str:
        start_str = self.start_time.strftime("%I:%M %p")
        end_str = self.end_time.strftime("%I:%M %p")
        return f"{start_str} - {end_str}: {self.task.name}"


@dataclass
class TimeSlot:
    """An available time slot."""
    start: datetime
    end: datetime
    
    @property
    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() / 60)


class StudyPlanner:
    """
    Smart study planner that generates optimal study schedules.
    
    Usage:
        planner = StudyPlanner()
        planner.add_task("Data 8 Homework", due_date=..., difficulty=Difficulty.MEDIUM)
        schedule = planner.generate_schedule(available_hours=4)
    """
    
    # Default time estimates by difficulty (minutes)
    DIFFICULTY_ESTIMATES = {
        Difficulty.EASY: 30,
        Difficulty.MEDIUM: 90,
        Difficulty.HARD: 180,
        Difficulty.COMPLEX: 300,
    }
    
    # Peak productivity hours (for scheduling hard tasks)
    PEAK_HOURS = [(9, 12), (14, 17)]  # 9am-12pm, 2pm-5pm
    
    def __init__(
        self,
        canvas_client=None,
        assignment_tracker=None,
        calendar_service=None,
    ):
        """
        Initialize study planner.
        
        Args:
            canvas_client: Canvas LMS client for fetching assignments
            assignment_tracker: Local assignment tracker
            calendar_service: Calendar service for busy times
        """
        self.canvas = canvas_client
        self.assignments = assignment_tracker
        self.calendar = calendar_service
        
        self.tasks: List[StudyTask] = []
        self.schedule: List[StudyBlock] = []
    
    def add_task(
        self,
        name: str,
        course: Optional[str] = None,
        due_date: Optional[datetime] = None,
        difficulty: Difficulty = Difficulty.MEDIUM,
        estimated_minutes: Optional[int] = None,
    ) -> StudyTask:
        """Add a task to the planner."""
        task = StudyTask(
            name=name,
            course=course,
            due_date=due_date,
            difficulty=difficulty,
            estimated_minutes=estimated_minutes or self.DIFFICULTY_ESTIMATES[difficulty],
            source="manual",
        )
        
        # Calculate priority based on due date
        if due_date:
            hours_until = (due_date - datetime.now()).total_seconds() / 3600
            if hours_until <= 24:
                task.priority = Priority.URGENT
            elif hours_until <= 72:
                task.priority = Priority.HIGH
            elif hours_until <= 168:
                task.priority = Priority.MEDIUM
            else:
                task.priority = Priority.LOW
        
        self.tasks.append(task)
        return task
    
    async def fetch_canvas_tasks(self, days: int = 7) -> List[StudyTask]:
        """Fetch tasks from Canvas."""
        if not self.canvas or not self.canvas.is_configured:
            return []
        
        try:
            assignments = await self.canvas.get_upcoming_assignments(days=days)
            tasks = []
            
            for a in assignments:
                # Estimate difficulty based on points
                if a.points_possible >= 100:
                    difficulty = Difficulty.COMPLEX
                elif a.points_possible >= 50:
                    difficulty = Difficulty.HARD
                elif a.points_possible >= 20:
                    difficulty = Difficulty.MEDIUM
                else:
                    difficulty = Difficulty.EASY
                
                task = StudyTask(
                    name=a.name,
                    course=a.course_name,
                    due_date=a.due_at,
                    difficulty=difficulty,
                    estimated_minutes=self.DIFFICULTY_ESTIMATES[difficulty],
                    source="canvas",
                )
                tasks.append(task)
            
            self.tasks.extend(tasks)
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to fetch Canvas tasks: {e}")
            return []
    
    def fetch_local_tasks(self, days: int = 7) -> List[StudyTask]:
        """Fetch tasks from local assignment tracker."""
        if not self.assignments:
            return []
        
        try:
            assignments = self.assignments.get_upcoming(days=days)
            tasks = []
            
            for a in assignments:
                task = StudyTask(
                    name=a.name,
                    course=a.course,
                    due_date=a.due_date,
                    difficulty=Difficulty.MEDIUM,
                    estimated_minutes=60,
                    source="assignment_tracker",
                )
                tasks.append(task)
            
            self.tasks.extend(tasks)
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to fetch local tasks: {e}")
            return []
    
    def get_prioritized_tasks(self) -> List[StudyTask]:
        """Get tasks sorted by urgency."""
        incomplete = [t for t in self.tasks if not t.completed]
        return sorted(incomplete, key=lambda t: -t.urgency_score)
    
    def generate_schedule(
        self,
        available_minutes: int = 240,
        start_time: Optional[datetime] = None,
        prefer_peak_hours: bool = True,
    ) -> List[StudyBlock]:
        """
        Generate an optimal study schedule.
        
        Args:
            available_minutes: Total available study time
            start_time: When to start (default: now)
            prefer_peak_hours: Schedule hard tasks during peak hours
            
        Returns:
            List of scheduled study blocks
        """
        start_time = start_time or datetime.now()
        tasks = self.get_prioritized_tasks()
        
        if not tasks:
            return []
        
        schedule = []
        remaining_minutes = available_minutes
        current_time = start_time
        
        # Separate tasks by difficulty for peak hour scheduling
        hard_tasks = [t for t in tasks if t.difficulty in (Difficulty.HARD, Difficulty.COMPLEX)]
        other_tasks = [t for t in tasks if t.difficulty not in (Difficulty.HARD, Difficulty.COMPLEX)]
        
        # Schedule hard tasks first if in peak hours
        if prefer_peak_hours and self._is_peak_hour(current_time.hour):
            for task in hard_tasks:
                if remaining_minutes < 30:
                    break
                
                duration = min(task.estimated_minutes, remaining_minutes, 120)  # Max 2 hour blocks
                
                block = StudyBlock(
                    task=task,
                    start_time=current_time,
                    end_time=current_time + timedelta(minutes=duration),
                    duration_minutes=duration,
                )
                schedule.append(block)
                
                current_time += timedelta(minutes=duration + 10)  # 10 min break
                remaining_minutes -= duration + 10
        
        # Schedule remaining tasks
        for task in (other_tasks + [t for t in hard_tasks if not any(b.task == t for b in schedule)]):
            if remaining_minutes < 30:
                break
            
            duration = min(task.estimated_minutes, remaining_minutes, 90)  # Max 90 min blocks
            
            block = StudyBlock(
                task=task,
                start_time=current_time,
                end_time=current_time + timedelta(minutes=duration),
                duration_minutes=duration,
            )
            schedule.append(block)
            
            current_time += timedelta(minutes=duration + 5)  # 5 min break
            remaining_minutes -= duration + 5
        
        self.schedule = schedule
        return schedule
    
    def suggest_next_task(self) -> Optional[StudyTask]:
        """Suggest what to work on next."""
        tasks = self.get_prioritized_tasks()
        
        if not tasks:
            return None
        
        # Consider current time for peak hours
        current_hour = datetime.now().hour
        
        if self._is_peak_hour(current_hour):
            # Suggest hard task during peak hours
            hard_tasks = [t for t in tasks if t.difficulty in (Difficulty.HARD, Difficulty.COMPLEX)]
            if hard_tasks:
                return hard_tasks[0]
        
        return tasks[0]
    
    def suggest_for_duration(self, available_minutes: int) -> List[StudyTask]:
        """Suggest tasks that fit within available time."""
        tasks = self.get_prioritized_tasks()
        suggestions = []
        remaining = available_minutes
        
        for task in tasks:
            if task.estimated_minutes <= remaining:
                suggestions.append(task)
                remaining -= task.estimated_minutes
            
            if remaining < 30:
                break
        
        return suggestions
    
    def _is_peak_hour(self, hour: int) -> bool:
        """Check if hour is during peak productivity."""
        for start, end in self.PEAK_HOURS:
            if start <= hour < end:
                return True
        return False
    
    def format_schedule(self, schedule: Optional[List[StudyBlock]] = None) -> str:
        """Format schedule for display."""
        schedule = schedule or self.schedule
        
        if not schedule:
            return "No study blocks scheduled. Add tasks and generate a schedule."
        
        lines = ["📅 Study Schedule", ""]
        
        total_minutes = 0
        for block in schedule:
            start_str = block.start_time.strftime("%I:%M %p")
            end_str = block.end_time.strftime("%I:%M %p")
            
            priority_icon = {
                Priority.URGENT: "🔴",
                Priority.HIGH: "🟠",
                Priority.MEDIUM: "🟡",
                Priority.LOW: "🟢",
            }.get(block.task.priority, "⚪")
            
            course_str = f" ({block.task.course})" if block.task.course else ""
            lines.append(f"{priority_icon} {start_str} - {end_str}")
            lines.append(f"   {block.task.name}{course_str}")
            lines.append(f"   ⏱️ {block.duration_minutes} min | {block.task.difficulty.value}")
            lines.append("")
            
            total_minutes += block.duration_minutes
        
        hours = total_minutes // 60
        mins = total_minutes % 60
        lines.append(f"📊 Total: {hours}h {mins}m of focused study")
        
        return "\n".join(lines)
    
    def format_suggestion(self, task: Optional[StudyTask] = None) -> str:
        """Format task suggestion for display."""
        task = task or self.suggest_next_task()
        
        if not task:
            return "No tasks to work on! You're all caught up. 🎉"
        
        lines = ["💡 Suggested Task", ""]
        
        priority_icon = {
            Priority.URGENT: "🔴 URGENT",
            Priority.HIGH: "🟠 High Priority",
            Priority.MEDIUM: "🟡 Medium Priority",
            Priority.LOW: "🟢 Low Priority",
        }.get(task.priority, "")
        
        lines.append(f"**{task.name}**")
        if task.course:
            lines.append(f"Course: {task.course}")
        lines.append(f"Priority: {priority_icon}")
        lines.append(f"Difficulty: {task.difficulty.value}")
        lines.append(f"Estimated time: {task.estimated_minutes} minutes")
        
        if task.due_date:
            due_str = task.due_date.strftime("%b %d, %I:%M %p")
            hours_until = (task.due_date - datetime.now()).total_seconds() / 3600
            if hours_until < 24:
                lines.append(f"⚠️ Due: {due_str} ({int(hours_until)} hours left!)")
            else:
                lines.append(f"Due: {due_str}")
        
        return "\n".join(lines)
    
    def clear_tasks(self):
        """Clear all tasks."""
        self.tasks = []
        self.schedule = []
