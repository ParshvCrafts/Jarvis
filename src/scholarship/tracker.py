"""
Application Tracking for JARVIS Scholarship Module.

Handles:
- Application status tracking
- Deadline management
- Statistics and reporting
"""

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .models import (
    Application,
    ApplicationStatus,
    Scholarship,
    GeneratedEssay,
)


class ApplicationTracker:
    """
    Track scholarship applications and their status.
    
    Uses SQLite for local persistence with optional Supabase sync.
    """
    
    def __init__(
        self,
        db_path: str = "data/scholarship_applications.db",
        supabase_client=None,
    ):
        """
        Initialize application tracker.
        
        Args:
            db_path: Path to SQLite database
            supabase_client: Optional Supabase client for sync
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.supabase = supabase_client
        
        self._init_db()
        logger.info(f"Application tracker initialized: {self.db_path}")
    
    def _init_db(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id TEXT PRIMARY KEY,
                    scholarship_id TEXT,
                    scholarship_name TEXT NOT NULL,
                    status TEXT DEFAULT 'discovered',
                    deadline TEXT,
                    started_at TEXT,
                    submitted_at TEXT,
                    result_at TEXT,
                    essay_ids TEXT DEFAULT '[]',
                    essays_complete INTEGER DEFAULT 0,
                    google_doc_url TEXT,
                    google_doc_id TEXT,
                    notes TEXT DEFAULT '',
                    award_amount REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS generated_essays (
                    id TEXT PRIMARY KEY,
                    application_id TEXT,
                    scholarship_name TEXT,
                    question_text TEXT,
                    essay_text TEXT NOT NULL,
                    word_count INTEGER DEFAULT 0,
                    target_word_count INTEGER DEFAULT 0,
                    generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    llm_used TEXT,
                    quality_score REAL,
                    FOREIGN KEY (application_id) REFERENCES applications(id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_applications_status 
                ON applications(status)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_applications_deadline 
                ON applications(deadline)
            """)
            
            conn.commit()
    
    # =========================================================================
    # Application CRUD
    # =========================================================================
    
    def create_application(
        self,
        scholarship: Scholarship,
        status: ApplicationStatus = ApplicationStatus.DISCOVERED,
    ) -> Application:
        """
        Create a new application for a scholarship.
        
        Args:
            scholarship: The scholarship to apply for
            status: Initial status
            
        Returns:
            Created Application object
        """
        application = Application(
            scholarship_id=scholarship.id,
            scholarship_name=scholarship.name,
            status=status,
            deadline=scholarship.deadline,
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO applications (
                    id, scholarship_id, scholarship_name, status, deadline
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                application.id,
                application.scholarship_id,
                application.scholarship_name,
                application.status.value,
                application.deadline.isoformat() if application.deadline else None,
            ))
            conn.commit()
        
        logger.info(f"Created application: {scholarship.name}")
        return application
    
    def get_application(self, application_id: str) -> Optional[Application]:
        """Get an application by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM applications WHERE id = ?",
                (application_id,)
            ).fetchone()
            
            if row:
                return self._row_to_application(row)
            return None
    
    def get_application_by_name(self, scholarship_name: str) -> Optional[Application]:
        """Get an application by scholarship name."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM applications WHERE scholarship_name LIKE ?",
                (f"%{scholarship_name}%",)
            ).fetchone()
            
            if row:
                return self._row_to_application(row)
            return None
    
    def _row_to_application(self, row: sqlite3.Row) -> Application:
        """Convert database row to Application object."""
        import json
        
        return Application(
            id=row["id"],
            scholarship_id=row["scholarship_id"] or "",
            scholarship_name=row["scholarship_name"],
            status=ApplicationStatus(row["status"]),
            deadline=date.fromisoformat(row["deadline"]) if row["deadline"] else None,
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            submitted_at=datetime.fromisoformat(row["submitted_at"]) if row["submitted_at"] else None,
            result_at=datetime.fromisoformat(row["result_at"]) if row["result_at"] else None,
            essay_ids=json.loads(row["essay_ids"]) if row["essay_ids"] else [],
            essays_complete=bool(row["essays_complete"]),
            google_doc_url=row["google_doc_url"],
            google_doc_id=row["google_doc_id"],
            notes=row["notes"] or "",
            award_amount=row["award_amount"],
        )
    
    def update_status(
        self,
        application_id: str,
        status: ApplicationStatus,
        notes: Optional[str] = None,
    ) -> bool:
        """
        Update application status.
        
        Args:
            application_id: Application ID
            status: New status
            notes: Optional notes to add
            
        Returns:
            True if updated successfully
        """
        updates = ["status = ?", "updated_at = ?"]
        values = [status.value, datetime.now().isoformat()]
        
        # Set timestamp based on status
        if status == ApplicationStatus.IN_PROGRESS:
            updates.append("started_at = ?")
            values.append(datetime.now().isoformat())
        elif status == ApplicationStatus.SUBMITTED:
            updates.append("submitted_at = ?")
            values.append(datetime.now().isoformat())
        elif status in [ApplicationStatus.WON, ApplicationStatus.LOST]:
            updates.append("result_at = ?")
            values.append(datetime.now().isoformat())
        
        if notes:
            updates.append("notes = notes || ?")
            values.append(f"\n{notes}")
        
        values.append(application_id)
        
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                f"UPDATE applications SET {', '.join(updates)} WHERE id = ?",
                values
            )
            conn.commit()
            
            if result.rowcount > 0:
                logger.info(f"Updated application {application_id} to {status.value}")
                return True
            return False
    
    def update_google_doc(
        self,
        application_id: str,
        doc_url: str,
        doc_id: Optional[str] = None,
    ) -> bool:
        """Update Google Doc link for application."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE applications 
                SET google_doc_url = ?, google_doc_id = ?, updated_at = ?
                WHERE id = ?
            """, (doc_url, doc_id, datetime.now().isoformat(), application_id))
            conn.commit()
            return True
    
    def mark_essays_complete(self, application_id: str) -> bool:
        """Mark essays as complete for an application."""
        return self.update_status(application_id, ApplicationStatus.ESSAYS_COMPLETE)
    
    def mark_submitted(self, application_id: str) -> bool:
        """Mark application as submitted."""
        return self.update_status(application_id, ApplicationStatus.SUBMITTED)
    
    def mark_won(self, application_id: str, award_amount: Optional[float] = None) -> bool:
        """Mark application as won."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE applications 
                SET status = ?, result_at = ?, award_amount = ?, updated_at = ?
                WHERE id = ?
            """, (
                ApplicationStatus.WON.value,
                datetime.now().isoformat(),
                award_amount,
                datetime.now().isoformat(),
                application_id,
            ))
            conn.commit()
            return True
    
    def mark_lost(self, application_id: str) -> bool:
        """Mark application as lost."""
        return self.update_status(application_id, ApplicationStatus.LOST)
    
    # =========================================================================
    # Essay Management
    # =========================================================================
    
    def save_essay(
        self,
        application_id: str,
        essay: GeneratedEssay,
    ) -> str:
        """
        Save a generated essay for an application.
        
        Args:
            application_id: Application ID
            essay: Generated essay
            
        Returns:
            Essay ID
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO generated_essays (
                    id, application_id, scholarship_name, question_text,
                    essay_text, word_count, target_word_count, llm_used, quality_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                essay.id,
                application_id,
                essay.scholarship_name,
                essay.question_text,
                essay.essay_text,
                essay.word_count,
                essay.target_word_count,
                essay.llm_used,
                essay.quality_score,
            ))
            
            # Update application essay_ids
            import json
            row = conn.execute(
                "SELECT essay_ids FROM applications WHERE id = ?",
                (application_id,)
            ).fetchone()
            
            essay_ids = json.loads(row[0]) if row and row[0] else []
            essay_ids.append(essay.id)
            
            conn.execute("""
                UPDATE applications SET essay_ids = ?, updated_at = ? WHERE id = ?
            """, (json.dumps(essay_ids), datetime.now().isoformat(), application_id))
            
            conn.commit()
        
        return essay.id
    
    def get_essays(self, application_id: str) -> List[GeneratedEssay]:
        """Get all essays for an application."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM generated_essays WHERE application_id = ?",
                (application_id,)
            ).fetchall()
            
            essays = []
            for row in rows:
                essays.append(GeneratedEssay(
                    id=row["id"],
                    scholarship_name=row["scholarship_name"],
                    question_text=row["question_text"],
                    essay_text=row["essay_text"],
                    word_count=row["word_count"],
                    target_word_count=row["target_word_count"],
                    llm_used=row["llm_used"],
                    quality_score=row["quality_score"],
                ))
            
            return essays
    
    # =========================================================================
    # Queries
    # =========================================================================
    
    def get_all_applications(self) -> List[Application]:
        """Get all applications."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM applications ORDER BY deadline ASC"
            ).fetchall()
            
            return [self._row_to_application(row) for row in rows]
    
    def get_by_status(self, status: ApplicationStatus) -> List[Application]:
        """Get applications by status."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM applications WHERE status = ? ORDER BY deadline ASC",
                (status.value,)
            ).fetchall()
            
            return [self._row_to_application(row) for row in rows]
    
    def get_pending(self) -> List[Application]:
        """Get all pending applications (not submitted, won, or lost)."""
        pending_statuses = [
            ApplicationStatus.DISCOVERED.value,
            ApplicationStatus.SAVED.value,
            ApplicationStatus.IN_PROGRESS.value,
            ApplicationStatus.ESSAYS_COMPLETE.value,
        ]
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            placeholders = ",".join("?" * len(pending_statuses))
            rows = conn.execute(
                f"SELECT * FROM applications WHERE status IN ({placeholders}) ORDER BY deadline ASC",
                pending_statuses
            ).fetchall()
            
            return [self._row_to_application(row) for row in rows]
    
    def get_due_soon(self, days: int = 7) -> List[Application]:
        """Get applications due within specified days."""
        deadline = (date.today() + timedelta(days=days)).isoformat()
        today = date.today().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM applications 
                WHERE deadline IS NOT NULL 
                AND deadline >= ? AND deadline <= ?
                AND status NOT IN (?, ?, ?)
                ORDER BY deadline ASC
            """, (
                today, deadline,
                ApplicationStatus.SUBMITTED.value,
                ApplicationStatus.WON.value,
                ApplicationStatus.LOST.value,
            )).fetchall()
            
            return [self._row_to_application(row) for row in rows]
    
    def get_submitted(self) -> List[Application]:
        """Get all submitted applications."""
        return self.get_by_status(ApplicationStatus.SUBMITTED)
    
    def get_won(self) -> List[Application]:
        """Get all won applications."""
        return self.get_by_status(ApplicationStatus.WON)
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get application statistics."""
        with sqlite3.connect(self.db_path) as conn:
            # Total counts by status
            status_counts = {}
            for status in ApplicationStatus:
                count = conn.execute(
                    "SELECT COUNT(*) FROM applications WHERE status = ?",
                    (status.value,)
                ).fetchone()[0]
                status_counts[status.value] = count
            
            # Total applications
            total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
            
            # Total won amount
            won_amount = conn.execute(
                "SELECT SUM(award_amount) FROM applications WHERE status = ?",
                (ApplicationStatus.WON.value,)
            ).fetchone()[0] or 0
            
            # Essays generated
            essay_count = conn.execute(
                "SELECT COUNT(*) FROM generated_essays"
            ).fetchone()[0]
            
            # Due this week
            week_deadline = (date.today() + timedelta(days=7)).isoformat()
            due_this_week = conn.execute("""
                SELECT COUNT(*) FROM applications 
                WHERE deadline <= ? AND status NOT IN (?, ?, ?)
            """, (
                week_deadline,
                ApplicationStatus.SUBMITTED.value,
                ApplicationStatus.WON.value,
                ApplicationStatus.LOST.value,
            )).fetchone()[0]
        
        return {
            "total": total,
            "by_status": status_counts,
            "won_amount": won_amount,
            "essays_generated": essay_count,
            "due_this_week": due_this_week,
            "win_rate": (
                status_counts.get("won", 0) / 
                (status_counts.get("won", 0) + status_counts.get("lost", 0))
                if (status_counts.get("won", 0) + status_counts.get("lost", 0)) > 0
                else 0
            ),
        }
    
    def get_statistics_summary(self) -> str:
        """Get formatted statistics summary."""
        stats = self.get_statistics()
        
        lines = [
            "📊 **Scholarship Application Statistics**",
            "",
            f"**Total Applications:** {stats['total']}",
            "",
            "**By Status:**",
            f"  🔍 Discovered: {stats['by_status'].get('discovered', 0)}",
            f"  📝 In Progress: {stats['by_status'].get('in_progress', 0)}",
            f"  ✅ Essays Complete: {stats['by_status'].get('essays_complete', 0)}",
            f"  📤 Submitted: {stats['by_status'].get('submitted', 0)}",
            f"  🏆 Won: {stats['by_status'].get('won', 0)}",
            f"  ❌ Lost: {stats['by_status'].get('lost', 0)}",
            "",
            f"**Total Won:** ${stats['won_amount']:,.0f}",
            f"**Win Rate:** {stats['win_rate']:.0%}",
            f"**Essays Generated:** {stats['essays_generated']}",
            "",
            f"⏰ **Due This Week:** {stats['due_this_week']}",
        ]
        
        return "\n".join(lines)
    
    def get_due_soon_summary(self, days: int = 7) -> str:
        """Get summary of applications due soon."""
        applications = self.get_due_soon(days)
        
        if not applications:
            return f"No applications due in the next {days} days."
        
        lines = [f"⏰ **Applications Due in {days} Days:**", ""]
        
        for app in applications:
            days_left = (app.deadline - date.today()).days if app.deadline else 0
            status_emoji = {
                ApplicationStatus.DISCOVERED: "🔍",
                ApplicationStatus.SAVED: "💾",
                ApplicationStatus.IN_PROGRESS: "📝",
                ApplicationStatus.ESSAYS_COMPLETE: "✅",
            }.get(app.status, "📋")
            
            lines.append(
                f"{status_emoji} **{app.scholarship_name}**"
                f"\n   Due: {app.deadline.strftime('%b %d')} ({days_left} days) | Status: {app.status.value}"
            )
        
        return "\n".join(lines)
