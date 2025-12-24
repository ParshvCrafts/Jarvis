"""
Source Collection and Management for JARVIS Research Module.

Handles:
- Source collection from search results
- Source ranking by relevance, citations, recency
- Abstract analysis with LLM
- Source storage and retrieval
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from .scholarly_search import Paper, SearchDatabase


class SourceStatus(Enum):
    """Source processing status."""
    FOUND = "found"
    ANALYZED = "analyzed"
    SELECTED = "selected"
    CITED = "cited"
    REJECTED = "rejected"


@dataclass
class Source:
    """
    Research source with analysis.
    
    Extends Paper with analysis and selection metadata.
    """
    # Core paper data
    title: str
    authors: List[str]  # Simplified to list of names
    year: Optional[int]
    abstract: Optional[str]
    doi: Optional[str] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    citation_count: int = 0
    source_database: str = "unknown"
    venue: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    is_open_access: bool = False
    
    # Analysis data
    summary: Optional[str] = None
    key_findings: List[str] = field(default_factory=list)
    relevant_quotes: List[str] = field(default_factory=list)
    methodology: Optional[str] = None
    
    # Selection data
    relevance_score: float = 0.0
    status: SourceStatus = SourceStatus.FOUND
    selection_reason: Optional[str] = None
    
    # Metadata
    id: Optional[str] = None
    added_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_paper(cls, paper: Paper) -> "Source":
        """Create Source from Paper object."""
        return cls(
            title=paper.title,
            authors=[a.name for a in paper.authors],
            year=paper.year,
            abstract=paper.abstract,
            doi=paper.doi,
            url=paper.url,
            pdf_url=paper.pdf_url,
            citation_count=paper.citation_count,
            source_database=paper.source_database.value,
            venue=paper.venue,
            keywords=paper.keywords,
            is_open_access=paper.is_open_access,
            id=paper.paper_id,
        )
    
    def get_author_string(self, max_authors: int = 3) -> str:
        """Get formatted author string."""
        if not self.authors:
            return "Unknown"
        
        if len(self.authors) <= max_authors:
            if len(self.authors) == 1:
                return self.authors[0]
            elif len(self.authors) == 2:
                return f"{self.authors[0]} & {self.authors[1]}"
            else:
                return ", ".join(self.authors[:-1]) + f", & {self.authors[-1]}"
        else:
            return f"{self.authors[0]} et al."
    
    def get_first_author_last_name(self) -> str:
        """Get first author's last name for citations."""
        if not self.authors:
            return "Unknown"
        
        first_author = self.authors[0]
        # Try to extract last name
        parts = first_author.split()
        if len(parts) > 1:
            return parts[-1]
        return first_author
    
    def __str__(self) -> str:
        return f"{self.get_author_string()} ({self.year}). {self.title}"


