"""
Essay Import Tools for JARVIS Scholarship Module.

Handles:
- Bulk import of past essays from files
- Personal statement import
- Profile information import
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .models import (
    PastEssay,
    PersonalStatement,
    PersonalProfile,
    EssayOutcome,
)
from .rag import ScholarshipRAG

# Try importing document parsing libraries
DOCX_AVAILABLE = False
PDF_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    logger.debug("python-docx not installed")

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    logger.debug("PyPDF2 not installed")


class EssayImporter:
    """
    Import past essays and personal information for RAG.
    
    Supports:
    - Text files (.txt)
    - Word documents (.docx)
    - PDF files (.pdf)
    - Markdown files (.md)
    """
    
    def __init__(
        self,
        rag: Optional[ScholarshipRAG] = None,
    ):
        """
        Initialize essay importer.
        
        Args:
            rag: RAG system to add essays to
        """
        self.rag = rag
        self._imported_count = 0
        self._failed_count = 0
    
    # =========================================================================
    # File Reading
    # =========================================================================
    
    def read_text_file(self, path: Path) -> str:
        """Read a text file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(path, "r", encoding="latin-1") as f:
                return f.read()
    
    def read_docx_file(self, path: Path) -> str:
        """Read a Word document."""
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx not installed. Run: pip install python-docx")
        
        doc = docx.Document(path)
        paragraphs = [p.text for p in doc.paragraphs]
        return "\n\n".join(paragraphs)
    
    def read_pdf_file(self, path: Path) -> str:
        """Read a PDF file."""
        if not PDF_AVAILABLE:
            raise ImportError("PyPDF2 not installed. Run: pip install PyPDF2")
        
        text = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text.append(page.extract_text())
        
        return "\n\n".join(text)
    
    def read_file(self, path: Path) -> str:
        """
        Read any supported file type.
        
        Args:
            path: Path to file
            
        Returns:
            File contents as string
        """
        suffix = path.suffix.lower()
        
        if suffix in [".txt", ".md"]:
            return self.read_text_file(path)
        elif suffix == ".docx":
            return self.read_docx_file(path)
        elif suffix == ".pdf":
            return self.read_pdf_file(path)
        else:
            # Try as text
            return self.read_text_file(path)
    
    # =========================================================================
    # Essay Parsing
    # =========================================================================
    
    def parse_essay_file(
        self,
        path: Path,
        default_scholarship: str = "Unknown",
    ) -> Optional[PastEssay]:
        """
        Parse an essay from a file.
        
        Expected formats:
        1. Filename: "ScholarshipName_Question.txt"
        2. File content with headers:
           Scholarship: Name
           Question: The question
           Outcome: won/lost/pending
           ---
           Essay content here
        
        Args:
            path: Path to essay file
            default_scholarship: Default scholarship name if not found
            
        Returns:
            PastEssay object or None
        """
        try:
            content = self.read_file(path)
            
            # Try to parse structured format
            scholarship_name = default_scholarship
            question = ""
            outcome = EssayOutcome.PENDING
            essay_text = content
            
            # Check for header format
            if "---" in content:
                parts = content.split("---", 1)
                header = parts[0]
                essay_text = parts[1].strip() if len(parts) > 1 else content
                
                # Parse header
                for line in header.split("\n"):
                    line = line.strip()
                    if line.lower().startswith("scholarship:"):
                        scholarship_name = line.split(":", 1)[1].strip()
                    elif line.lower().startswith("question:"):
                        question = line.split(":", 1)[1].strip()
                    elif line.lower().startswith("outcome:"):
                        outcome_str = line.split(":", 1)[1].strip().lower()
                        if outcome_str in ["won", "winner", "winning"]:
                            outcome = EssayOutcome.WON
                        elif outcome_str in ["lost", "rejected", "denied"]:
                            outcome = EssayOutcome.LOST
            
            # Try to get scholarship name from filename
            if scholarship_name == default_scholarship:
                filename = path.stem
                # Remove common suffixes
                filename = re.sub(r'_essay|_response|_\d+$', '', filename, flags=re.IGNORECASE)
                scholarship_name = filename.replace("_", " ").replace("-", " ").title()
            
            # Extract themes
            themes = self._extract_themes(essay_text)
            
            essay = PastEssay(
                scholarship_name=scholarship_name,
                question=question or f"Essay for {scholarship_name}",
                essay_text=essay_text,
                word_count=len(essay_text.split()),
                outcome=outcome,
                themes=themes,
                date_written=datetime.fromtimestamp(path.stat().st_mtime),
            )
            
            return essay
            
        except Exception as e:
            logger.error(f"Failed to parse essay file {path}: {e}")
            return None
    
    def _extract_themes(self, text: str) -> List[str]:
        """Extract themes from essay text."""
        theme_keywords = {
            "leadership": ["lead", "leader", "leadership", "captain", "president", "founded", "organized"],
            "community": ["community", "volunteer", "service", "help", "impact", "give back", "nonprofit"],
            "academic": ["research", "study", "academic", "gpa", "honors", "scholar", "professor"],
            "diversity": ["diverse", "diversity", "culture", "background", "identity", "heritage"],
            "challenge": ["challenge", "overcome", "obstacle", "struggle", "adversity", "difficult"],
            "growth": ["grow", "growth", "learn", "develop", "improve", "change", "transform"],
            "passion": ["passion", "passionate", "love", "dedicate", "commit", "dream"],
            "innovation": ["innovate", "create", "invent", "new", "solution", "technology", "build"],
            "career": ["career", "goal", "future", "aspire", "profession", "industry"],
            "family": ["family", "parent", "mother", "father", "sibling", "heritage", "immigrant"],
            "stem": ["science", "technology", "engineering", "math", "data", "computer", "ai", "machine learning"],
            "social_impact": ["social", "justice", "equality", "change", "policy", "advocate"],
        }
        
        text_lower = text.lower()
        found_themes = []
        
        for theme, keywords in theme_keywords.items():
            if any(kw in text_lower for kw in keywords):
                found_themes.append(theme)
        
        return found_themes
    
    # =========================================================================
    # Bulk Import
    # =========================================================================
    
    async def import_folder(
        self,
        folder_path: str,
        recursive: bool = True,
        default_outcome: EssayOutcome = EssayOutcome.PENDING,
    ) -> Tuple[int, int]:
        """
        Import all essays from a folder.
        
        Args:
            folder_path: Path to folder containing essays
            recursive: Search subdirectories
            default_outcome: Default outcome for essays
            
        Returns:
            (imported_count, failed_count)
        """
        folder = Path(folder_path)
        if not folder.exists():
            raise ValueError(f"Folder not found: {folder_path}")
        
        self._imported_count = 0
        self._failed_count = 0
        
        # Find all supported files
        extensions = [".txt", ".md", ".docx", ".pdf"]
        files = []
        
        if recursive:
            for ext in extensions:
                files.extend(folder.rglob(f"*{ext}"))
        else:
            for ext in extensions:
                files.extend(folder.glob(f"*{ext}"))
        
        logger.info(f"Found {len(files)} files to import from {folder_path}")
        
        for file_path in files:
            try:
                essay = self.parse_essay_file(file_path)
                
                if essay:
                    # Set default outcome if still pending
                    if essay.outcome == EssayOutcome.PENDING and default_outcome != EssayOutcome.PENDING:
                        essay.outcome = default_outcome
                    
                    # Add to RAG
                    if self.rag:
                        essay_id = await self.rag.add_essay(essay)
                        if essay_id:
                            self._imported_count += 1
                            logger.debug(f"Imported: {essay.scholarship_name}")
                        else:
                            self._failed_count += 1
                    else:
                        self._imported_count += 1
                else:
                    self._failed_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to import {file_path}: {e}")
                self._failed_count += 1
        
        logger.info(f"Import complete: {self._imported_count} imported, {self._failed_count} failed")
        return self._imported_count, self._failed_count
    
    async def import_winning_essays_folder(
        self,
        folder_path: str,
    ) -> Tuple[int, int]:
        """Import essays from a folder, marking all as winners."""
        return await self.import_folder(
            folder_path,
            default_outcome=EssayOutcome.WON,
        )
    
    # =========================================================================
    # Single Essay Import
    # =========================================================================
    
    async def import_essay(
        self,
        scholarship_name: str,
        question: str,
        essay_text: str,
        outcome: EssayOutcome = EssayOutcome.PENDING,
        themes: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Import a single essay.
        
        Args:
            scholarship_name: Name of the scholarship
            question: The essay question
            essay_text: The essay content
            outcome: Essay outcome
            themes: Optional themes (auto-extracted if not provided)
            
        Returns:
            Essay ID if successful
        """
        essay = PastEssay(
            scholarship_name=scholarship_name,
            question=question,
            essay_text=essay_text,
            word_count=len(essay_text.split()),
            outcome=outcome,
            themes=themes or self._extract_themes(essay_text),
        )
        
        if self.rag:
            return await self.rag.add_essay(essay)
        return essay.id
    
    async def import_winning_essay(
        self,
        scholarship_name: str,
        question: str,
        essay_text: str,
    ) -> Optional[str]:
        """Import a winning essay."""
        return await self.import_essay(
            scholarship_name=scholarship_name,
            question=question,
            essay_text=essay_text,
            outcome=EssayOutcome.WON,
        )
    
    # =========================================================================
    # Personal Statement Import
    # =========================================================================
    
    async def import_personal_statement(
        self,
        file_path: Optional[str] = None,
        text: Optional[str] = None,
        split_sections: bool = True,
    ) -> int:
        """
        Import personal statement.
        
        Args:
            file_path: Path to personal statement file
            text: Personal statement text (alternative to file)
            split_sections: Split into sections for better RAG
            
        Returns:
            Number of sections imported
        """
        if file_path:
            content = self.read_file(Path(file_path))
        elif text:
            content = text
        else:
            raise ValueError("Either file_path or text must be provided")
        
        sections_imported = 0
        
        if split_sections:
            # Split by paragraphs
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            
            # Group into sections
            section_names = ["introduction", "body_1", "body_2", "body_3", "conclusion"]
            
            for i, para in enumerate(paragraphs):
                section_name = section_names[min(i, len(section_names) - 1)]
                if i >= len(section_names):
                    section_name = f"body_{i}"
                
                statement = PersonalStatement(
                    section_name=section_name,
                    content=para,
                    themes=self._extract_themes(para),
                )
                
                if self.rag:
                    stmt_id = await self.rag.add_personal_statement(statement)
                    if stmt_id:
                        sections_imported += 1
                else:
                    sections_imported += 1
        else:
            # Import as single section
            statement = PersonalStatement(
                section_name="full",
                content=content,
                themes=self._extract_themes(content),
            )
            
            if self.rag:
                stmt_id = await self.rag.add_personal_statement(statement)
                if stmt_id:
                    sections_imported = 1
            else:
                sections_imported = 1
        
        logger.info(f"Imported {sections_imported} personal statement sections")
        return sections_imported
    
    # =========================================================================
    # Profile Import
    # =========================================================================
    
    async def import_profile_section(
        self,
        section: str,
        content: str,
    ) -> Optional[str]:
        """
        Import a profile section.
        
        Args:
            section: Section name (achievements, stories, goals, etc.)
            content: Section content
            
        Returns:
            Section ID if successful
        """
        profile = PersonalProfile(
            section=section,
            content=content,
        )
        
        if self.rag:
            return await self.rag.add_profile_section(profile)
        return profile.id
    
    async def import_achievements(self, achievements: List[str]) -> int:
        """Import list of achievements."""
        count = 0
        for achievement in achievements:
            result = await self.import_profile_section("achievement", achievement)
            if result:
                count += 1
        return count
    
    async def import_stories(self, stories: Dict[str, str]) -> int:
        """
        Import personal stories.
        
        Args:
            stories: Dict of story_name -> story_content
            
        Returns:
            Number imported
        """
        count = 0
        for name, content in stories.items():
            result = await self.import_profile_section(f"story_{name}", content)
            if result:
                count += 1
        return count
    
    # =========================================================================
    # Batch Import from Structured Data
    # =========================================================================
    
    async def import_from_json(self, json_path: str) -> Dict[str, int]:
        """
        Import essays from a JSON file.
        
        Expected format:
        {
            "essays": [
                {
                    "scholarship_name": "...",
                    "question": "...",
                    "essay_text": "...",
                    "outcome": "won/lost/pending"
                }
            ],
            "personal_statement": "...",
            "achievements": ["...", "..."],
            "stories": {"name": "content"}
        }
        
        Args:
            json_path: Path to JSON file
            
        Returns:
            Dict with import counts
        """
        import json
        
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        results = {
            "essays": 0,
            "personal_statement_sections": 0,
            "achievements": 0,
            "stories": 0,
        }
        
        # Import essays
        for essay_data in data.get("essays", []):
            outcome = EssayOutcome.PENDING
            if essay_data.get("outcome"):
                outcome_str = essay_data["outcome"].lower()
                if outcome_str == "won":
                    outcome = EssayOutcome.WON
                elif outcome_str == "lost":
                    outcome = EssayOutcome.LOST
            
            result = await self.import_essay(
                scholarship_name=essay_data.get("scholarship_name", "Unknown"),
                question=essay_data.get("question", ""),
                essay_text=essay_data.get("essay_text", ""),
                outcome=outcome,
            )
            if result:
                results["essays"] += 1
        
        # Import personal statement
        if data.get("personal_statement"):
            count = await self.import_personal_statement(text=data["personal_statement"])
            results["personal_statement_sections"] = count
        
        # Import achievements
        if data.get("achievements"):
            count = await self.import_achievements(data["achievements"])
            results["achievements"] = count
        
        # Import stories
        if data.get("stories"):
            count = await self.import_stories(data["stories"])
            results["stories"] = count
        
        logger.info(f"JSON import complete: {results}")
        return results
    
    def get_import_summary(self) -> str:
        """Get summary of last import operation."""
        return (
            f"📥 **Import Summary**\n"
            f"✅ Imported: {self._imported_count}\n"
            f"❌ Failed: {self._failed_count}"
        )
