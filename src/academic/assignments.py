"""
Assignment Tracker for JARVIS.

Provides local assignment tracking beyond Canvas:
- Manual assignment creation
- Priority levels
- Custom reminders
- Completion tracking
- Integration with Canvas assignments
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional

from loguru import logger


class Priority(str, Enum):
    """Assignment priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AssignmentType(str, Enum):
    """Assignment types."""
    HOMEWORK = "homework"
    PROJECT = "project"
    EXAM = "exam"
    READING = "reading"
    LAB = "lab"
    QUIZ = "quiz"
    OTHER = "other"


@dataclass
class TrackedAssignment:
    """A tracked assignment (local or from Canvas)."""
    id: Optional[int] = None
    name: str = ""
    course: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Priority = Priority.MEDIUM
    assignment_type: AssignmentType = AssignmentType.HOMEWORK
    description: Optional[str] = None
    estimated_hours: Optional[float] = None
    completed: bool = False
    completed_at: Optional[datetime] = None
    canvas_id: Optional[int] = None  # Link to Canvas assignment
    created_at: datetime = field(default_factory=datetime.now)
    reminder_sent: bool = False
    
    @property
    def is_due_today(self) -> bool:
        if not self.due_date:
            return False
        return self.due_date.date() == datetime.now().date()
    
    @property
    def is_due_tomorrow(self) -> bool:
        if not self.due_date:
            return False
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        return self.due_date.date() == tomorrow
    
    @property
    def is_overdue(self) -> bool:
        if not self.due_date or self.completed:
            return False
        return datetime.now() > self.due_date
    
    @property
    def days_until_due(self) -> Optional[int]:
        if not self.due_date:
            return None
        delta = self.due_date.date() - datetime.now().date()
        return delta.days
    
    @property
    def urgency_score(self) -> float:
        """Calculate urgency score for sorting (higher = more urgent)."""
        if self.completed:
            return -1000
        
        score = 0
        
        # Priority weight
        priority_weights = {Priority.HIGH: 30, Priority.MEDIUM: 15, Priority.LOW: 5}
        score += priority_weights.get(self.priority, 15)
        
        # Due date weight (closer = higher score)
        if self.due_date:
            days = self.days_until_due or 0
            if days < 0:  # Overdue
                score += 100 + abs(days) * 10
            elif days == 0:  # Today
                score += 80
            elif days == 1:  # Tomorrow
                score += 60
            elif days <= 3:
                score += 40
            elif days <= 7:
                score += 20
        
        # Type weight (exams more urgent)
        type_weights = {
            AssignmentType.EXAM: 20,
            AssignmentType.PROJECT: 15,
            AssignmentType.QUIZ: 10,
            AssignmentType.HOMEWORK: 5,
            AssignmentType.LAB: 5,
            AssignmentType.READING: 2,
        }
        score += type_weights.get(self.assignment_type, 5)
        
        return score
    
    def __str__(self) -> str:
        status = "✓ " if self.completed else ""
        due_str = self.due_date.strftime("%b %d") if self.due_date else "No due date"
        course_str = f" ({self.course})" if self.course else ""
        return f"{status}{self.name}{course_str} - Due: {due_str}"


