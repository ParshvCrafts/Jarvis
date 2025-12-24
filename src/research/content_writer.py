"""
Content Writer for JARVIS Research Module.

Writes research paper content section by section:
- Academic tone and style
- Source integration with citations
- Logical flow and transitions
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .source_manager import Source
from .citation_manager import CitationManager, CitationStyle
from .outline_generator import PaperOutline, Section


@dataclass
class WrittenSection:
    """A completed section with content."""
    title: str
    content: str
    word_count: int
    citations_used: List[str]  # Source IDs
    level: int


class ContentWriter:
    """
    Writes research paper content using LLM.
    
    Features:
    - Section-by-section writing
    - Source integration with proper citations
    - Academic tone maintenance
    - Transition handling
    """
    
    def __init__(
        self,
        llm_router,
        citation_manager: Optional[CitationManager] = None,
    ):
        """
        Initialize content writer.
        
        Args:
            llm_router: LLM router for content generation
            citation_manager: Citation manager for formatting
        """
        self.llm_router = llm_router
        self.citation_manager = citation_manager or CitationManager()
        self._written_sections: List[WrittenSection] = []
    
    async def write_section(
        self,
        section: Section,
        outline: PaperOutline,
        sources: Dict[str, Source],
        previous_section: Optional[WrittenSection] = None,
    ) -> WrittenSection:
        """
        Write a single section.
        
        Args:
            section: Section to write
            outline: Full paper outline for context
            sources: Available sources (id -> Source)
            previous_section: Previous section for transitions
            
        Returns:
            WrittenSection with content
        """
        # Get sources for this section
        section_sources = [sources[sid] for sid in section.sources if sid in sources]
        
        # Build prompt based on section type
        if section.title.lower() == "introduction":
            content = await self._write_introduction(section, outline, section_sources)
        elif section.title.lower() == "conclusion":
            content = await self._write_conclusion(section, outline, section_sources)
        elif section.title.lower() == "references":
            content = self._write_references(sources)
        elif "literature" in section.title.lower() or "review" in section.title.lower():
            content = await self._write_literature_review(section, outline, section_sources)
        else:
            content = await self._write_body_section(section, outline, section_sources, previous_section)
        
        # Count words
        word_count = len(content.split())
        
        # Track citations used
        citations_used = [s.id for s in section_sources if s.id]
        
        written = WrittenSection(
            title=section.title,
            content=content,
            word_count=word_count,
            citations_used=citations_used,
            level=section.level,
        )
        
        self._written_sections.append(written)
        section.is_complete = True
        section.content = content
        
        logger.info(f"Wrote section '{section.title}': {word_count} words")
        return written
    
    async def _write_introduction(
        self,
        section: Section,
        outline: PaperOutline,
        sources: List[Source],
    ) -> str:
        """Write introduction section."""
        # Build section overview for roadmap
        main_sections = [s.title for s in outline.sections if s.level == 1 and s.title not in ["Introduction", "References"]]
        
        prompt = f"""Write an academic introduction for a research paper.

Topic: {outline.title}
Thesis: {outline.thesis}
Target Length: ~{section.word_target} words
Citation Style: {outline.citation_style.upper()}

Paper sections to preview: {', '.join(main_sections)}

The introduction should include:
1. An engaging hook that introduces the topic's significance
2. Background context establishing the importance of this research
3. The thesis statement (provided above)
4. A brief roadmap of the paper's structure

Write in formal academic tone, third person perspective. Do not use first person (I, we).
Make it engaging but scholarly. Include relevant statistics or facts if appropriate.

Write the introduction now:"""

        try:
            content = await self.llm_router.generate(prompt)
            return self._clean_content(content)
        except Exception as e:
            logger.error(f"Failed to write introduction: {e}")
            return self._fallback_introduction(outline)
    
    async def _write_literature_review(
        self,
        section: Section,
        outline: PaperOutline,
        sources: List[Source],
    ) -> str:
        """Write literature review section."""
        # Build source summaries
        source_info = self._format_sources_for_prompt(sources)
        
        prompt = f"""Write a literature review section for a research paper.

Topic: {outline.title}
Section: {section.title}
Description: {section.description}
Target Length: ~{section.word_target} words
Citation Style: {outline.citation_style.upper()}

Available Sources to Cite:
{source_info}