class SourceRanker:
    """
    Ranks sources by multiple criteria.
    
    Criteria:
    - Relevance to topic (semantic similarity)
    - Citation count (credibility)
    - Recency (prefer recent papers)
    - Open access (can actually read)
    """
    
    def __init__(
        self,
        relevance_weight: float = 0.4,
        citation_weight: float = 0.25,
        recency_weight: float = 0.25,
        access_weight: float = 0.1,
        prefer_recent_years: int = 5,
    ):
        """
        Initialize ranker with weights.
        
        Args:
            relevance_weight: Weight for relevance score
            citation_weight: Weight for citation count
            recency_weight: Weight for recency
            access_weight: Weight for open access
            prefer_recent_years: Prefer papers within this many years
        """
        self.relevance_weight = relevance_weight
        self.citation_weight = citation_weight
        self.recency_weight = recency_weight
        self.access_weight = access_weight
        self.prefer_recent_years = prefer_recent_years
    
    def rank_sources(
        self,
        sources: List[Source],
        query: str,
        llm_scorer: Optional[Callable[[str, str], float]] = None,
    ) -> List[Source]:
        """
        Rank sources by combined score.
        
        Args:
            sources: List of sources to rank
            query: Original search query for relevance
            llm_scorer: Optional LLM-based relevance scorer
            
        Returns:
            Sources sorted by score (highest first)
        """
        current_year = datetime.now().year
        
        # Calculate max citation for normalization
        max_citations = max((s.citation_count for s in sources), default=1)
        if max_citations == 0:
            max_citations = 1
        
        for source in sources:
            # Relevance score
            if llm_scorer and source.abstract:
                relevance = llm_scorer(query, source.abstract)
            else:
                relevance = self._keyword_relevance(query, source)
            
            # Citation score (normalized)
            citation_score = min(source.citation_count / max_citations, 1.0)
            
            # Recency score
            if source.year:
                years_old = current_year - source.year
                if years_old <= self.prefer_recent_years:
                    recency_score = 1.0
                else:
                    recency_score = max(0, 1.0 - (years_old - self.prefer_recent_years) * 0.1)
            else:
                recency_score = 0.5  # Unknown year
            
            # Open access score
            access_score = 1.0 if source.is_open_access else 0.3
            
            # Combined score
            source.relevance_score = (
                self.relevance_weight * relevance +
                self.citation_weight * citation_score +
                self.recency_weight * recency_score +
                self.access_weight * access_score
            )
        
        # Sort by score
        return sorted(sources, key=lambda s: s.relevance_score, reverse=True)
    
    def _keyword_relevance(self, query: str, source: Source) -> float:
        """Calculate simple keyword-based relevance."""
        query_words = set(query.lower().split())
        
        # Check title
        title_words = set(source.title.lower().split())
        title_overlap = len(query_words & title_words) / len(query_words) if query_words else 0
        
        # Check abstract
        abstract_score = 0
        if source.abstract:
            abstract_words = set(source.abstract.lower().split())
            abstract_overlap = len(query_words & abstract_words) / len(query_words) if query_words else 0
            abstract_score = abstract_overlap
        
        # Check keywords
        keyword_score = 0
        if source.keywords:
            keyword_text = " ".join(source.keywords).lower()
            keyword_words = set(keyword_text.split())
            keyword_overlap = len(query_words & keyword_words) / len(query_words) if query_words else 0
            keyword_score = keyword_overlap
        
        # Weighted combination
        return 0.5 * title_overlap + 0.35 * abstract_score + 0.15 * keyword_score
    
    def select_top_sources(
        self,
        sources: List[Source],
        min_sources: int = 8,
        max_sources: int = 15,
        min_score: float = 0.3,
    ) -> List[Source]:
        """
        Select top sources meeting criteria.
        
        Args:
            sources: Ranked sources
            min_sources: Minimum sources to select
            max_sources: Maximum sources to select
            min_score: Minimum relevance score
            
        Returns:
            Selected sources
        """
        selected = []
        
        for source in sources:
            if len(selected) >= max_sources:
                break
            
            if source.relevance_score >= min_score or len(selected) < min_sources:
                source.status = SourceStatus.SELECTED
                selected.append(source)
        
        logger.info(f"Selected {len(selected)} sources from {len(sources)} candidates")
        return selected


