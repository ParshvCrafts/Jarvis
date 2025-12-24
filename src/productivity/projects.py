"""
Project Tracker for JARVIS.

Manage coding projects beyond assignments:
- Project creation and tracking
- Milestones and tasks
- Time logging
- GitHub integration
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

from loguru import logger


class ProjectStatus(str, Enum):
    """Project status."""
    IDEA = "idea"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class Milestone:
    """A project milestone."""
    id: Optional[int] = None
    project_id: int = 0
    name: str = ""
    description: Optional[str] = None
    completed: bool = False
    completed_at: Optional[datetime] = None
    due_date: Optional[date] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        status = "✅" if self.completed else "⬜"
        return f"{status} {self.name}"


@dataclass
class TimeLog:
    """A time log entry for a project."""
    id: Optional[int] = None
    project_id: int = 0
    duration_minutes: int = 0
    date: date = field(default_factory=date.today)
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Project:
    """A coding project."""
    id: Optional[int] = None
    name: str = ""
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.IDEA
    github_url: Optional[str] = None
    start_date: Optional[date] = None
    target_date: Optional[date] = None
    technologies: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Loaded separately
    milestones: List[Milestone] = field(default_factory=list)
    total_time_minutes: int = 0
    
    @property
    def status_emoji(self) -> str:
        """Get emoji for status."""
        emojis = {
            ProjectStatus.IDEA: "💡",
            ProjectStatus.PLANNING: "📋",
            ProjectStatus.IN_PROGRESS: "🚀",
            ProjectStatus.PAUSED: "⏸️",
            ProjectStatus.COMPLETED: "✅",
            ProjectStatus.ARCHIVED: "📦",
        }
        return emojis.get(self.status, "📁")
    
    @property
    def progress(self) -> float:
        """Calculate progress based on milestones."""
        if not self.milestones:
            return 0.0
        completed = sum(1 for m in self.milestones if m.completed)
        return completed / len(self.milestones)
    
    def __str__(self) -> str:
        return f"{self.status_emoji} {self.name} ({self.status.value})"


class ProjectTracker:
    """
    Project tracking system.
    
    Usage:
        tracker = ProjectTracker()
        project = tracker.create("Sentiment Analysis App", technologies=["Python", "NLTK"])
        tracker.add_milestone(project.id, "Data collection")
        tracker.log_time(project.id, 120, "Worked on preprocessing")
    """
    
    def __init__(self, db_path: str = "data/projects.db"):
        """
        Initialize project tracker.
        
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
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'idea',
                    github_url TEXT,
                    start_date DATE,
                    target_date DATE,
                    technologies TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_milestones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    completed BOOLEAN DEFAULT FALSE,
                    completed_at TIMESTAMP,
                    due_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_time_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    date DATE NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_milestones_project 
                ON project_milestones(project_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_time_logs_project 
                ON project_time_logs(project_id)
            """)
            conn.commit()
    
    def create(
        self,
        name: str,
        description: Optional[str] = None,
        github_url: Optional[str] = None,
        technologies: Optional[List[str]] = None,
        target_date: Optional[date] = None,
    ) -> Project:
        """
        Create a new project.
        
        Args:
            name: Project name
            description: Project description
            github_url: GitHub repository URL
            technologies: List of technologies used
            target_date: Target completion date
            
        Returns:
            Created project
        """
        project = Project(
            name=name,
            description=description,
            status=ProjectStatus.IDEA,
            github_url=github_url,
            start_date=date.today(),
            target_date=target_date,
            technologies=technologies or [],
        )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO projects 
                (name, description, status, github_url, start_date, target_date, technologies)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                project.name,
                project.description,
                project.status.value,
                project.github_url,
                project.start_date,
                project.target_date,
                "|".join(project.technologies),
            ))
            project.id = cursor.lastrowid
            conn.commit()
        
        logger.info(f"Created project: {project.name}")
        return project
    
    def get(self, project_id: int) -> Optional[Project]:
        """Get a project by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?",
                (project_id,)
            ).fetchone()
            
            if row:
                project = self._row_to_project(row)
                project.milestones = self._get_milestones(project_id)
                project.total_time_minutes = self._get_total_time(project_id)
                return project
        return None
    
    def get_by_name(self, name: str) -> Optional[Project]:
        """Get a project by name (partial match)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM projects WHERE LOWER(name) LIKE LOWER(?)",
                (f"%{name}%",)
            ).fetchone()
            
            if row:
                project = self._row_to_project(row)
                project.milestones = self._get_milestones(project.id)
                project.total_time_minutes = self._get_total_time(project.id)
                return project
        return None
    
    def get_all(self, status: Optional[ProjectStatus] = None) -> List[Project]:
        """Get all projects, optionally filtered by status."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if status:
                rows = conn.execute(
                    "SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC",
                    (status.value,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM projects ORDER BY updated_at DESC"
                ).fetchall()
            
            projects = []
            for row in rows:
                project = self._row_to_project(row)
                project.milestones = self._get_milestones(project.id)
                project.total_time_minutes = self._get_total_time(project.id)
                projects.append(project)
            
            return projects
    
    def get_active(self) -> List[Project]:
        """Get active (in-progress) projects."""
        return self.get_all(ProjectStatus.IN_PROGRESS)
    
    def update_status(self, project_id: int, status: ProjectStatus) -> str:
        """Update project status."""
        project = self.get(project_id)
        if not project:
            return "Project not found."
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE projects 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status.value, project_id))
            conn.commit()
        
        return f"Updated {project.name} status to {status.value}"
    
    def update_notes(self, project_id: int, notes: str) -> str:
        """Update project notes."""
        project = self.get(project_id)
        if not project:
            return "Project not found."
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE projects 
                SET notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (notes, project_id))
            conn.commit()
        
        return f"Updated notes for {project.name}"
    
    def add_milestone(
        self,
        project_id: int,
        name: str,
        description: Optional[str] = None,
        due_date: Optional[date] = None,
    ) -> Milestone:
        """Add a milestone to a project."""
        milestone = Milestone(
            project_id=project_id,
            name=name,
            description=description,
            due_date=due_date,
        )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO project_milestones (project_id, name, description, due_date)
                VALUES (?, ?, ?, ?)
            """, (project_id, name, description, due_date))
            milestone.id = cursor.lastrowid
            
            # Update project timestamp
            conn.execute(
                "UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (project_id,)
            )
            conn.commit()
        
        return milestone
    
    def complete_milestone(self, project_id: int, milestone_name: str) -> str:
        """Mark a milestone as complete."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE project_milestones 
                SET completed = TRUE, completed_at = CURRENT_TIMESTAMP
                WHERE project_id = ? AND LOWER(name) LIKE LOWER(?)
            """, (project_id, f"%{milestone_name}%"))
            
            if cursor.rowcount == 0:
                return f"Milestone '{milestone_name}' not found."
            
            conn.execute(
                "UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (project_id,)
            )
            conn.commit()
        
        return f"✅ Completed milestone: {milestone_name}"
    
    def log_time(
        self,
        project_id: int,
        duration_minutes: int,
        notes: Optional[str] = None,
        log_date: Optional[date] = None,
    ) -> str:
        """Log time spent on a project."""
        project = self.get(project_id)
        if not project:
            return "Project not found."
        
        log_date = log_date or date.today()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO project_time_logs (project_id, duration_minutes, date, notes)
                VALUES (?, ?, ?, ?)
            """, (project_id, duration_minutes, log_date, notes))
            
            conn.execute(
                "UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (project_id,)
            )
            conn.commit()
        
        hours = duration_minutes // 60
        mins = duration_minutes % 60
        time_str = f"{hours}h {mins}m" if hours else f"{mins}m"
        
        return f"⏱️ Logged {time_str} on {project.name}"
    
    def _get_milestones(self, project_id: int) -> List[Milestone]:
        """Get milestones for a project."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM project_milestones
                WHERE project_id = ?
                ORDER BY completed, created_at
            """, (project_id,)).fetchall()
            
            return [self._row_to_milestone(row) for row in rows]
    
    def _get_total_time(self, project_id: int) -> int:
        """Get total time logged for a project."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT COALESCE(SUM(duration_minutes), 0) FROM project_time_logs
                WHERE project_id = ?
            """, (project_id,)).fetchone()
            
            return row[0] if row else 0
    
    def get_time_this_week(self, project_id: int) -> int:
        """Get time logged this week for a project."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT COALESCE(SUM(duration_minutes), 0) FROM project_time_logs
                WHERE project_id = ? AND date >= ?
            """, (project_id, week_start)).fetchone()
            
            return row[0] if row else 0
    
    def format_project(self, project: Project, detailed: bool = False) -> str:
        """Format a project for display."""
        lines = [f"{project.status_emoji} **{project.name}**"]
        
        if project.description:
            lines.append(f"   {project.description}")
        
        lines.append(f"   Status: {project.status.value}")
        
        if project.technologies:
            lines.append(f"   Tech: {', '.join(project.technologies)}")
        
        hours = project.total_time_minutes // 60
        mins = project.total_time_minutes % 60
        lines.append(f"   Time: {hours}h {mins}m total")
        
        if project.milestones:
            completed = sum(1 for m in project.milestones if m.completed)
            lines.append(f"   Progress: {completed}/{len(project.milestones)} milestones")
        
        if detailed:
            if project.github_url:
                lines.append(f"   GitHub: {project.github_url}")
            
            if project.milestones:
                lines.append("   Milestones:")
                for m in project.milestones:
                    lines.append(f"     {m}")
        
        return "\n".join(lines)
    
    def format_projects(self, projects: List[Project]) -> str:
        """Format multiple projects for display."""
        if not projects:
            return "No projects found."
        
        lines = ["📁 Your Projects", ""]
        for project in projects:
            lines.append(self.format_project(project))
            lines.append("")
        
        return "\n".join(lines)
    
    def _row_to_project(self, row: sqlite3.Row) -> Project:
        """Convert database row to Project."""
        return Project(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            status=ProjectStatus(row["status"]),
            github_url=row["github_url"],
            start_date=datetime.strptime(row["start_date"], "%Y-%m-%d").date() if row["start_date"] else None,
            target_date=datetime.strptime(row["target_date"], "%Y-%m-%d").date() if row["target_date"] else None,
            technologies=row["technologies"].split("|") if row["technologies"] else [],
            notes=row["notes"],
            created_at=datetime.fromisoformat(row["created_at"]) if isinstance(row["created_at"], str) else row["created_at"],
            updated_at=datetime.fromisoformat(row["updated_at"]) if isinstance(row["updated_at"], str) else row["updated_at"],
        )
    
    def _row_to_milestone(self, row: sqlite3.Row) -> Milestone:
        """Convert database row to Milestone."""
        return Milestone(
            id=row["id"],
            project_id=row["project_id"],
            name=row["name"],
            description=row["description"],
            completed=bool(row["completed"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            due_date=datetime.strptime(row["due_date"], "%Y-%m-%d").date() if row["due_date"] else None,
            created_at=datetime.fromisoformat(row["created_at"]) if isinstance(row["created_at"], str) else row["created_at"],
        )
