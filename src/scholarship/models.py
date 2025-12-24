"""
Data Models for JARVIS Scholarship Automation Module.

Defines all data structures for:
- User eligibility profile
- Scholarships and questions
- Past essays with outcomes
- Applications and tracking
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class EssayOutcome(Enum):
    """Outcome of a scholarship essay/application."""
    WON = "won"
    LOST = "lost"
    PENDING = "pending"
    SUBMITTED = "submitted"
    DRAFT = "draft"


class ApplicationStatus(Enum):
    """Status of a scholarship application."""
    DISCOVERED = "discovered"
    SAVED = "saved"
    IN_PROGRESS = "in_progress"
    ESSAYS_COMPLETE = "essays_complete"
    SUBMITTED = "submitted"
    WON = "won"
    LOST = "lost"
    EXPIRED = "expired"


class CitizenshipStatus(Enum):
    """Citizenship status for eligibility."""
    US_CITIZEN = "US Citizen"
    PERMANENT_RESIDENT = "Permanent Resident"
    DACA = "DACA"
    INTERNATIONAL = "International"
    UNDOCUMENTED = "Undocumented"


class EducationLevel(Enum):
    """Education level."""
    HIGH_SCHOOL = "High School"
    UNDERGRADUATE = "Undergraduate"
    GRADUATE = "Graduate"
    PHD = "PhD"
    POSTDOC = "Postdoc"


class FieldOfStudy(Enum):
    """Broad field of study."""
    STEM = "STEM"
    HUMANITIES = "Humanities"
    SOCIAL_SCIENCES = "Social Sciences"
    BUSINESS = "Business"
    ARTS = "Arts"
    HEALTH = "Health Sciences"
    LAW = "Law"
    EDUCATION = "Education"
    OTHER = "Other"


@dataclass
class EligibilityProfile:
    """
    User's eligibility profile for scholarship matching.
    
    Contains all criteria used to match against scholarship requirements.
    """
    # Basic Info
    name: str = "Parshv"
    age: int = 18
    gender: str = "Male"
    ethnicity: str = "Asian Indian"
    citizenship: CitizenshipStatus = CitizenshipStatus.PERMANENT_RESIDENT
    
    # Academic Info
    major: str = "Data Science"
    field_of_study: FieldOfStudy = FieldOfStudy.STEM
    education_level: EducationLevel = EducationLevel.UNDERGRADUATE
    year: str = "Freshman"
    university: str = "UC Berkeley"
    gpa: float = 4.0
    
    # Location
    state: str = "California"
    country: str = "USA"
    
    # Background
    financial_need: bool = False
    first_generation: bool = False
    
    # Interests and Activities
    interests: List[str] = field(default_factory=lambda: [
        "AI", "Machine Learning", "Data Science", "Technology"
    ])
    activities: List[str] = field(default_factory=lambda: [
        "Research", "Clubs", "Volunteer", "Projects"
    ])
    
    # Additional criteria
    military_affiliation: bool = False
    disability: bool = False
    lgbtq: bool = False
    
    # Achievements (for essay context)
    achievements: List[str] = field(default_factory=list)
    work_experience: List[str] = field(default_factory=list)
    leadership_roles: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "ethnicity": self.ethnicity,
            "citizenship": self.citizenship.value if isinstance(self.citizenship, Enum) else self.citizenship,
            "major": self.major,
            "field": self.field_of_study.value if isinstance(self.field_of_study, Enum) else self.field_of_study,
            "education_level": self.education_level.value if isinstance(self.education_level, Enum) else self.education_level,
            "year": self.year,
            "university": self.university,
            "gpa": self.gpa,
            "state": self.state,
            "country": self.country,
            "financial_need": self.financial_need,
            "first_generation": self.first_generation,
            "interests": self.interests,
            "activities": self.activities,
            "military_affiliation": self.military_affiliation,
            "disability": self.disability,
            "lgbtq": self.lgbtq,
            "achievements": self.achievements,
            "work_experience": self.work_experience,
            "leadership_roles": self.leadership_roles,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EligibilityProfile":
        """Create from dictionary."""
        # Handle enum conversions
        if "citizenship" in data and isinstance(data["citizenship"], str):
            data["citizenship"] = CitizenshipStatus(data["citizenship"])
        if "field" in data and isinstance(data["field"], str):
            data["field"] = FieldOfStudy(data["field"])
        if "education_level" in data and isinstance(data["education_level"], str):
            data["education_level"] = EducationLevel(data["education_level"])
        return cls(**data)


@dataclass
class ScholarshipQuestion:
    """A single question/essay prompt for a scholarship."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    question_text: str = ""
    word_limit: int = 500
    is_required: bool = True
    question_number: int = 1
    themes: List[str] = field(default_factory=list)
    
    # Generated essay (if any)
    generated_essay: Optional[str] = None
    actual_word_count: Optional[int] = None


