"""
Data Models for JARVIS Internship Automation Module.

Defines all data structures for:
- User profile and preferences
- Internship listings
- Resume components (projects, skills, experience)
- Applications and tracking
- Generated documents
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class ApplicationStatus(Enum):
    """Status of an internship application."""
    SAVED = "saved"
    APPLIED = "applied"
    PHONE_SCREEN = "phone_screen"
    TECHNICAL = "technical"
    INTERVIEW = "interview"
    FINAL_ROUND = "final_round"
    OFFER = "offer"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class JobType(Enum):
    """Type of job/internship."""
    INTERNSHIP = "internship"
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    CO_OP = "co_op"


class LocationType(Enum):
    """Work location type."""
    REMOTE = "remote"
    ONSITE = "onsite"
    HYBRID = "hybrid"


class SkillCategory(Enum):
    """Category of skill."""
    PROGRAMMING = "programming"
    DATA_SCIENCE = "data_science"
    MACHINE_LEARNING = "machine_learning"
    DATABASE = "database"
    CLOUD = "cloud"
    TOOLS = "tools"
    SOFT_SKILLS = "soft_skills"
    DOMAIN = "domain"
    OTHER = "other"


class ProficiencyLevel(Enum):
    """Skill proficiency level."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class UserProfile:
    """User's profile for job matching."""
    name: str = "Parshv"
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""
    
    # Education
    university: str = "UC Berkeley"
    major: str = "Data Science"
    minor: Optional[str] = None
    gpa: float = 4.0
    graduation_year: int = 2028
    education_level: str = "Undergraduate"
    year: str = "Freshman"
    
    # Preferences
    target_roles: List[str] = field(default_factory=lambda: [
        "Data Science Intern",
        "ML Intern", 
        "Software Engineering Intern",
        "AI Research Intern"
    ])
    preferred_location: LocationType = LocationType.REMOTE
    willing_to_relocate: bool = True
    target_companies: List[str] = field(default_factory=lambda: [
        "Google", "Meta", "Amazon", "Microsoft", "Apple"
    ])
    min_salary: int = 0  # Flexible for internships
    
    # Skills summary
    primary_skills: List[str] = field(default_factory=lambda: [
        "Python", "SQL", "Machine Learning", "Data Analysis"
    ])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "email": self.email,
            "university": self.university,
            "major": self.major,
            "gpa": self.gpa,
            "graduation_year": self.graduation_year,
            "year": self.year,
            "target_roles": self.target_roles,
            "preferred_location": self.preferred_location.value,
            "primary_skills": self.primary_skills,
        }


@dataclass
class Skill:
    """A skill with proficiency and evidence."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    category: SkillCategory = SkillCategory.PROGRAMMING
    proficiency: ProficiencyLevel = ProficiencyLevel.INTERMEDIATE
    years_experience: float = 0.0
    evidence: List[str] = field(default_factory=list)  # Project IDs that demonstrate this
    keywords: List[str] = field(default_factory=list)  # Related keywords for matching
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "proficiency": self.proficiency.value,
            "years_experience": self.years_experience,
            "evidence": self.evidence,
            "keywords": self.keywords,
        }


@dataclass
class Project:
    """A project for resume/portfolio."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    detailed_description: str = ""
    technologies: List[str] = field(default_factory=list)
    skills_demonstrated: List[str] = field(default_factory=list)
    
    # Impact and metrics
    impact_metrics: List[str] = field(default_factory=list)
    quantified_results: List[str] = field(default_factory=list)
    
    # Dates
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_ongoing: bool = False
    
    # Links
    github_url: Optional[str] = None
    demo_url: Optional[str] = None
    paper_url: Optional[str] = None
    
    # Resume bullets (pre-written)
    resume_bullets: List[str] = field(default_factory=list)
    
    # For RAG
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "detailed_description": self.detailed_description,
            "technologies": self.technologies,
            "skills_demonstrated": self.skills_demonstrated,
            "impact_metrics": self.impact_metrics,
            "quantified_results": self.quantified_results,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_ongoing": self.is_ongoing,
            "github_url": self.github_url,
            "resume_bullets": self.resume_bullets,
        }
    
    def get_searchable_text(self) -> str:
        """Get text for embedding/search."""
        parts = [
            self.name,
            self.description,
            self.detailed_description,
            " ".join(self.technologies),
            " ".join(self.skills_demonstrated),
            " ".join(self.impact_metrics),
            " ".join(self.resume_bullets),
        ]
        return " ".join(filter(None, parts))


