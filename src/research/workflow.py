"""
LangGraph Agentic Workflow for JARVIS Research Module.

Orchestrates the complete research paper writing process:
PLANNING → RESEARCHING → ANALYZING → WRITING → FINALIZING → COMPLETE
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypedDict

from loguru import logger

# LangGraph imports
try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.warning("LangGraph not installed. Run: pip install langgraph")

from .scholarly_search import ScholarlySearch, Paper
from .source_manager import SourceManager, Source
from .citation_manager import CitationManager, CitationStyle
from .outline_generator import OutlineGenerator, PaperOutline
from .content_writer import ContentWriter
from .google_docs import GoogleDocsClient, MockGoogleDocsClient, DocumentStyle
from .project_store import ProjectStore, ResearchProject, ProjectStatus


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PLANNING = "planning"
    RESEARCHING = "researching"
    ANALYZING = "analyzing"
    WRITING = "writing"
    FINALIZING = "finalizing"
    COMPLETE = "complete"
    ERROR = "error"
    PAUSED = "paused"


class ResearchState(TypedDict):
    """State for the research workflow."""
    # Input
    topic: str
    page_count: int
    citation_style: str
    focus_areas: List[str]
    custom_requirements: str
    
    # Project
    project_id: Optional[int]
    project: Optional[ResearchProject]
    
    # Research
    papers: List[Paper]
    sources: Dict[str, Source]
    selected_sources: List[Source]
    
    # Writing
    outline: Optional[PaperOutline]
    sections_written: List[str]
    
    # Output
    google_doc_url: Optional[str]
    word_count: int
    
    # Status
    status: WorkflowStatus
    current_step: str
    progress: float
    error: Optional[str]
    messages: List[str]


@dataclass
class WorkflowConfig:
    """Configuration for research workflow."""
    min_sources: int = 8
    max_sources: int = 15
    prefer_recent_years: int = 5
    search_limit_per_db: int = 15
    use_google_docs: bool = True
    save_progress: bool = True


class ResearchWorkflow:
    """
    LangGraph-based research paper workflow.
    
    Autonomously:
    1. Plans paper structure
    2. Searches multiple databases
    3. Analyzes and selects sources
    4. Writes content section by section
    5. Creates formatted Google Doc
    """
    
    def __init__(
        self,
        llm_router,
        config: Optional[WorkflowConfig] = None,
        project_store: Optional[ProjectStore] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        email: Optional[str] = None,
    ):
        """
        Initialize research workflow.
        
        Args:
            llm_router: LLM router for content generation
            config: Workflow configuration
            project_store: Project persistence store
            progress_callback: Callback for progress updates
            email: Email for API polite pools
        """
        self.llm_router = llm_router
        self.config = config or WorkflowConfig()
        self.project_store = project_store or ProjectStore()
        self.progress_callback = progress_callback
        self.email = email
        
        # Initialize components
        self.search = ScholarlySearch(email=email)
        self.source_manager = SourceManager(llm_router=llm_router)
        self.citation_manager = CitationManager()
        self.outline_generator = OutlineGenerator(llm_router=llm_router)
        self.content_writer = ContentWriter(llm_router=llm_router, citation_manager=self.citation_manager)
        
        # Google Docs client (or mock)
        if self.config.use_google_docs:
            self.docs_client = GoogleDocsClient()
        else:
            self.docs_client = MockGoogleDocsClient()
        
        # Build workflow graph
        self._graph = self._build_graph() if LANGGRAPH_AVAILABLE else None
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(ResearchState)
        
        # Add nodes
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("research", self._research_node)
        workflow.add_node("analyze", self._analyze_node)
        workflow.add_node("write", self._write_node)
        workflow.add_node("finalize", self._finalize_node)
        
        # Add edges
        workflow.set_entry_point("plan")
        workflow.add_edge("plan", "research")
        workflow.add_edge("research", "analyze")
        workflow.add_edge("analyze", "write")
        workflow.add_edge("write", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def _update_progress(self, message: str, progress: float):
        """Update progress via callback."""
        if self.progress_callback:
            self.progress_callback(message, progress)
        logger.info(f"[{progress:.0f}%] {message}")
    
    # =========================================================================
    # Workflow Nodes
    # =========================================================================
    
    async def _plan_node(self, state: ResearchState) -> ResearchState:
        """Planning phase: Create project and outline."""
        self._update_progress("📋 Planning paper structure...", 5)
        
        state["status"] = WorkflowStatus.PLANNING
        state["current_step"] = "Planning"
        state["messages"].append("Starting research paper planning...")
        
        # Create project
        project = ResearchProject(
            topic=state["topic"],
            page_count=state["page_count"],
            citation_style=state["citation_style"],
            focus_areas=state["focus_areas"],
            custom_requirements=state["custom_requirements"],
            status=ProjectStatus.PLANNING,
        )
        
        if self.config.save_progress:
            project.id = self.project_store.create_project(project)
        
        state["project"] = project
        state["project_id"] = project.id
        
        # Set citation style
        style_map = {
            "apa": CitationStyle.APA,
            "mla": CitationStyle.MLA,
            "chicago": CitationStyle.CHICAGO,
            "ieee": CitationStyle.IEEE,
        }
        self.citation_manager.set_style(style_map.get(state["citation_style"].lower(), CitationStyle.APA))
        
        state["progress"] = 10
        state["messages"].append(f"Created project: {project.topic}")
        
        return state
    
    async def _research_node(self, state: ResearchState) -> ResearchState:
        """Research phase: Search databases and collect sources."""
        self._update_progress("🔍 Searching academic databases...", 15)
        
        state["status"] = WorkflowStatus.RESEARCHING
        state["current_step"] = "Researching"
        
        if state["project"]:
            state["project"].status = ProjectStatus.RESEARCHING
            if self.config.save_progress:
                self.project_store.update_project(state["project"])
        
        # Search all databases
        try:
            papers = await self.search.search_all(
                query=state["topic"],
                limit_per_source=self.config.search_limit_per_db,
                year_start=datetime.now().year - self.config.prefer_recent_years if self.config.prefer_recent_years else None,
            )
            
            state["papers"] = papers
            state["messages"].append(f"Found {len(papers)} papers from academic databases")
            
            self._update_progress(f"📚 Found {len(papers)} relevant papers", 30)
            
        except Exception as e:
            logger.error(f"Research failed: {e}")
            state["error"] = str(e)
            state["messages"].append(f"Research error: {e}")
        
        state["progress"] = 35
        return state
    
    async def _analyze_node(self, state: ResearchState) -> ResearchState:
        """Analysis phase: Rank, select, and analyze sources."""
        self._update_progress("📊 Analyzing sources...", 40)
        
        state["status"] = WorkflowStatus.ANALYZING
        state["current_step"] = "Analyzing"
        
        if state["project"]:
            state["project"].status = ProjectStatus.ANALYZING
            if self.config.save_progress:
                self.project_store.update_project(state["project"])
        
        # Add papers to source manager
        sources = self.source_manager.add_papers(state["papers"])
        
        # Rank and select
        selected = self.source_manager.rank_and_select(
            query=state["topic"],
            min_sources=self.config.min_sources,
            max_sources=self.config.max_sources,
        )
        
        state["messages"].append(f"Selected {len(selected)} best sources")
        self._update_progress(f"✅ Selected {len(selected)} sources for paper", 45)
        
        # Analyze selected sources
        self._update_progress("🔬 Analyzing source abstracts...", 50)
        
        for i, source in enumerate(selected):
            await self.source_manager.analyze_source(source)
            progress = 50 + (i / len(selected)) * 10
            self._update_progress(f"Analyzed {i+1}/{len(selected)} sources", progress)
        
        # Store sources
        state["sources"] = {s.id: s for s in sources if s.id}
        state["selected_sources"] = selected
        
        # Save sources to project
        if self.config.save_progress and state["project_id"]:
            self.project_store.add_sources(state["project_id"], selected)
        
        # Generate outline
        self._update_progress("📝 Generating paper outline...", 62)
        
        outline = self.outline_generator.generate_outline(
            topic=state["topic"],
            sources=selected,
            target_pages=state["page_count"],
            citation_style=state["citation_style"],
            focus_areas=state["focus_areas"] if state["focus_areas"] else None,
            custom_requirements=state["custom_requirements"] if state["custom_requirements"] else None,
        )
        
        state["outline"] = outline
        state["messages"].append(f"Created outline with {len(outline.sections)} sections")
        
        # Update project
        if state["project"]:
            state["project"].title = outline.title
            state["project"].thesis = outline.thesis
            state["project"].source_count = len(selected)
            if self.config.save_progress:
                self.project_store.update_project(state["project"])
        
        state["progress"] = 65
        return state
    
    async def _write_node(self, state: ResearchState) -> ResearchState:
        """Writing phase: Write paper content section by section."""
        self._update_progress("✍️ Writing paper content...", 68)
        
        state["status"] = WorkflowStatus.WRITING
        state["current_step"] = "Writing"
        
        if state["project"]:
            state["project"].status = ProjectStatus.WRITING
            if self.config.save_progress:
                self.project_store.update_project(state["project"])
        
        outline = state["outline"]
        sources = state["sources"]
        
        # Create Google Doc
        self._update_progress("📄 Creating Google Doc...", 70)
        
        if self.docs_client.is_available:
            if not self.docs_client.authenticate():
                logger.warning("Google Docs auth failed, using mock")
                self.docs_client = MockGoogleDocsClient()
        
        doc_id = self.docs_client.create_document(outline.title)
        
        # Apply academic formatting
        self.docs_client.apply_document_style(DocumentStyle(
            font_family="Times New Roman",
            font_size=12,
            line_spacing=2.0,
            margin_top=1.0,
            margin_bottom=1.0,
            margin_left=1.0,
            margin_right=1.0,
        ))
        
        # Write title
        self.docs_client.insert_title(outline.title)
        self.docs_client.insert_paragraph("")
        
        # Write each section
        sections_written = []
        total_sections = len(outline.sections)
        
        for i, section in enumerate(outline.sections):
            progress = 70 + (i / total_sections) * 25
            self._update_progress(f"Writing: {section.title}", progress)
            
            # Update project current section
            if state["project"]:
                state["project"].current_section = section.title
                state["project"].progress_percent = progress
                if self.config.save_progress:
                    self.project_store.update_progress(
                        state["project_id"],
                        ProjectStatus.WRITING,
                        progress,
                        section.title,
                    )
            
            # Write section
            written = await self.content_writer.write_section(
                section=section,
                outline=outline,
                sources=sources,
                previous_section=self.content_writer._written_sections[-1] if self.content_writer._written_sections else None,
            )
            
            # Insert into Google Doc
            self.docs_client.insert_heading(section.title, section.level)
            
            # Split content into paragraphs
            paragraphs = written.content.split("\n\n")
            for para in paragraphs:
                if para.strip():
                    self.docs_client.insert_paragraph(para.strip())
            
            sections_written.append(section.title)
            
            # Save section
            if self.config.save_progress and state["project_id"]:
                self.project_store.save_section(
                    state["project_id"],
                    section.title,
                    written.content,
                    section.level,
                    i,
                )
            
            state["messages"].append(f"Wrote {section.title}: {written.word_count} words")
        
        state["sections_written"] = sections_written
        state["word_count"] = self.content_writer.get_word_count()
        state["progress"] = 95
        
        return state
    
    async def _finalize_node(self, state: ResearchState) -> ResearchState:
        """Finalization phase: Complete document and share."""
        self._update_progress("📝 Finalizing document...", 96)
        
        state["status"] = WorkflowStatus.FINALIZING
        state["current_step"] = "Finalizing"
        
        if state["project"]:
            state["project"].status = ProjectStatus.FINALIZING
            if self.config.save_progress:
                self.project_store.update_project(state["project"])
        
        # Get shareable link
        doc_url = self.docs_client.set_sharing(anyone_can_view=True)
        state["google_doc_url"] = doc_url
        
        # Mark complete
        state["status"] = WorkflowStatus.COMPLETE
        state["progress"] = 100
        
        if state["project"]:
            state["project"].status = ProjectStatus.COMPLETE
            state["project"].google_doc_url = doc_url
            state["project"].word_count = state["word_count"]
            state["project"].completed_at = datetime.now()
            
            if self.config.save_progress:
                self.project_store.mark_complete(
                    state["project_id"],
                    doc_url,
                    state["word_count"],
                )
        
        self._update_progress("✅ Research paper complete!", 100)
        state["messages"].append(f"Paper complete: {state['word_count']} words")
        state["messages"].append(f"Document: {doc_url}")
        
        return state
    
    # =========================================================================
    # Public Interface
    # =========================================================================
    
    async def run(
        self,
        topic: str,
        page_count: int = 10,
        citation_style: str = "apa",
        focus_areas: Optional[List[str]] = None,
        custom_requirements: Optional[str] = None,
    ) -> ResearchState:
        """
        Run the complete research workflow.
        
        Args:
            topic: Research topic
            page_count: Target page count
            citation_style: Citation format (apa, mla, chicago, ieee)
            focus_areas: Specific areas to focus on
            custom_requirements: Additional requirements
            
        Returns:
            Final workflow state
        """
        # Initialize state
        initial_state: ResearchState = {
            "topic": topic,
            "page_count": page_count,
            "citation_style": citation_style,
            "focus_areas": focus_areas or [],
            "custom_requirements": custom_requirements or "",
            "project_id": None,
            "project": None,
            "papers": [],
            "sources": {},
            "selected_sources": [],
            "outline": None,
            "sections_written": [],
            "google_doc_url": None,
            "word_count": 0,
            "status": WorkflowStatus.PLANNING,
            "current_step": "Starting",
            "progress": 0,
            "error": None,
            "messages": [],
        }
        
        self._update_progress(f"🚀 Starting research paper on: {topic}", 0)
        
        if self._graph and LANGGRAPH_AVAILABLE:
            # Use LangGraph
            try:
                final_state = await self._graph.ainvoke(initial_state)
                return final_state
            except Exception as e:
                logger.error(f"Workflow failed: {e}")
                initial_state["status"] = WorkflowStatus.ERROR
                initial_state["error"] = str(e)
                return initial_state
        else:
            # Manual execution without LangGraph
            state = initial_state
            try:
                state = await self._plan_node(state)
                state = await self._research_node(state)
                state = await self._analyze_node(state)
                state = await self._write_node(state)
                state = await self._finalize_node(state)
                return state
            except Exception as e:
                logger.error(f"Workflow failed: {e}")
                state["status"] = WorkflowStatus.ERROR
                state["error"] = str(e)
                return state
    
    async def resume(self, project_id: int) -> ResearchState:
        """
        Resume an incomplete project from where it left off.
        
        Args:
            project_id: Project ID to resume
            
        Returns:
            Final workflow state
        """
        project = self.project_store.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        self._update_progress(f"📂 Resuming project: {project.topic}", project.progress_percent)
        
        # Load existing data
        saved_sources = self.project_store.get_sources(project_id)
        saved_sections = self.project_store.get_sections(project_id)
        
        # If complete, just return status
        if project.status == ProjectStatus.COMPLETE:
            return {
                "topic": project.topic,
                "status": WorkflowStatus.COMPLETE,
                "google_doc_url": project.google_doc_url,
                "word_count": project.word_count,
                "messages": ["Project already complete"],
                "progress": 100,
                "current_step": "Complete",
            }
        
        # Build state from saved data
        state: ResearchState = {
            "topic": project.topic,
            "page_count": project.page_count,
            "citation_style": project.citation_style,
            "focus_areas": project.focus_areas,
            "custom_requirements": project.custom_requirements,
            "project_id": project_id,
            "project": project,
            "papers": [],
            "sources": {s.id: s for s in saved_sources if s.id},
            "selected_sources": saved_sources,
            "outline": None,
            "sections_written": [s["section_name"] for s in saved_sections if s.get("status") == "complete"],
            "google_doc_url": project.google_doc_url,
            "word_count": project.word_count,
            "status": WorkflowStatus(project.status.value) if hasattr(project.status, 'value') else WorkflowStatus.PLANNING,
            "current_step": project.current_section or "Resuming",
            "progress": project.progress_percent,
            "error": None,
            "messages": [f"Resuming from {project.status.value}..."],
        }
        
        # Determine where to resume based on status
        try:
            if project.status == ProjectStatus.PLANNING:
                # Start from beginning
                state = await self._plan_node(state)
                state = await self._research_node(state)
                state = await self._analyze_node(state)
                state = await self._write_node(state)
                state = await self._finalize_node(state)
                
            elif project.status == ProjectStatus.RESEARCHING:
                # Have project, need to research
                state = await self._research_node(state)
                state = await self._analyze_node(state)
                state = await self._write_node(state)
                state = await self._finalize_node(state)
                
            elif project.status == ProjectStatus.ANALYZING:
                # Have sources, need to analyze and write
                if saved_sources:
                    state = await self._analyze_node(state)
                else:
                    state = await self._research_node(state)
                    state = await self._analyze_node(state)
                state = await self._write_node(state)
                state = await self._finalize_node(state)
                
            elif project.status == ProjectStatus.WRITING:
                # Have outline, continue writing
                # Regenerate outline from saved data
                if saved_sources:
                    self.source_manager.add_papers_from_sources(saved_sources)
                    state["outline"] = self.outline_generator.generate_outline(
                        topic=project.topic,
                        sources=saved_sources,
                        target_pages=project.page_count,
                        citation_style=project.citation_style,
                        focus_areas=project.focus_areas,
                    )
                    # Mark completed sections
                    completed_names = {s["section_name"] for s in saved_sections if s.get("status") == "complete"}
                    for section in state["outline"].sections:
                        if section.title in completed_names:
                            section.is_complete = True
                    
                    state = await self._write_node(state)
                    state = await self._finalize_node(state)
                else:
                    # No sources, start over
                    return await self.run(
                        topic=project.topic,
                        page_count=project.page_count,
                        citation_style=project.citation_style,
                        focus_areas=project.focus_areas,
                    )
                
            elif project.status == ProjectStatus.FINALIZING:
                # Just need to finalize
                state = await self._finalize_node(state)
                
            elif project.status in [ProjectStatus.PAUSED, ProjectStatus.ERROR]:
                # Resume from last known good state
                if saved_sections:
                    # Had started writing, continue from there
                    state["outline"] = self.outline_generator.generate_outline(
                        topic=project.topic,
                        sources=saved_sources,
                        target_pages=project.page_count,
                        citation_style=project.citation_style,
                    )
                    state = await self._write_node(state)
                    state = await self._finalize_node(state)
                elif saved_sources:
                    state = await self._analyze_node(state)
                    state = await self._write_node(state)
                    state = await self._finalize_node(state)
                else:
                    # Start over
                    return await self.run(
                        topic=project.topic,
                        page_count=project.page_count,
                        citation_style=project.citation_style,
                    )
            
            return state
            
        except Exception as e:
            logger.error(f"Resume failed: {e}")
            state["status"] = WorkflowStatus.ERROR
            state["error"] = str(e)
            # Save error state
            if self.config.save_progress:
                self.project_store.update_progress(
                    project_id,
                    ProjectStatus.ERROR,
                    state["progress"],
                    f"Error: {str(e)[:100]}",
                )
            return state
    
    def get_completion_summary(self, state: ResearchState) -> str:
        """Get human-readable completion summary."""
        if state["status"] == WorkflowStatus.ERROR:
            return f"❌ Research failed: {state.get('error', 'Unknown error')}"
        
        if state["status"] != WorkflowStatus.COMPLETE:
            return f"⏳ Research in progress: {state.get('current_step', 'Unknown')} ({state.get('progress', 0):.0f}%)"
        
        lines = [
            "✅ **Research Paper Complete!**",
            "",
            f"📄 **Document:** {state.get('google_doc_url', 'N/A')}",
            "",
            f"📊 **Stats:**",
            f"   - Pages: ~{state.get('word_count', 0) // 250}",
            f"   - Words: {state.get('word_count', 0):,}",
            f"   - Sources: {len(state.get('selected_sources', []))}",
            f"   - Citation Style: {state.get('citation_style', 'APA').upper()}",
            "",
            f"📝 **Sections Written:**",
        ]
        
        for section in state.get("sections_written", []):
            lines.append(f"   - {section}")
        
        return "\n".join(lines)
    
    async def close(self):
        """Clean up resources."""
        await self.search.close()
        self.docs_client.close()
