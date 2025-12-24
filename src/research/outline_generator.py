"""
Outline Generator for JARVIS Research Module.

Creates structured research paper outlines based on:
- Topic and requirements
- Collected sources
- User preferences
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

from .source_manager import Source


class PaperType(Enum):
    """Types of research papers."""
    ARGUMENTATIVE = "argumentative"
    ANALYTICAL = "analytical"
    EXPOSITORY = "expository"
    LITERATURE_REVIEW = "literature_review"
    RESEARCH = "research"


@dataclass
class Section:
    """A paper section."""
    title: str
    level: int  # 1 = main section, 2 = subsection, 3 = sub-subsection
    description: str = ""
    content: str = ""
    word_target: int = 0
    sources: List[str] = field(default_factory=list)  # Source IDs
    is_complete: bool = False


@dataclass
class PaperOutline:
    """Complete paper outline."""
    title: str
    thesis: str
    sections: List[Section]
    paper_type: PaperType = PaperType.RESEARCH
    target_pages: int = 10
    target_words: int = 2500
    citation_style: str = "apa"
    
    def get_section_by_title(self, title: str) -> Optional[Section]:
        """Find section by title."""
        for section in self.sections:
            if section.title.lower() == title.lower():
                return section
        return None
    
    def get_incomplete_sections(self) -> List[Section]:
        """Get sections that need content."""
        return [s for s in self.sections if not s.is_complete]
    
    def get_progress(self) -> float:
        """Get completion percentage."""
        if not self.sections:
            return 0.0
        complete = sum(1 for s in self.sections if s.is_complete)
        return complete / len(self.sections)
    
    def to_markdown(self) -> str:
        """Convert outline to markdown."""
        lines = [f"# {self.title}", ""]
        lines.append(f"**Thesis:** {self.thesis}")
        lines.append(f"**Target:** {self.target_pages} pages (~{self.target_words} words)")
        lines.append(f"**Citation Style:** {self.citation_style.upper()}")
        lines.append("")
        lines.append("## Outline")
        lines.append("")
        
        for section in self.sections:
            prefix = "#" * (section.level + 1)
            status = "✅" if section.is_complete else "⬜"
            lines.append(f"{prefix} {status} {section.title}")
            if section.description:
                lines.append(f"   {section.description}")
            if section.word_target:
                lines.append(f"   *Target: ~{section.word_target} words*")
            lines.append("")
        
        return "\n".join(lines)


class OutlineGenerator:
    """
    Generates research paper outlines.
    
    Uses LLM to create customized outlines based on:
    - Research topic
    - Available sources
    - User requirements
    """
    
    # Standard academic paper structure
    STANDARD_STRUCTURE = [
        Section(title="Introduction", level=1, description="Hook, background, thesis, roadmap", word_target=300),
        Section(title="Literature Review", level=1, description="Review of existing research", word_target=600),
        Section(title="Analysis", level=1, description="Main arguments and discussion", word_target=800),
        Section(title="Implications", level=1, description="Real-world relevance and applications", word_target=400),
        Section(title="Conclusion", level=1, description="Summary and final thoughts", word_target=300),
        Section(title="References", level=1, description="Bibliography", word_target=0),
    ]
    
    def __init__(self, llm_router=None):
        """
        Initialize outline generator.
        
        Args:
            llm_router: LLM router for intelligent outline generation
        """
        self.llm_router = llm_router
    
    def generate_outline(
        self,
        topic: str,
        sources: List[Source],
        target_pages: int = 10,
        citation_style: str = "apa",
        paper_type: PaperType = PaperType.RESEARCH,
        focus_areas: Optional[List[str]] = None,
        custom_requirements: Optional[str] = None,
    ) -> PaperOutline:
        """
        Generate a paper outline.
        
        Args:
            topic: Research topic
            sources: Available sources
            target_pages: Target page count
            citation_style: Citation format
            paper_type: Type of paper
            focus_areas: Specific areas to focus on
            custom_requirements: Additional requirements
            
        Returns:
            PaperOutline object
        """
        # Calculate word targets
        words_per_page = 250  # Double-spaced
        target_words = target_pages * words_per_page
        
        # Generate thesis
        thesis = self._generate_thesis(topic, sources, focus_areas)
        
        # Generate sections based on paper type and length
        sections = self._generate_sections(
            topic=topic,
            sources=sources,
            target_words=target_words,
            paper_type=paper_type,
            focus_areas=focus_areas,
        )
        
        # Assign sources to sections
        self._assign_sources_to_sections(sections, sources)
        
        outline = PaperOutline(
            title=self._generate_title(topic),
            thesis=thesis,
            sections=sections,
            paper_type=paper_type,
            target_pages=target_pages,
            target_words=target_words,
            citation_style=citation_style,
        )
        
        logger.info(f"Generated outline with {len(sections)} sections for '{topic}'")
        return outline
    
    def _generate_title(self, topic: str) -> str:
        """Generate paper title from topic."""
        # Clean up topic for title
        title = topic.strip()
        
        # Capitalize appropriately
        words = title.split()
        small_words = {"a", "an", "the", "and", "but", "or", "for", "nor", "on", "at", "to", "by", "in", "of"}
        
        titled_words = []
        for i, word in enumerate(words):
            if i == 0 or word.lower() not in small_words:
                titled_words.append(word.capitalize())
            else:
                titled_words.append(word.lower())
        
        return " ".join(titled_words)
    
    def _generate_thesis(
        self,
        topic: str,
        sources: List[Source],
        focus_areas: Optional[List[str]] = None,
    ) -> str:
        """Generate thesis statement."""
        # Extract key themes from sources
        themes = set()
        for source in sources[:10]:
            if source.keywords:
                themes.update(source.keywords[:3])
        
        # Build thesis based on topic and themes
        if focus_areas:
            focus_str = ", ".join(focus_areas[:3])
            thesis = f"This paper examines {topic}, focusing on {focus_str}, and argues that understanding these aspects is crucial for addressing the broader implications of this issue."
        else:
            thesis = f"This paper provides a comprehensive analysis of {topic}, examining its key dimensions, implications, and potential solutions based on current scholarly research."
        
        return thesis
    
    def _generate_sections(
        self,
        topic: str,
        sources: List[Source],
        target_words: int,
        paper_type: PaperType,
        focus_areas: Optional[List[str]] = None,
    ) -> List[Section]:
        """Generate paper sections."""
        sections = []
        
        # Introduction (always ~12% of paper)
        intro_words = int(target_words * 0.12)
        sections.append(Section(
            title="Introduction",
            level=1,
            description=f"Introduce {topic}, provide background context, present thesis statement, and outline paper structure.",
            word_target=intro_words,
        ))
        
        # Literature Review (25-30% of paper)
        lit_review_words = int(target_words * 0.28)
        sections.append(Section(
            title="Literature Review",
            level=1,
            description=f"Review existing scholarly research on {topic}.",
            word_target=lit_review_words,
        ))
        
        # Add literature review subsections based on themes
        if focus_areas:
            words_per_theme = lit_review_words // len(focus_areas)
            for area in focus_areas[:4]:
                sections.append(Section(
                    title=area,
                    level=2,
                    description=f"Review research related to {area}.",
                    word_target=words_per_theme,
                ))
        else:
            # Generate themes from sources
            themes = self._extract_themes(sources, topic)
            words_per_theme = lit_review_words // max(len(themes), 1)
            for theme in themes[:3]:
                sections.append(Section(
                    title=theme,
                    level=2,
                    description=f"Review research on {theme}.",
                    word_target=words_per_theme,
                ))
        
        # Analysis/Discussion (30-35% of paper)
        analysis_words = int(target_words * 0.32)
        sections.append(Section(
            title="Analysis and Discussion",
            level=1,
            description=f"Analyze key aspects of {topic} and discuss findings.",
            word_target=analysis_words,
        ))
        
        # Add analysis subsections
        analysis_topics = self._generate_analysis_topics(topic, sources, focus_areas)
        words_per_analysis = analysis_words // max(len(analysis_topics), 1)
        for analysis_topic in analysis_topics[:3]:
            sections.append(Section(
                title=analysis_topic,
                level=2,
                description=f"Analyze {analysis_topic}.",
                word_target=words_per_analysis,
            ))
        
        # Implications (15% of paper)
        impl_words = int(target_words * 0.15)
        sections.append(Section(
            title="Implications and Future Directions",
            level=1,
            description=f"Discuss real-world implications and future research directions.",
            word_target=impl_words,
        ))
        
        # Conclusion (8% of paper)
        conclusion_words = int(target_words * 0.08)
        sections.append(Section(
            title="Conclusion",
            level=1,
            description="Summarize findings, restate thesis, and provide closing thoughts.",
            word_target=conclusion_words,
        ))
        
        # References (no word count)
        sections.append(Section(
            title="References",
            level=1,
            description="Complete bibliography of all cited sources.",
            word_target=0,
        ))
        
        return sections
    
    def _extract_themes(self, sources: List[Source], topic: str) -> List[str]:
        """Extract main themes from sources."""
        # Collect all keywords
        keyword_counts: Dict[str, int] = {}
        for source in sources:
            for keyword in source.keywords:
                keyword_lower = keyword.lower()
                if keyword_lower not in topic.lower():  # Exclude topic itself
                    keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        # Sort by frequency
        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Return top themes
        themes = [kw for kw, count in sorted_keywords[:5] if count >= 2]
        
        if not themes:
            # Default themes
            themes = [
                f"Background and Context",
                f"Key Concepts and Definitions",
                f"Current Research and Findings",
            ]
        
        return themes
    
    def _generate_analysis_topics(
        self,
        topic: str,
        sources: List[Source],
        focus_areas: Optional[List[str]] = None,
    ) -> List[str]:
        """Generate analysis section topics."""
        if focus_areas:
            return [f"Analysis of {area}" for area in focus_areas[:3]]
        
        # Default analysis structure
        return [
            f"Critical Examination of {topic}",
            "Comparative Analysis",
            "Synthesis and Interpretation",
        ]
    
    def _assign_sources_to_sections(
        self,
        sections: List[Section],
        sources: List[Source],
    ):
        """Assign sources to appropriate sections."""
        # Skip intro and conclusion for source assignment
        content_sections = [s for s in sections if s.level <= 2 and s.title not in ["Introduction", "Conclusion", "References"]]
        
        if not content_sections or not sources:
            return
        
        # Distribute sources across sections
        sources_per_section = max(1, len(sources) // len(content_sections))
        
        source_index = 0
        for section in content_sections:
            section_sources = []
            for _ in range(sources_per_section):
                if source_index < len(sources):
                    section_sources.append(sources[source_index].id or str(source_index))
                    source_index += 1
            section.sources = section_sources
        
        # Assign remaining sources to literature review
        lit_review = next((s for s in sections if s.title == "Literature Review"), None)
        if lit_review:
            while source_index < len(sources):
                lit_review.sources.append(sources[source_index].id or str(source_index))
                source_index += 1
    
    async def generate_outline_with_llm(
        self,
        topic: str,
        sources: List[Source],
        target_pages: int = 10,
        citation_style: str = "apa",
        custom_requirements: Optional[str] = None,
    ) -> PaperOutline:
        """
        Generate outline using LLM for better customization.
        
        Args:
            topic: Research topic
            sources: Available sources
            target_pages: Target page count
            citation_style: Citation format
            custom_requirements: Additional requirements
            
        Returns:
            PaperOutline object
        """
        if not self.llm_router:
            return self.generate_outline(topic, sources, target_pages, citation_style)
        
        # Build source summary for LLM
        source_summary = "\n".join([
            f"- {s.title} ({s.year}): {s.summary or s.abstract[:200] if s.abstract else 'No abstract'}..."
            for s in sources[:10]
        ])
        
        prompt = f"""Create a detailed research paper outline for the following topic:

