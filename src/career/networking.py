"""
Networking Tracker for JARVIS.

Track professional connections:
- Contact management
- Interaction history
- Follow-up reminders
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class ContactType(Enum):
    PROFESSOR = "professor"
    TA = "ta"
    INDUSTRY = "industry"
    ALUMNI = "alumni"
    STUDENT = "student"
    RECRUITER = "recruiter"
    MENTOR = "mentor"
    OTHER = "other"


class InteractionType(Enum):
    EMAIL = "email"
    MEETING = "meeting"
    COFFEE_CHAT = "coffee_chat"
    CAREER_FAIR = "career_fair"
    LINKEDIN = "linkedin"
    CALL = "call"
    EVENT = "event"
    OTHER = "other"


@dataclass
class Contact:
    id: Optional[int] = None
    name: str = ""
    company: str = ""
    role: str = ""
    contact_type: ContactType = ContactType.OTHER
    email: str = ""
    linkedin: str = ""
    phone: str = ""
    how_met: str = ""
    notes: str = ""
    last_contact: Optional[date] = None
    follow_up_date: Optional[date] = None
    is_favorite: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Contact":
        return cls(
            id=row["id"],
            name=row["name"],
            company=row["company"] or "",
            role=row["role"] or "",
            contact_type=ContactType(row["contact_type"]) if row["contact_type"] else ContactType.OTHER,
            email=row["email"] or "",
            linkedin=row["linkedin"] or "",
            phone=row["phone"] or "",
            how_met=row["how_met"] or "",
            notes=row["notes"] or "",
            last_contact=date.fromisoformat(row["last_contact"]) if row["last_contact"] else None,
            follow_up_date=date.fromisoformat(row["follow_up_date"]) if row["follow_up_date"] else None,
            is_favorite=bool(row["is_favorite"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
        )


@dataclass
class Interaction:
    id: Optional[int] = None
    contact_id: int = 0
    interaction_type: InteractionType = InteractionType.OTHER
    date: date = field(default_factory=date.today)
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Interaction":
        return cls(
            id=row["id"],
            contact_id=row["contact_id"],
            interaction_type=InteractionType(row["type"]) if row["type"] else InteractionType.OTHER,
            date=date.fromisoformat(row["date"]) if row["date"] else date.today(),
            notes=row["notes"] or "",
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
        )


class NetworkingTracker:
    """
    Professional networking tracker.
    
    Features:
    - Contact management
    - Interaction logging
    - Follow-up reminders
    - Network analytics
    """
    
    def __init__(self, data_dir: str = "data", follow_up_days: int = 14):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "networking.db"
        self.follow_up_days = follow_up_days
        
        self._init_db()
        logger.info("Networking Tracker initialized")
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    company TEXT,
                    role TEXT,
                    contact_type TEXT,
                    email TEXT,
                    linkedin TEXT,
                    phone TEXT,
                    how_met TEXT,
                    notes TEXT,
                    last_contact TEXT,
                    follow_up_date TEXT,
                    is_favorite INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    date TEXT NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (contact_id) REFERENCES contacts(id)
                )
            """)
            conn.commit()
    
    def add_contact(
        self,
        name: str,
        company: str = "",
        role: str = "",
        contact_type: str = "other",
        how_met: str = "",
        email: str = "",
        linkedin: str = "",
        notes: str = "",
    ) -> Contact:
        """Add a new contact."""
        try:
            ctype = ContactType(contact_type.lower())
        except ValueError:
            ctype = ContactType.OTHER
        
        contact = Contact(
            name=name,
            company=company,
            role=role,
            contact_type=ctype,
            how_met=how_met,
            email=email,
            linkedin=linkedin,
            notes=notes,
            last_contact=date.today(),
        )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO contacts (name, company, role, contact_type, email, linkedin,
                    how_met, notes, last_contact, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contact.name, contact.company, contact.role, contact.contact_type.value,
                contact.email, contact.linkedin, contact.how_met, contact.notes,
                contact.last_contact.isoformat() if contact.last_contact else None,
                contact.created_at.isoformat()
            ))
            contact.id = cursor.lastrowid
            conn.commit()
        
        logger.info(f"Added contact: {name}")
        return contact
    
    def log_interaction(
        self,
        contact_name: str,
        interaction_type: str = "other",
        notes: str = "",
        interaction_date: Optional[str] = None,
    ) -> str:
        """Log an interaction with a contact."""
        # Find contact
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM contacts WHERE LOWER(name) LIKE ? LIMIT 1",
                (f"%{contact_name.lower()}%",)
            ).fetchone()
            
            if not row:
                return f"No contact found matching '{contact_name}'."
            
            contact = Contact.from_row(row)
        
        try:
            itype = InteractionType(interaction_type.lower().replace(" ", "_"))
        except ValueError:
            itype = InteractionType.OTHER
        
        int_date = date.fromisoformat(interaction_date) if interaction_date else date.today()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO interactions (contact_id, type, date, notes, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (contact.id, itype.value, int_date.isoformat(), notes, datetime.now().isoformat()))
            
            # Update last contact date
            conn.execute(
                "UPDATE contacts SET last_contact = ? WHERE id = ?",
                (int_date.isoformat(), contact.id)
            )
            conn.commit()
        
        return f"✅ Logged {itype.value.replace('_', ' ')} with {contact.name}"
    
    def add_note(self, contact_name: str, note: str) -> str:
        """Add a note to a contact."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, notes FROM contacts WHERE LOWER(name) LIKE ? LIMIT 1",
                (f"%{contact_name.lower()}%",)
            ).fetchone()
            
            if not row:
                return f"No contact found matching '{contact_name}'."
            
            contact_id, existing_notes = row
            timestamp = datetime.now().strftime("%Y-%m-%d")
            new_notes = f"{existing_notes}\n[{timestamp}] {note}" if existing_notes else f"[{timestamp}] {note}"
            
            conn.execute(
                "UPDATE contacts SET notes = ? WHERE id = ?",
                (new_notes, contact_id)
            )
            conn.commit()
        
        return f"✅ Note added for {contact_name}"
    
    def set_follow_up(self, contact_name: str, days: Optional[int] = None) -> str:
        """Set a follow-up reminder for a contact."""
        follow_up = date.today() + timedelta(days=days or self.follow_up_days)
        
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "UPDATE contacts SET follow_up_date = ? WHERE LOWER(name) LIKE ?",
                (follow_up.isoformat(), f"%{contact_name.lower()}%")
            )
            conn.commit()
            
            if result.rowcount == 0:
                return f"No contact found matching '{contact_name}'."
        
        return f"⏰ Follow-up reminder set for {contact_name} on {follow_up.strftime('%b %d, %Y')}"
    
    def get_follow_ups(self) -> List[Contact]:
        """Get contacts due for follow-up."""
        today = date.today().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Contacts with explicit follow-up dates
            rows = conn.execute("""
                SELECT * FROM contacts 
                WHERE follow_up_date IS NOT NULL AND follow_up_date <= ?
                ORDER BY follow_up_date
            """, (today,)).fetchall()
            
            # Also get contacts not contacted in follow_up_days
            cutoff = (date.today() - timedelta(days=self.follow_up_days)).isoformat()
            stale_rows = conn.execute("""
                SELECT * FROM contacts 
                WHERE (follow_up_date IS NULL OR follow_up_date > ?)
                AND last_contact IS NOT NULL AND last_contact < ?
                ORDER BY last_contact
            """, (today, cutoff)).fetchall()
        
        contacts = [Contact.from_row(row) for row in rows]
        stale_contacts = [Contact.from_row(row) for row in stale_rows]
        
        # Combine, avoiding duplicates
        seen_ids = {c.id for c in contacts}
        for c in stale_contacts:
            if c.id not in seen_ids:
                contacts.append(c)
        
        return contacts
    
    def get_contacts(
        self,
        contact_type: Optional[str] = None,
        company: Optional[str] = None,
        limit: int = 50,
    ) -> List[Contact]:
        """Get contacts with optional filters."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM contacts WHERE 1=1"
            params = []
            
            if contact_type:
                query += " AND contact_type = ?"
                params.append(contact_type)
            
            if company:
                query += " AND LOWER(company) LIKE ?"
                params.append(f"%{company.lower()}%")
            
            query += " ORDER BY is_favorite DESC, last_contact DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
        
        return [Contact.from_row(row) for row in rows]
    
    def search_contacts(self, query: str) -> List[Contact]:
        """Search contacts by name, company, or notes."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM contacts 
                WHERE LOWER(name) LIKE ? 
                OR LOWER(company) LIKE ?
                OR LOWER(role) LIKE ?
                OR LOWER(notes) LIKE ?
                ORDER BY is_favorite DESC, last_contact DESC
                LIMIT 20
            """, (f"%{query.lower()}%",) * 4).fetchall()
        
        return [Contact.from_row(row) for row in rows]
    
    def format_contacts(self, contacts: List[Contact]) -> str:
        """Format contacts for display."""
        if not contacts:
            return "No contacts found."
        
        lines = ["🤝 **Your Network**\n"]
        
        by_type = {}
        for contact in contacts:
            if contact.contact_type not in by_type:
                by_type[contact.contact_type] = []
            by_type[contact.contact_type].append(contact)
        
        type_emoji = {
            ContactType.PROFESSOR: "👨‍🏫",
            ContactType.TA: "👨‍🎓",
            ContactType.INDUSTRY: "💼",
            ContactType.ALUMNI: "🎓",
            ContactType.STUDENT: "📚",
            ContactType.RECRUITER: "🔍",
            ContactType.MENTOR: "🌟",
            ContactType.OTHER: "👤",
        }
        
        for ctype, type_contacts in by_type.items():
            emoji = type_emoji.get(ctype, "👤")
            lines.append(f"\n{emoji} **{ctype.value.title()}**")
            
            for contact in type_contacts:
                star = "⭐ " if contact.is_favorite else ""
                lines.append(f"  • {star}**{contact.name}**")
                if contact.company or contact.role:
                    lines.append(f"    {contact.role}{' @ ' if contact.role and contact.company else ''}{contact.company}")
                if contact.last_contact:
                    days_ago = (date.today() - contact.last_contact).days
                    lines.append(f"    Last contact: {days_ago} days ago")
        
        return "\n".join(lines)
    
    def format_follow_ups(self, contacts: List[Contact]) -> str:
        """Format follow-up list."""
        if not contacts:
            return "✅ No follow-ups needed right now!"
        
        lines = ["📬 **Follow-up Reminders**\n"]
        
        for contact in contacts:
            days_since = (date.today() - contact.last_contact).days if contact.last_contact else "?"
            lines.append(f"  • **{contact.name}**")
            if contact.company:
                lines.append(f"    {contact.company}")
            lines.append(f"    Last contact: {days_since} days ago")
            if contact.how_met:
                lines.append(f"    Met: {contact.how_met}")
        
        return "\n".join(lines)
    
    def get_stats(self) -> str:
        """Get networking statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
            
            by_type = conn.execute("""
                SELECT contact_type, COUNT(*) as count 
                FROM contacts 
                GROUP BY contact_type
            """).fetchall()
            
            interactions_30d = conn.execute("""
                SELECT COUNT(*) FROM interactions 
                WHERE date >= ?
            """, ((date.today() - timedelta(days=30)).isoformat(),)).fetchone()[0]
            
            recent_contacts = conn.execute("""
                SELECT COUNT(*) FROM contacts 
                WHERE last_contact >= ?
            """, ((date.today() - timedelta(days=30)).isoformat(),)).fetchone()[0]
        
        lines = [
            "📊 **Networking Stats**\n",
            f"Total Contacts: {total}",
            f"Interactions (30 days): {interactions_30d}",
            f"Active Contacts (30 days): {recent_contacts}\n",
            "**By Type:**",
        ]
        
        type_emoji = {
            "professor": "👨‍🏫",
            "ta": "👨‍🎓",
            "industry": "💼",
            "alumni": "🎓",
            "student": "📚",
            "recruiter": "🔍",
            "mentor": "🌟",
            "other": "👤",
        }
        
        for ctype, count in by_type:
            emoji = type_emoji.get(ctype, "👤")
            lines.append(f"  {emoji} {ctype.title()}: {count}")
        
        return "\n".join(lines)
    
    def toggle_favorite(self, contact_name: str) -> str:
        """Toggle favorite status for a contact."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, name, is_favorite FROM contacts WHERE LOWER(name) LIKE ?",
                (f"%{contact_name.lower()}%",)
            ).fetchone()
            
            if not row:
                return f"No contact found matching '{contact_name}'."
            
            new_status = 0 if row[2] else 1
            conn.execute(
                "UPDATE contacts SET is_favorite = ? WHERE id = ?",
                (new_status, row[0])
            )
            conn.commit()
        
        status = "favorited" if new_status else "unfavorited"
        return f"⭐ {row[1]} {status}"
