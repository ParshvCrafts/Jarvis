"""
Productivity Module for JARVIS.

Provides advanced productivity features for UC Berkeley Data Science students:
- YouTube Music / Spotify control
- Learning Journal
- Habit Tracker
- Project Tracker
- Code Snippet Library
- Smart Study Planner
- Weekly Review
- Focus Mode
- Dataset Explorer
- Break Reminders
"""

from __future__ import annotations

# Music Control
try:
    from .music import MusicController, Playlist
    MUSIC_AVAILABLE = True
except ImportError:
    MUSIC_AVAILABLE = False
    MusicController = None

# Learning Journal
try:
    from .learning_journal import LearningJournal, JournalEntry
    JOURNAL_AVAILABLE = True
except ImportError:
    JOURNAL_AVAILABLE = False
    LearningJournal = None

# Habit Tracker
try:
    from .habits import HabitTracker, Habit, HabitLog
    HABITS_AVAILABLE = True
except ImportError:
    HABITS_AVAILABLE = False
    HabitTracker = None

# Project Tracker
try:
    from .projects import ProjectTracker, Project, Milestone
    PROJECTS_AVAILABLE = True
except ImportError:
    PROJECTS_AVAILABLE = False
    ProjectTracker = None

# Code Snippets
try:
    from .snippets import SnippetLibrary, CodeSnippet
    SNIPPETS_AVAILABLE = True
except ImportError:
    SNIPPETS_AVAILABLE = False
    SnippetLibrary = None

# Study Planner
try:
    from .study_planner import StudyPlanner, StudyBlock
    PLANNER_AVAILABLE = True
except ImportError:
    PLANNER_AVAILABLE = False
    StudyPlanner = None

# Weekly Review
try:
    from .weekly_review import WeeklyReview
    REVIEW_AVAILABLE = True
except ImportError:
    REVIEW_AVAILABLE = False
    WeeklyReview = None

# Focus Mode
try:
    from .focus_mode import FocusMode
    FOCUS_AVAILABLE = True
except ImportError:
    FOCUS_AVAILABLE = False
    FocusMode = None

# Dataset Explorer
try:
    from .dataset_explorer import DatasetExplorer
    DATASET_AVAILABLE = True
except ImportError:
    DATASET_AVAILABLE = False
    DatasetExplorer = None

# Break Reminders
try:
    from .breaks import BreakReminder
    BREAKS_AVAILABLE = True
except ImportError:
    BREAKS_AVAILABLE = False
    BreakReminder = None

# Productivity Manager
try:
    from .manager import ProductivityManager
    PRODUCTIVITY_AVAILABLE = True
except ImportError:
    PRODUCTIVITY_AVAILABLE = False
    ProductivityManager = None

__all__ = [
    "MusicController",
    "Playlist",
    "LearningJournal",
    "JournalEntry",
    "HabitTracker",
    "Habit",
    "HabitLog",
    "ProjectTracker",
    "Project",
    "Milestone",
    "SnippetLibrary",
    "CodeSnippet",
    "StudyPlanner",
    "StudyBlock",
    "WeeklyReview",
    "FocusMode",
    "DatasetExplorer",
    "BreakReminder",
    "ProductivityManager",
    "MUSIC_AVAILABLE",
    "JOURNAL_AVAILABLE",
    "HABITS_AVAILABLE",
    "PROJECTS_AVAILABLE",
    "SNIPPETS_AVAILABLE",
    "PLANNER_AVAILABLE",
    "REVIEW_AVAILABLE",
    "FOCUS_AVAILABLE",
    "DATASET_AVAILABLE",
    "BREAKS_AVAILABLE",
    "PRODUCTIVITY_AVAILABLE",
]
