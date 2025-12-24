"""
Quick Notes System for JARVIS.

Provides voice-to-note capture with:
- Quick note creation
- Categorization by course/topic
- Search functionality
- Export capabilities
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from loguru import logger


@dataclass
class Note:
    """A quick note."""
    id: Optional[int] = None
    content: str = ""
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    def __str__(self) -> str:
        cat_str = f"[{self.category}] " if self.category else ""
        return f"{cat_str}{self.content}"


class NotesManager:
    """
    Quick notes manager for voice-to-note capture.
    
    Usage:
        notes = NotesManager()
        notes.add("Look up gradient descent for homework", category="Data 8")
        results = notes.search("gradient")
        recent = notes.get_recent(limit=5)
    """
    
    def __init__(self, db_path: str = "data/notes.db"):
        """
        Initialize notes manager.
        
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
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    category TEXT,
                    tags TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notes_category 
                ON notes(category)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notes_created 
                ON notes(created_at)
            """)
            # Full-text search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts 
                USING fts5(content, category, tags, content=notes, content_rowid=id)
            """)
            # Triggers to keep FTS in sync
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
                    INSERT INTO notes_fts(rowid, content, category, tags) 
                    VALUES (new.id, new.content, new.category, new.tags);
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
                    INSERT INTO notes_fts(notes_fts, rowid, content, category, tags) 
                    VALUES ('delete', old.id, old.content, old.category, old.tags);
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
                    INSERT INTO notes_fts(notes_fts, rowid, content, category, tags) 
                    VALUES ('delete', old.id, old.content, old.category, old.tags);
                    INSERT INTO notes_fts(rowid, content, category, tags) 
                    VALUES (new.id, new.content, new.category, new.tags);
                END
            """)
            conn.commit()
    
    # =========================================================================
    # CRUD Operations
    # =========================================================================
    
    def add(
        self,
        content: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Note:
        """
        Add a new note.
        
        Args:
            content: Note content
            category: Optional category (course, topic, etc.)
            tags: Optional list of tags
            
        Returns:
            Created note
        """
        note = Note(
            content=content,
            category=category,
            tags=tags or [],
            created_at=datetime.now(),
        )
        
        tags_str = ",".join(note.tags) if note.tags else None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO notes (content, category, tags, created_at)
                VALUES (?, ?, ?, ?)
            """, (note.content, note.category, tags_str, note.created_at.isoformat()))
            note.id = cursor.lastrowid
            conn.commit()
        
        logger.info(f"Added note: {note.content[:50]}...")
        return note
    
    def get(self, note_id: int) -> Optional[Note]:
        """Get a note by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM notes WHERE id = ?", (note_id,)
            ).fetchone()
            
            if row:
                return self._row_to_note(row)
        return None
    
    def update(
        self,
        note_id: int,
        content: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        Update a note.
        
        Args:
            note_id: Note ID
            content: New content (optional)
            category: New category (optional)
            tags: New tags (optional)
            
        Returns:
            True if updated
        """
        note = self.get(note_id)
        if not note:
            return False
        
        if content is not None:
            note.content = content
        if category is not None:
            note.category = category
        if tags is not None:
            note.tags = tags
        
        note.updated_at = datetime.now()
        tags_str = ",".join(note.tags) if note.tags else None
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE notes 
                SET content = ?, category = ?, tags = ?, updated_at = ?
                WHERE id = ?
            """, (note.content, note.category, tags_str, note.updated_at.isoformat(), note_id))
            conn.commit()
        
        return True
    
    def delete(self, note_id: int) -> bool:
        """Delete a note."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    # =========================================================================
    # Query Operations
    # =========================================================================
    
    def get_recent(self, limit: int = 10) -> List[Note]:
        """Get recent notes."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM notes 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [self._row_to_note(row) for row in rows]
    
    def get_by_category(self, category: str) -> List[Note]:
        """Get notes by category."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM notes 
                WHERE category = ? 
                ORDER BY created_at DESC
            """, (category,)).fetchall()
            
            return [self._row_to_note(row) for row in rows]
    
    def search(self, query: str, limit: int = 20) -> List[Note]:
        """
        Search notes using full-text search.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            Matching notes
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Use FTS5 for search
            rows = conn.execute("""
                SELECT notes.* FROM notes
                JOIN notes_fts ON notes.id = notes_fts.rowid
                WHERE notes_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit)).fetchall()
            
            return [self._row_to_note(row) for row in rows]
    
    def get_categories(self) -> List[str]:
        """Get all unique categories."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT DISTINCT category FROM notes 
                WHERE category IS NOT NULL
                ORDER BY category
            """).fetchall()
            
            return [row[0] for row in rows]
    
    def count(self) -> int:
        """Get total note count."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM notes").fetchone()
            return row[0]
    
    # =========================================================================
    # Export
    # =========================================================================
    
    def export_to_text(self, filepath: str, category: Optional[str] = None) -> str:
        """
        Export notes to a text file.
        
        Args:
            filepath: Output file path
            category: Optional category filter
            
        Returns:
            Path to exported file
        """
        if category:
            notes = self.get_by_category(category)
        else:
            notes = self.get_recent(limit=1000)
        
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# JARVIS Notes Export\n")
            f.write(f"# Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            if category:
                f.write(f"# Category: {category}\n")
            f.write(f"# Total: {len(notes)} notes\n\n")
            
            current_category = None
            for note in notes:
                if note.category != current_category:
                    current_category = note.category
                    f.write(f"\n## {current_category or 'Uncategorized'}\n\n")
                
                date_str = note.created_at.strftime("%Y-%m-%d %H:%M")
                f.write(f"- [{date_str}] {note.content}\n")
                if note.tags:
                    f.write(f"  Tags: {', '.join(note.tags)}\n")
        
        return str(output_path)
    
    # =========================================================================
    # Formatting
    # =========================================================================
    
    def format_notes(self, notes: List[Note], include_date: bool = True) -> str:
        """Format notes as readable string."""
        if not notes:
            return "No notes found."
        
        lines = []
        for note in notes:
            if include_date:
                date_str = note.created_at.strftime("%b %d, %I:%M %p")
                cat_str = f"[{note.category}] " if note.category else ""
                lines.append(f"• {cat_str}{note.content} ({date_str})")
            else:
                cat_str = f"[{note.category}] " if note.category else ""
                lines.append(f"• {cat_str}{note.content}")
        
        return "\n".join(lines)
    
    def _row_to_note(self, row: sqlite3.Row) -> Note:
        """Convert database row to Note object."""
        tags = row["tags"].split(",") if row["tags"] else []
        return Note(
            id=row["id"],
            content=row["content"],
            category=row["category"],
            tags=tags,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        )
