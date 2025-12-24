"""
Application Tracker for JARVIS Internship Automation Module.

Tracks the full lifecycle of internship applications:
- Saved opportunities
- Applied positions
- Interview stages
- Offers and outcomes
- Analytics and statistics
"""

import json
import os
import sqlite3
from dataclasses import asdict
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .models import (
    Application,
    ApplicationStatus,
    ApplicationStats,
    InternshipListing,
)


class ApplicationTracker:
    """
    Track internship applications through their lifecycle.
    
    Features:
    - SQLite persistence
    - Status workflow management
    - Follow-up reminders
    - Analytics and statistics
    """
    
    def __init__(self, db_path: str = "data/internship_applications.db"):
        self.db_path = db_path
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._init_db()
        
        logger.info(f"Application tracker initialized: {db_path}")
    
    def _init_db(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Applications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id TEXT PRIMARY KEY,
                internship_id TEXT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT DEFAULT 'saved',
                resume_version_id TEXT,
                cover_letter_id TEXT,
                date_saved TEXT,
                date_applied TEXT,
                follow_up_date TEXT,
                response_date TEXT,
                notes TEXT,
                contact_person TEXT,
                contact_email TEXT,
                interviews TEXT,
                outcome_notes TEXT,
                salary_offered INTEGER,
                url TEXT,
                location TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Internship listings cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS internship_listings (
                id TEXT PRIMARY KEY,
                company TEXT,
                role TEXT,
                location TEXT,
                location_type TEXT,
                description TEXT,
                requirements TEXT,
                salary_min INTEGER,
                salary_max INTEGER,
                deadline TEXT,
                url TEXT,
                source_api TEXT,
                match_score REAL,
                keywords TEXT,
                status TEXT DEFAULT 'new',
                discovered_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_status ON applications(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_company ON applications(company)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_listing_company ON internship_listings(company)")
        
        conn.commit()
        conn.close()
    
    # =========================================================================
    # Application CRUD
    # =========================================================================
    
    def save_application(self, application: Application) -> str:
        """Save or update an application."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO applications (
                id, internship_id, company, role, status,
                resume_version_id, cover_letter_id,
                date_saved, date_applied, follow_up_date, response_date,
                notes, contact_person, contact_email,
                interviews, outcome_notes, salary_offered,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            application.id,
            application.internship_id,
            application.company,
            application.role,
            application.status.value,
            application.resume_version_id,
            application.cover_letter_id,
            application.date_saved.isoformat() if application.date_saved else None,
            application.date_applied.isoformat() if application.date_applied else None,
            application.follow_up_date.isoformat() if application.follow_up_date else None,
            application.response_date.isoformat() if application.response_date else None,
            application.notes,
            application.contact_person,
            application.contact_email,
            json.dumps(application.interviews),
            application.outcome_notes,
            application.salary_offered,
            datetime.now().isoformat(),
        ))
        
        conn.commit()
        conn.close()
        
        logger.debug(f"Saved application: {application.company} - {application.role}")
        return application.id
    
    def get_application(self, app_id: str) -> Optional[Application]:
        """Get an application by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_application(row, cursor.description)
        return None
    
    def get_application_by_company(self, company: str, role: Optional[str] = None) -> Optional[Application]:
        """Get application by company name."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if role:
            cursor.execute(
                "SELECT * FROM applications WHERE LOWER(company) LIKE ? AND LOWER(role) LIKE ?",
                (f"%{company.lower()}%", f"%{role.lower()}%")
            )
        else:
            cursor.execute(
                "SELECT * FROM applications WHERE LOWER(company) LIKE ?",
                (f"%{company.lower()}%",)
            )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_application(row, cursor.description)
        return None
    
    def get_all_applications(self) -> List[Application]:
        """Get all applications."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM applications ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        description = cursor.description
        conn.close()
        
        return [self._row_to_application(row, description) for row in rows]
    
    def get_applications_by_status(self, status: ApplicationStatus) -> List[Application]:
        """Get applications by status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM applications WHERE status = ? ORDER BY updated_at DESC",
            (status.value,)
        )
        rows = cursor.fetchall()
        description = cursor.description
        conn.close()
        
        return [self._row_to_application(row, description) for row in rows]
    
    def delete_application(self, app_id: str) -> bool:
        """Delete an application."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM applications WHERE id = ?", (app_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def _row_to_application(self, row: tuple, description) -> Application:
        """Convert database row to Application object."""
        columns = [col[0] for col in description]
        data = dict(zip(columns, row))
        
        return Application(
            id=data.get("id", ""),
            internship_id=data.get("internship_id", ""),
            company=data.get("company", ""),
            role=data.get("role", ""),
            status=ApplicationStatus(data.get("status", "saved")),
            resume_version_id=data.get("resume_version_id"),
            cover_letter_id=data.get("cover_letter_id"),
            date_saved=datetime.fromisoformat(data["date_saved"]) if data.get("date_saved") else datetime.now(),
            date_applied=datetime.fromisoformat(data["date_applied"]) if data.get("date_applied") else None,
            follow_up_date=date.fromisoformat(data["follow_up_date"]) if data.get("follow_up_date") else None,
            response_date=datetime.fromisoformat(data["response_date"]) if data.get("response_date") else None,
            notes=data.get("notes", ""),
            contact_person=data.get("contact_person", ""),
            contact_email=data.get("contact_email", ""),
            interviews=json.loads(data.get("interviews", "[]")),
            outcome_notes=data.get("outcome_notes", ""),
            salary_offered=data.get("salary_offered"),
        )
    
    # =========================================================================
    # Status Management
    # =========================================================================
    
    def update_status(
        self,
        app_id: str,
        new_status: ApplicationStatus,
        notes: Optional[str] = None,
    ) -> bool:
        """Update application status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        updates = ["status = ?", "updated_at = ?"]
        params = [new_status.value, datetime.now().isoformat()]
        
        # Set date_applied if moving to applied
        if new_status == ApplicationStatus.APPLIED:
            updates.append("date_applied = ?")
            params.append(datetime.now().isoformat())
            
            # Set follow-up date (7 days from now)
            updates.append("follow_up_date = ?")
            params.append((date.today() + timedelta(days=7)).isoformat())
        
        # Set response_date if getting response
        if new_status in [ApplicationStatus.PHONE_SCREEN, ApplicationStatus.INTERVIEW, 
                          ApplicationStatus.OFFER, ApplicationStatus.REJECTED]:
            updates.append("response_date = ?")
            params.append(datetime.now().isoformat())
        
        if notes:
            updates.append("notes = notes || ? || '\n'")
            params.append(f"[{datetime.now().strftime('%Y-%m-%d')}] {notes}")
        
        params.append(app_id)
        
        cursor.execute(
            f"UPDATE applications SET {', '.join(updates)} WHERE id = ?",
            params
        )
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if updated:
            logger.info(f"Updated application {app_id} to {new_status.value}")
        
        return updated
    
    def mark_applied(self, app_id: str) -> bool:
        """Mark application as applied."""
        return self.update_status(app_id, ApplicationStatus.APPLIED)
    
    def mark_interview(self, app_id: str, interview_type: str = "interview") -> bool:
        """Mark application as having interview."""
        app = self.get_application(app_id)
        if app:
            app.interviews.append({
                "type": interview_type,
                "date": datetime.now().isoformat(),
                "notes": "",
            })
            self.save_application(app)
        return self.update_status(app_id, ApplicationStatus.INTERVIEW)
    
    def mark_offer(self, app_id: str, salary: Optional[int] = None) -> bool:
        """Mark application as received offer."""
        if salary:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE applications SET salary_offered = ? WHERE id = ?",
                (salary, app_id)
            )
            conn.commit()
            conn.close()
        return self.update_status(app_id, ApplicationStatus.OFFER)
    
    def mark_rejected(self, app_id: str) -> bool:
        """Mark application as rejected."""
        return self.update_status(app_id, ApplicationStatus.REJECTED)
    
    def mark_accepted(self, app_id: str) -> bool:
        """Mark offer as accepted."""
        return self.update_status(app_id, ApplicationStatus.ACCEPTED)
    
    # =========================================================================
    # Internship Listings
    # =========================================================================
    
    def save_listing(self, listing: InternshipListing) -> str:
        """Save an internship listing."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO internship_listings (
                id, company, role, location, location_type,
                description, requirements, salary_min, salary_max,
                deadline, url, source_api, match_score, keywords, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            listing.id,
            listing.company,
            listing.role,
            listing.location,
            listing.location_type.value,
            listing.description[:2000] if listing.description else "",
            json.dumps(listing.requirements),
            listing.salary_min,
            listing.salary_max,
            listing.deadline.isoformat() if listing.deadline else None,
            listing.url,
            listing.source_api,
            listing.match_score,
            json.dumps(listing.keywords),
            listing.status,
        ))
        
        conn.commit()
        conn.close()
        
        return listing.id
    
    def get_saved_listings(self) -> List[InternshipListing]:
        """Get all saved internship listings."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM internship_listings WHERE status = 'saved' ORDER BY match_score DESC"
        )
        rows = cursor.fetchall()
        description = cursor.description
        conn.close()
        
        return [self._row_to_listing(row, description) for row in rows]
    
    def _row_to_listing(self, row: tuple, description) -> InternshipListing:
        """Convert database row to InternshipListing."""
        from .models import LocationType
        
        columns = [col[0] for col in description]
        data = dict(zip(columns, row))
        
        return InternshipListing(
            id=data.get("id", ""),
            company=data.get("company", ""),
            role=data.get("role", ""),
            location=data.get("location", ""),
            location_type=LocationType(data.get("location_type", "remote")),
            description=data.get("description", ""),
            requirements=json.loads(data.get("requirements", "[]")),
            salary_min=data.get("salary_min"),
            salary_max=data.get("salary_max"),
            deadline=date.fromisoformat(data["deadline"]) if data.get("deadline") else None,
            url=data.get("url", ""),
            source_api=data.get("source_api", ""),
            match_score=data.get("match_score", 0),
            keywords=json.loads(data.get("keywords", "[]")),
            status=data.get("status", "new"),
        )
    
    # =========================================================================
    # Queries and Reminders
    # =========================================================================
    
    def get_pending_applications(self) -> List[Application]:
        """Get applications that are pending (applied but no response)."""
        return self.get_applications_by_status(ApplicationStatus.APPLIED)
    
    def get_follow_up_reminders(self) -> List[Application]:
        """Get applications that need follow-up."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        
        cursor.execute("""
            SELECT * FROM applications 
            WHERE follow_up_date <= ? 
            AND status IN ('applied', 'phone_screen', 'interview')
            ORDER BY follow_up_date
        """, (today,))
        
        rows = cursor.fetchall()
        description = cursor.description
        conn.close()
        
        return [self._row_to_application(row, description) for row in rows]
    
    def get_recent_applications(self, days: int = 7) -> List[Application]:
        """Get applications from the last N days."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT * FROM applications 
            WHERE date_applied >= ? OR date_saved >= ?
            ORDER BY updated_at DESC
        """, (cutoff, cutoff))
        
        rows = cursor.fetchall()
        description = cursor.description
        conn.close()
        
        return [self._row_to_application(row, description) for row in rows]
    
    def get_interviews_this_week(self) -> List[Application]:
        """Get applications with interviews scheduled this week."""
        apps = self.get_applications_by_status(ApplicationStatus.INTERVIEW)
        # In a real implementation, would filter by interview date
        return apps
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def get_statistics(self) -> ApplicationStats:
        """Get comprehensive application statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = ApplicationStats()
        
        # Count by status
        cursor.execute("SELECT status, COUNT(*) FROM applications GROUP BY status")
        status_counts = dict(cursor.fetchall())
        
        stats.total_saved = status_counts.get("saved", 0)
        stats.total_applied = sum(
            status_counts.get(s, 0) for s in 
            ["applied", "phone_screen", "technical", "interview", "final_round", "offer", "accepted", "rejected"]
        )
        stats.total_interviews = sum(
            status_counts.get(s, 0) for s in 
            ["phone_screen", "technical", "interview", "final_round", "offer", "accepted"]
        )
        stats.total_offers = status_counts.get("offer", 0) + status_counts.get("accepted", 0)
        stats.total_rejected = status_counts.get("rejected", 0)
        stats.total_applications = stats.total_saved + stats.total_applied
        
        # Calculate rates
        if stats.total_applied > 0:
            responded = stats.total_interviews + stats.total_rejected
            stats.response_rate = responded / stats.total_applied
            stats.interview_rate = stats.total_interviews / stats.total_applied
            stats.offer_rate = stats.total_offers / stats.total_applied
        
        # Average response time
        cursor.execute("""
            SELECT AVG(julianday(response_date) - julianday(date_applied))
            FROM applications
            WHERE response_date IS NOT NULL AND date_applied IS NOT NULL
        """)
        avg_days = cursor.fetchone()[0]
        stats.avg_days_to_response = avg_days or 0
        
        # Top companies
        cursor.execute("""
            SELECT company, COUNT(*) as cnt 
            FROM applications 
            GROUP BY company 
            ORDER BY cnt DESC 
            LIMIT 5
        """)
        stats.top_companies_applied = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return stats
    
    def get_statistics_summary(self) -> str:
        """Get formatted statistics summary."""
        stats = self.get_statistics()
        
        lines = [
            "📊 **Internship Application Statistics**",
            "",
            f"**Total Applications:** {stats.total_applications}",
            f"  - Saved: {stats.total_saved}",
            f"  - Applied: {stats.total_applied}",
            "",
            f"**Progress:**",
            f"  - Interviews: {stats.total_interviews}",
            f"  - Offers: {stats.total_offers}",
            f"  - Rejected: {stats.total_rejected}",
            "",
            f"**Rates:**",
            f"  - Response Rate: {stats.response_rate:.1%}",
            f"  - Interview Rate: {stats.interview_rate:.1%}",
            f"  - Offer Rate: {stats.offer_rate:.1%}",
            "",
        ]
        
        if stats.avg_days_to_response > 0:
            lines.append(f"**Avg Response Time:** {stats.avg_days_to_response:.1f} days")
        
        if stats.top_companies_applied:
            lines.extend([
                "",
                f"**Top Companies:** {', '.join(stats.top_companies_applied[:3])}",
            ])
        
        return "\n".join(lines)
    
    # =========================================================================
    # Quick Actions
    # =========================================================================
    
    def create_application_from_listing(
        self,
        listing: InternshipListing,
        auto_save_listing: bool = True,
    ) -> Application:
        """Create an application from an internship listing."""
        if auto_save_listing:
            self.save_listing(listing)
        
        app = Application(
            internship_id=listing.id,
            company=listing.company,
            role=listing.role,
            status=ApplicationStatus.SAVED,
        )
        
        self.save_application(app)
        return app
    
    def quick_track(
        self,
        company: str,
        role: str,
        status: ApplicationStatus = ApplicationStatus.APPLIED,
    ) -> Application:
        """Quickly track a new application."""
        app = Application(
            company=company,
            role=role,
            status=status,
            date_applied=datetime.now() if status == ApplicationStatus.APPLIED else None,
        )
        
        if status == ApplicationStatus.APPLIED:
            app.follow_up_date = date.today() + timedelta(days=7)
        
        self.save_application(app)
        return app
