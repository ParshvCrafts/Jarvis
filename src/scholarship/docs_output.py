"""
Google Docs Output for JARVIS Scholarship Module.

Enhanced features:
- Formatted Google Docs with proper styling
- Multi-essay documents with table of contents
- Local markdown backup with full metadata
- RAG source attribution
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger

from .models import Scholarship, GeneratedEssay

GOOGLE_DOCS_AVAILABLE = False
GoogleDocsClient = None

try:
    from ..research.google_docs import GoogleDocsClient
    GOOGLE_DOCS_AVAILABLE = True
except ImportError:
    pass


class ScholarshipDocsOutput:
    """
    Generate formatted Google Docs and local backups for scholarship essays.
    
    Features:
    - Professional formatting with headers and styling
    - Multi-essay documents with navigation
    - Word count annotations
    - RAG source attribution
    - Local markdown backup
    """
    
    def __init__(
        self,
        credentials_path: str = "config/google_credentials.json",
        token_path: str = "config/google_token.json",
        output_dir: str = "data/scholarship_essays",
    ):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._client = None
    
    @property
    def is_available(self) -> bool:
        """Check if Google Docs is available."""
        return GOOGLE_DOCS_AVAILABLE
    
    def _ensure_client(self) -> bool:
        """Initialize Google Docs client if needed."""
        if self._client:
            return True
        if not GOOGLE_DOCS_AVAILABLE:
            logger.warning("Google Docs not available - using local backup only")
            return False
        try:
            self._client = GoogleDocsClient(self.credentials_path, self.token_path)
            return True
        except Exception as e:
            logger.error(f"Google Docs init failed: {e}")
            return False
    
    def create_essay_document(
        self,
        scholarship: Scholarship,
        essays: List[GeneratedEssay],
        include_metadata: bool = True,
        include_rag_sources: bool = False,
    ) -> Optional[str]:
        """
        Create Google Doc with formatted essays.
        
        Args:
            scholarship: Scholarship information
            essays: List of generated essays
            include_metadata: Include generation metadata
            include_rag_sources: Include RAG source attribution
            
        Returns:
            Google Doc URL or None if failed
        """
        if not self._ensure_client():
            # Fall back to local backup
            backup_path = self.create_local_backup(
                scholarship, essays, include_rag_sources
            )
            logger.info(f"Created local backup: {backup_path}")
            return None
        
        try:
            # Create document with formatted title
            title = f"{scholarship.name} - Application Essays"
            self._client.create_document(title)
            
            # Header section
            self._client.insert_heading(scholarship.name, 1)
            
            # Metadata block
            deadline_str = scholarship.deadline.strftime("%B %d, %Y") if scholarship.deadline else "TBD"
            amount_str = f"${scholarship.amount:,.0f}" if scholarship.amount else "Varies"
            
            metadata_text = (
                f"📅 Deadline: {deadline_str}\n"
                f"💰 Amount: {amount_str}\n"
                f"🔗 URL: {scholarship.url or 'N/A'}\n"
                f"📝 Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
            )
            self._client.insert_paragraph(metadata_text)
            
            # Table of contents for multiple essays
            if len(essays) > 1:
                self._client.insert_heading("Table of Contents", 2)
                toc_lines = []
                for i, essay in enumerate(essays, 1):
                    question_preview = essay.question_text[:50] + "..." if len(essay.question_text) > 50 else essay.question_text
                    toc_lines.append(f"{i}. {question_preview}")
                self._client.insert_paragraph("\n".join(toc_lines))
            
            # Each essay
            for i, essay in enumerate(essays, 1):
                self._client.insert_heading(f"Question {i}", 2)
                
                # Question/prompt
                self._client.insert_paragraph(f"📋 Prompt:\n{essay.question_text}")
                
                # Word count info
                word_status = "✅" if abs(essay.word_count - essay.target_word_count) <= 5 else "⚠️"
                self._client.insert_paragraph(
                    f"{word_status} Word Count: {essay.word_count} / {essay.target_word_count} limit"
                )
                
                # Essay content
                self._client.insert_heading("Essay", 3)
                self._client.insert_paragraph(essay.essay_text)
                
                # Quality score if available
                if essay.quality_score:
                    self._client.insert_paragraph(f"📊 Quality Score: {essay.quality_score}/10")
                
                # RAG sources if requested
                if include_rag_sources and essay.rag_sources:
                    self._client.insert_heading("Sources Used", 4)
                    sources_text = self._format_rag_sources(essay.rag_sources)
                    self._client.insert_paragraph(sources_text)
            
            # Footer
            self._client.insert_paragraph("\n---\nGenerated by JARVIS Scholarship Module")
            
            # Set sharing and return URL
            url = self._client.set_sharing(anyone_can_view=True)
            logger.info(f"Created Google Doc: {url}")
            
            # Also create local backup
            self.create_local_backup(scholarship, essays, include_rag_sources)
            
            return url
            
        except Exception as e:
            logger.error(f"Google Doc creation failed: {e}")
            # Fall back to local backup
            return self.create_local_backup(scholarship, essays, include_rag_sources)
    
    def _format_rag_sources(self, rag_sources: Dict[str, Any]) -> str:
        """Format RAG sources for display."""
        lines = []
        
        if rag_sources.get("essays"):
            lines.append("**Similar Essays:**")
            for essay_info in rag_sources["essays"][:3]:
                name = essay_info.get("scholarship", "Unknown")
                score = essay_info.get("similarity", 0)
                lines.append(f"  • {name} ({score:.0%} match)")
        
        if rag_sources.get("profile_sections"):
            lines.append("**Profile Sections:**")
            for section in rag_sources["profile_sections"][:3]:
                lines.append(f"  • {section}")
        
        return "\n".join(lines) if lines else "No sources recorded"
    
    def create_local_backup(
        self,
        scholarship: Scholarship,
        essays: List[GeneratedEssay],
        include_rag_sources: bool = True,
    ) -> str:
        """
        Create local markdown backup with full metadata.
        
        Args:
            scholarship: Scholarship information
            essays: List of generated essays
            include_rag_sources: Include RAG source attribution
            
        Returns:
            Path to created file
        """
        # Create filename
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in scholarship.name)
        safe_name = safe_name.replace(" ", "_")[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}.md"
        filepath = self.output_dir / filename
        
        # Build markdown content
        lines = [
            f"# {scholarship.name}",
            "",
            "## Scholarship Information",
            "",
            f"- **Provider:** {scholarship.provider or 'Unknown'}",
            f"- **Amount:** ${scholarship.amount:,.0f}" if scholarship.amount else "- **Amount:** Varies",
            f"- **Deadline:** {scholarship.deadline.strftime('%B %d, %Y')}" if scholarship.deadline else "- **Deadline:** TBD",
            f"- **URL:** {scholarship.url}" if scholarship.url else "",
            "",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "---",
            "",
        ]
        
        # Each essay
        for i, essay in enumerate(essays, 1):
            word_status = "✅" if abs(essay.word_count - essay.target_word_count) <= 5 else "⚠️"
            
            lines.extend([
                f"## Question {i}",
                "",
                f"**Prompt:** {essay.question_text}",
                "",
                f"**Word Limit:** {essay.target_word_count} | **Actual:** {essay.word_count} {word_status}",
                "",
            ])
            
            if essay.quality_score:
                lines.append(f"**Quality Score:** {essay.quality_score}/10")
                lines.append("")
            
            lines.extend([
                "### Essay",
                "",
                essay.essay_text,
                "",
            ])
            
            # RAG sources
            if include_rag_sources and essay.rag_sources:
                lines.extend([
                    "### RAG Sources Used",
                    "",
                    self._format_rag_sources_markdown(essay.rag_sources),
                    "",
                ])
            
            lines.extend(["---", ""])
        
        # Footer
        lines.extend([
            "",
            "*Generated by JARVIS Scholarship Module*",
            f"*Backup created: {datetime.now().isoformat()}*",
        ])
        
        # Write file
        filepath.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Created local backup: {filepath}")
        
        return str(filepath)
    
    def _format_rag_sources_markdown(self, rag_sources: Dict[str, Any]) -> str:
        """Format RAG sources as markdown."""
        lines = []
        
        if rag_sources.get("essays"):
            lines.append("**Similar Past Essays:**")
            for essay_info in rag_sources.get("essays", [])[:5]:
                name = essay_info.get("scholarship", "Unknown")
                score = essay_info.get("similarity", 0)
                outcome = essay_info.get("outcome", "unknown")
                emoji = "🏆" if outcome == "won" else "📝"
                lines.append(f"- {emoji} {name} ({score:.0%} match)")
        
        if rag_sources.get("statement_sections"):
            lines.append("")
            lines.append("**Personal Statement Sections:**")
            for section in rag_sources.get("statement_sections", [])[:3]:
                lines.append(f"- {section}")
        
        if rag_sources.get("profile_sections"):
            lines.append("")
            lines.append("**Profile Sections:**")
            for section in rag_sources.get("profile_sections", [])[:3]:
                lines.append(f"- {section}")
        
        return "\n".join(lines) if lines else "No sources recorded"
    
    def create_multi_scholarship_document(
        self,
        scholarships_essays: List[tuple],
        title: str = "Scholarship Applications",
    ) -> Optional[str]:
        """
        Create a single document with multiple scholarship applications.
        
        Args:
            scholarships_essays: List of (Scholarship, List[GeneratedEssay]) tuples
            title: Document title
            
        Returns:
            Google Doc URL or local backup path
        """
        if not self._ensure_client():
            return self._create_multi_local_backup(scholarships_essays, title)
        
        try:
            self._client.create_document(title)
            self._client.insert_heading(title, 1)
            self._client.insert_paragraph(
                f"Generated: {datetime.now().strftime('%B %d, %Y')}\n"
                f"Total Applications: {len(scholarships_essays)}"
            )
            
            # Table of contents
            self._client.insert_heading("Applications", 2)
            for i, (scholarship, _) in enumerate(scholarships_essays, 1):
                deadline = scholarship.deadline.strftime("%m/%d") if scholarship.deadline else "TBD"
                self._client.insert_paragraph(f"{i}. {scholarship.name} (Due: {deadline})")
            
            # Each scholarship
            for scholarship, essays in scholarships_essays:
                self._client.insert_heading(scholarship.name, 2)
                
                for j, essay in enumerate(essays, 1):
                    self._client.insert_heading(f"Q{j}: {essay.question_text[:40]}...", 3)
                    self._client.insert_paragraph(
                        f"Words: {essay.word_count}/{essay.target_word_count}"
                    )
                    self._client.insert_paragraph(essay.essay_text)
            
            return self._client.set_sharing(anyone_can_view=True)
            
        except Exception as e:
            logger.error(f"Multi-doc creation failed: {e}")
            return self._create_multi_local_backup(scholarships_essays, title)
    
    def _create_multi_local_backup(
        self,
        scholarships_essays: List[tuple],
        title: str,
    ) -> str:
        """Create local backup for multiple scholarships."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"multi_scholarship_{timestamp}.md"
        filepath = self.output_dir / filename
        
        lines = [f"# {title}", "", f"*Generated: {datetime.now().isoformat()}*", ""]
        
        for scholarship, essays in scholarships_essays:
            lines.extend([f"## {scholarship.name}", ""])
            for i, essay in enumerate(essays, 1):
                lines.extend([
                    f"### Question {i}",
                    f"**Prompt:** {essay.question_text}",
                    f"**Words:** {essay.word_count}/{essay.target_word_count}",
                    "", essay.essay_text, "", "---", ""
                ])
        
        filepath.write_text("\n".join(lines), encoding="utf-8")
        return str(filepath)
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all local backup files."""
        backups = []
        for file in self.output_dir.glob("*.md"):
            stat = file.stat()
            backups.append({
                "filename": file.name,
                "path": str(file),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        return sorted(backups, key=lambda x: x["modified"], reverse=True)
