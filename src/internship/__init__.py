"""
JARVIS Internship Automation Module.

Automates the entire internship search and application process:
- Multi-source job discovery (Adzuna, The Muse, RemoteOK, JSearch, Tavily)
- Resume customization with RAG
- Cover letter generation with company research
- Application tracking and analytics
- ATS optimization

Components:
- models.py: Data models for internships, resumes, applications
- discovery.py: Multi-source job search
- resume_rag.py: RAG system for projects/experience
- resume_generator.py: Resume customization workflow
- cover_letter.py: Cover letter generation
- tracker.py: Application tracking
- prompts.py: LLM prompt templates
- manager.py: Main orchestrator

Usage:
    from src.internship import InternshipManager, InternshipConfig
    
    config = InternshipConfig(
        tavily_api_key="your_key",
    )
    manager = InternshipManager(config=config)
    
    # Search for internships
    listings = await manager.search_internships("data science intern")
    
    # Generate resume
    resume = await manager.generate_resume(listings[0])
    
    # Generate cover letter
    cover_letter = await manager.generate_cover_letter(listings[0])
    
    # Track application
    manager.track_application("Google", "Data Science Intern")
"""

from loguru import logger

# Module availability flag
INTERNSHIP_AVAILABLE = False

# Try importing components
try:
    from .models import (
        UserProfile,
        Skill,
        SkillCategory,
        ProficiencyLevel,
        Project,
        WorkExperience,
        Education,
        MasterResume,
        InternshipListing,
        Application,
        ApplicationStatus,
        JobType,
        LocationType,
        GeneratedResume,
        CoverLetter,
        ApplicationStats,
    )
    
    from .discovery import (
        InternshipDiscovery,
        SearchCriteria,
    )
    
    from .resume_rag import (
        ResumeRAG,
        ResumeRAGContext,
    )
    
    from .resume_generator import (
        ResumeGenerator,
        ResumeGenerationConfig,
        ResumeFormat,
    )
    
    from .cover_letter import (
        CoverLetterGenerator,
        CoverLetterConfig,
    )
    
    from .tracker import (
        ApplicationTracker,
    )
    
    from .prompts import (
        InternshipPrompts,
    )
    
    from .manager import (
        InternshipManager,
        InternshipConfig,
    )
    
    from .diagnostics import (
        diagnose_internship_apis,
        APIStatus,
    )
    
    from .skill_analysis import (
        SkillAnalyzer,
        SkillGapAnalysis,
        format_skill_gap_analysis,
    )
    
    from .analytics import (
        ApplicationAnalytics,
        DashboardData,
        format_dashboard,
        save_html_dashboard,
    )
    
    from .quality_check import (
        ResumeQualityChecker,
        QualityReport,
        format_quality_report,
    )
    
    from .github_import import (
        GitHubImporter,
        get_github_import_summary,
    )
    
    from .importer import (
        ResumeImporter,
        import_resume_data,
        get_import_status_message,
    )
    
    INTERNSHIP_AVAILABLE = True
    logger.info("Internship module loaded successfully")
    
except ImportError as e:
    logger.warning(f"Internship module not fully available: {e}")

# Export all
__all__ = [
    # Availability flag
    "INTERNSHIP_AVAILABLE",
    
    # Models
    "UserProfile",
    "Skill",
    "SkillCategory",
    "ProficiencyLevel",
    "Project",
    "WorkExperience",
    "Education",
    "MasterResume",
    "InternshipListing",
    "Application",
    "ApplicationStatus",
    "JobType",
    "LocationType",
    "GeneratedResume",
    "CoverLetter",
    "ApplicationStats",
    
    # Discovery
    "InternshipDiscovery",
    "SearchCriteria",
    
    # Resume RAG
    "ResumeRAG",
    "ResumeRAGContext",
    
    # Resume Generator
    "ResumeGenerator",
    "ResumeGenerationConfig",
    "ResumeFormat",
    
    # Cover Letter
    "CoverLetterGenerator",
    "CoverLetterConfig",
    
    # Tracker
    "ApplicationTracker",
    
    # Prompts
    "InternshipPrompts",
    
    # Manager
    "InternshipManager",
    "InternshipConfig",
]