Guidelines:
1. Synthesize the research, don't just summarize each source
2. Identify themes and patterns across sources
3. Use in-text citations in {outline.citation_style.upper()} format: {self._get_citation_example()}
4. Maintain academic tone (formal, third person)
5. Show how sources relate to each other and the topic
6. Include critical analysis, not just description

Write the literature review section now:"""

        try:
            content = await self.llm_router.generate(prompt)
            content = self._add_citations(content, sources)
            return self._clean_content(content)
        except Exception as e:
            logger.error(f"Failed to write literature review: {e}")
            return self._fallback_literature_review(sources)
    
    async def _write_body_section(
        self,
        section: Section,
        outline: PaperOutline,
        sources: List[Source],
        previous_section: Optional[WrittenSection] = None,
    ) -> str:
        """Write a body section (analysis, discussion, etc.)."""
        source_info = self._format_sources_for_prompt(sources)
        
        transition = ""
        if previous_section:
            transition = f"Previous section '{previous_section.title}' ended with discussion of the topic. Provide a smooth transition."
        
        prompt = f"""Write a body section for a research paper.

Topic: {outline.title}
Section: {section.title}
Description: {section.description}
Target Length: ~{section.word_target} words
Citation Style: {outline.citation_style.upper()}
{transition}

Available Sources to Cite:
{source_info}

Guidelines:
1. Present analysis and arguments clearly
2. Support claims with evidence from sources
3. Use in-text citations: {self._get_citation_example()}
4. Maintain academic tone (formal, third person)
5. Include topic sentences for each paragraph
6. Provide smooth transitions between ideas

Write the section now:"""

        try:
            content = await self.llm_router.generate(prompt)
            content = self._add_citations(content, sources)
            return self._clean_content(content)
        except Exception as e:
            logger.error(f"Failed to write body section: {e}")
            return f"[Content for {section.title} to be added]"
    
    async def _write_conclusion(
        self,
        section: Section,
        outline: PaperOutline,
        sources: List[Source],
    ) -> str:
        """Write conclusion section."""
        # Summarize what was covered
        covered_sections = [s.title for s in outline.sections if s.is_complete and s.title not in ["Introduction", "Conclusion", "References"]]
        
        prompt = f"""Write a conclusion for a research paper.

Topic: {outline.title}
Thesis: {outline.thesis}
Target Length: ~{section.word_target} words
Sections Covered: {', '.join(covered_sections)}

The conclusion should:
1. Summarize the main findings and arguments
2. Restate the thesis in light of the evidence presented
3. Discuss broader implications
4. Suggest future research directions (optional)
5. End with a memorable closing thought

Do NOT introduce new information or citations.
Maintain academic tone (formal, third person).

Write the conclusion now:"""

        try:
            content = await self.llm_router.generate(prompt)
            return self._clean_content(content)
        except Exception as e:
            logger.error(f"Failed to write conclusion: {e}")
            return self._fallback_conclusion(outline)
    
    def _write_references(self, sources: Dict[str, Source]) -> str:
        """Generate references/bibliography section."""
        source_list = list(sources.values())
        return self.citation_manager.generate_bibliography(source_list)
    
    def _format_sources_for_prompt(self, sources: List[Source]) -> str:
        """Format sources for LLM prompt."""
        if not sources:
            return "No specific sources provided. Write based on general knowledge."
        
        lines = []
        for i, source in enumerate(sources[:8], 1):
            author = source.get_author_string()
            year = source.year or "n.d."
            
            # Include key findings if available
            findings = ""
            if source.key_findings:
                findings = f"\n   Key findings: {'; '.join(source.key_findings[:2])}"
            elif source.summary:
                findings = f"\n   Summary: {source.summary[:200]}..."
            elif source.abstract:
                findings = f"\n   Abstract: {source.abstract[:200]}..."
            
            lines.append(f"{i}. {author} ({year}). \"{source.title}\"{findings}")
        
        return "\n".join(lines)
    
    def _get_citation_example(self) -> str:
        """Get citation format example for current style."""
        style = self.citation_manager.style
        
        examples = {
            CitationStyle.APA: "(Author, Year) or (Author, Year, p. X) for quotes",
            CitationStyle.MLA: "(Author Page) - no comma between author and page",
            CitationStyle.CHICAGO: "(Author Year, Page)",
            CitationStyle.IEEE: "[1], [2], etc.",
        }
        
        return examples.get(style, "(Author, Year)")
    
    def _add_citations(self, content: str, sources: List[Source]) -> str:
        """Add proper citations to content where needed."""
        # This is a simplified version - in practice, the LLM should include citations
        # We just ensure they're properly formatted
        
        for source in sources:
            author_last = source.get_first_author_last_name()
            year = source.year or "n.d."
            
            # Look for mentions of the author and add citation if missing
            pattern = rf"\b{re.escape(author_last)}\b(?!\s*\(\d{{4}}\)|\s*\({year}\))"
            
            # Only add citation if author is mentioned without one
            if re.search(pattern, content, re.IGNORECASE):
                citation = self.citation_manager.get_in_text_citation(source)
                # Don't double-cite
                if citation not in content:
                    # Add citation after first mention
                    content = re.sub(
                        pattern,
                        f"{author_last} {citation}",
                        content,
                        count=1,
                        flags=re.IGNORECASE
                    )
        
        return content
    
    def _clean_content(self, content: str) -> str:
        """Clean up generated content."""
        # Remove any meta-commentary from LLM
        content = re.sub(r"^(Here is|Here's|I'll write|Let me write).*?:\s*\n", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\n\n(I hope this|Let me know|Feel free).*$", "", content, flags=re.IGNORECASE | re.DOTALL)
        
        # Clean up excessive whitespace
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = content.strip()
        
        return content
    
    def _fallback_introduction(self, outline: PaperOutline) -> str:
        """Fallback introduction if LLM fails."""
        return f"""The topic of {outline.title} has garnered significant attention in recent years due to its far-reaching implications across multiple domains. As society continues to grapple with the complexities of this issue, understanding its various dimensions becomes increasingly important.