@dataclass
class WorkExperience:
    """Work experience entry."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    company: str = ""
    role: str = ""
    location: str = ""
    location_type: LocationType = LocationType.ONSITE
    
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    
    description: str = ""
    achievements: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    
    # For RAG
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "company": self.company,
            "role": self.role,
            "location": self.location,
            "location_type": self.location_type.value,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_current": self.is_current,
            "description": self.description,
            "achievements": self.achievements,
            "technologies": self.technologies,
        }
    
    def get_searchable_text(self) -> str:
        """Get text for embedding/search."""
        parts = [
            self.company,
            self.role,
            self.description,
            " ".join(self.achievements),
            " ".join(self.technologies),
        ]
        return " ".join(filter(None, parts))


@dataclass
class Education:
    """Education entry."""
    institution: str = ""
    degree: str = ""
    major: str = ""
    minor: Optional[str] = None
    gpa: Optional[float] = None
    start_date: Optional[date] = None
    graduation_date: Optional[date] = None
    honors: List[str] = field(default_factory=list)
    relevant_coursework: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "institution": self.institution,
            "degree": self.degree,
            "major": self.major,
            "minor": self.minor,
            "gpa": self.gpa,
            "graduation_date": self.graduation_date.isoformat() if self.graduation_date else None,
            "honors": self.honors,
            "relevant_coursework": self.relevant_coursework,
        }


@dataclass
class MasterResume:
    """Master resume containing all information."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    version: int = 1
    
    # Contact
    contact: Dict[str, str] = field(default_factory=dict)
    
    # Sections
    education: List[Education] = field(default_factory=list)
    experience: List[WorkExperience] = field(default_factory=list)
    projects: List[Project] = field(default_factory=list)
    skills: List[Skill] = field(default_factory=list)
    
    # Additional sections
    summary: str = ""
    certifications: List[str] = field(default_factory=list)
    awards: List[str] = field(default_factory=list)
    publications: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "contact": self.contact,
            "education": [e.to_dict() for e in self.education],
            "experience": [e.to_dict() for e in self.experience],
            "projects": [p.to_dict() for p in self.projects],
            "skills": [s.to_dict() for s in self.skills],
            "summary": self.summary,
            "certifications": self.certifications,
            "awards": self.awards,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class InternshipListing:
    """An internship/job listing."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Basic info
    company: str = ""
    role: str = ""
    location: str = ""
    location_type: LocationType = LocationType.REMOTE
    job_type: JobType = JobType.INTERNSHIP
    
    # Details
    description: str = ""
    requirements: List[str] = field(default_factory=list)
    preferred_qualifications: List[str] = field(default_factory=list)
    responsibilities: List[str] = field(default_factory=list)
    
    # Compensation
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_type: str = "hourly"  # hourly, annual
    benefits: List[str] = field(default_factory=list)
    
    # Application
    deadline: Optional[date] = None
    url: str = ""
    application_url: str = ""
    
    # Source
    source_api: str = ""  # adzuna, themuse, remoteok, etc.
    source_id: str = ""
    
    # Matching
    match_score: float = 0.0
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    
    # Keywords extracted
    keywords: List[str] = field(default_factory=list)
    
    # Status
    status: str = "new"  # new, saved, applied, hidden
    
    # Metadata
    posted_date: Optional[date] = None
    discovered_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "company": self.company,
            "role": self.role,
            "location": self.location,
            "location_type": self.location_type.value,
            "job_type": self.job_type.value,
            "description": self.description,
            "requirements": self.requirements,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "url": self.url,
            "source_api": self.source_api,
            "match_score": self.match_score,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "keywords": self.keywords,
            "status": self.status,
            "posted_date": self.posted_date.isoformat() if self.posted_date else None,
        }
    
    def get_salary_display(self) -> str:
        """Get formatted salary string."""
        if self.salary_min and self.salary_max:
            if self.salary_type == "hourly":
                return f"${self.salary_min}-${self.salary_max}/hr"
            return f"${self.salary_min:,}-${self.salary_max:,}/yr"
        elif self.salary_min:
            if self.salary_type == "hourly":
                return f"${self.salary_min}/hr"
            return f"${self.salary_min:,}/yr"
        return "Not specified"


@dataclass
class Application:
    """An internship application."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Reference
    internship_id: str = ""
    company: str = ""
    role: str = ""
    
    # Status
    status: ApplicationStatus = ApplicationStatus.SAVED
    
    # Documents used
    resume_version_id: Optional[str] = None
    cover_letter_id: Optional[str] = None
    
    # Dates
    date_saved: datetime = field(default_factory=datetime.now)
    date_applied: Optional[datetime] = None
    follow_up_date: Optional[date] = None
    response_date: Optional[datetime] = None
    
    # Notes
    notes: str = ""
    contact_person: str = ""
    contact_email: str = ""
    
    # Interview tracking
    interviews: List[Dict[str, Any]] = field(default_factory=list)
    
    # Outcome
    outcome_notes: str = ""
    salary_offered: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "internship_id": self.internship_id,
            "company": self.company,
            "role": self.role,
            "status": self.status.value,
            "resume_version_id": self.resume_version_id,
            "cover_letter_id": self.cover_letter_id,
            "date_saved": self.date_saved.isoformat(),
            "date_applied": self.date_applied.isoformat() if self.date_applied else None,
            "follow_up_date": self.follow_up_date.isoformat() if self.follow_up_date else None,
            "notes": self.notes,
            "interviews": self.interviews,
        }


