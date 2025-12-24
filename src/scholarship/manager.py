"""
Scholarship Manager for JARVIS Scholarship Module.

Main orchestrator that integrates all components:
- Discovery
- RAG (Supabase or ChromaDB local)
- Essay Generation
- Tracking
- Output
- Database Setup
"""

import os
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

from loguru import logger

from .models import (
    EligibilityProfile,
    Scholarship,
    ScholarshipQuestion,
    Application,
    ApplicationStatus,
    GeneratedEssay,
)
from .discovery import ScholarshipDiscovery
from .rag import ScholarshipRAG
from .generator import EssayGenerator, GenerationConfig, GenerationState
from .tracker import ApplicationTracker
from .importer import EssayImporter
from .docs_output import ScholarshipDocsOutput
from .setup import ScholarshipDatabaseSetup, get_database_mode
from .local_rag import LocalRAGStore, CHROMADB_AVAILABLE


@dataclass
class ScholarshipConfig:
    """Configuration for scholarship manager."""
    # Profile
    profile: Optional[EligibilityProfile] = None
    
    # Discovery
    tavily_api_key: Optional[str] = None
    serper_api_key: Optional[str] = None
    match_threshold: float = 0.80
    
    # RAG
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    use_local_rag: bool = True
    
    # Generation
    primary_llm: str = "groq"
    fallback_llm: str = "gemini"
    auto_adjust_words: bool = True
    
    # Output
    google_credentials_path: str = "config/google_credentials.json"
    
    # Database
    db_path: str = "data/scholarship_applications.db"


