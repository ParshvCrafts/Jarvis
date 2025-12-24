"""
Internship Manager for JARVIS Internship Automation Module.

Main orchestrator that integrates all components:
- Discovery (multi-source job search)
- Resume RAG and customization
- Cover letter generation
- Application tracking
- Voice command handling
"""

import os
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from .models import (
    UserProfile,
    InternshipListing,
    Application,
    ApplicationStatus,
    Project,
    Skill,
    WorkExperience,
    MasterResume,
    GeneratedResume,
    CoverLetter,
)
from .discovery import InternshipDiscovery, SearchCriteria
from .resume_rag import ResumeRAG
from .resume_generator import ResumeGenerator, ResumeGenerationConfig
from .cover_letter import CoverLetterGenerator, CoverLetterConfig
from .tracker import ApplicationTracker
from .diagnostics import diagnose_internship_apis
from .skill_analysis import SkillAnalyzer, format_skill_gap_analysis
from .analytics import ApplicationAnalytics, format_dashboard, save_html_dashboard
from .quality_check import ResumeQualityChecker, format_quality_report
from .github_import import GitHubImporter, get_github_import_summary


@dataclass
class InternshipConfig:
    """Configuration for internship manager."""
    # Profile
    profile: Optional[UserProfile] = None
    
    # API Keys
    adzuna_app_id: Optional[str] = None
    adzuna_api_key: Optional[str] = None
    rapidapi_key: Optional[str] = None
    tavily_api_key: Optional[str] = None
    serper_api_key: Optional[str] = None
    
    # Paths
    db_path: str = "data/internship_applications.db"
    resume_rag_path: str = "data/resume_rag"
    output_directory: str = "data/generated_documents"
    
    # Search settings
    default_search_sources: List[str] = field(default_factory=lambda: [
        "remoteok", "themuse", "tavily", "serper"
    ])
    max_results_per_source: int = 50
    
    # Resume settings
    ats_optimization: bool = True
    target_ats_score: float = 85.0
    
    # Cover letter settings
    cover_letter_word_count: int = 350
    include_company_research: bool = True