@dataclass
class GeneratedResume:
    """A generated/customized resume."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Reference
    application_id: Optional[str] = None
    internship_id: Optional[str] = None
    company: str = ""
    role: str = ""
    
    # Content
    content: Dict[str, Any] = field(default_factory=dict)  # Structured resume content
    full_text: str = ""  # Plain text version
    
    # Files
    pdf_path: Optional[str] = None
    docx_path: Optional[str] = None
    google_doc_url: Optional[str] = None
    
    # Optimization
    ats_score: float = 0.0
    keywords_included: List[str] = field(default_factory=list)
    keywords_missing: List[str] = field(default_factory=list)
    
    # Projects selected
    projects_used: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "application_id": self.application_id,
            "company": self.company,
            "role": self.role,
            "ats_score": self.ats_score,
            "keywords_included": self.keywords_included,
            "projects_used": self.projects_used,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class CoverLetter:
    """A generated cover letter."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Reference
    application_id: Optional[str] = None
    company: str = ""
    role: str = ""
    
    # Content
    content: str = ""
    word_count: int = 0
    
    # Company research used
    company_info: Dict[str, str] = field(default_factory=dict)
    
    # Stories/experiences used
    stories_used: List[str] = field(default_factory=list)
    
    # Files
    pdf_path: Optional[str] = None
    docx_path: Optional[str] = None
    google_doc_url: Optional[str] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "company": self.company,
            "role": self.role,
            "word_count": self.word_count,
            "company_info": self.company_info,
            "stories_used": self.stories_used,
            "created_at": self.created_at.isoformat(),
        }


@dataclass 
class ApplicationStats:
    """Statistics about applications."""
    total_applications: int = 0
    total_saved: int = 0
    total_applied: int = 0
    total_interviews: int = 0
    total_offers: int = 0
    total_rejected: int = 0
    
    response_rate: float = 0.0  # % that got any response
    interview_rate: float = 0.0  # % that got interview
    offer_rate: float = 0.0  # % that got offer
    
    avg_days_to_response: float = 0.0
    
    most_successful_resume: Optional[str] = None
    top_companies_applied: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_applications": self.total_applications,
            "total_applied": self.total_applied,
            "total_interviews": self.total_interviews,
            "total_offers": self.total_offers,
            "response_rate": f"{self.response_rate:.1%}",
            "interview_rate": f"{self.interview_rate:.1%}",
            "offer_rate": f"{self.offer_rate:.1%}",
        }
