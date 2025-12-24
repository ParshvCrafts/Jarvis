"""
Advanced Research & Paper Writing Module for JARVIS.

This module provides a sophisticated agentic workflow that can:
- Search multiple scholarly databases (Semantic Scholar, OpenAlex, arXiv, CrossRef)
- Collect and analyze academic sources
- Generate research paper outlines
- Write complete papers with proper citations
- Create formatted Google Docs
- Manage research projects

Components:
- scholarly_search: Multi-database academic search
- source_manager: Source collection, ranking, and analysis
- citation_manager: Citation formatting (APA, MLA, Chicago, IEEE)
- google_docs: Document creation and formatting
- outline_generator: Paper structure creation
- content_writer: Section-by-section writing
- workflow: LangGraph agentic orchestration
- project_store: Project persistence
- manager: Main orchestrator
"""

from typing import TYPE_CHECKING

# Availability flags
SEMANTIC_SCHOLAR_AVAILABLE = True
OPENALEX_AVAILABLE = True
ARXIV_AVAILABLE = True
CROSSREF_AVAILABLE = True
GOOGLE_DOCS_AVAILABLE = True
RESEARCH_AVAILABLE = True

try:
    from .scholarly_search import (
        ScholarlySearch,
        SemanticScholarClient,
        OpenAlexClient,
        ArxivClient,
        CrossRefClient,
        Paper,
        Author,
        SearchDatabase,
        SearchResult,
    )
except ImportError as e:
    RESEARCH_AVAILABLE = False
    ScholarlySearch = None
    SemanticScholarClient = None
    OpenAlexClient = None
    ArxivClient = None
    CrossRefClient = None
    Paper = None
    Author = None
    SearchDatabase = None
    SearchResult = None

try:
    from .source_manager import SourceManager, Source, SourceRanker
except ImportError:
    SourceManager = None
    Source = None
    SourceRanker = None

try:
    from .citation_manager import CitationManager, CitationStyle
except ImportError:
    CitationManager = None
    CitationStyle = None

try:
    from .google_docs import GoogleDocsClient
except ImportError:
    GOOGLE_DOCS_AVAILABLE = False
    GoogleDocsClient = None

try:
    from .outline_generator import OutlineGenerator, PaperOutline
except ImportError:
    OutlineGenerator = None
    PaperOutline = None

try:
    from .content_writer import ContentWriter
except ImportError:
    ContentWriter = None

try:
    from .workflow import ResearchWorkflow, ResearchState, WorkflowStatus
except ImportError:
    ResearchWorkflow = None
    ResearchState = None
    WorkflowStatus = None

try:
    from .project_store import ProjectStore, ResearchProject
except ImportError:
    ProjectStore = None
    ResearchProject = None

try:
    from .manager import ResearchManager
except ImportError:
    ResearchManager = None

__all__ = [
    # Availability flags
    "RESEARCH_AVAILABLE",
    "GOOGLE_DOCS_AVAILABLE",
    # Search
    "ScholarlySearch",
    "SemanticScholarClient",
    "OpenAlexClient", 
    "ArxivClient",
    "CrossRefClient",
    # Sources
    "SourceManager",
    "Source",
    "SourceRanker",
    # Citations
    "CitationManager",
    "CitationStyle",
    # Google Docs
    "GoogleDocsClient",
    # Outline
    "OutlineGenerator",
    "PaperOutline",
    # Writing
    "ContentWriter",
    # Workflow
    "ResearchWorkflow",
    "ResearchState",
    "WorkflowStatus",
    # Projects
    "ProjectStore",
    "ResearchProject",
    # Manager
    "ResearchManager",
]