@dataclass
class Scholarship:
    """
    Scholarship data model.
    
    Contains all information about a scholarship opportunity.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Basic Info
    name: str = ""
    provider: str = ""
    description: str = ""
    
    # Award
    amount: float = 0.0
    amount_text: str = ""  # e.g., "Up to $10,000"
    is_renewable: bool = False
    
    # Dates
    deadline: Optional[date] = None
    open_date: Optional[date] = None
    
    # Eligibility Requirements
    eligibility_requirements: Dict[str, Any] = field(default_factory=dict)
    required_criteria: List[str] = field(default_factory=list)
    preferred_criteria: List[str] = field(default_factory=list)
    
    # Application Details
    questions: List[ScholarshipQuestion] = field(default_factory=list)
    required_materials: List[str] = field(default_factory=list)  # transcript, recommendation, etc.
    
    # URLs
    url: str = ""
    application_url: str = ""
    
    # Source
    source: str = ""  # scholarships.com, bold.org, etc.
    
    # Matching
    match_percentage: float = 0.0
    match_details: Dict[str, bool] = field(default_factory=dict)
    
    # Metadata
    discovered_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "description": self.description,
            "amount": self.amount,
            "amount_text": self.amount_text,
            "is_renewable": self.is_renewable,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "open_date": self.open_date.isoformat() if self.open_date else None,
            "eligibility_requirements": self.eligibility_requirements,
            "required_criteria": self.required_criteria,
            "preferred_criteria": self.preferred_criteria,
            "questions": [
                {
                    "id": q.id,
                    "question_text": q.question_text,
                    "word_limit": q.word_limit,
                    "is_required": q.is_required,
                    "question_number": q.question_number,
                    "themes": q.themes,
                }
                for q in self.questions
            ],
            "required_materials": self.required_materials,
            "url": self.url,
            "application_url": self.application_url,
            "source": self.source,
            "match_percentage": self.match_percentage,
            "match_details": self.match_details,
            "discovered_at": self.discovered_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scholarship":
        """Create from dictionary."""
        # Parse dates
        if data.get("deadline") and isinstance(data["deadline"], str):
            data["deadline"] = date.fromisoformat(data["deadline"])
        if data.get("open_date") and isinstance(data["open_date"], str):
            data["open_date"] = date.fromisoformat(data["open_date"])
        if data.get("discovered_at") and isinstance(data["discovered_at"], str):
            data["discovered_at"] = datetime.fromisoformat(data["discovered_at"])
        if data.get("last_updated") and isinstance(data["last_updated"], str):
            data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        
        # Parse questions
        if "questions" in data:
            data["questions"] = [
                ScholarshipQuestion(**q) if isinstance(q, dict) else q
                for q in data["questions"]
            ]
        
        return cls(**data)
    
    def get_total_word_count(self) -> int:
        """Get total word count across all questions."""
        return sum(q.word_limit for q in self.questions)
    
    def days_until_deadline(self) -> Optional[int]:
        """Get days until deadline."""
        if not self.deadline:
            return None
        return (self.deadline - date.today()).days


@dataclass
class PastEssay:
    """
    A past scholarship essay for RAG retrieval.
    
    Stores essay content with metadata for similarity search.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Essay Content
    scholarship_name: str = ""
    question: str = ""
    essay_text: str = ""
    word_count: int = 0
    
    # Outcome
    outcome: EssayOutcome = EssayOutcome.PENDING
    
    # Analysis
    themes: List[str] = field(default_factory=list)
    key_points: List[str] = field(default_factory=list)
    tone: str = ""  # inspiring, reflective, analytical, etc.
    
    # Metadata
    date_written: datetime = field(default_factory=datetime.now)
    date_submitted: Optional[datetime] = None
    
    # Vector embedding (stored separately in Supabase)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "scholarship_name": self.scholarship_name,
            "question": self.question,
            "essay_text": self.essay_text,
            "word_count": self.word_count,
            "outcome": self.outcome.value,
            "themes": self.themes,
            "key_points": self.key_points,
            "tone": self.tone,
            "date_written": self.date_written.isoformat(),
            "date_submitted": self.date_submitted.isoformat() if self.date_submitted else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PastEssay":
        """Create from dictionary."""
        if data.get("outcome") and isinstance(data["outcome"], str):
            data["outcome"] = EssayOutcome(data["outcome"])
        if data.get("date_written") and isinstance(data["date_written"], str):
            data["date_written"] = datetime.fromisoformat(data["date_written"])
        if data.get("date_submitted") and isinstance(data["date_submitted"], str):
            data["date_submitted"] = datetime.fromisoformat(data["date_submitted"])
        # Remove embedding from dict creation (handled separately)
        data.pop("embedding", None)
        return cls(**data)


