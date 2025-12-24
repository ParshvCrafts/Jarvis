"""
Job Application Tracker for JARVIS.

Track internship/job applications:
- Application status workflow
- Deadline reminders
- Success rate tracking
- Notes per application
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class ApplicationStatus(Enum):
    SAVED = "saved"
    APPLIED = "applied"
    PHONE_SCREEN = "phone_screen"
    TECHNICAL = "technical"
    ONSITE = "onsite"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


@dataclass
class JobApplication:
    id: Optional[int] = None
    company: str = ""
    position: str = ""
    status: ApplicationStatus = ApplicationStatus.SAVED
    applied_date: Optional[date] = None
    deadline: Optional[date] = None
    url: str = ""
    contact_name: str = ""
    contact_email: str = ""
    notes: str = ""
    salary_range: str = ""
    location: str = ""
    is_remote: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "JobApplication":
        return cls(
            id=row["id"],
            company=row["company"],
            position=row["position"],
            status=ApplicationStatus(row["status"]),
            applied_date=date.fromisoformat(row["applied_date"]) if row["applied_date"] else None,
            deadline=date.fromisoformat(row["deadline"]) if row["deadline"] else None,
            url=row["url"] or "",
            contact_name=row["contact_name"] or "",
            contact_email=row["contact_email"] or "",
            notes=row["notes"] or "",
            salary_range=row["salary_range"] or "",
            location=row["location"] or "",
            is_remote=bool(row["is_remote"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
        )


class ApplicationTracker:
    """
    Job application tracking system.
    
    Features:
    - Track applications through stages
    - Deadline reminders
    - Success rate analytics
    - Notes and contacts
    """
    
    # Status progression order
    STATUS_ORDER = [
        ApplicationStatus.SAVED,
        ApplicationStatus.APPLIED,
        ApplicationStatus.PHONE_SCREEN,
        ApplicationStatus.TECHNICAL,
        ApplicationStatus.ONSITE,
        ApplicationStatus.OFFER,
    ]
    
    def __init__(self, data_dir: str = "data", reminder_days: int = 3):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "applications.db"
        self.reminder_days = reminder_days
        
        self._init_db()
        logger.info("Application Tracker initialized")
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    position TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'saved',
                    applied_date TEXT,
                    deadline TEXT,
                    url TEXT,
                    contact_name TEXT,
                    contact_email TEXT,
                    notes TEXT,
                    salary_range TEXT,
                    location TEXT,
                    is_remote INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS status_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    application_id INTEGER NOT NULL,
                    old_status TEXT,
                    new_status TEXT NOT NULL,
                    changed_at TEXT NOT NULL,
                    notes TEXT,
                    FOREIGN KEY (application_id) REFERENCES applications(id)
                )
            """)
            conn.commit()
    
    def add_application(
        self,
        company: str,
        position: str,
        status: str = "applied",
        deadline: Optional[str] = None,
        url: str = "",
        location: str = "",
        notes: str = "",
    ) -> JobApplication:
        """Add a new job application."""
        try:
            app_status = ApplicationStatus(status.lower().replace(" ", "_"))
        except ValueError:
            app_status = ApplicationStatus.APPLIED
        
        now = datetime.now()
        applied_date = date.today() if app_status != ApplicationStatus.SAVED else None
        
        app = JobApplication(
            company=company,
            position=position,
            status=app_status,
            applied_date=applied_date,
            deadline=date.fromisoformat(deadline) if deadline else None,
            url=url,
            location=location,
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO applications (company, position, status, applied_date, deadline,
                    url, location, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                app.company, app.position, app.status.value,
                app.applied_date.isoformat() if app.applied_date else None,
                app.deadline.isoformat() if app.deadline else None,
                app.url, app.location, app.notes,
                app.created_at.isoformat(), app.updated_at.isoformat()
            ))
            app.id = cursor.lastrowid
            
            # Record initial status
            conn.execute("""
                INSERT INTO status_history (application_id, new_status, changed_at)
                VALUES (?, ?, ?)
            """, (app.id, app.status.value, now.isoformat()))
            
            conn.commit()
        
        logger.info(f"Added application: {company} - {position}")
        return app
    
    def update_status(
        self,
        company: str,
        new_status: str,
        notes: str = "",
    ) -> str:
        """Update application status by company name."""
        try:
            status = ApplicationStatus(new_status.lower().replace(" ", "_"))
        except ValueError:
            return f"Invalid status: {new_status}. Valid: {[s.value for s in ApplicationStatus]}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Find application by company (case-insensitive)
            row = conn.execute(
                "SELECT * FROM applications WHERE LOWER(company) LIKE ? ORDER BY updated_at DESC LIMIT 1",
                (f"%{company.lower()}%",)
            ).fetchone()
            
            if not row:
                return f"No application found for '{company}'."
            
            app = JobApplication.from_row(row)
            old_status = app.status
            
            # Update status
            now = datetime.now()
            applied_date = app.applied_date
            if status == ApplicationStatus.APPLIED and not applied_date:
                applied_date = date.today()
            
            conn.execute("""
                UPDATE applications 
                SET status = ?, applied_date = ?, updated_at = ?
                WHERE id = ?
            """, (status.value, applied_date.isoformat() if applied_date else None, 
                  now.isoformat(), app.id))
            
            # Record status change
            conn.execute("""
                INSERT INTO status_history (application_id, old_status, new_status, changed_at, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (app.id, old_status.value, status.value, now.isoformat(), notes))
            
            conn.commit()
        
        status_emoji = {
            ApplicationStatus.APPLIED: "📤",
            ApplicationStatus.PHONE_SCREEN: "📞",
            ApplicationStatus.TECHNICAL: "💻",
            ApplicationStatus.ONSITE: "🏢",
            ApplicationStatus.OFFER: "🎉",
            ApplicationStatus.REJECTED: "❌",
            ApplicationStatus.WITHDRAWN: "🚫",
        }
        
        emoji = status_emoji.get(status, "📋")
        return f"{emoji} Updated {app.company} - {app.position}: {old_status.value} → {status.value}"
    
    def get_applications(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[JobApplication]:
        """Get applications, optionally filtered by status."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if status:
                rows = conn.execute(
                    "SELECT * FROM applications WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                    (status, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM applications ORDER BY updated_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
        
        return [JobApplication.from_row(row) for row in rows]
    
    def get_pending_applications(self) -> List[JobApplication]:
        """Get applications that are still in progress."""
        active_statuses = [
            ApplicationStatus.SAVED.value,
            ApplicationStatus.APPLIED.value,
            ApplicationStatus.PHONE_SCREEN.value,
            ApplicationStatus.TECHNICAL.value,
            ApplicationStatus.ONSITE.value,
        ]
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            placeholders = ",".join("?" * len(active_statuses))
            rows = conn.execute(
                f"SELECT * FROM applications WHERE status IN ({placeholders}) ORDER BY deadline, updated_at",
                active_statuses
            ).fetchall()
        
        return [JobApplication.from_row(row) for row in rows]
    
    def get_upcoming_deadlines(self, days: int = 7) -> List[JobApplication]:
        """Get applications with deadlines in the next N days."""
        cutoff = (date.today() + timedelta(days=days)).isoformat()
        today = date.today().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM applications 
                WHERE deadline IS NOT NULL 
                AND deadline >= ? AND deadline <= ?
                AND status NOT IN ('rejected', 'withdrawn', 'offer')
                ORDER BY deadline
            """, (today, cutoff)).fetchall()
        
        return [JobApplication.from_row(row) for row in rows]
    
    def get_stats(self) -> str:
        """Get application statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
            
            by_status = conn.execute("""
                SELECT status, COUNT(*) as count 
                FROM applications 
                GROUP BY status
            """).fetchall()
            
            # Calculate response rate
            applied = conn.execute(
                "SELECT COUNT(*) FROM applications WHERE status != 'saved'"
            ).fetchone()[0]
            
            responses = conn.execute("""
                SELECT COUNT(*) FROM applications 
                WHERE status IN ('phone_screen', 'technical', 'onsite', 'offer', 'rejected')
            """).fetchone()[0]
            
            offers = conn.execute(
                "SELECT COUNT(*) FROM applications WHERE status = 'offer'"
            ).fetchone()[0]
        
        response_rate = (responses / applied * 100) if applied > 0 else 0
        offer_rate = (offers / applied * 100) if applied > 0 else 0
        
        status_emoji = {
            "saved": "📌",
            "applied": "📤",
            "phone_screen": "📞",
            "technical": "💻",
            "onsite": "🏢",
            "offer": "🎉",
            "rejected": "❌",
            "withdrawn": "🚫",
        }
        
        lines = [
            "📊 **Application Statistics**\n",
            f"Total Applications: {total}",
            f"Response Rate: {response_rate:.1f}%",
            f"Offer Rate: {offer_rate:.1f}%\n",
            "**By Status:**",
        ]
        
        for status, count in by_status:
            emoji = status_emoji.get(status, "📋")
            lines.append(f"  {emoji} {status.replace('_', ' ').title()}: {count}")
        
        return "\n".join(lines)
    
    def format_applications(self, applications: List[JobApplication]) -> str:
        """Format applications for display."""
        if not applications:
            return "No applications found."
        
        status_emoji = {
            ApplicationStatus.SAVED: "📌",
            ApplicationStatus.APPLIED: "📤",
            ApplicationStatus.PHONE_SCREEN: "📞",
            ApplicationStatus.TECHNICAL: "💻",
            ApplicationStatus.ONSITE: "🏢",
            ApplicationStatus.OFFER: "🎉",
            ApplicationStatus.REJECTED: "❌",
            ApplicationStatus.WITHDRAWN: "🚫",
        }
        
        lines = ["📋 **Your Applications**\n"]
        
        for app in applications:
            emoji = status_emoji.get(app.status, "📋")
            deadline_str = ""
            if app.deadline:
                days_left = (app.deadline - date.today()).days
                if days_left < 0:
                    deadline_str = " ⚠️ PAST DUE"
                elif days_left == 0:
                    deadline_str = " ⚠️ DUE TODAY"
                elif days_left <= 3:
                    deadline_str = f" ⏰ {days_left}d left"
            
            lines.append(f"{emoji} **{app.company}** - {app.position}{deadline_str}")
            lines.append(f"   Status: {app.status.value.replace('_', ' ').title()}")
            if app.location:
                lines.append(f"   Location: {app.location}")
            if app.applied_date:
                lines.append(f"   Applied: {app.applied_date.strftime('%b %d, %Y')}")
        
        return "\n".join(lines)
    
    def add_note(self, company: str, note: str) -> str:
        """Add a note to an application."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, notes FROM applications WHERE LOWER(company) LIKE ? ORDER BY updated_at DESC LIMIT 1",
                (f"%{company.lower()}%",)
            ).fetchone()
            
            if not row:
                return f"No application found for '{company}'."
            
            app_id, existing_notes = row
            new_notes = f"{existing_notes}\n[{datetime.now().strftime('%Y-%m-%d')}] {note}" if existing_notes else f"[{datetime.now().strftime('%Y-%m-%d')}] {note}"
            
            conn.execute(
                "UPDATE applications SET notes = ?, updated_at = ? WHERE id = ?",
                (new_notes, datetime.now().isoformat(), app_id)
            )
            conn.commit()
        
        return f"✅ Note added to {company} application."
