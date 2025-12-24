"""
Career Module for JARVIS.

Phase 3: Career & Advanced Intelligence Features
- Interview Prep Mode
- Resume/Experience Tracker
- Job Application Tracker
- Expense Tracker
- Notion Integration
- Networking Tracker
- Voice Journal
- Learning Path Generator
"""

from typing import Optional

# Interview Prep
INTERVIEW_AVAILABLE = False
try:
    from .interview import InterviewPrep, InterviewQuestion, InterviewSession
    INTERVIEW_AVAILABLE = True
except ImportError:
    InterviewPrep = None
    InterviewQuestion = None
    InterviewSession = None

# Resume/Experience Tracker
RESUME_AVAILABLE = False
try:
    from .resume import ResumeTracker, Experience, Skill
    RESUME_AVAILABLE = True
except ImportError:
    ResumeTracker = None
    Experience = None
    Skill = None

# Job Application Tracker
APPLICATIONS_AVAILABLE = False
try:
    from .applications import ApplicationTracker, JobApplication
    APPLICATIONS_AVAILABLE = True
except ImportError:
    ApplicationTracker = None
    JobApplication = None

# Expense Tracker
EXPENSE_AVAILABLE = False
try:
    from .expense import ExpenseTracker, Expense, Budget
    EXPENSE_AVAILABLE = True
except ImportError:
    ExpenseTracker = None
    Expense = None
    Budget = None

# Notion Integration
NOTION_AVAILABLE = False
try:
    from .notion import NotionIntegration, NotionPage
    NOTION_AVAILABLE = True
except ImportError:
    NotionIntegration = None
    NotionPage = None

# Networking Tracker
NETWORKING_AVAILABLE = False
try:
    from .networking import NetworkingTracker, Contact, Interaction
    NETWORKING_AVAILABLE = True
except ImportError:
    NetworkingTracker = None
    Contact = None
    Interaction = None

# Voice Journal
JOURNAL_AVAILABLE = False
try:
    from .voice_journal import VoiceJournal, JournalEntry
    JOURNAL_AVAILABLE = True
except ImportError:
    VoiceJournal = None
    JournalEntry = None

# Learning Path Generator
LEARNING_PATH_AVAILABLE = False
try:
    from .learning_path import LearningPathGenerator, LearningPath, PathItem
    LEARNING_PATH_AVAILABLE = True
except ImportError:
    LearningPathGenerator = None
    LearningPath = None
    PathItem = None

# Career Manager (orchestrates all career features)
CAREER_MANAGER_AVAILABLE = False
try:
    from .manager import CareerManager
    CAREER_MANAGER_AVAILABLE = True
except ImportError as e:
    import logging
    logging.debug(f"CareerManager not available: {e}")
    CareerManager = None

__all__ = [
    # Availability flags
    "INTERVIEW_AVAILABLE",
    "RESUME_AVAILABLE",
    "APPLICATIONS_AVAILABLE",
    "EXPENSE_AVAILABLE",
    "NOTION_AVAILABLE",
    "NETWORKING_AVAILABLE",
    "JOURNAL_AVAILABLE",
    "LEARNING_PATH_AVAILABLE",
    "CAREER_MANAGER_AVAILABLE",
    # Classes
    "InterviewPrep",
    "InterviewQuestion",
    "InterviewSession",
    "ResumeTracker",
    "Experience",
    "Skill",
    "ApplicationTracker",
    "JobApplication",
    "ExpenseTracker",
    "Expense",
    "Budget",
    "NotionIntegration",
    "NotionPage",
    "NetworkingTracker",
    "Contact",
    "Interaction",
    "VoiceJournal",
    "JournalEntry",
    "LearningPathGenerator",
    "LearningPath",
    "PathItem",
    "CareerManager",
]