class SourceManager:
    """
    Manages source collection, analysis, and storage.
    """
    
    def __init__(
        self,
        llm_router=None,
        ranker: Optional[SourceRanker] = None,
    ):
        """
        Initialize source manager.
        
        Args:
            llm_router: LLM router for analysis
            ranker: Source ranker (default: SourceRanker())
        """
        self.llm_router = llm_router
        self.ranker = ranker or SourceRanker()
        self.sources: Dict[str, Source] = {}  # id -> Source
    
    def add_papers(self, papers: List[Paper]) -> List[Source]:
        """
        Add papers as sources.
        
        Args:
            papers: Papers from search
            
        Returns:
            Created sources
        """
        sources = []
        for paper in papers:
            source = Source.from_paper(paper)
            # Generate ID if not present
            if not source.id:
                source.id = f"{source.source_database}_{hash(source.title)}"
            
            self.sources[source.id] = source
            sources.append(source)
        
        return sources
    
    def add_papers_from_sources(self, saved_sources: List[Source]) -> List[Source]:
        """
        Add previously saved sources back to the manager.
        
        Args:
            saved_sources: Sources loaded from database
            
        Returns:
            Added sources
        """
        for source in saved_sources:
            if source.id:
                self.sources[source.id] = source
            else:
                source.id = f"{source.source_database}_{hash(source.title)}"
                self.sources[source.id] = source
        
        return saved_sources
    
    def rank_and_select(
        self,
        query: str,
        min_sources: int = 8,
        max_sources: int = 15,
    ) -> List[Source]:
        """
        Rank all sources and select top ones.
        
        Args:
            query: Research query
            min_sources: Minimum to select
            max_sources: Maximum to select
            
        Returns:
            Selected sources
        """
        all_sources = list(self.sources.values())
        
        # Rank sources
        ranked = self.ranker.rank_sources(all_sources, query)
        
        # Select top sources
        selected = self.ranker.select_top_sources(
            ranked,
            min_sources=min_sources,
            max_sources=max_sources,
        )
        
        return selected
    
    async def analyze_source(self, source: Source) -> Source:
        """
        Analyze source abstract with LLM.
        
        Args:
            source: Source to analyze
            
        Returns:
            Source with analysis
        """
        if not self.llm_router or not source.abstract:
            return source
        
        prompt = f"""Analyze this academic paper abstract and extract key information.

Title: {source.title}
Authors: {source.get_author_string()}
Year: {source.year}

Abstract:
{source.abstract}

Provide:
1. A 2-3 sentence summary of the paper's main contribution
2. 2-3 key findings or arguments
3. The methodology used (if mentioned)
4. One relevant quote that could be cited

Format your response as:
SUMMARY: [summary]
FINDINGS:
- [finding 1]
- [finding 2]
- [finding 3]
METHODOLOGY: [methodology or "Not specified"]
QUOTE: "[relevant quote from abstract]"
"""
        
        try:
            response = await self.llm_router.generate(prompt)
            self._parse_analysis(source, response)
            source.status = SourceStatus.ANALYZED
            logger.debug(f"Analyzed source: {source.title[:50]}...")
        except Exception as e:
            logger.warning(f"Failed to analyze source: {e}")
        
        return source
    
    def _parse_analysis(self, source: Source, response: str):
        """Parse LLM analysis response."""
        # Extract summary
        summary_match = re.search(r"SUMMARY:\s*(.+?)(?=FINDINGS:|$)", response, re.DOTALL)
        if summary_match:
            source.summary = summary_match.group(1).strip()
        
        # Extract findings
        findings_match = re.search(r"FINDINGS:\s*(.+?)(?=METHODOLOGY:|$)", response, re.DOTALL)
        if findings_match:
            findings_text = findings_match.group(1)
            findings = re.findall(r"-\s*(.+?)(?=\n-|\n\n|$)", findings_text, re.DOTALL)
            source.key_findings = [f.strip() for f in findings if f.strip()]
        
        # Extract methodology
        method_match = re.search(r"METHODOLOGY:\s*(.+?)(?=QUOTE:|$)", response, re.DOTALL)
        if method_match:
            methodology = method_match.group(1).strip()
            if methodology.lower() != "not specified":
                source.methodology = methodology
        
        # Extract quote
        quote_match = re.search(r'QUOTE:\s*["\']?(.+?)["\']?\s*$', response, re.DOTALL)
        if quote_match:
            quote = quote_match.group(1).strip().strip('"\'')
            if quote:
                source.relevant_quotes.append(quote)
    
    async def analyze_all_selected(self) -> List[Source]:
        """Analyze all selected sources."""
        selected = [s for s in self.sources.values() if s.status == SourceStatus.SELECTED]
        
        for source in selected:
            await self.analyze_source(source)
        
        return selected
    
    def get_selected_sources(self) -> List[Source]:
        """Get all selected sources."""
        return [s for s in self.sources.values() if s.status in [SourceStatus.SELECTED, SourceStatus.ANALYZED, SourceStatus.CITED]]
    
    def get_source_by_id(self, source_id: str) -> Optional[Source]:
        """Get source by ID."""
        return self.sources.get(source_id)
    
    def mark_cited(self, source_id: str):
        """Mark source as cited."""
        if source_id in self.sources:
            self.sources[source_id].status = SourceStatus.CITED
    
    def get_sources_summary(self) -> str:
        """Get summary of collected sources."""
        total = len(self.sources)
        by_status = {}
        by_database = {}
        
        for source in self.sources.values():
            by_status[source.status.value] = by_status.get(source.status.value, 0) + 1
            by_database[source.source_database] = by_database.get(source.source_database, 0) + 1
        
        lines = [f"📚 **Source Collection Summary**"]
        lines.append(f"Total sources: {total}")
        lines.append("")
        lines.append("By database:")
        for db, count in sorted(by_database.items()):
            lines.append(f"  - {db}: {count}")
        lines.append("")
        lines.append("By status:")
        for status, count in sorted(by_status.items()):
            lines.append(f"  - {status}: {count}")
        
        return "\n".join(lines)
    
    def clear(self):
        """Clear all sources."""
        self.sources.clear()
