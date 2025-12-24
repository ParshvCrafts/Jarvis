"""
JARVIS Contacts Management System

Provides:
- Contact storage with SQLite database
- CRUD operations for contacts
- Smart contact resolution (name/nickname search)
- CSV/vCard import
- Country code handling
"""

from __future__ import annotations

import csv
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class Contact:
    """Represents a contact."""
    id: int = 0
    name: str = ""
    nickname: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    category: str = "general"
    favorite: bool = False
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "nickname": self.nickname,
            "phone": self.phone,
            "email": self.email,
            "whatsapp": self.whatsapp,
            "category": self.category,
            "favorite": self.favorite,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ContactsDatabase:
    """SQLite database for contacts."""
    
    def __init__(self, db_path: Path, default_country_code: str = "+1"):
        """
        Initialize contacts database.
        
        Args:
            db_path: Path to SQLite database file
            default_country_code: Default country code for phone numbers
        """
        self.db_path = Path(db_path)
        self.default_country_code = default_country_code
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    nickname TEXT,
                    phone TEXT,
                    email TEXT,
                    whatsapp TEXT,
                    category TEXT DEFAULT 'general',
                    favorite INTEGER DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Recent contacts tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recent_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_id INTEGER NOT NULL,
                    action TEXT DEFAULT 'message',
                    contacted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for fast search
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_contacts_name 
                ON contacts(name COLLATE NOCASE)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_contacts_nickname 
                ON contacts(nickname COLLATE NOCASE)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_contacts_category 
                ON contacts(category)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_recent_contacts_time 
                ON recent_contacts(contacted_at DESC)
            """)
            
            conn.commit()
        
        logger.debug("Contacts database initialized")
    
    def _normalize_phone(self, phone: Optional[str]) -> Optional[str]:
        """
        Normalize phone number with country code.
        
        Args:
            phone: Phone number (may or may not have country code)
            
        Returns:
            Normalized phone number with country code
        """
        if not phone:
            return None
        
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # If already has country code, return as-is
        if cleaned.startswith('+'):
            return cleaned
        
        # If starts with 00, replace with +
        if cleaned.startswith('00'):
            return '+' + cleaned[2:]
        
        # Add default country code
        return self.default_country_code + cleaned
    
    def _row_to_contact(self, row: tuple) -> Contact:
        """Convert database row to Contact object."""
        return Contact(
            id=row[0],
            name=row[1],
            nickname=row[2],
            phone=row[3],
            email=row[4],
            whatsapp=row[5],
            category=row[6] or "general",
            favorite=bool(row[7]),
            notes=row[8],
            created_at=datetime.fromisoformat(row[9]) if row[9] else None,
            updated_at=datetime.fromisoformat(row[10]) if row[10] else None,
        )
    
    # =========================================================================
    # CRUD Operations
    # =========================================================================
    
    def add_contact(
        self,
        name: str,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        nickname: Optional[str] = None,
        whatsapp: Optional[str] = None,
        category: str = "general",
        favorite: bool = False,
        notes: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[Contact]]:
        """
        Add a new contact.
        
        Args:
            name: Full name of contact
            phone: Phone number
            email: Email address
            nickname: Nickname for voice recognition
            whatsapp: WhatsApp number (defaults to phone if not provided)
            category: Category (family, friend, work, etc.)
            favorite: Whether this is a favorite contact
            notes: Additional notes
            
        Returns:
            Tuple of (success, message, contact)
        """
        # Normalize phone numbers
        phone = self._normalize_phone(phone)
        whatsapp = self._normalize_phone(whatsapp) or phone
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if contact with same name exists
                cursor.execute(
                    "SELECT id FROM contacts WHERE name = ? COLLATE NOCASE",
                    (name,)
                )
                if cursor.fetchone():
                    return False, f"Contact '{name}' already exists", None
                
                cursor.execute("""
                    INSERT INTO contacts 
                    (name, nickname, phone, email, whatsapp, category, favorite, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, nickname, phone, email, whatsapp, category, int(favorite), notes))
                
                contact_id = cursor.lastrowid
                conn.commit()
                
                # Fetch the created contact
                contact = self.get_contact_by_id(contact_id)
                logger.info(f"Added contact: {name}")
                return True, f"Added {name} to contacts", contact
                
        except Exception as e:
            logger.error(f"Failed to add contact: {e}")
            return False, f"Failed to add contact: {e}", None
    
    def update_contact(
        self,
        contact_id: int,
        **fields
    ) -> Tuple[bool, str]:
        """
        Update an existing contact.
        
        Args:
            contact_id: ID of contact to update
            **fields: Fields to update
            
        Returns:
            Tuple of (success, message)
        """
        if not fields:
            return False, "No fields to update"
        
        # Normalize phone numbers if provided
        if 'phone' in fields:
            fields['phone'] = self._normalize_phone(fields['phone'])
        if 'whatsapp' in fields:
            fields['whatsapp'] = self._normalize_phone(fields['whatsapp'])
        
        # Build update query
        set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
        values = list(fields.values())
        values.append(contact_id)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(f"""
                    UPDATE contacts 
                    SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, values)
                
                if cursor.rowcount == 0:
                    return False, "Contact not found"
                
                conn.commit()
                logger.info(f"Updated contact ID {contact_id}")
                return True, "Contact updated"
                
        except Exception as e:
            logger.error(f"Failed to update contact: {e}")
            return False, f"Failed to update contact: {e}"
    
    def delete_contact(self, contact_id: Optional[int] = None, name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Delete a contact by ID or name.
        
        Args:
            contact_id: ID of contact to delete
            name: Name of contact to delete
            
        Returns:
            Tuple of (success, message)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if contact_id:
                    cursor.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
                elif name:
                    cursor.execute("DELETE FROM contacts WHERE name = ? COLLATE NOCASE", (name,))
                else:
                    return False, "Must provide contact_id or name"
                
                if cursor.rowcount == 0:
                    return False, "Contact not found"
                
                conn.commit()
                logger.info(f"Deleted contact: {contact_id or name}")
                return True, "Contact deleted"
                
        except Exception as e:
            logger.error(f"Failed to delete contact: {e}")
            return False, f"Failed to delete contact: {e}"
    
    def get_contact_by_id(self, contact_id: int) -> Optional[Contact]:
        """Get contact by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,))
            row = cursor.fetchone()
            return self._row_to_contact(row) if row else None
    
    def get_contact(self, name_or_nickname: str) -> Optional[Contact]:
        """
        Get contact by name or nickname.
        
        Searches nickname first (for voice commands like "Papa"),
        then falls back to name search.
        
        Args:
            name_or_nickname: Name or nickname to search
            
        Returns:
            Contact if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # First try exact nickname match
            cursor.execute(
                "SELECT * FROM contacts WHERE nickname = ? COLLATE NOCASE",
                (name_or_nickname,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_contact(row)
            
            # Then try exact name match
            cursor.execute(
                "SELECT * FROM contacts WHERE name = ? COLLATE NOCASE",
                (name_or_nickname,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_contact(row)
            
            return None
    
    def search_contacts(self, query: str, limit: int = 10) -> List[Contact]:
        """
        Search contacts by name or nickname (fuzzy search).
        
        Args:
            query: Search query
            limit: Maximum results to return
            
        Returns:
            List of matching contacts
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Use LIKE for fuzzy matching
            pattern = f"%{query}%"
            cursor.execute("""
                SELECT * FROM contacts 
                WHERE name LIKE ? COLLATE NOCASE 
                   OR nickname LIKE ? COLLATE NOCASE
                ORDER BY favorite DESC, name ASC
                LIMIT ?
            """, (pattern, pattern, limit))
            
            return [self._row_to_contact(row) for row in cursor.fetchall()]
    
    def list_contacts(
        self,
        category: Optional[str] = None,
        favorites_only: bool = False,
        limit: int = 100
    ) -> List[Contact]:
        """
        List all contacts, optionally filtered.
        
        Args:
            category: Filter by category
            favorites_only: Only return favorites
            limit: Maximum results
            
        Returns:
            List of contacts
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM contacts WHERE 1=1"
            params = []
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            if favorites_only:
                query += " AND favorite = 1"
            
            query += " ORDER BY favorite DESC, name ASC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return [self._row_to_contact(row) for row in cursor.fetchall()]
    
    def count_contacts(self) -> int:
        """Get total number of contacts."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM contacts")
            return cursor.fetchone()[0]
    
    # =========================================================================
    # Recent Contacts
    # =========================================================================
    
    def log_contact(self, contact_id: int, action: str = "message") -> None:
        """
        Log a contact interaction for recent contacts tracking.
        
        Args:
            contact_id: ID of the contact
            action: Type of action (message, call, video_call)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO recent_contacts (contact_id, action) VALUES (?, ?)",
                    (contact_id, action)
                )
                conn.commit()
        except Exception as e:
            logger.debug(f"Failed to log contact: {e}")
    
    def get_recent_contacts(self, limit: int = 5) -> List[Contact]:
        """
        Get recently contacted people.
        
        Args:
            limit: Maximum number of recent contacts
            
        Returns:
            List of recently contacted people (most recent first)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get unique recent contacts ordered by most recent
            cursor.execute("""
                SELECT DISTINCT c.* FROM contacts c
                INNER JOIN recent_contacts r ON c.id = r.contact_id
                ORDER BY r.contacted_at DESC
                LIMIT ?
            """, (limit,))
            
            return [self._row_to_contact(row) for row in cursor.fetchall()]
    
    # =========================================================================
    # Favorites
    # =========================================================================
    
    def set_favorite(self, contact_id: int, favorite: bool = True) -> Tuple[bool, str]:
        """Set or unset a contact as favorite."""
        return self.update_contact(contact_id, favorite=int(favorite))
    
    def get_favorites(self, limit: int = 10) -> List[Contact]:
        """Get favorite contacts."""
        return self.list_contacts(favorites_only=True, limit=limit)
    
    # =========================================================================
    # Fuzzy Matching / Suggestions
    # =========================================================================
    
    def suggest_contact(self, query: str, threshold: float = 0.6) -> List[Tuple[Contact, float]]:
        """
        Find contacts similar to query (for "Did you mean?" suggestions).
        
        Uses simple similarity scoring based on:
        - Substring matching
        - Common prefix/suffix
        - Character overlap
        
        Args:
            query: Search query
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of (contact, score) tuples sorted by score
        """
        query_lower = query.lower()
        results = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM contacts")
            
            for row in cursor.fetchall():
                contact = self._row_to_contact(row)
                
                # Calculate similarity for name and nickname
                name_score = self._similarity(query_lower, contact.name.lower())
                nickname_score = 0.0
                if contact.nickname:
                    nickname_score = self._similarity(query_lower, contact.nickname.lower())
                
                best_score = max(name_score, nickname_score)
                
                if best_score >= threshold:
                    results.append((contact, best_score))
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:5]
    
    # Common aliases for relationship names
    RELATIONSHIP_ALIASES = {
        "dad": ["papa", "father", "daddy", "pop", "pops", "pa"],
        "mom": ["mama", "mother", "mommy", "mum", "mummy", "ma"],
        "papa": ["dad", "father", "daddy", "pop", "pops", "pa"],
        "mama": ["mom", "mother", "mommy", "mum", "mummy", "ma"],
        "daddy": ["dad", "papa", "father", "pop", "pops", "pa"],
        "mommy": ["mom", "mama", "mother", "mum", "mummy", "ma"],
    }
    
    def _similarity(self, s1: str, s2: str) -> float:
        """
        Calculate similarity between two strings.
        
        Simple algorithm combining:
        - Exact match (1.0)
        - Relationship alias match (0.85)
        - Substring match (0.8)
        - Common prefix (0.6)
        - Character overlap (Jaccard similarity)
        """
        if s1 == s2:
            return 1.0
        
        # Check relationship aliases (daddy -> papa, etc.)
        s1_aliases = self.RELATIONSHIP_ALIASES.get(s1, [])
        s2_aliases = self.RELATIONSHIP_ALIASES.get(s2, [])
        if s2 in s1_aliases or s1 in s2_aliases:
            return 0.85
        
        # Substring match
        if s1 in s2 or s2 in s1:
            return 0.8
        
        # Common prefix
        prefix_len = 0
        for c1, c2 in zip(s1, s2):
            if c1 == c2:
                prefix_len += 1
            else:
                break
        
        if prefix_len >= 3:
            return 0.6 + (prefix_len / max(len(s1), len(s2))) * 0.2
        
        # Character overlap (Jaccard)
        set1 = set(s1)
        set2 = set(s2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 0.0
        
        return intersection / union * 0.5
    
    # =========================================================================
    # Import Functions
    # =========================================================================
    
    def import_from_csv(self, csv_path: Path) -> Tuple[int, int, List[str]]:
        """
        Import contacts from CSV file.
        
        Expected columns: name, phone, email, nickname, category
        (Google Contacts export format supported)
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Tuple of (imported_count, skipped_count, errors)
        """
        imported = 0
        skipped = 0
        errors = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # Handle different column name formats
                    name = row.get('Name') or row.get('name') or row.get('Full Name')
                    phone = row.get('Phone') or row.get('phone') or row.get('Phone 1 - Value')
                    email = row.get('Email') or row.get('email') or row.get('E-mail 1 - Value')
                    nickname = row.get('Nickname') or row.get('nickname')
                    category = row.get('Category') or row.get('category') or row.get('Group Membership')
                    
                    if not name:
                        skipped += 1
                        continue
                    
                    success, msg, _ = self.add_contact(
                        name=name,
                        phone=phone,
                        email=email,
                        nickname=nickname,
                        category=category or "imported",
                    )
                    
                    if success:
                        imported += 1
                    else:
                        skipped += 1
                        if "already exists" not in msg:
                            errors.append(f"{name}: {msg}")
            
            logger.info(f"Imported {imported} contacts from CSV, skipped {skipped}")
            return imported, skipped, errors
            
        except Exception as e:
            logger.error(f"CSV import failed: {e}")
            return imported, skipped, [str(e)]
    
    def import_from_vcard(self, vcard_path: Path) -> Tuple[int, int, List[str]]:
        """
        Import contacts from vCard (.vcf) file.
        
        Args:
            vcard_path: Path to vCard file
            
        Returns:
            Tuple of (imported_count, skipped_count, errors)
        """
        imported = 0
        skipped = 0
        errors = []
        
        try:
            with open(vcard_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into individual vCards
            vcards = content.split('BEGIN:VCARD')
            
            for vcard in vcards:
                if not vcard.strip():
                    continue
                
                # Parse vCard fields
                name = None
                phone = None
                email = None
                
                for line in vcard.split('\n'):
                    line = line.strip()
                    
                    if line.startswith('FN:'):
                        name = line[3:]
                    elif line.startswith('TEL'):
                        # Extract phone number
                        phone = line.split(':')[-1]
                    elif line.startswith('EMAIL'):
                        email = line.split(':')[-1]
                
                if not name:
                    skipped += 1
                    continue
                
                success, msg, _ = self.add_contact(
                    name=name,
                    phone=phone,
                    email=email,
                    category="imported",
                )
                
                if success:
                    imported += 1
                else:
                    skipped += 1
                    if "already exists" not in msg:
                        errors.append(f"{name}: {msg}")
            
            logger.info(f"Imported {imported} contacts from vCard, skipped {skipped}")
            return imported, skipped, errors
            
        except Exception as e:
            logger.error(f"vCard import failed: {e}")
            return imported, skipped, [str(e)]


class ContactsManager:
    """
    High-level contacts manager with voice command support.
    """
    
    def __init__(self, db_path: Path, default_country_code: str = "+1"):
        """
        Initialize contacts manager.
        
        Args:
            db_path: Path to contacts database
            default_country_code: Default country code
        """
        self.db = ContactsDatabase(db_path, default_country_code)
        self.default_country_code = default_country_code
    
    def resolve_contact(self, name_or_nickname: str) -> Tuple[Optional[Contact], str]:
        """
        Resolve a contact name/nickname to a Contact object.
        
        Includes "Did you mean?" suggestions for similar names.
        
        Args:
            name_or_nickname: Name or nickname to resolve
            
        Returns:
            Tuple of (contact, message)
        """
        # Try exact match first
        contact = self.db.get_contact(name_or_nickname)
        if contact:
            return contact, f"Found {contact.name}"
        
        # Try fuzzy search
        matches = self.db.search_contacts(name_or_nickname, limit=5)
        
        if len(matches) == 1:
            return matches[0], f"Found {matches[0].name}"
        elif len(matches) > 1:
            names = [c.name for c in matches]
            return None, f"Multiple matches found: {', '.join(names)}. Please be more specific."
        
        # Try similarity-based suggestions ("Did you mean?")
        suggestions = self.db.suggest_contact(name_or_nickname, threshold=0.4)
        if suggestions:
            best_match, score = suggestions[0]
            if score >= 0.6:
                # High confidence - suggest the match
                return None, f"I don't have '{name_or_nickname}' in contacts. Did you mean '{best_match.name}'?"
            elif len(suggestions) <= 3:
                # Lower confidence - show options
                names = [c.name for c, _ in suggestions]
                return None, f"I don't have '{name_or_nickname}'. Did you mean: {', '.join(names)}?"
        
        return None, f"No contact found for '{name_or_nickname}'. Would you like to add them?"
    
    def get_phone_number(self, name_or_nickname: str) -> Tuple[Optional[str], str]:
        """
        Get phone number for a contact.
        
        Args:
            name_or_nickname: Contact name or nickname
            
        Returns:
            Tuple of (phone_number, message)
        """
        contact, msg = self.resolve_contact(name_or_nickname)
        
        if not contact:
            return None, msg
        
        if not contact.phone:
            return None, f"{contact.name} doesn't have a phone number saved"
        
        return contact.phone, f"{contact.name}'s phone number is {contact.phone}"
    
    def get_whatsapp_number(self, name_or_nickname: str) -> Tuple[Optional[str], str]:
        """
        Get WhatsApp number for a contact.
        
        Args:
            name_or_nickname: Contact name or nickname
            
        Returns:
            Tuple of (whatsapp_number, message)
        """
        contact, msg = self.resolve_contact(name_or_nickname)
        
        if not contact:
            return None, msg
        
        whatsapp = contact.whatsapp or contact.phone
        if not whatsapp:
            return None, f"{contact.name} doesn't have a WhatsApp number saved"
        
        return whatsapp, f"{contact.name}'s WhatsApp number is {whatsapp}"
    
    def get_email(self, name_or_nickname: str) -> Tuple[Optional[str], str]:
        """
        Get email for a contact.
        
        Args:
            name_or_nickname: Contact name or nickname
            
        Returns:
            Tuple of (email, message)
        """
        contact, msg = self.resolve_contact(name_or_nickname)
        
        if not contact:
            return None, msg
        
        if not contact.email:
            return None, f"{contact.name} doesn't have an email saved"
        
        return contact.email, f"{contact.name}'s email is {contact.email}"
    
    # =========================================================================
    # Voice Command Helpers
    # =========================================================================
    
    def add_contact(
        self,
        name: str,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        nickname: Optional[str] = None,
        whatsapp: Optional[str] = None,
        category: str = "general",
        favorite: bool = False,
    ) -> Tuple[bool, str]:
        """Add a contact (voice command wrapper)."""
        success, msg, _ = self.db.add_contact(
            name=name,
            phone=phone,
            email=email,
            nickname=nickname,
            whatsapp=whatsapp,
            category=category,
            favorite=favorite,
        )
        return success, msg
    
    def delete_contact(self, name: str) -> Tuple[bool, str]:
        """Delete a contact by name."""
        return self.db.delete_contact(name=name)
    
    def list_contacts(self, category: Optional[str] = None) -> List[Contact]:
        """List contacts."""
        return self.db.list_contacts(category=category)
    
    def search_contacts(self, query: str) -> List[Contact]:
        """Search contacts."""
        return self.db.search_contacts(query)
    
    def import_contacts(self, file_path: str) -> Tuple[int, int, str]:
        """
        Import contacts from file.
        
        Args:
            file_path: Path to CSV or vCard file
            
        Returns:
            Tuple of (imported, skipped, message)
        """
        path = Path(file_path)
        
        if not path.exists():
            return 0, 0, f"File not found: {file_path}"
        
        if path.suffix.lower() == '.csv':
            imported, skipped, errors = self.db.import_from_csv(path)
        elif path.suffix.lower() in ['.vcf', '.vcard']:
            imported, skipped, errors = self.db.import_from_vcard(path)
        else:
            return 0, 0, f"Unsupported file format: {path.suffix}"
        
        if errors:
            return imported, skipped, f"Imported {imported} contacts with {len(errors)} errors"
        return imported, skipped, f"Imported {imported} contacts successfully"
    
    def get_contact_count(self) -> int:
        """Get total number of contacts."""
        return self.db.count_contacts()
    
    # =========================================================================
    # Recent Contacts
    # =========================================================================
    
    def log_contact_interaction(self, contact: Contact, action: str = "message") -> None:
        """Log a contact interaction for recent contacts tracking."""
        self.db.log_contact(contact.id, action)
    
    def get_recent_contacts(self, limit: int = 5) -> List[Contact]:
        """Get recently contacted people."""
        return self.db.get_recent_contacts(limit)
    
    # =========================================================================
    # Favorites
    # =========================================================================
    
    def set_favorite(self, name: str, favorite: bool = True) -> Tuple[bool, str]:
        """Set or unset a contact as favorite."""
        contact = self.db.get_contact(name)
        if not contact:
            return False, f"Contact '{name}' not found"
        
        success, msg = self.db.set_favorite(contact.id, favorite)
        if success:
            action = "added to" if favorite else "removed from"
            return True, f"{contact.name} {action} favorites"
        return False, msg
    
    def get_favorites(self, limit: int = 10) -> List[Contact]:
        """Get favorite contacts."""
        return self.db.get_favorites(limit)
