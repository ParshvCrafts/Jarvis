"""
Academic Module for JARVIS.

Provides academic features for UC Berkeley Data Science students:
- Canvas LMS integration (assignments, grades, announcements)
- Pomodoro study timer
- Daily briefing
- Assignment tracker
- Quick notes
- Google Drive access
- GitHub integration
- arXiv paper search
- Concept explainer
- Deadline alerts
"""

from __future__ import annotations

# Canvas LMS
try:
    from .canvas import CanvasClient, Assignment, Grade, Announcement
    CANVAS_AVAILABLE = True
except ImportError:
    CANVAS_AVAILABLE = False
    CanvasClient = None

# Pomodoro Timer
try:
    from .pomodoro import PomodoroTimer, StudySession
    POMODORO_AVAILABLE = True
except ImportError:
    POMODORO_AVAILABLE = False
    PomodoroTimer = None

# Quick Notes
try:
    from .notes import NotesManager, Note
    NOTES_AVAILABLE = True
except ImportError:
    NOTES_AVAILABLE = False
    NotesManager = None

# Assignment Tracker
try:
    from .assignments import AssignmentTracker, TrackedAssignment
    ASSIGNMENTS_AVAILABLE = True
except ImportError:
    ASSIGNMENTS_AVAILABLE = False
    AssignmentTracker = None

# GitHub Integration
try:
    from .github_integration import GitHubClient
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    GitHubClient = None

# arXiv Search
try:
    from .arxiv_search import ArxivClient
    ARXIV_AVAILABLE = True
except ImportError:
    ARXIV_AVAILABLE = False
    ArxivClient = None

# Daily Briefing
try:
    from .briefing import DailyBriefing
    BRIEFING_AVAILABLE = True
except ImportError:
    BRIEFING_AVAILABLE = False
    DailyBriefing = None

# Google Drive
try:
    from .google_drive import GoogleDriveClient, DriveFile
    DRIVE_AVAILABLE = True
except ImportError:
    DRIVE_AVAILABLE = False
    GoogleDriveClient = None
    DriveFile = None

# Academic Manager (orchestrates all features)
try:
    from .manager import AcademicManager
    ACADEMIC_AVAILABLE = True
except ImportError:
    ACADEMIC_AVAILABLE = False
    AcademicManager = None

__all__ = [
    "CanvasClient",
    "Assignment",
    "Grade",
    "Announcement",
    "PomodoroTimer",
    "StudySession",
    "NotesManager",
    "Note",
    "AssignmentTracker",
    "TrackedAssignment",
    "GitHubClient",
    "ArxivClient",
    "DailyBriefing",
    "GoogleDriveClient",
    "DriveFile",
    "AcademicManager",
    "CANVAS_AVAILABLE",
    "POMODORO_AVAILABLE",
    "NOTES_AVAILABLE",
    "ASSIGNMENTS_AVAILABLE",
    "GITHUB_AVAILABLE",
    "ARXIV_AVAILABLE",
    "BRIEFING_AVAILABLE",
    "DRIVE_AVAILABLE",
    "ACADEMIC_AVAILABLE",
]