class ScholarshipManager:
    """
    Main manager for scholarship automation.
    
    Provides unified interface for:
    - Discovering scholarships
    - Generating essays
    - Tracking applications
    - Managing output
    """
    
    def __init__(
        self,
        config: Optional[ScholarshipConfig] = None,
        llm_router=None,
    ):
        """
        Initialize scholarship manager.
        
        Args:
            config: Configuration options
            llm_router: LLM router for generation
        """
        self.config = config or ScholarshipConfig()
        self.llm_router = llm_router
        self.profile = self.config.profile or EligibilityProfile()
        
        # Initialize components
        self._init_components()
        
        logger.info("Scholarship Manager initialized")
    
    def _init_components(self):
        """Initialize all sub-components."""
        # Discovery
        self.discovery = ScholarshipDiscovery(
            profile=self.profile,
            tavily_api_key=self.config.tavily_api_key,
            serper_api_key=self.config.serper_api_key,
            match_threshold=self.config.match_threshold,
        )
        
        # RAG (with optional Supabase)
        supabase_client = None
        if self.config.supabase_url and self.config.supabase_key:
            try:
                from .supabase_client import SupabaseClient
                supabase_client = SupabaseClient(
                    url=self.config.supabase_url,
                    key=self.config.supabase_key,
                )
            except Exception as e:
                logger.warning(f"Supabase init failed: {e}")
        
        self.rag = ScholarshipRAG(
            supabase_client=supabase_client,
            use_local_fallback=self.config.use_local_rag,
        )
        
        # Generator
        gen_config = GenerationConfig(
            primary_llm=self.config.primary_llm,
            fallback_llm=self.config.fallback_llm,
            auto_adjust=self.config.auto_adjust_words,
        )
        self.generator = EssayGenerator(
            llm_router=self.llm_router,
            rag=self.rag,
            config=gen_config,
        )
        
        # Tracker
        self.tracker = ApplicationTracker(
            db_path=self.config.db_path,
            supabase_client=supabase_client,
        )
        
        # Importer
        self.importer = EssayImporter(rag=self.rag)
        
        # Output
        self.docs_output = ScholarshipDocsOutput(
            credentials_path=self.config.google_credentials_path,
        )
    
    # =========================================================================
    # Discovery
    # =========================================================================
    
    async def search_scholarships(
        self,
        query: Optional[str] = None,
        max_results: int = 20,
    ) -> List[Scholarship]:
        """Search for scholarships matching profile."""
        scholarships = await self.discovery.search(
            query=query,
            max_results=max_results,
        )
        logger.info(f"Found {len(scholarships)} scholarships")
        return scholarships
    
    async def search_due_soon(self, days: int = 30) -> List[Scholarship]:
        """Search for scholarships due within days."""
        return await self.discovery.search_by_deadline(
            days=days,
            min_match=self.config.match_threshold,
        )
    
    async def search_stem(self) -> List[Scholarship]:
        """Search for STEM scholarships."""
        return await self.discovery.search_stem()
    
    async def search_data_science(self) -> List[Scholarship]:
        """Search for data science scholarships."""
        return await self.discovery.search_data_science()
    
    def get_search_summary(self, scholarships: List[Scholarship]) -> str:
        """Get formatted search summary."""
        return self.discovery.get_search_summary(scholarships)
    
    # =========================================================================
    # Essay Generation
    # =========================================================================
    
    async def generate_essay(
        self,
        scholarship: Scholarship,
        question: ScholarshipQuestion,
    ) -> GenerationState:
        """Generate essay for a scholarship question."""
        return await self.generator.generate(
            scholarship=scholarship,
            question=question,
            profile=self.profile,
        )
    
    async def generate_all_essays(
        self,
        scholarship: Scholarship,
    ) -> List[GenerationState]:
        """Generate essays for all questions in a scholarship."""
        return await self.generator.generate_all(
            scholarship=scholarship,
            profile=self.profile,
        )
    
    async def generate_and_save(
        self,
        scholarship: Scholarship,
        create_doc: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate all essays and save to tracker/docs.
        
        Args:
            scholarship: The scholarship
            create_doc: Create Google Doc
            
        Returns:
            Dict with results
        """
        # Create application
        application = self.tracker.create_application(
            scholarship,
            status=ApplicationStatus.IN_PROGRESS,
        )
        
        # Generate essays
        states = await self.generate_all_essays(scholarship)
        
        essays = []
        for state in states:
            if state.final_essay:
                essays.append(state.final_essay)
                self.tracker.save_essay(application.id, state.final_essay)
        
        # Update status
        if essays:
            self.tracker.update_status(
                application.id,
                ApplicationStatus.ESSAYS_COMPLETE,
            )
        
        # Create Google Doc
        doc_url = None
        if create_doc and essays:
            doc_url = self.docs_output.create_essay_document(scholarship, essays)
            if doc_url:
                self.tracker.update_google_doc(application.id, doc_url)
        
        # Create local backup
        backup_path = self.docs_output.create_local_backup(scholarship, essays)
        
        return {
            "application_id": application.id,
            "essays_generated": len(essays),
            "google_doc_url": doc_url,
            "local_backup": backup_path,
            "states": states,
        }
    
    # =========================================================================
    # Application Tracking
    # =========================================================================
    
    def get_applications(self) -> List[Application]:
        """Get all applications."""
        return self.tracker.get_all_applications()
    
    def get_pending_applications(self) -> List[Application]:
        """Get pending applications."""
        return self.tracker.get_pending()
    
    def get_due_soon(self, days: int = 7) -> List[Application]:
        """Get applications due soon."""
        return self.tracker.get_due_soon(days)
    
    def mark_submitted(self, application_id: str) -> bool:
        """Mark application as submitted."""
        return self.tracker.mark_submitted(application_id)
    
    def mark_won(self, application_id: str, amount: Optional[float] = None) -> bool:
        """Mark application as won."""
        return self.tracker.mark_won(application_id, amount)
    
    def mark_lost(self, application_id: str) -> bool:
        """Mark application as lost."""
        return self.tracker.mark_lost(application_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get application statistics."""
        return self.tracker.get_statistics()
    
    def get_statistics_summary(self) -> str:
        """Get formatted statistics."""
        return self.tracker.get_statistics_summary()
    
    def get_due_soon_summary(self, days: int = 7) -> str:
        """Get due soon summary."""
        return self.tracker.get_due_soon_summary(days)
    
    # =========================================================================
    # Import
    # =========================================================================
    
    async def import_essays_folder(self, folder_path: str) -> tuple:
        """Import essays from folder."""
        return await self.importer.import_folder(folder_path)
    
    async def import_winning_essays(self, folder_path: str) -> tuple:
        """Import winning essays from folder."""
        return await self.importer.import_winning_essays_folder(folder_path)
    
    async def import_essay(
        self,
        scholarship_name: str,
        question: str,
        essay_text: str,
        won: bool = False,
    ) -> Optional[str]:
        """Import a single essay."""
        from .models import EssayOutcome
        outcome = EssayOutcome.WON if won else EssayOutcome.PENDING
        return await self.importer.import_essay(
            scholarship_name=scholarship_name,
            question=question,
            essay_text=essay_text,
            outcome=outcome,
        )
    
    async def import_personal_statement(self, file_path: str) -> int:
        """Import personal statement."""
        return await self.importer.import_personal_statement(file_path=file_path)
    
    # =========================================================================
    # Voice Command Handlers
    # =========================================================================
    
    async def handle_voice_command(self, command: str) -> str:
        """
        Handle voice commands for scholarships.
        
        Commands:
        - "find scholarships" / "search scholarships"
        - "scholarships due soon"
        - "scholarship status" / "application status"
        - "generate essay for [scholarship]"
        - "mark [scholarship] submitted"
        - "mark [scholarship] won"
        - "setup scholarship database"
        - "import essays from [folder]"
        - "import my essays"
        """
        command_lower = command.lower()
        
        # Setup command
        if "setup" in command_lower and ("scholarship" in command_lower or "database" in command_lower):
            result = await self.setup_database()
            return result
        
        # Import commands
        if "import" in command_lower and "essay" in command_lower:
            # Check for folder path
            import re
            folder_match = re.search(r'from\s+["\']?([^"\']+)["\']?', command_lower)
            if folder_match:
                folder = folder_match.group(1).strip()
                imported, failed = await self.import_essays_folder(folder)
                return f"📥 Imported {imported} essays ({failed} failed)"
            
            # Default essays folder
            default_folder = "data/past_essays"
            from pathlib import Path
            if Path(default_folder).exists():
                imported, failed = await self.import_essays_folder(default_folder)
                return f"📥 Imported {imported} essays from {default_folder} ({failed} failed)"
            
            return "Please specify a folder: 'import essays from [folder path]'"
        
        # Import personal statement
        if "import" in command_lower and "personal statement" in command_lower:
            import re
            file_match = re.search(r'from\s+["\']?([^"\']+)["\']?', command_lower)
            if file_match:
                file_path = file_match.group(1).strip()
                count = await self.import_personal_statement(file_path)
                return f"📝 Imported {count} personal statement sections"
            return "Please specify a file: 'import personal statement from [file path]'"
        
        # Search commands
        if any(kw in command_lower for kw in ["find scholarship", "search scholarship"]):
            # Check for specific types
            if "stem" in command_lower:
                scholarships = await self.search_stem()
            elif "data science" in command_lower:
                scholarships = await self.search_data_science()
            else:
                scholarships = await self.search_scholarships()
            return self.get_search_summary(scholarships)
        
        if "due soon" in command_lower or "due this week" in command_lower:
            days = 7 if "week" in command_lower else 30
            applications = self.get_due_soon(days)
            return self.get_due_soon_summary(days)
        
        # Status commands
        if any(kw in command_lower for kw in ["scholarship status", "application status", "scholarship stats"]):
            return self.get_status_summary()
        
        if "statistics" in command_lower or "stats" in command_lower:
            return self.get_statistics_summary()
        
        # Mark commands
        if "mark" in command_lower and "submitted" in command_lower:
            # Extract scholarship name
            name = command_lower.replace("mark", "").replace("submitted", "").replace("as", "").strip()
            app = self.tracker.get_application_by_name(name)
            if app:
                self.mark_submitted(app.id)
                return f"✅ Marked {app.scholarship_name} as submitted"
            return f"❌ Application not found: {name}"
        
        if "mark" in command_lower and "won" in command_lower:
            name = command_lower.replace("mark", "").replace("won", "").replace("as", "").strip()
            app = self.tracker.get_application_by_name(name)
            if app:
                self.mark_won(app.id)
                return f"🏆 Marked {app.scholarship_name} as won!"
            return f"❌ Application not found: {name}"
        
        if "mark" in command_lower and "lost" in command_lower:
            name = command_lower.replace("mark", "").replace("lost", "").replace("as", "").strip()
            app = self.tracker.get_application_by_name(name)
            if app:
                self.mark_lost(app.id)
                return f"📝 Marked {app.scholarship_name} as lost"
            return f"❌ Application not found: {name}"
        
        # Database verification
        if "verify" in command_lower and "database" in command_lower:
            return self.verify_database()
        
        return "Command not recognized. Try: find scholarships, due soon, status, setup database, import essays"
    
    # =========================================================================
    # Status
    # =========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive manager status."""
        rag_stats = self.rag.get_stats()
        app_stats = self.tracker.get_statistics()
        
        # Determine RAG mode
        rag_mode, rag_desc = get_database_mode()
        
        # Check API availability
        tavily_available = bool(self.config.tavily_api_key or os.getenv("TAVILY_API_KEY"))
        serper_available = bool(self.config.serper_api_key or os.getenv("SERPER_API_KEY"))
        supabase_available = bool(self.config.supabase_url and self.config.supabase_key)
        
        return {
            "profile": self.profile.name,
            "rag_mode": rag_mode,
            "rag_description": rag_desc,
            "rag_essays": rag_stats.get("local_essays", 0),
            "rag_statements": rag_stats.get("local_statements", 0),
            "rag_profiles": rag_stats.get("local_profiles", 0),
            "applications": app_stats.get("total", 0),
            "won_count": app_stats.get("won", 0),
            "won_amount": app_stats.get("won_amount", 0),
            "pending_count": app_stats.get("pending", 0),
            "submitted_count": app_stats.get("submitted", 0),
            "tavily_available": tavily_available,
            "serper_available": serper_available,
            "supabase_available": supabase_available,
            "chromadb_available": CHROMADB_AVAILABLE,
            "llm_available": self.llm_router is not None,
            "google_docs_available": self.docs_output.is_available,
        }
    
    def get_status_summary(self) -> str:
        """Get formatted status summary for display."""
        status = self.get_status()
        
        lines = [
            "🎓 **Scholarship Module Status**",
            "",
            f"**Profile:** {status['profile']}",
            "",
            "**RAG System:**",
        ]
        
        # RAG mode
        if status['rag_mode'] == 'cloud':
            lines.append(f"  ✅ Supabase: Connected (Cloud Mode)")
        else:
            lines.append(f"  ⚠️ Supabase: Not connected")
            if status['chromadb_available']:
                lines.append(f"  ✅ ChromaDB: Active (Local Mode)")
            else:
                lines.append(f"  ⚠️ ChromaDB: Not installed (In-Memory Mode)")
        
        lines.append(f"  📚 Essays Indexed: {status['rag_essays']}")
        lines.append(f"  📝 Statement Sections: {status['rag_statements']}")
        lines.append(f"  👤 Profile Sections: {status['rag_profiles']}")
        
        lines.extend([
            "",
            "**Discovery APIs:**",
            f"  {'✅' if status['tavily_available'] else '❌'} Tavily API",
            f"  {'✅' if status['serper_available'] else '❌'} Serper API",
            "",
            "**Applications:**",
            f"  📊 Total: {status['applications']}",
            f"  ⏳ Pending: {status['pending_count']}",
            f"  📤 Submitted: {status['submitted_count']}",
            f"  🏆 Won: {status['won_count']} (${status['won_amount']:,.0f})",
            "",
            "**Integrations:**",
            f"  {'✅' if status['llm_available'] else '❌'} LLM Router",
            f"  {'✅' if status['google_docs_available'] else '❌'} Google Docs",
        ])
        
        return "\n".join(lines)
    
    # =========================================================================
    # Database Setup
    # =========================================================================
    
    async def setup_database(self) -> str:
        """
        Setup Supabase database tables for scholarship module.
        
        Returns:
            Status message with setup results
        """
        from .setup import setup_scholarship_database
        return await setup_scholarship_database(
            self.config.supabase_url,
            self.config.supabase_key,
        )
    
    def verify_database(self) -> str:
        """
        Verify database setup status.
        
        Returns:
            Status report
        """
        setup = ScholarshipDatabaseSetup(
            self.config.supabase_url,
            self.config.supabase_key,
        )
        return setup.get_status_report()
    
    def get_database_mode(self) -> tuple:
        """
        Get current database mode.
        
        Returns:
            (mode, description) tuple
        """
        return get_database_mode()