@dataclass
class PersonalStatement:
    """Personal statement sections for RAG."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    version: int = 1
    section_name: str = ""  # intro, body_1, conclusion, etc.
    content: str = ""
    themes: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "version": self.version,
            "section_name": self.section_name,
            "content": self.content,
            "themes": self.themes,
        }


@dataclass
class PersonalProfile:
    """Personal profile sections for RAG."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    section: str = ""  # achievements, stories, goals, etc.
    content: str = ""
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "section": self.section,
            "content": self.content,
        }


@dataclass
class Application:
    """
    Scholarship application tracking.
    
    Tracks the full lifecycle of a scholarship application.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Scholarship Reference
    scholarship_id: str = ""
    scholarship_name: str = ""
    
    # Status
    status: ApplicationStatus = ApplicationStatus.DISCOVERED
    
    # Dates
    deadline: Optional[date] = None
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    result_at: Optional[datetime] = None
    
    # Essays
    essay_ids: List[str] = field(default_factory=list)
    essays_complete: bool = False
    
    # Google Doc
    google_doc_url: Optional[str] = None
    google_doc_id: Optional[str] = None
    
    # Notes
    notes: str = ""
    
    # Award (if won)
    award_amount: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "scholarship_id": self.scholarship_id,
            "scholarship_name": self.scholarship_name,
            "status": self.status.value,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "result_at": self.result_at.isoformat() if self.result_at else None,
            "essay_ids": self.essay_ids,
            "essays_complete": self.essays_complete,
            "google_doc_url": self.google_doc_url,
            "google_doc_id": self.google_doc_id,
            "notes": self.notes,
            "award_amount": self.award_amount,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Application":
        """Create from dictionary."""
        if data.get("status") and isinstance(data["status"], str):
            data["status"] = ApplicationStatus(data["status"])
        if data.get("deadline") and isinstance(data["deadline"], str):
            data["deadline"] = date.fromisoformat(data["deadline"])
        if data.get("started_at") and isinstance(data["started_at"], str):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("submitted_at") and isinstance(data["submitted_at"], str):
            data["submitted_at"] = datetime.fromisoformat(data["submitted_at"])
        if data.get("result_at") and isinstance(data["result_at"], str):
            data["result_at"] = datetime.fromisoformat(data["result_at"])
        return cls(**data)


@dataclass
class PromptTemplate:
    """Stored prompt template for reuse."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    category: str = ""  # scholarship, internship, club, etc.
    prompt_text: str = ""
    variables: List[str] = field(default_factory=list)
    effectiveness_score: float = 0.0
    usage_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "prompt_text": self.prompt_text,
            "variables": self.variables,
            "effectiveness_score": self.effectiveness_score,
            "usage_count": self.usage_count,
        }


@dataclass
class GeneratedEssay:
    """A generated essay with metadata."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Context
    scholarship_id: str = ""
    scholarship_name: str = ""
    question_id: str = ""
    question_text: str = ""
    
    # Essay
    essay_text: str = ""
    word_count: int = 0
    target_word_count: int = 0
    
    # Generation Info
    generated_at: datetime = field(default_factory=datetime.now)
    llm_used: str = ""
    prompt_template: str = ""
    
    # RAG Context Used
    similar_essays_used: List[str] = field(default_factory=list)
    profile_sections_used: List[str] = field(default_factory=list)
    
    # Quality
    revision_count: int = 0
    quality_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "scholarship_id": self.scholarship_id,
            "scholarship_name": self.scholarship_name,
            "question_id": self.question_id,
            "question_text": self.question_text,
            "essay_text": self.essay_text,
            "word_count": self.word_count,
            "target_word_count": self.target_word_count,
            "generated_at": self.generated_at.isoformat(),
            "llm_used": self.llm_used,
            "prompt_template": self.prompt_template,
            "similar_essays_used": self.similar_essays_used,
            "profile_sections_used": self.profile_sections_used,
            "revision_count": self.revision_count,
            "quality_score": self.quality_score,
        }