Topic: {topic}
Target Length: {target_pages} pages (~{target_pages * 250} words)
Citation Style: {citation_style.upper()}
{f'Additional Requirements: {custom_requirements}' if custom_requirements else ''}

Available Sources:
{source_summary}

Generate an outline with:
1. A compelling thesis statement
2. Main sections with subsections
3. Brief description of what each section should cover
4. Suggested word count per section

Format your response as:
THESIS: [thesis statement]

OUTLINE:
I. Introduction (~X words)
   - [description]
   
II. Literature Review (~X words)
   A. [Subsection 1]
   B. [Subsection 2]
   
III. [Main Section] (~X words)
   A. [Subsection]
   
IV. Conclusion (~X words)

V. References
"""
        
        try:
            response = await self.llm_router.generate(prompt)
            return self._parse_llm_outline(response, topic, target_pages, citation_style, sources)
        except Exception as e:
            logger.warning(f"LLM outline generation failed: {e}, using default")
            return self.generate_outline(topic, sources, target_pages, citation_style)
    
    def _parse_llm_outline(
        self,
        response: str,
        topic: str,
        target_pages: int,
        citation_style: str,
        sources: List[Source],
    ) -> PaperOutline:
        """Parse LLM-generated outline."""
        import re
        
        # Extract thesis
        thesis_match = re.search(r"THESIS:\s*(.+?)(?=\n\n|OUTLINE:)", response, re.DOTALL)
        thesis = thesis_match.group(1).strip() if thesis_match else self._generate_thesis(topic, sources, None)
        
        # Parse sections (simplified parsing)
        sections = []
        
        # Look for Roman numeral sections
        section_pattern = r"([IVX]+)\.\s+(.+?)(?:\s*\(~?(\d+)\s*words?\))?"
        for match in re.finditer(section_pattern, response):
            title = match.group(2).strip()
            word_target = int(match.group(3)) if match.group(3) else 0
            
            sections.append(Section(
                title=title,
                level=1,
                word_target=word_target,
            ))
        
        # Look for letter subsections
        subsection_pattern = r"([A-Z])\.\s+(.+?)(?:\s*\(~?(\d+)\s*words?\))?"
        for match in re.finditer(subsection_pattern, response):
            title = match.group(2).strip()
            word_target = int(match.group(3)) if match.group(3) else 0
            
            sections.append(Section(
                title=title,
                level=2,
                word_target=word_target,
            ))
        
        # If parsing failed, use default structure
        if len(sections) < 3:
            return self.generate_outline(topic, sources, target_pages, citation_style)
        
        # Assign sources
        self._assign_sources_to_sections(sections, sources)
        
        return PaperOutline(
            title=self._generate_title(topic),
            thesis=thesis,
            sections=sections,
            target_pages=target_pages,
            target_words=target_pages * 250,
            citation_style=citation_style,
        )