class InternshipManager:
    """
    Main manager for internship automation.
    
    Provides unified interface for:
    - Finding internships
    - Customizing resumes
    - Generating cover letters
    - Tracking applications
    - Voice command handling
    """
    
    def __init__(
        self,
        config: Optional[InternshipConfig] = None,
        llm_router=None,
    ):
        self.config = config or InternshipConfig()
        self.llm_router = llm_router
        
        # Initialize profile
        self.profile = self.config.profile or UserProfile()
        
        # Initialize components
        self._init_components()
        
        logger.info("Internship Manager initialized")
    
    def _init_components(self):
        """Initialize all sub-components."""
        # Discovery
        self.discovery = InternshipDiscovery(
            profile=self.profile,
            adzuna_app_id=self.config.adzuna_app_id or os.getenv("ADZUNA_APP_ID"),
            adzuna_api_key=self.config.adzuna_api_key or os.getenv("ADZUNA_API_KEY"),
            rapidapi_key=self.config.rapidapi_key or os.getenv("RAPIDAPI_KEY"),
            tavily_api_key=self.config.tavily_api_key or os.getenv("TAVILY_API_KEY"),
            serper_api_key=self.config.serper_api_key or os.getenv("SERPER_API_KEY"),
        )
        
        # Resume RAG
        self.resume_rag = ResumeRAG(
            persist_directory=self.config.resume_rag_path,
        )
        
        # Resume Generator
        resume_config = ResumeGenerationConfig(
            ats_optimization=self.config.ats_optimization,
            target_ats_score=self.config.target_ats_score,
            output_directory=self.config.output_directory,
        )
        self.resume_generator = ResumeGenerator(
            profile=self.profile,
            resume_rag=self.resume_rag,
            llm_router=self.llm_router,
            config=resume_config,
        )
        
        # Cover Letter Generator
        cover_config = CoverLetterConfig(
            target_word_count=self.config.cover_letter_word_count,
            include_company_research=self.config.include_company_research,
            output_directory=self.config.output_directory,
        )
        self.cover_letter_generator = CoverLetterGenerator(
            profile=self.profile,
            resume_rag=self.resume_rag,
            llm_router=self.llm_router,
            tavily_api_key=self.config.tavily_api_key or os.getenv("TAVILY_API_KEY"),
            config=cover_config,
        )
        
        # Application Tracker
        self.tracker = ApplicationTracker(db_path=self.config.db_path)
    
    # =========================================================================
    # Discovery
    # =========================================================================
    
    async def search_internships(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        company: Optional[str] = None,
        max_results: int = 50,
    ) -> List[InternshipListing]:
        """Search for internships across all sources."""
        return await self.discovery.search(
            query=query,
            location=location,
            company=company,
            max_results=max_results,
            sources=self.config.default_search_sources,
        )
    
    async def search_remote_internships(
        self,
        query: str = "data science",
    ) -> List[InternshipListing]:
        """Search specifically for remote internships."""
        return await self.discovery.search_remote(query)
    
    async def search_company_internships(
        self,
        company: str,
    ) -> List[InternshipListing]:
        """Search for internships at a specific company."""
        return await self.discovery.search_by_company(company)
    
    async def search_faang_internships(self) -> List[InternshipListing]:
        """Search for internships at FAANG companies."""
        return await self.discovery.search_faang()
    
    def get_search_summary(self, listings: List[InternshipListing]) -> str:
        """Get formatted summary of search results."""
        return self.discovery.get_search_summary(listings)
    
    # =========================================================================
    # Resume Generation
    # =========================================================================
    
    async def generate_resume(
        self,
        job: InternshipListing,
    ) -> GeneratedResume:
        """Generate a customized resume for a job."""
        return await self.resume_generator.generate_for_job(job)
    
    async def generate_resume_for_company(
        self,
        company: str,
        role: str,
        description: str = "",
        requirements: List[str] = None,
    ) -> GeneratedResume:
        """Generate resume for a company/role without full listing."""
        listing = InternshipListing(
            company=company,
            role=role,
            description=description,
            requirements=requirements or [],
        )
        return await self.resume_generator.generate_for_job(listing)
    
    def get_resume_summary(self, resume: GeneratedResume) -> str:
        """Get summary of generated resume."""
        return self.resume_generator.get_generation_summary(resume)
    
    # =========================================================================
    # Cover Letter Generation
    # =========================================================================
    
    async def generate_cover_letter(
        self,
        job: InternshipListing,
    ) -> CoverLetter:
        """Generate a cover letter for a job."""
        return await self.cover_letter_generator.generate(job)
    
    async def generate_cover_letter_for_company(
        self,
        company: str,
        role: str,
        description: str = "",
        requirements: List[str] = None,
    ) -> CoverLetter:
        """Generate cover letter for a company/role."""
        listing = InternshipListing(
            company=company,
            role=role,
            description=description,
            requirements=requirements or [],
        )
        return await self.cover_letter_generator.generate(listing)
    
    def get_cover_letter_summary(self, cover_letter: CoverLetter) -> str:
        """Get summary of generated cover letter."""
        return self.cover_letter_generator.get_generation_summary(cover_letter)
    
    # =========================================================================
    # Full Application Package
    # =========================================================================
    
    async def generate_application_package(
        self,
        job: InternshipListing,
        include_cover_letter: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate complete application package (resume + cover letter).
        
        Returns:
            Dict with resume, cover_letter, and application tracking info
        """
        logger.info(f"Generating application package for {job.company} - {job.role}")
        
        # Generate resume
        resume = await self.generate_resume(job)
        
        # Generate cover letter
        cover_letter = None
        if include_cover_letter:
            cover_letter = await self.generate_cover_letter(job)
        
        # Create application tracking entry
        application = self.tracker.create_application_from_listing(job)
        application.resume_version_id = resume.id
        if cover_letter:
            application.cover_letter_id = cover_letter.id
        self.tracker.save_application(application)
        
        return {
            "resume": resume,
            "cover_letter": cover_letter,
            "application": application,
            "summary": self._get_package_summary(resume, cover_letter, job),
        }
    
    def _get_package_summary(
        self,
        resume: GeneratedResume,
        cover_letter: Optional[CoverLetter],
        job: InternshipListing,
    ) -> str:
        """Get summary of generated application package."""
        lines = [
            f"📦 **Application Package Generated**",
            f"",
            f"**Company:** {job.company}",
            f"**Role:** {job.role}",
            f"",
            f"**Resume:**",
            f"  - ATS Score: {resume.ats_score:.0f}%",
            f"  - Projects Used: {len(resume.projects_used)}",
        ]
        
        if resume.pdf_path:
            lines.append(f"  - PDF: {resume.pdf_path}")
        
        if cover_letter:
            lines.extend([
                f"",
                f"**Cover Letter:**",
                f"  - Word Count: {cover_letter.word_count}",
            ])
            if cover_letter.docx_path:
                lines.append(f"  - DOCX: {cover_letter.docx_path}")
        
        lines.extend([
            f"",
            f"✅ Application tracked! Say 'mark {job.company} as applied' when you submit.",
        ])
        
        return "\n".join(lines)
    
    # =========================================================================
    # Application Tracking
    # =========================================================================
    
    def track_application(
        self,
        company: str,
        role: str,
        status: ApplicationStatus = ApplicationStatus.APPLIED,
    ) -> Application:
        """Quick track a new application."""
        return self.tracker.quick_track(company, role, status)
    
    def update_application_status(
        self,
        company: str,
        new_status: ApplicationStatus,
        notes: Optional[str] = None,
    ) -> bool:
        """Update application status by company name."""
        app = self.tracker.get_application_by_company(company)
        if app:
            return self.tracker.update_status(app.id, new_status, notes)
        return False
    
    def mark_applied(self, company: str) -> bool:
        """Mark application as applied."""
        return self.update_application_status(company, ApplicationStatus.APPLIED)
    
    def mark_interview(self, company: str) -> bool:
        """Mark application as having interview."""
        app = self.tracker.get_application_by_company(company)
        if app:
            return self.tracker.mark_interview(app.id)
        return False
    
    def mark_offer(self, company: str, salary: Optional[int] = None) -> bool:
        """Mark application as received offer."""
        app = self.tracker.get_application_by_company(company)
        if app:
            return self.tracker.mark_offer(app.id, salary)
        return False
    
    def mark_rejected(self, company: str) -> bool:
        """Mark application as rejected."""
        return self.update_application_status(company, ApplicationStatus.REJECTED)
    
    def get_pending_applications(self) -> List[Application]:
        """Get pending applications."""
        return self.tracker.get_pending_applications()
    
    def get_follow_up_reminders(self) -> List[Application]:
        """Get applications needing follow-up."""
        return self.tracker.get_follow_up_reminders()
    
    def get_statistics(self) -> str:
        """Get application statistics summary."""
        return self.tracker.get_statistics_summary()
    
    # =========================================================================
    # Resume RAG Management
    # =========================================================================
    
    def add_project(self, project: Project) -> str:
        """Add a project to the resume RAG."""
        return self.resume_rag.add_project(project)
    
    def add_experience(self, experience: WorkExperience) -> str:
        """Add work experience to the resume RAG."""
        return self.resume_rag.add_experience(experience)
    
    def add_skill(self, skill: Skill) -> str:
        """Add a skill to the system."""
        return self.resume_rag.add_skill(skill)
    
    def add_story(self, story_id: str, story_text: str) -> str:
        """Add a story for cover letters."""
        return self.resume_rag.add_story(story_id, story_text)
    
    def get_rag_stats(self) -> Dict[str, int]:
        """Get RAG storage statistics."""
        return self.resume_rag.get_stats()
    
    # =========================================================================
    # Voice Command Handler
    # =========================================================================
    
    async def handle_voice_command(self, command: str) -> str:
        """
        Handle voice commands for internship automation.
        
        Commands:
        - "find internships" / "search internships"
        - "find [company] internships"
        - "remote internships"
        - "customize resume for [company]"
        - "write cover letter for [company]"
        - "track [company] application"
        - "update [company] to interview"
        - "application status" / "my applications"
        - "follow up reminders"
        """
        command_lower = command.lower()
        
        # Search commands
        if any(kw in command_lower for kw in ["find internship", "search internship"]):
            # Check for specific company
            import re
            company_match = re.search(r'(?:at|for)\s+(\w+)', command_lower)
            
            if company_match:
                company = company_match.group(1).title()
                listings = await self.search_company_internships(company)
            elif "remote" in command_lower:
                listings = await self.search_remote_internships()
            elif "faang" in command_lower:
                listings = await self.search_faang_internships()
            else:
                listings = await self.search_internships()
            
            return self.get_search_summary(listings)
        
        # Resume commands
        if "resume" in command_lower and any(kw in command_lower for kw in ["customize", "generate", "create"]):
            import re
            company_match = re.search(r'for\s+(\w+)', command_lower)
            
            if company_match:
                company = company_match.group(1).title()
                role_match = re.search(r'(\w+\s+)?intern', command_lower)
                role = role_match.group(0).title() if role_match else "Intern"
                
                resume = await self.generate_resume_for_company(company, role)
                return self.get_resume_summary(resume)
            
            return "Please specify a company: 'customize resume for Google'"
        
        # Cover letter commands
        if "cover letter" in command_lower:
            import re
            company_match = re.search(r'for\s+(\w+)', command_lower)
            
            if company_match:
                company = company_match.group(1).title()
                role_match = re.search(r'(\w+\s+)?intern', command_lower)
                role = role_match.group(0).title() if role_match else "Intern"
                
                cover_letter = await self.generate_cover_letter_for_company(company, role)
                return self.get_cover_letter_summary(cover_letter)
            
            return "Please specify a company: 'write cover letter for Google'"
        
        # Tracking commands
        if "track" in command_lower and "application" in command_lower:
            import re
            company_match = re.search(r'track\s+(\w+)', command_lower)
            
            if company_match:
                company = company_match.group(1).title()
                app = self.track_application(company, "Intern")
                return f"✅ Tracking application to {company}"
            
            return "Please specify: 'track Google application'"
        
        # Status update commands
        if "update" in command_lower or "mark" in command_lower:
            import re
            
            # Extract company
            company_match = re.search(r'(?:update|mark)\s+(\w+)', command_lower)
            if not company_match:
                return "Please specify a company"
            
            company = company_match.group(1).title()
            
            # Determine new status
            if "interview" in command_lower:
                success = self.mark_interview(company)
                return f"{'✅' if success else '❌'} Marked {company} as interview"
            elif "offer" in command_lower:
                success = self.mark_offer(company)
                return f"{'🎉' if success else '❌'} Marked {company} as offer received!"
            elif "reject" in command_lower:
                success = self.mark_rejected(company)
                return f"{'📝' if success else '❌'} Marked {company} as rejected"
            elif "applied" in command_lower:
                success = self.mark_applied(company)
                return f"{'✅' if success else '❌'} Marked {company} as applied"
            
            return "Specify status: interview, offer, rejected, or applied"
        
        # Statistics commands
        if any(kw in command_lower for kw in ["statistics", "stats", "status", "my application"]):
            return self.get_statistics()
        
        # Follow-up reminders
        if "follow up" in command_lower or "reminder" in command_lower:
            reminders = self.get_follow_up_reminders()
            if not reminders:
                return "✅ No follow-ups needed right now!"
            
            lines = ["📋 **Follow-up Reminders:**", ""]
            for app in reminders[:5]:
                lines.append(f"- {app.company} ({app.role}) - Applied {app.date_applied.strftime('%b %d') if app.date_applied else 'N/A'}")
            
            return "\n".join(lines)
        
        # Pending applications
        if "pending" in command_lower:
            pending = self.get_pending_applications()
            if not pending:
                return "No pending applications."
            
            lines = [f"⏳ **{len(pending)} Pending Applications:**", ""]
            for app in pending[:10]:
                lines.append(f"- {app.company} - {app.role}")
            
            return "\n".join(lines)
        
        # API diagnostics
        if "diagnose" in command_lower and "api" in command_lower:
            return await diagnose_internship_apis()
        
        # Skill gap analysis
        if "skill" in command_lower and ("gap" in command_lower or "missing" in command_lower):
            import re
            company_match = re.search(r'for\s+(\w+)', command_lower)
            if company_match:
                company = company_match.group(1).title()
                # Find the job listing
                listings = await self.search_company_internships(company)
                if listings:
                    analysis = self.analyze_skill_gap(listings[0])
                    return format_skill_gap_analysis(analysis)
                return f"No listings found for {company}"
            return "Please specify: 'skill gap for Google'"
        
        # Dashboard
        if "dashboard" in command_lower:
            return self.get_dashboard()
        
        # Import from GitHub
        if "import" in command_lower and "github" in command_lower:
            result = await self.import_from_github()
            return get_github_import_summary(result)
        
        return (
            "Commands: find internships, customize resume for [company], "
            "write cover letter for [company], track [company] application, "
            "update [company] to interview/offer/rejected, application status, "
            "diagnose APIs, skill gap for [company], dashboard, import from github"
        )
    
    # =========================================================================
    # Status
    # =========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get manager status."""
        rag_stats = self.resume_rag.get_stats()
        app_stats = self.tracker.get_statistics()
        
        return {
            "profile": self.profile.name,
            "rag_projects": rag_stats.get("projects", 0),
            "rag_experience": rag_stats.get("experience", 0),
            "rag_skills": rag_stats.get("skills", 0),
            "rag_stories": rag_stats.get("stories", 0),
            "total_applications": app_stats.total_applications,
            "pending_applications": app_stats.total_applied - app_stats.total_offers - app_stats.total_rejected,
            "offers": app_stats.total_offers,
            "discovery_available": bool(self.config.tavily_api_key or os.getenv("TAVILY_API_KEY")),
            "llm_available": self.llm_router is not None,
        }
    
    def get_status_summary(self) -> str:
        """Get formatted status summary."""
        status = self.get_status()
        
        lines = [
            "💼 **Internship Module Status**",
            "",
            f"**Profile:** {status['profile']}",
            "",
            "**Resume RAG:**",
            f"  📁 Projects: {status['rag_projects']}",
            f"  💼 Experience: {status['rag_experience']}",
            f"  🔧 Skills: {status['rag_skills']}",
            f"  📖 Stories: {status['rag_stories']}",
            "",
            "**Applications:**",
            f"  📊 Total: {status['total_applications']}",
            f"  ⏳ Pending: {status['pending_applications']}",
            f"  🎉 Offers: {status['offers']}",
            "",
            "**Integrations:**",
            f"  {'✅' if status['discovery_available'] else '❌'} Job Discovery APIs",
            f"  {'✅' if status['llm_available'] else '❌'} LLM Router",
        ]
        
        return "\n".join(lines)
    
    # =========================================================================
    # Enhanced Features
    # =========================================================================
    
    def analyze_skill_gap(self, job: InternshipListing) -> Any:
        """Analyze skill gap for a job."""
        analyzer = SkillAnalyzer(self.resume_rag._skills)
        return analyzer.analyze(job)
    
    def get_dashboard(self) -> str:
        """Get application analytics dashboard."""
        analytics = ApplicationAnalytics(self.tracker)
        data = analytics.get_dashboard_data()
        return format_dashboard(data)
    
    def save_dashboard_html(self, output_path: str = "data/internship_dashboard.html") -> str:
        """Save HTML dashboard to file."""
        analytics = ApplicationAnalytics(self.tracker)
        data = analytics.get_dashboard_data()
        return save_html_dashboard(data, output_path)
    
    async def import_from_github(
        self,
        username: Optional[str] = None,
        max_projects: int = 10,
    ) -> Dict[str, Any]:
        """Import projects from GitHub."""
        importer = GitHubImporter()
        
        if not importer.is_configured:
            return {
                "success": False,
                "message": "GITHUB_TOKEN not configured in .env",
                "imported": 0,
            }
        
        return await importer.import_to_rag(
            self.resume_rag,
            username=username,
            max_projects=max_projects,
        )
    
    def check_resume_quality(
        self,
        resume: GeneratedResume,
        job: Optional[InternshipListing] = None,
    ) -> str:
        """Check resume quality and return formatted report."""
        checker = ResumeQualityChecker()
        report = checker.check_resume(resume, job)
        return format_quality_report(report, job)
    
    async def diagnose_apis(self) -> str:
        """Run API diagnostics."""
        return await diagnose_internship_apis()
