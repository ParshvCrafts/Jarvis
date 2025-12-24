"""
Project Persistence for JARVIS Research Module.

Handles:
- Research project storage
- Source tracking
- Progress state management
- Resume capability
"""

import json
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .source_manager import Source, SourceStatus
from .citation_manager import CitationStyle


class ProjectStatus(Enum):
    """Research project status."""
    PLANNING = "planning"
    RESEARCHING = "researching"
    ANALYZING = "analyzing"
    WRITING = "writing"
    FINALIZING = "finalizing"
    COMPLETE = "complete"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class ResearchProject:
    """A research project with all its data."""
    # Core info
    id: Optional[int] = None
    topic: str = ""
    title: str = ""
    thesis: str = ""
    
    # Requirements
    page_count: int = 10
    citation_style: str = "apa"
    focus_areas: List[str] = field(default_factory=list)
    custom_requirements: str = ""
    
    # Status
    status: ProjectStatus = ProjectStatus.PLANNING
    current_section: str = ""
    progress_percent: float = 0.0
    
    # Google Docs
    google_doc_id: Optional[str] = None
    google_doc_url: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # Stats
    word_count: int = 0
    source_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "topic": self.topic,
            "title": self.title,
            "thesis": self.thesis,
            "page_count": self.page_count,
            "citation_style": self.citation_style,
            "focus_areas": json.dumps(self.focus_areas),
            "custom_requirements": self.custom_requirements,
            "status": self.status.value,
            "current_section": self.current_section,
            "progress_percent": self.progress_percent,
            "google_doc_id": self.google_doc_id,
            "google_doc_url": self.google_doc_url,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "word_count": self.word_count,
            "source_count": self.source_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchProject":
        """Create from dictionary."""
        return cls(
            id=data.get("id"),
            topic=data.get("topic", ""),
            title=data.get("title", ""),
            thesis=data.get("thesis", ""),
            page_count=data.get("page_count", 10),
            citation_style=data.get("citation_style", "apa"),
            focus_areas=json.loads(data.get("focus_areas", "[]")),
            custom_requirements=data.get("custom_requirements", ""),
            status=ProjectStatus(data.get("status", "planning")),
            current_section=data.get("current_section", ""),
            progress_percent=data.get("progress_percent", 0.0),
            google_doc_id=data.get("google_doc_id"),
            google_doc_url=data.get("google_doc_url"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            word_count=data.get("word_count", 0),
            source_count=data.get("source_count", 0),
        )
    
    def get_status_display(self) -> str:
        """Get human-readable status."""
        status_icons = {
            ProjectStatus.PLANNING: "📋",
            ProjectStatus.RESEARCHING: "🔍",
            ProjectStatus.ANALYZING: "📊",
            ProjectStatus.WRITING: "✍️",
            ProjectStatus.FINALIZING: "📝",
            ProjectStatus.COMPLETE: "✅",
            ProjectStatus.PAUSED: "⏸️",
            ProjectStatus.ERROR: "❌",
        }
        icon = status_icons.get(self.status, "❓")
        return f"{icon} {self.status.value.title()}"


class ProjectStore:
    """
    SQLite-based storage for research projects.
    
    Stores:
    - Project metadata
    - Sources
    - Section content
    - Progress state
    """
    
    def __init__(self, db_path: str = "data/research_projects.db"):
        """
        Initialize project store.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Research projects table
                CREATE TABLE IF NOT EXISTS research_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    title TEXT,
                    thesis TEXT,
                    page_count INTEGER DEFAULT 10,
                    citation_style TEXT DEFAULT 'apa',
                    focus_areas TEXT DEFAULT '[]',
                    custom_requirements TEXT,
                    status TEXT DEFAULT 'planning',
                    current_section TEXT,
                    progress_percent REAL DEFAULT 0.0,
                    google_doc_id TEXT,
                    google_doc_url TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    completed_at TEXT,
                    word_count INTEGER DEFAULT 0,
                    source_count INTEGER DEFAULT 0
                );
                
                -- Research sources table
                CREATE TABLE IF NOT EXISTS research_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    source_id TEXT,
                    title TEXT NOT NULL,
                    authors TEXT,
                    year INTEGER,
                    abstract TEXT,
                    doi TEXT,
                    url TEXT,
                    pdf_url TEXT,
                    citation_count INTEGER DEFAULT 0,
                    source_database TEXT,
                    venue TEXT,
                    keywords TEXT DEFAULT '[]',
                    is_open_access INTEGER DEFAULT 0,
                    summary TEXT,
                    key_findings TEXT DEFAULT '[]',
                    relevant_quotes TEXT DEFAULT '[]',
                    methodology TEXT,
                    relevance_score REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'found',
                    added_at TEXT,
                    FOREIGN KEY (project_id) REFERENCES research_projects(id)
                );
                
                -- Research sections table
                CREATE TABLE IF NOT EXISTS research_sections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    section_name TEXT NOT NULL,
                    level INTEGER DEFAULT 1,
                    content TEXT,
                    word_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    section_order INTEGER DEFAULT 0,
                    FOREIGN KEY (project_id) REFERENCES research_projects(id)
                );
                
                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_sources_project ON research_sources(project_id);
                CREATE INDEX IF NOT EXISTS idx_sections_project ON research_sections(project_id);
            """)
            conn.commit()
        
        logger.debug(f"Research database initialized at {self.db_path}")
    
    # =========================================================================
    # Project Operations
    # =========================================================================
    
    def create_project(self, project: ResearchProject) -> int:
        """
        Create a new research project.
        
        Args:
            project: Project to create
            
        Returns:
            Project ID
        """
        project.created_at = datetime.now()
        project.updated_at = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO research_projects (
                    topic, title, thesis, page_count, citation_style,
                    focus_areas, custom_requirements, status, current_section,
                    progress_percent, google_doc_id, google_doc_url,
                    created_at, updated_at, word_count, source_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project.topic, project.title, project.thesis,
                project.page_count, project.citation_style,
                json.dumps(project.focus_areas), project.custom_requirements,
                project.status.value, project.current_section,
                project.progress_percent, project.google_doc_id,
                project.google_doc_url, project.created_at.isoformat(),
                project.updated_at.isoformat(), project.word_count,
                project.source_count,
            ))
            project.id = cursor.lastrowid
            conn.commit()
        
        logger.info(f"Created research project: {project.topic} (ID: {project.id})")
        return project.id
    
    def update_project(self, project: ResearchProject):
        """Update an existing project."""
        project.updated_at = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE research_projects SET
                    topic = ?, title = ?, thesis = ?, page_count = ?,
                    citation_style = ?, focus_areas = ?, custom_requirements = ?,
                    status = ?, current_section = ?, progress_percent = ?,
                    google_doc_id = ?, google_doc_url = ?, updated_at = ?,
                    completed_at = ?, word_count = ?, source_count = ?
                WHERE id = ?
            """, (
                project.topic, project.title, project.thesis,
                project.page_count, project.citation_style,
                json.dumps(project.focus_areas), project.custom_requirements,
                project.status.value, project.current_section,
                project.progress_percent, project.google_doc_id,
                project.google_doc_url, project.updated_at.isoformat(),
                project.completed_at.isoformat() if project.completed_at else None,
                project.word_count, project.source_count, project.id,
            ))
            conn.commit()
    
    def get_project(self, project_id: int) -> Optional[ResearchProject]:
        """Get project by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM research_projects WHERE id = ?",
                (project_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return ResearchProject.from_dict(dict(row))
        return None
    
    def get_project_by_topic(self, topic: str) -> Optional[ResearchProject]:
        """Get project by topic (partial match)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM research_projects WHERE topic LIKE ? ORDER BY created_at DESC LIMIT 1",
                (f"%{topic}%",)
            )
            row = cursor.fetchone()
            
            if row:
                return ResearchProject.from_dict(dict(row))
        return None
    
    def get_all_projects(self, limit: int = 20) -> List[ResearchProject]:
        """Get all projects, most recent first."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM research_projects ORDER BY updated_at DESC LIMIT ?",
                (limit,)
            )
            return [ResearchProject.from_dict(dict(row)) for row in cursor.fetchall()]
    
    def get_incomplete_projects(self) -> List[ResearchProject]:
        """Get projects that aren't complete."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM research_projects WHERE status != 'complete' ORDER BY updated_at DESC"
            )
            return [ResearchProject.from_dict(dict(row)) for row in cursor.fetchall()]
    
    def delete_project(self, project_id: int):
        """Delete a project and all its data."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM research_sources WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM research_sections WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM research_projects WHERE id = ?", (project_id,))
            conn.commit()
        
        logger.info(f"Deleted research project ID: {project_id}")
    
    # =========================================================================
    # Source Operations
    # =========================================================================
    
    def add_source(self, project_id: int, source: Source) -> int:
        """Add a source to a project."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO research_sources (
                    project_id, source_id, title, authors, year, abstract,
                    doi, url, pdf_url, citation_count, source_database,
                    venue, keywords, is_open_access, summary, key_findings,
                    relevant_quotes, methodology, relevance_score, status, added_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_id, source.id, source.title,
                json.dumps(source.authors), source.year, source.abstract,
                source.doi, source.url, source.pdf_url, source.citation_count,
                source.source_database, source.venue,
                json.dumps(source.keywords), int(source.is_open_access),
                source.summary, json.dumps(source.key_findings),
                json.dumps(source.relevant_quotes), source.methodology,
                source.relevance_score, source.status.value,
                source.added_at.isoformat(),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def add_sources(self, project_id: int, sources: List[Source]):
        """Add multiple sources to a project."""
        for source in sources:
            self.add_source(project_id, source)
        
        # Update source count
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE research_projects SET source_count = ? WHERE id = ?",
                (len(sources), project_id)
            )
            conn.commit()
    
    def get_sources(self, project_id: int) -> List[Source]:
        """Get all sources for a project."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM research_sources WHERE project_id = ? ORDER BY relevance_score DESC",
                (project_id,)
            )
            
            sources = []
            for row in cursor.fetchall():
                source = Source(
                    title=row["title"],
                    authors=json.loads(row["authors"]),
                    year=row["year"],
                    abstract=row["abstract"],
                    doi=row["doi"],
                    url=row["url"],
                    pdf_url=row["pdf_url"],
                    citation_count=row["citation_count"],
                    source_database=row["source_database"],
                    venue=row["venue"],
                    keywords=json.loads(row["keywords"]),
                    is_open_access=bool(row["is_open_access"]),
                    summary=row["summary"],
                    key_findings=json.loads(row["key_findings"]),
                    relevant_quotes=json.loads(row["relevant_quotes"]),
                    methodology=row["methodology"],
                    relevance_score=row["relevance_score"],
                    status=SourceStatus(row["status"]),
                    id=row["source_id"],
                )
                sources.append(source)
            
            return sources
    
    def get_selected_sources(self, project_id: int) -> List[Source]:
        """Get selected sources for a project."""
        sources = self.get_sources(project_id)
        return [s for s in sources if s.status in [SourceStatus.SELECTED, SourceStatus.ANALYZED, SourceStatus.CITED]]
    
    # =========================================================================
    # Section Operations
    # =========================================================================
    
    def save_section(
        self,
        project_id: int,
        section_name: str,
        content: str,
        level: int = 1,
        order: int = 0,
    ):
        """Save or update a section."""
        word_count = len(content.split())
        
        with sqlite3.connect(self.db_path) as conn:
            # Check if section exists
            cursor = conn.execute(
                "SELECT id FROM research_sections WHERE project_id = ? AND section_name = ?",
                (project_id, section_name)
            )
            existing = cursor.fetchone()
            
            if existing:
                conn.execute("""
                    UPDATE research_sections SET
                        content = ?, word_count = ?, status = 'complete'
                    WHERE project_id = ? AND section_name = ?
                """, (content, word_count, project_id, section_name))
            else:
                conn.execute("""
                    INSERT INTO research_sections (
                        project_id, section_name, level, content,
                        word_count, status, section_order
                    ) VALUES (?, ?, ?, ?, ?, 'complete', ?)
                """, (project_id, section_name, level, content, word_count, order))
            
            conn.commit()
    
    def get_sections(self, project_id: int) -> List[Dict[str, Any]]:
        """Get all sections for a project."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM research_sections WHERE project_id = ? ORDER BY section_order",
                (project_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_projects_summary(self) -> str:
        """Get summary of all projects."""
        projects = self.get_all_projects(limit=10)
        
        if not projects:
            return "No research projects found."
        
        lines = ["📚 **Research Projects**", ""]
        
        for project in projects:
            status = project.get_status_display()
            date = project.updated_at.strftime("%Y-%m-%d")
            lines.append(f"- **{project.topic}** ({status}) - {date}")
            if project.google_doc_url:
                lines.append(f"  📄 [Document]({project.google_doc_url})")
        
        return "\n".join(lines)
    
    def update_progress(
        self,
        project_id: int,
        status: ProjectStatus,
        progress: float,
        current_section: str = "",
    ):
        """Update project progress."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE research_projects SET
                    status = ?, progress_percent = ?, current_section = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                status.value, progress, current_section,
                datetime.now().isoformat(), project_id,
            ))
            conn.commit()
    
    def mark_complete(
        self,
        project_id: int,
        google_doc_url: str,
        word_count: int,
    ):
        """Mark project as complete."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE research_projects SET
                    status = 'complete', progress_percent = 100.0,
                    google_doc_url = ?, word_count = ?,
                    completed_at = ?, updated_at = ?
                WHERE id = ?
            """, (
                google_doc_url, word_count,
                datetime.now().isoformat(), datetime.now().isoformat(),
                project_id,
            ))
            conn.commit()
        
        logger.info(f"Research project {project_id} marked complete")