class AssignmentTracker:
    """
    Local assignment tracker with Canvas integration.
    
    Usage:
        tracker = AssignmentTracker()
        tracker.add("ML Project", course="CS 189", due_date=datetime(...), priority=Priority.HIGH)
        urgent = tracker.get_urgent()
        tracker.mark_complete(assignment_id)
    """
    
    def __init__(self, db_path: str = "data/assignments.db"):
        """
        Initialize assignment tracker.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    course TEXT,
                    due_date TIMESTAMP,
                    priority TEXT DEFAULT 'medium',
                    assignment_type TEXT DEFAULT 'homework',
                    description TEXT,
                    estimated_hours REAL,
                    completed BOOLEAN DEFAULT FALSE,
                    completed_at TIMESTAMP,
                    canvas_id INTEGER,
                    created_at TIMESTAMP NOT NULL,
                    reminder_sent BOOLEAN DEFAULT FALSE,
                    UNIQUE(canvas_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_assignments_due 
                ON assignments(due_date)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_assignments_course 
                ON assignments(course)
            """)
            conn.commit()
    
    # =========================================================================
    # CRUD Operations
    # =========================================================================
    
    def add(
        self,
        name: str,
        course: Optional[str] = None,
        due_date: Optional[datetime] = None,
        priority: Priority = Priority.MEDIUM,
        assignment_type: AssignmentType = AssignmentType.HOMEWORK,
        description: Optional[str] = None,
        estimated_hours: Optional[float] = None,
        canvas_id: Optional[int] = None,
    ) -> TrackedAssignment:
        """
        Add a new assignment.
        
        Args:
            name: Assignment name
            course: Course name
            due_date: Due date
            priority: Priority level
            assignment_type: Type of assignment
            description: Optional description
            estimated_hours: Estimated time to complete
            canvas_id: Canvas assignment ID (for sync)
            
        Returns:
            Created assignment
        """
        assignment = TrackedAssignment(
            name=name,
            course=course,
            due_date=due_date,
            priority=priority,
            assignment_type=assignment_type,
            description=description,
            estimated_hours=estimated_hours,
            canvas_id=canvas_id,
            created_at=datetime.now(),
        )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO assignments 
                (name, course, due_date, priority, assignment_type, description, 
                 estimated_hours, canvas_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                assignment.name,
                assignment.course,
                assignment.due_date.isoformat() if assignment.due_date else None,
                assignment.priority.value,
                assignment.assignment_type.value,
                assignment.description,
                assignment.estimated_hours,
                assignment.canvas_id,
                assignment.created_at.isoformat(),
            ))
            assignment.id = cursor.lastrowid
            conn.commit()
        
        logger.info(f"Added assignment: {assignment.name}")
        return assignment
    
    def get(self, assignment_id: int) -> Optional[TrackedAssignment]:
        """Get assignment by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM assignments WHERE id = ?", (assignment_id,)
            ).fetchone()
            
            if row:
                return self._row_to_assignment(row)
        return None
    
    def get_by_canvas_id(self, canvas_id: int) -> Optional[TrackedAssignment]:
        """Get assignment by Canvas ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM assignments WHERE canvas_id = ?", (canvas_id,)
            ).fetchone()
            
            if row:
                return self._row_to_assignment(row)
        return None
    
    def update(
        self,
        assignment_id: int,
        **kwargs,
    ) -> bool:
        """Update an assignment."""
        assignment = self.get(assignment_id)
        if not assignment:
            return False
        
        # Build update query
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if hasattr(assignment, key):
                if key == "due_date" and value:
                    value = value.isoformat()
                elif key == "priority" and isinstance(value, Priority):
                    value = value.value
                elif key == "assignment_type" and isinstance(value, AssignmentType):
                    value = value.value
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(assignment_id)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"UPDATE assignments SET {', '.join(updates)} WHERE id = ?",
                values
            )
            conn.commit()
        
        return True
    
    def delete(self, assignment_id: int) -> bool:
        """Delete an assignment."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM assignments WHERE id = ?", (assignment_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def mark_complete(self, assignment_id: int) -> bool:
        """Mark an assignment as complete."""
        return self.update(
            assignment_id,
            completed=True,
            completed_at=datetime.now().isoformat(),
        )
    
    def mark_incomplete(self, assignment_id: int) -> bool:
        """Mark an assignment as incomplete."""
        return self.update(
            assignment_id,
            completed=False,
            completed_at=None,
        )
    
    # =========================================================================
    # Query Operations
    # =========================================================================
    
    def get_all(self, include_completed: bool = False) -> List[TrackedAssignment]:
        """Get all assignments."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if include_completed:
                rows = conn.execute(
                    "SELECT * FROM assignments ORDER BY due_date"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM assignments WHERE completed = FALSE ORDER BY due_date"
                ).fetchall()
            
            return [self._row_to_assignment(row) for row in rows]
    
    def get_upcoming(self, days: int = 7) -> List[TrackedAssignment]:
        """Get assignments due in the next N days."""
        cutoff = datetime.now() + timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM assignments 
                WHERE completed = FALSE 
                AND due_date IS NOT NULL 
                AND due_date <= ?
                ORDER BY due_date
            """, (cutoff.isoformat(),)).fetchall()
            
            return [self._row_to_assignment(row) for row in rows]
    
    def get_due_today(self) -> List[TrackedAssignment]:
        """Get assignments due today."""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM assignments 
                WHERE completed = FALSE 
                AND due_date >= ? AND due_date < ?
                ORDER BY due_date
            """, (today_start.isoformat(), today_end.isoformat())).fetchall()
            
            return [self._row_to_assignment(row) for row in rows]
    
    def get_due_tomorrow(self) -> List[TrackedAssignment]:
        """Get assignments due tomorrow."""
        tomorrow_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        tomorrow_end = tomorrow_start + timedelta(days=1)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM assignments 
                WHERE completed = FALSE 
                AND due_date >= ? AND due_date < ?
                ORDER BY due_date
            """, (tomorrow_start.isoformat(), tomorrow_end.isoformat())).fetchall()
            
            return [self._row_to_assignment(row) for row in rows]
    
    def get_overdue(self) -> List[TrackedAssignment]:
        """Get overdue assignments."""
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM assignments 
                WHERE completed = FALSE 
                AND due_date IS NOT NULL 
                AND due_date < ?
                ORDER BY due_date
            """, (now.isoformat(),)).fetchall()
            
            return [self._row_to_assignment(row) for row in rows]
    
    def get_urgent(self, limit: int = 5) -> List[TrackedAssignment]:
        """Get most urgent assignments sorted by urgency score."""
        assignments = self.get_all(include_completed=False)
        assignments.sort(key=lambda a: a.urgency_score, reverse=True)
        return assignments[:limit]
    
    def get_by_course(self, course: str) -> List[TrackedAssignment]:
        """Get assignments for a specific course."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM assignments 
                WHERE course LIKE ? AND completed = FALSE
                ORDER BY due_date
            """, (f"%{course}%",)).fetchall()
            
            return [self._row_to_assignment(row) for row in rows]
    
    def get_by_type(self, assignment_type: AssignmentType) -> List[TrackedAssignment]:
        """Get assignments by type."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM assignments 
                WHERE assignment_type = ? AND completed = FALSE
                ORDER BY due_date
            """, (assignment_type.value,)).fetchall()
            
            return [self._row_to_assignment(row) for row in rows]
    
    def get_exams(self) -> List[TrackedAssignment]:
        """Get upcoming exams."""
        return self.get_by_type(AssignmentType.EXAM)
    
    def get_needing_reminder(self, hours_before: int = 24) -> List[TrackedAssignment]:
        """Get assignments that need a reminder."""
        cutoff = datetime.now() + timedelta(hours=hours_before)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM assignments 
                WHERE completed = FALSE 
                AND reminder_sent = FALSE
                AND due_date IS NOT NULL 
                AND due_date <= ?
                AND due_date > ?
                ORDER BY due_date
            """, (cutoff.isoformat(), datetime.now().isoformat())).fetchall()
            
            return [self._row_to_assignment(row) for row in rows]
    
    def mark_reminder_sent(self, assignment_id: int) -> bool:
        """Mark reminder as sent for an assignment."""
        return self.update(assignment_id, reminder_sent=True)
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def get_stats(self) -> dict:
        """Get assignment statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM assignments").fetchone()[0]
            completed = conn.execute(
                "SELECT COUNT(*) FROM assignments WHERE completed = TRUE"
            ).fetchone()[0]
            pending = total - completed
            overdue = len(self.get_overdue())
            due_today = len(self.get_due_today())
            due_week = len(self.get_upcoming(days=7))
            
            return {
                "total": total,
                "completed": completed,
                "pending": pending,
                "overdue": overdue,
                "due_today": due_today,
                "due_this_week": due_week,
                "completion_rate": (completed / total * 100) if total > 0 else 0,
            }
    
    # =========================================================================
    # Formatting
    # =========================================================================
    
    def format_assignments(
        self,
        assignments: List[TrackedAssignment],
        include_course: bool = True,
    ) -> str:
        """Format assignments as readable string."""
        if not assignments:
            return "No assignments found."
        
        lines = []
        for a in assignments:
            status = "✓ " if a.completed else ""
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(a.priority.value, "")
            
            if a.due_date:
                if a.is_due_today:
                    due_str = f"TODAY at {a.due_date.strftime('%I:%M %p')}"
                elif a.is_due_tomorrow:
                    due_str = f"Tomorrow"
                elif a.is_overdue:
                    due_str = f"OVERDUE ({a.due_date.strftime('%b %d')})"
                else:
                    due_str = a.due_date.strftime("%A, %b %d")
            else:
                due_str = "No due date"
            
            course_str = f" ({a.course})" if include_course and a.course else ""
            lines.append(f"• {status}{priority_icon} {a.name}{course_str} - {due_str}")
        
        return "\n".join(lines)
    
    def _row_to_assignment(self, row: sqlite3.Row) -> TrackedAssignment:
        """Convert database row to TrackedAssignment object."""
        return TrackedAssignment(
            id=row["id"],
            name=row["name"],
            course=row["course"],
            due_date=datetime.fromisoformat(row["due_date"]) if row["due_date"] else None,
            priority=Priority(row["priority"]) if row["priority"] else Priority.MEDIUM,
            assignment_type=AssignmentType(row["assignment_type"]) if row["assignment_type"] else AssignmentType.HOMEWORK,
            description=row["description"],
            estimated_hours=row["estimated_hours"],
            completed=bool(row["completed"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            canvas_id=row["canvas_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            reminder_sent=bool(row["reminder_sent"]),
        )