{outline.thesis}

This paper examines the current state of research on this topic, analyzing key findings from scholarly sources and discussing their implications. The following sections provide a comprehensive review of the literature, followed by detailed analysis and discussion of the main themes that emerge from the research."""
    
    def _fallback_literature_review(self, sources: List[Source]) -> str:
        """Fallback literature review if LLM fails."""
        if not sources:
            return "A review of the literature reveals several important themes and findings related to this topic."
        
        paragraphs = []
        for source in sources[:5]:
            citation = self.citation_manager.get_in_text_citation(source)
            if source.summary:
                paragraphs.append(f"{source.summary} {citation}.")
            elif source.abstract:
                paragraphs.append(f"{source.abstract[:300]}... {citation}.")
        
        return "\n\n".join(paragraphs)
    
    def _fallback_conclusion(self, outline: PaperOutline) -> str:
        """Fallback conclusion if LLM fails."""
        return f"""This paper has examined {outline.title} through a comprehensive review of scholarly literature and analysis of key themes. The evidence presented supports the thesis that {outline.thesis.lower()}

The findings discussed throughout this paper highlight the importance of continued research and attention to this topic. As the field continues to evolve, future studies should build upon these foundations to further our understanding.

In conclusion, this analysis contributes to the broader discourse on {outline.title} and provides a foundation for future inquiry into this important area of study."""
    
    async def write_full_paper(
        self,
        outline: PaperOutline,
        sources: Dict[str, Source],
        progress_callback: Optional[callable] = None,
    ) -> List[WrittenSection]:
        """
        Write the complete paper.
        
        Args:
            outline: Paper outline
            sources: All available sources
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of written sections
        """
        self._written_sections = []
        previous_section = None
        
        for i, section in enumerate(outline.sections):
            if progress_callback:
                progress = (i / len(outline.sections)) * 100
                progress_callback(f"Writing {section.title}... ({progress:.0f}%)")
            
            written = await self.write_section(
                section=section,
                outline=outline,
                sources=sources,
                previous_section=previous_section,
            )
            
            previous_section = written
        
        if progress_callback:
            progress_callback("Writing complete! (100%)")
        
        return self._written_sections
    
    def get_full_paper_text(self) -> str:
        """Get the complete paper as formatted text."""
        if not self._written_sections:
            return ""
        
        lines = []
        for section in self._written_sections:
            # Add heading
            if section.level == 1:
                lines.append(f"\n## {section.title}\n")
            else:
                lines.append(f"\n### {section.title}\n")
            
            # Add content
            lines.append(section.content)
            lines.append("")
        
        return "\n".join(lines)
    
    def get_word_count(self) -> int:
        """Get total word count."""
        return sum(s.word_count for s in self._written_sections)
    
    def get_citation_count(self) -> int:
        """Get number of unique citations used."""
        all_citations = set()
        for section in self._written_sections:
            all_citations.update(section.citations_used)
        return len(all_citations)
