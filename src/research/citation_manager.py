"""
Citation Management for JARVIS Research Module.

Supports multiple citation formats:
- APA 7th Edition (default for most classes)
- MLA 9th Edition (English/Humanities)
- Chicago (History/Social Sciences)
- IEEE (Engineering/CS)
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from loguru import logger

from .source_manager import Source


class CitationStyle(Enum):
    """Supported citation styles."""
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    IEEE = "ieee"


@dataclass
class Citation:
    """A formatted citation."""
    source_id: str
    in_text: str
    full_reference: str
    style: CitationStyle


class CitationManager:
    """
    Manages citation formatting for research papers.
    
    Generates both in-text citations and full reference entries
    in multiple academic formats.
    """
    
    def __init__(self, style: CitationStyle = CitationStyle.APA):
        """
        Initialize citation manager.
        
        Args:
            style: Default citation style
        """
        self.style = style
        self.citations: List[Citation] = []
        self._citation_counter = 0  # For IEEE style
    
    def set_style(self, style: CitationStyle):
        """Change citation style."""
        self.style = style
        # Reset IEEE counter when changing styles
        self._citation_counter = 0
        self.citations.clear()
    
    def get_in_text_citation(
        self,
        source: Source,
        page: Optional[str] = None,
        is_direct_quote: bool = False,
    ) -> str:
        """
        Generate in-text citation for a source.
        
        Args:
            source: Source to cite
            page: Page number(s) for direct quotes
            is_direct_quote: Whether this is a direct quote
            
        Returns:
            Formatted in-text citation
        """
        if self.style == CitationStyle.APA:
            return self._apa_in_text(source, page, is_direct_quote)
        elif self.style == CitationStyle.MLA:
            return self._mla_in_text(source, page)
        elif self.style == CitationStyle.CHICAGO:
            return self._chicago_in_text(source, page)
        elif self.style == CitationStyle.IEEE:
            return self._ieee_in_text(source)
        else:
            return self._apa_in_text(source, page, is_direct_quote)
    
    def get_full_reference(self, source: Source) -> str:
        """
        Generate full reference entry for bibliography.
        
        Args:
            source: Source to create reference for
            
        Returns:
            Formatted reference entry
        """
        if self.style == CitationStyle.APA:
            return self._apa_reference(source)
        elif self.style == CitationStyle.MLA:
            return self._mla_reference(source)
        elif self.style == CitationStyle.CHICAGO:
            return self._chicago_reference(source)
        elif self.style == CitationStyle.IEEE:
            return self._ieee_reference(source)
        else:
            return self._apa_reference(source)
    
    def create_citation(
        self,
        source: Source,
        page: Optional[str] = None,
        is_direct_quote: bool = False,
    ) -> Citation:
        """
        Create and store a citation.
        
        Args:
            source: Source to cite
            page: Page number(s)
            is_direct_quote: Whether direct quote
            
        Returns:
            Citation object
        """
        citation = Citation(
            source_id=source.id or str(hash(source.title)),
            in_text=self.get_in_text_citation(source, page, is_direct_quote),
            full_reference=self.get_full_reference(source),
            style=self.style,
        )
        
        # Avoid duplicates
        existing = next((c for c in self.citations if c.source_id == citation.source_id), None)
        if not existing:
            self.citations.append(citation)
        
        return citation
    
    def generate_bibliography(self, sources: List[Source]) -> str:
        """
        Generate complete bibliography/works cited.
        
        Args:
            sources: Sources to include
            
        Returns:
            Formatted bibliography
        """
        # Generate all references
        references = []
        for source in sources:
            ref = self.get_full_reference(source)
            references.append(ref)
        
        # Sort alphabetically (except IEEE which uses numbers)
        if self.style != CitationStyle.IEEE:
            references.sort(key=lambda r: r.lower())
        
        # Format based on style
        if self.style == CitationStyle.APA:
            title = "References"
        elif self.style == CitationStyle.MLA:
            title = "Works Cited"
        elif self.style == CitationStyle.CHICAGO:
            title = "Bibliography"
        elif self.style == CitationStyle.IEEE:
            title = "References"
        else:
            title = "References"
        
        lines = [f"## {title}", ""]
        for ref in references:
            lines.append(ref)
            lines.append("")
        
        return "\n".join(lines)
    
    # =========================================================================
    # APA 7th Edition
    # =========================================================================
    
    def _apa_in_text(
        self,
        source: Source,
        page: Optional[str] = None,
        is_direct_quote: bool = False,
    ) -> str:
        """Generate APA in-text citation."""
        # Get author(s)
        if not source.authors:
            author_part = "Unknown"
        elif len(source.authors) == 1:
            author_part = source.get_first_author_last_name()
        elif len(source.authors) == 2:
            last_names = [self._get_last_name(a) for a in source.authors]
            author_part = f"{last_names[0]} & {last_names[1]}"
        else:
            author_part = f"{source.get_first_author_last_name()} et al."
        
        # Get year
        year = source.year or "n.d."
        
        # Build citation
        if page and is_direct_quote:
            return f"({author_part}, {year}, p. {page})"
        else:
            return f"({author_part}, {year})"
    
    def _apa_reference(self, source: Source) -> str:
        """Generate APA reference entry."""
        parts = []
        
        # Authors
        if source.authors:
            author_list = []
            for i, author in enumerate(source.authors[:20]):  # APA allows up to 20
                last_name = self._get_last_name(author)
                initials = self._get_initials(author)
                if i == len(source.authors) - 1 and len(source.authors) > 1:
                    author_list.append(f"& {last_name}, {initials}")
                else:
                    author_list.append(f"{last_name}, {initials}")
            
            if len(source.authors) > 20:
                author_list = author_list[:19] + ["..."] + [author_list[-1]]
            
            parts.append(", ".join(author_list[:-1]) + " " + author_list[-1] if len(author_list) > 1 else author_list[0])
        else:
            parts.append("Unknown Author")
        
        # Year
        year = f"({source.year})" if source.year else "(n.d.)"
        parts.append(year)
        
        # Title (italicized for articles)
        title = source.title
        if not title.endswith("."):
            title += "."
        parts.append(f"*{title}*")
        
        # Venue/Journal
        if source.venue:
            parts.append(f"*{source.venue}*.")
        
        # DOI or URL
        if source.doi:
            parts.append(f"https://doi.org/{source.doi}")
        elif source.url:
            parts.append(source.url)
        
        return " ".join(parts)
    
    # =========================================================================
    # MLA 9th Edition
    # =========================================================================
    
    def _mla_in_text(self, source: Source, page: Optional[str] = None) -> str:
        """Generate MLA in-text citation."""
        author = source.get_first_author_last_name() if source.authors else "Unknown"
        
        if page:
            return f"({author} {page})"
        else:
            return f"({author})"
    
    def _mla_reference(self, source: Source) -> str:
        """Generate MLA works cited entry."""
        parts = []
        
        # Author(s)
        if source.authors:
            if len(source.authors) == 1:
                last = self._get_last_name(source.authors[0])
                first = self._get_first_name(source.authors[0])
                parts.append(f"{last}, {first}.")
            elif len(source.authors) == 2:
                last1 = self._get_last_name(source.authors[0])
                first1 = self._get_first_name(source.authors[0])
                parts.append(f"{last1}, {first1}, and {source.authors[1]}.")
            else:
                last = self._get_last_name(source.authors[0])
                first = self._get_first_name(source.authors[0])
                parts.append(f"{last}, {first}, et al.")
        
        # Title in quotes
        title = source.title.rstrip(".")
        parts.append(f'"{title}."')
        
        # Container/Journal (italicized)
        if source.venue:
            parts.append(f"*{source.venue}*,")
        
        # Year
        if source.year:
            parts.append(f"{source.year}.")
        
        # URL or DOI
        if source.doi:
            parts.append(f"https://doi.org/{source.doi}.")
        elif source.url:
            parts.append(f"{source.url}.")
        
        return " ".join(parts)
    
    # =========================================================================
    # Chicago Style
    # =========================================================================
    
    def _chicago_in_text(self, source: Source, page: Optional[str] = None) -> str:
        """Generate Chicago in-text citation (author-date)."""
        author = source.get_first_author_last_name() if source.authors else "Unknown"
        year = source.year or "n.d."
        
        if page:
            return f"({author} {year}, {page})"
        else:
            return f"({author} {year})"
    
    def _chicago_reference(self, source: Source) -> str:
        """Generate Chicago bibliography entry."""
        parts = []
        
        # Authors
        if source.authors:
            if len(source.authors) == 1:
                last = self._get_last_name(source.authors[0])
                first = self._get_first_name(source.authors[0])
                parts.append(f"{last}, {first}.")
            else:
                # First author inverted, rest normal
                last = self._get_last_name(source.authors[0])
                first = self._get_first_name(source.authors[0])
                other_authors = ", ".join(source.authors[1:])
                parts.append(f"{last}, {first}, and {other_authors}.")
        
        # Year
        if source.year:
            parts.append(f"{source.year}.")
        
        # Title in quotes
        title = source.title.rstrip(".")
        parts.append(f'"{title}."')
        
        # Journal (italicized)
        if source.venue:
            parts.append(f"*{source.venue}*.")
        
        # DOI or URL
        if source.doi:
            parts.append(f"https://doi.org/{source.doi}.")
        elif source.url:
            parts.append(source.url + ".")
        
        return " ".join(parts)
    
    # =========================================================================
    # IEEE Style
    # =========================================================================
    
    def _ieee_in_text(self, source: Source) -> str:
        """Generate IEEE in-text citation (numbered)."""
        # Find or assign number
        existing = next(
            (i + 1 for i, c in enumerate(self.citations) 
             if c.source_id == (source.id or str(hash(source.title)))),
            None
        )
        
        if existing:
            return f"[{existing}]"
        else:
            self._citation_counter += 1
            return f"[{self._citation_counter}]"
    
    def _ieee_reference(self, source: Source) -> str:
        """Generate IEEE reference entry."""
        # Get citation number
        num = self._citation_counter
        for i, c in enumerate(self.citations):
            if c.source_id == (source.id or str(hash(source.title))):
                num = i + 1
                break
        
        parts = [f"[{num}]"]
        
        # Authors (initials first)
        if source.authors:
            author_list = []
            for author in source.authors[:6]:
                initials = self._get_initials(author)
                last = self._get_last_name(author)
                author_list.append(f"{initials} {last}")
            
            if len(source.authors) > 6:
                author_list.append("et al.")
            
            parts.append(", ".join(author_list) + ",")
        
        # Title in quotes
        title = source.title.rstrip(".")
        parts.append(f'"{title},"')
        
        # Journal (italicized)
        if source.venue:
            parts.append(f"*{source.venue}*,")
        
        # Year
        if source.year:
            parts.append(f"{source.year}.")
        
        # DOI
        if source.doi:
            parts.append(f"doi: {source.doi}.")
        
        return " ".join(parts)
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _get_last_name(self, full_name: str) -> str:
        """Extract last name from full name."""
        parts = full_name.strip().split()
        if len(parts) > 1:
            return parts[-1]
        return full_name
    
    def _get_first_name(self, full_name: str) -> str:
        """Extract first name from full name."""
        parts = full_name.strip().split()
        if len(parts) > 1:
            return " ".join(parts[:-1])
        return full_name
    
    def _get_initials(self, full_name: str) -> str:
        """Get initials from full name."""
        parts = full_name.strip().split()
        if len(parts) > 1:
            # All parts except last name
            initials = [p[0].upper() + "." for p in parts[:-1] if p]
            return " ".join(initials)
        elif parts:
            return parts[0][0].upper() + "."
        return ""
    
    def format_citation_for_style(self, text: str, source: Source) -> str:
        """
        Insert citation into text appropriately.
        
        Args:
            text: Text to add citation to
            source: Source being cited
            
        Returns:
            Text with citation
        """
        citation = self.get_in_text_citation(source)
        
        # Add citation at end of sentence or clause
        text = text.rstrip()
        if text.endswith("."):
            # Insert before period
            return text[:-1] + " " + citation + "."
        else:
            return text + " " + citation
    
    def get_style_guide(self) -> str:
        """Get brief guide for current citation style."""
        guides = {
            CitationStyle.APA: """**APA 7th Edition Guide**
- In-text: (Author, Year) or (Author, Year, p. X) for quotes
- Multiple authors: (Author1 & Author2, Year) or (Author1 et al., Year)
- References: Alphabetical order, hanging indent
- DOIs preferred over URLs""",
            
            CitationStyle.MLA: """**MLA 9th Edition Guide**
- In-text: (Author Page) - no comma, no "p."
- Works Cited: Alphabetical by author's last name
- Titles in quotation marks, containers italicized
- Access dates for online sources""",
            
            CitationStyle.CHICAGO: """**Chicago Style Guide**
- In-text: (Author Year) or (Author Year, Page)
- Bibliography: Alphabetical order
- First author inverted (Last, First)
- Titles in quotation marks""",
            
            CitationStyle.IEEE: """**IEEE Style Guide**
- In-text: [1], [2], etc. (numbered in order of appearance)
- References: Numbered list in citation order
- Author initials before last name
- Titles in quotation marks""",
        }
        
        return guides.get(self.style, "Unknown citation style")
