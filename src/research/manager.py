"""
Research Manager for JARVIS.

Main orchestrator for the Advanced Research & Paper Writing module.
Handles voice commands and coordinates the research workflow.
"""

import asyncio
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from .scholarly_search import ScholarlySearch, Paper
from .source_manager import SourceManager, Source
from .citation_manager import CitationManager, CitationStyle
from .outline_generator import OutlineGenerator
from .content_writer import ContentWriter
from .google_docs import GoogleDocsClient, MockGoogleDocsClient
from .project_store import ProjectStore, ResearchProject, ProjectStatus
from .workflow import ResearchWorkflow, WorkflowConfig, WorkflowStatus, ResearchState


class ResearchManager:
    """
    Central manager for research and paper writing features.
    
    Handles voice command routing and workflow orchestration.
    
    Usage:
        manager = ResearchManager(config, llm_router)
        response = await manager.handle_command("Write a research paper on AI ethics")
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        llm_router=None,
        data_dir: str = "data",
        progress_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize research manager.
        
        Args:
            config: Research configuration from settings.yaml
            llm_router: LLM router for content generation
            data_dir: Directory for data storage
            progress_callback: Callback for progress updates
        """
        self.config = config or {}
        self.llm_router = llm_router
        self.data_dir = data_dir
        self._progress_callback = progress_callback
        
        # Initialize components
        self._init_components()
        
        # Active workflow state
        self._active_workflow: Optional[ResearchWorkflow] = None
        self._current_state: Optional[ResearchState] = None
        
        logger.info("Research Manager initialized")
    
    def _init_components(self):
        """Initialize research components."""
        # Get config values
        api_config = self.config.get("apis", {})
        defaults = self.config.get("defaults", {})
        
        # Email for polite API pools
        email = api_config.get("openalex", {}).get("email")
        
        # Project store
        self.project_store = ProjectStore(
            db_path=f"{self.data_dir}/research_projects.db"
        )
        
        # Workflow config
        self.workflow_config = WorkflowConfig(
            min_sources=defaults.get("min_sources", 8),
            max_sources=defaults.get("max_sources", 15),
            prefer_recent_years=defaults.get("recent_years", 5),
            search_limit_per_db=15,
            use_google_docs=self.config.get("google_docs", {}).get("enabled", True),
            save_progress=True,
        )
        
        # Search client for quick searches
        self.search = ScholarlySearch(email=email)
        
        # Citation manager
        default_style = defaults.get("citation_style", "apa")
        style_map = {
            "apa": CitationStyle.APA,
            "mla": CitationStyle.MLA,
            "chicago": CitationStyle.CHICAGO,
            "ieee": CitationStyle.IEEE,
        }
        self.citation_manager = CitationManager(style_map.get(default_style, CitationStyle.APA))
    
    def _progress_update(self, message: str, progress: float):
        """Handle progress updates."""
        if self._progress_callback:
            self._progress_callback(f"[{progress:.0f}%] {message}")
    
    # =========================================================================
    # Command Handling
    # =========================================================================
    
    async def handle_command(self, text: str) -> Optional[str]:
        """
        Handle a research-related command.
        
        Args:
            text: User command text
            
        Returns:
            Response string if command was handled, None otherwise
        """
        text_lower = text.lower().strip()
        
        # Research paper commands
        if self._is_paper_command(text_lower):
            return await self._handle_paper_command(text_lower, text)
        
        # Quick search commands
        if self._is_search_command(text_lower):
            return await self._handle_search_command(text_lower, text)
        
        # Project management commands
        if self._is_project_command(text_lower):
            return await self._handle_project_command(text_lower, text)
        
        # Citation commands
        if self._is_citation_command(text_lower):
            return self._handle_citation_command(text_lower, text)
        
        return None
    
    # =========================================================================
    # Command Detection
    # =========================================================================
    
    def _is_paper_command(self, text: str) -> bool:
        patterns = [
            "write a research paper", "research paper on", "research paper about",
            "write a paper on", "write a paper about", "write paper",
            "page paper on", "page paper about",
            "start research on", "begin research on",
        ]
        return any(p in text for p in patterns)
    
    def _is_search_command(self, text: str) -> bool:
        patterns = [
            "find papers", "search for papers", "find articles",
            "search for articles", "scholarly search", "academic search",
            "find research on", "search research on",
            "latest research on", "recent papers on",
        ]
        return any(p in text for p in patterns)
    
    def _is_project_command(self, text: str) -> bool:
        patterns = [
            "my research projects", "show research projects", "research projects",
            "resume my", "continue my", "resume research",
            "research status", "paper status",
            "what sources", "sources for",
        ]
        return any(p in text for p in patterns)
    
    def _is_citation_command(self, text: str) -> bool:
        patterns = [
            "how do i cite", "cite this", "citation for",
            "generate citation", "format citation",
            "bibliography", "works cited", "references for",
            "apa format", "mla format", "chicago format", "ieee format",
        ]
        return any(p in text for p in patterns)
    
    # =========================================================================
    # Command Handlers
    # =========================================================================
    
    async def _handle_paper_command(self, text: str, original: str) -> str:
        """Handle research paper writing commands."""
        # Extract topic
        topic = self._extract_topic(text, original)
        if not topic:
            return "What topic would you like me to research? Please say 'Write a research paper on [topic]'."
        
        # Extract page count
        page_count = self._extract_page_count(text)
        
        # Extract citation style
        citation_style = self._extract_citation_style(text)
        
        # Extract focus areas
        focus_areas = self._extract_focus_areas(text)
        
        # Start workflow
        return await self._start_research_workflow(
            topic=topic,
            page_count=page_count,
            citation_style=citation_style,
            focus_areas=focus_areas,
        )
    
    async def _handle_search_command(self, text: str, original: str) -> str:
        """Handle quick scholarly search commands."""
        # Extract search query
        query = self._extract_search_query(text, original)
        if not query:
            return "What topic would you like me to search for? Say 'Find papers about [topic]'."
        
        # Determine if recent papers only
        recent_only = "recent" in text or "latest" in text
        year_start = datetime.now().year - 5 if recent_only else None
        
        # Search
        try:
            papers = await self.search.search_all(
                query=query,
                limit_per_source=10,
                year_start=year_start,
            )
            
            if not papers:
                return f"No papers found for '{query}'. Try a different search term."
            
            # Format results
            return self._format_search_results(papers, query)
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return f"Search failed: {e}. Please try again."
    
    async def _handle_project_command(self, text: str, original: str) -> str:
        """Handle project management commands."""
        # Show all projects
        if "projects" in text and ("show" in text or "my" in text or "list" in text):
            return self.project_store.get_projects_summary()
        
        # Resume project
        if "resume" in text or "continue" in text:
            # Extract project name
            topic_match = re.search(r"(?:resume|continue)\s+(?:my\s+)?(.+?)(?:\s+paper)?$", text)
            if topic_match:
                topic = topic_match.group(1).strip()
                project = self.project_store.get_project_by_topic(topic)
                
                if project:
                    return await self._resume_project(project)
                else:
                    return f"No project found matching '{topic}'. Say 'show my research projects' to see all."
            else:
                # Show incomplete projects
                incomplete = self.project_store.get_incomplete_projects()
                if incomplete:
                    lines = ["Which project would you like to resume?", ""]
                    for p in incomplete[:5]:
                        lines.append(f"- {p.topic} ({p.get_status_display()})")
                    return "\n".join(lines)
                else:
                    return "No incomplete projects to resume."
        
        # Project status
        if "status" in text:
            if self._current_state:
                return self._get_current_status()
            else:
                return "No active research. Say 'show my research projects' to see past projects."
        
        # Sources for project
        if "sources" in text:
            topic_match = re.search(r"sources\s+(?:for|in)\s+(.+)", text)
            if topic_match:
                topic = topic_match.group(1).strip()
                project = self.project_store.get_project_by_topic(topic)
                if project:
                    sources = self.project_store.get_sources(project.id)
                    return self._format_project_sources(sources, project.topic)
            
            # Current project sources
            if self._current_state and self._current_state.get("selected_sources"):
                return self._format_project_sources(
                    self._current_state["selected_sources"],
                    self._current_state["topic"]
                )
            
            return "No sources found. Start a research project first."
        
        return "I can help with research projects. Try:\n- 'Show my research projects'\n- 'Resume my [topic] paper'\n- 'Research status'"
    
    def _handle_citation_command(self, text: str, original: str) -> str:
        """Handle citation-related commands."""
        # Change citation style
        if "apa" in text:
            self.citation_manager.set_style(CitationStyle.APA)
            return "Citation style set to APA 7th Edition.\n\n" + self.citation_manager.get_style_guide()
        elif "mla" in text:
            self.citation_manager.set_style(CitationStyle.MLA)
            return "Citation style set to MLA 9th Edition.\n\n" + self.citation_manager.get_style_guide()
        elif "chicago" in text:
            self.citation_manager.set_style(CitationStyle.CHICAGO)
            return "Citation style set to Chicago style.\n\n" + self.citation_manager.get_style_guide()
        elif "ieee" in text:
            self.citation_manager.set_style(CitationStyle.IEEE)
            return "Citation style set to IEEE style.\n\n" + self.citation_manager.get_style_guide()
        
        # Citation help
        if "how do i cite" in text or "citation" in text:
            return self.citation_manager.get_style_guide()
        
        return "I can help with citations. Try:\n- 'Use APA format'\n- 'Use MLA format'\n- 'How do I cite in APA?'"
    
    # =========================================================================
    # Workflow Management
    # =========================================================================
    
    async def _start_research_workflow(
        self,
        topic: str,
        page_count: int = 10,
        citation_style: str = "apa",
        focus_areas: Optional[List[str]] = None,
    ) -> str:
        """Start a new research workflow."""
        # Create workflow
        self._active_workflow = ResearchWorkflow(
            llm_router=self.llm_router,
            config=self.workflow_config,
            project_store=self.project_store,
            progress_callback=self._progress_update,
            email=self.config.get("apis", {}).get("openalex", {}).get("email"),
        )
        
        # Initial response
        initial_response = f"""🚀 **Starting Research Paper**

**Topic:** {topic}
**Length:** {page_count} pages (~{page_count * 250} words)
**Citation Style:** {citation_style.upper()}
{f"**Focus Areas:** {', '.join(focus_areas)}" if focus_areas else ""}

I'll now:
1. 📋 Plan the paper structure
2. 🔍 Search academic databases (Semantic Scholar, OpenAlex, arXiv, CrossRef)
3. 📊 Analyze and select the best sources
4. ✍️ Write each section with proper citations
5. 📄 Create a formatted Google Doc

**Estimated time:** 30-60 minutes

I'll provide updates as I progress. You can ask "research status" anytime.

Starting now..."""
        
        # Run workflow in background
        asyncio.create_task(self._run_workflow_async(
            topic=topic,
            page_count=page_count,
            citation_style=citation_style,
            focus_areas=focus_areas,
        ))
        
        return initial_response
    
    async def _run_workflow_async(
        self,
        topic: str,
        page_count: int,
        citation_style: str,
        focus_areas: Optional[List[str]],
    ):
        """Run workflow asynchronously."""
        try:
            self._current_state = await self._active_workflow.run(
                topic=topic,
                page_count=page_count,
                citation_style=citation_style,
                focus_areas=focus_areas,
            )
            
            # Notify completion
            if self._progress_callback:
                summary = self._active_workflow.get_completion_summary(self._current_state)
                self._progress_callback(summary)
                
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            if self._progress_callback:
                self._progress_callback(f"❌ Research failed: {e}")
        finally:
            await self._active_workflow.close()
    
    async def _resume_project(self, project: ResearchProject) -> str:
        """Resume an incomplete project."""
        if project.status == ProjectStatus.COMPLETE:
            return f"""✅ **Project Already Complete**

**Topic:** {project.topic}
**Document:** {project.google_doc_url}
**Words:** {project.word_count:,}

Would you like to start a new paper on this topic?"""
        
        # Create workflow and resume
        self._active_workflow = ResearchWorkflow(
            llm_router=self.llm_router,
            config=self.workflow_config,
            project_store=self.project_store,
            progress_callback=self._progress_update,
        )
        
        asyncio.create_task(self._resume_workflow_async(project.id))
        
        return f"""📂 **Resuming Research Project**

**Topic:** {project.topic}
**Status:** {project.get_status_display()}
**Progress:** {project.progress_percent:.0f}%
**Last Section:** {project.current_section or 'N/A'}

Continuing from where we left off..."""
    
    async def _resume_workflow_async(self, project_id: int):
        """Resume workflow asynchronously."""
        try:
            self._current_state = await self._active_workflow.resume(project_id)
            
            if self._progress_callback:
                summary = self._active_workflow.get_completion_summary(self._current_state)
                self._progress_callback(summary)
                
        except Exception as e:
            logger.error(f"Resume failed: {e}")
            if self._progress_callback:
                self._progress_callback(f"❌ Resume failed: {e}")
        finally:
            await self._active_workflow.close()
    
    def _get_current_status(self) -> str:
        """Get current workflow status."""
        if not self._current_state:
            return "No active research."
        
        state = self._current_state
        status = state.get("status", WorkflowStatus.PLANNING)
        
        if status == WorkflowStatus.COMPLETE:
            return self._active_workflow.get_completion_summary(state) if self._active_workflow else "Research complete."
        
        lines = [
            f"📊 **Research Status**",
            "",
            f"**Topic:** {state.get('topic', 'Unknown')}",
            f"**Status:** {status.value.title()}",
            f"**Progress:** {state.get('progress', 0):.0f}%",
            f"**Current Step:** {state.get('current_step', 'Unknown')}",
        ]
        
        if state.get("selected_sources"):
            lines.append(f"**Sources Selected:** {len(state['selected_sources'])}")
        
        if state.get("sections_written"):
            lines.append(f"**Sections Written:** {len(state['sections_written'])}")
        
        return "\n".join(lines)
    
    # =========================================================================
    # Extraction Helpers
    # =========================================================================
    
    def _extract_topic(self, text: str, original: str) -> Optional[str]:
        """Extract research topic from command."""
        patterns = [
            r"research paper (?:on|about)\s+(.+?)(?:\s+for\s+my|\s+in\s+(?:apa|mla|chicago|ieee)|\s+\d+\s*page|$)",
            r"write (?:a\s+)?paper (?:on|about)\s+(.+?)(?:\s+for\s+my|\s+in\s+(?:apa|mla|chicago|ieee)|\s+\d+\s*page|$)",
            r"(\d+)\s*page paper (?:on|about)\s+(.+?)(?:\s+for\s+my|\s+in\s+(?:apa|mla|chicago|ieee)|$)",
            r"start research (?:on|about)\s+(.+?)$",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Handle page count pattern differently
                if "page paper" in pattern:
                    return match.group(2).strip()
                return match.group(1).strip()
        
        return None
    
    def _extract_page_count(self, text: str) -> int:
        """Extract page count from command."""
        match = re.search(r"(\d+)\s*(?:page|pages)", text)
        if match:
            return int(match.group(1))
        return 10  # Default
    
    def _extract_citation_style(self, text: str) -> str:
        """Extract citation style from command."""
        if "mla" in text:
            return "mla"
        elif "chicago" in text:
            return "chicago"
        elif "ieee" in text:
            return "ieee"
        return "apa"  # Default
    
    def _extract_focus_areas(self, text: str) -> Optional[List[str]]:
        """Extract focus areas from command."""
        match = re.search(r"focus(?:ing)? on\s+(.+?)(?:\s+in\s+(?:apa|mla)|$)", text)
        if match:
            areas = match.group(1).split(",")
            return [a.strip() for a in areas if a.strip()]
        return None
    
    def _extract_search_query(self, text: str, original: str) -> Optional[str]:
        """Extract search query from command."""
        patterns = [
            r"(?:find|search for)\s+(?:papers|articles|research)\s+(?:on|about)\s+(.+)",
            r"(?:latest|recent)\s+(?:research|papers)\s+(?:on|about)\s+(.+)",
            r"scholarly search\s+(?:for\s+)?(.+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    # =========================================================================
    # Formatting Helpers
    # =========================================================================
    
    def _format_search_results(self, papers: List[Paper], query: str) -> str:
        """Format search results for display."""
        lines = [
            f"📚 **Found {len(papers)} papers on '{query}'**",
            "",
        ]
        
        for i, paper in enumerate(papers[:10], 1):
            authors = ", ".join(a.name for a in paper.authors[:2])
            if len(paper.authors) > 2:
                authors += " et al."
            
            year = paper.year or "n.d."
            citations = f"({paper.citation_count} citations)" if paper.citation_count else ""
            
            lines.append(f"**{i}. {paper.title}**")
            lines.append(f"   {authors} ({year}) {citations}")
            
            if paper.abstract:
                abstract = paper.abstract[:150] + "..." if len(paper.abstract) > 150 else paper.abstract
                lines.append(f"   *{abstract}*")
            
            if paper.url:
                lines.append(f"   🔗 {paper.url}")
            
            lines.append("")
        
        if len(papers) > 10:
            lines.append(f"*...and {len(papers) - 10} more results*")
        
        lines.append("")
        lines.append("Say 'Write a research paper on [topic]' to start writing!")
        
        return "\n".join(lines)
    
    def _format_project_sources(self, sources: List[Source], topic: str) -> str:
        """Format project sources for display."""
        if not sources:
            return f"No sources found for '{topic}'."
        
        lines = [
            f"📚 **Sources for '{topic}'**",
            f"Total: {len(sources)} sources",
            "",
        ]
        
        for i, source in enumerate(sources[:15], 1):
            year = source.year or "n.d."
            citation = f"({source.citation_count} citations)" if source.citation_count else ""
            
            lines.append(f"**{i}. {source.title}**")
            lines.append(f"   {source.get_author_string()} ({year}) {citation}")
            
            if source.summary:
                lines.append(f"   *{source.summary[:100]}...*")
            
            lines.append("")
        
        return "\n".join(lines)
    
    # =========================================================================
    # Public Interface
    # =========================================================================
    
    def get_projects(self, limit: int = 10) -> List[ResearchProject]:
        """Get recent research projects."""
        return self.project_store.get_all_projects(limit=limit)
    
    def get_project(self, project_id: int) -> Optional[ResearchProject]:
        """Get a specific project."""
        return self.project_store.get_project(project_id)
    
    async def quick_search(self, query: str, limit: int = 20) -> List[Paper]:
        """Perform a quick scholarly search."""
        return await self.search.search_all(query=query, limit_per_source=limit // 4)
    
    async def close(self):
        """Clean up resources."""
        await self.search.close()
        if self._active_workflow:
            await self._active_workflow.close()
