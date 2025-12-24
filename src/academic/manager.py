"""
Academic Manager for JARVIS.

Orchestrates all academic features and handles voice commands:
- Canvas LMS integration
- Pomodoro timer
- Daily briefing
- Assignment tracker
- Quick notes
- GitHub integration
- arXiv search
- Concept explainer
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from loguru import logger

from .canvas import CanvasClient, Assignment
from .pomodoro import PomodoroTimer, TimerState
from .notes import NotesManager, Note
from .assignments import AssignmentTracker, Priority, AssignmentType
from .github_integration import GitHubClient
from .arxiv_search import ArxivClient
from .briefing import DailyBriefing


class AcademicManager:
    """
    Central manager for all academic features.
    
    Handles voice command routing and feature orchestration.
    
    Usage:
        manager = AcademicManager(config, llm_router)
        response = await manager.handle_command("What's due this week?")
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        llm_router=None,
        data_dir: str = "data",
        on_timer_end: Optional[Callable[[str], None]] = None,
        on_pomodoro_music: Optional[Callable[[str], str]] = None,
        weather_service=None,
        calendar_service=None,
        email_service=None,
        habit_tracker=None,
        application_tracker=None,
        finance_manager=None,
    ):
        """
        Initialize academic manager.
        
        Args:
            config: Academic configuration from settings.yaml
            llm_router: LLM router for concept explanations
            data_dir: Directory for data storage
            on_timer_end: Callback when pomodoro timer ends
            on_pomodoro_music: Callback to play music when pomodoro starts
            weather_service: Weather service for briefings
            calendar_service: Calendar service for briefings
            email_service: Email service for briefings
            habit_tracker: Habit tracker for briefing streaks
            application_tracker: Job application tracker for briefing
            finance_manager: Finance manager for briefing tips
        """
        self.config = config or {}
        self.llm_router = llm_router
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # External services for briefing
        self.weather_service = weather_service
        self.calendar_service = calendar_service
        self.email_service = email_service
        self.habit_tracker = habit_tracker
        self.application_tracker = application_tracker
        self.finance_manager = finance_manager
        
        # Music callback for Pomodoro integration
        self._on_pomodoro_music = on_pomodoro_music
        
        # Deadline monitor state
        self._deadline_monitor_running = False
        
        # Initialize components
        self._init_canvas()
        self._init_pomodoro(on_timer_end)
        self._init_notes()
        self._init_assignments()
        self._init_github()
        self._init_arxiv()
        self._init_briefing()
        self._init_google_drive()
        
        logger.info("Academic Manager initialized")
    
    def _init_canvas(self):
        """Initialize Canvas client."""
        canvas_config = self.config.get("canvas", {})
        if canvas_config.get("enabled", True):
            self.canvas = CanvasClient(
                base_url=canvas_config.get("base_url"),
            )
        else:
            self.canvas = None
    
    def _init_pomodoro(self, on_timer_end: Optional[Callable[[str], None]]):
        """Initialize Pomodoro timer."""
        pomo_config = self.config.get("pomodoro", {})
        self.pomodoro = PomodoroTimer(
            db_path=str(self.data_dir / "pomodoro.db"),
            work_duration=pomo_config.get("work_duration", 25),
            short_break=pomo_config.get("short_break", 5),
            long_break=pomo_config.get("long_break", 15),
            sessions_before_long_break=pomo_config.get("sessions_before_long_break", 4),
            on_timer_end=on_timer_end,
        )
    
    def _init_notes(self):
        """Initialize notes manager."""
        self.notes = NotesManager(
            db_path=str(self.data_dir / "notes.db"),
        )
    
    def _init_assignments(self):
        """Initialize assignment tracker."""
        self.assignments = AssignmentTracker(
            db_path=str(self.data_dir / "assignments.db"),
        )
    
    def _init_github(self):
        """Initialize GitHub client."""
        github_config = self.config.get("github", {})
        if github_config.get("enabled", True):
            self.github = GitHubClient()
        else:
            self.github = None
    
    def _init_arxiv(self):
        """Initialize arXiv client."""
        arxiv_config = self.config.get("arxiv", {})
        if arxiv_config.get("enabled", True):
            self.arxiv = ArxivClient(
                db_path=str(self.data_dir / "reading_list.db"),
            )
        else:
            self.arxiv = None
    
    def _init_briefing(self):
        """Initialize daily briefing."""
        self.briefing = DailyBriefing(
            canvas_client=self.canvas,
            pomodoro_timer=self.pomodoro,
            assignment_tracker=self.assignments,
            notes_manager=self.notes,
            weather_service=self.weather_service,
            calendar_service=self.calendar_service,
            email_service=self.email_service,
            habit_tracker=self.habit_tracker,
            application_tracker=self.application_tracker,
            finance_manager=self.finance_manager,
        )
    
    def update_briefing_services(self, habit_tracker=None, application_tracker=None, finance_manager=None):
        """Update briefing with additional services after initialization."""
        if habit_tracker:
            self.briefing.habits = habit_tracker
        if application_tracker:
            self.briefing.applications = application_tracker
        if finance_manager:
            self.briefing.finance = finance_manager
    
    def _init_google_drive(self):
        """Initialize Google Drive client."""
        drive_config = self.config.get("google_drive", {})
        if drive_config.get("enabled", False):
            try:
                from .google_drive import GoogleDriveClient
                self.google_drive = GoogleDriveClient()
            except ImportError:
                self.google_drive = None
                logger.debug("Google Drive client not available")
        else:
            self.google_drive = None
    
    # =========================================================================
    # Command Handling
    # =========================================================================
    
    async def handle_command(self, text: str) -> Optional[str]:
        """
        Handle an academic-related command.
        
        Args:
            text: User command text
            
        Returns:
            Response string if command was handled, None otherwise
        """
        text_lower = text.lower().strip()
        
        # Daily briefing commands
        if self._is_briefing_command(text_lower):
            return await self._handle_briefing(text_lower)
        
        # Canvas commands
        if self._is_canvas_command(text_lower):
            return await self._handle_canvas(text_lower)
        
        # Pomodoro commands
        if self._is_pomodoro_command(text_lower):
            return await self._handle_pomodoro(text_lower, text)
        
        # Notes commands
        if self._is_notes_command(text_lower):
            return await self._handle_notes(text_lower, text)
        
        # Assignment commands
        if self._is_assignment_command(text_lower):
            return await self._handle_assignment(text_lower, text)
        
        # GitHub commands
        if self._is_github_command(text_lower):
            return await self._handle_github(text_lower)
        
        # arXiv commands
        if self._is_arxiv_command(text_lower):
            return await self._handle_arxiv(text_lower, text)
        
        # Google Drive commands
        if self._is_drive_command(text_lower):
            return await self._handle_drive(text_lower, text)
        
        # Concept explanation
        if self._is_explain_command(text_lower):
            return await self._handle_explain(text_lower, text)
        
        return None
    
    # =========================================================================
    # Command Detection
    # =========================================================================
    
    def _is_briefing_command(self, text: str) -> bool:
        patterns = [
            "good morning", "daily briefing", "morning briefing",
            "what's my day", "whats my day", "day summary",
            "evening summary", "what did i accomplish",
            "briefing", "my day",
        ]
        return any(p in text for p in patterns)
    
    def _is_canvas_command(self, text: str) -> bool:
        patterns = [
            "assignment", "due", "grade", "announcement",
            "canvas", "homework", "what's due", "whats due",
            "my courses", "course",
        ]
        return any(p in text for p in patterns)
    
    def _is_pomodoro_command(self, text: str) -> bool:
        patterns = [
            "pomodoro", "focus", "study session", "timer",
            "start studying", "take a break", "how much time",
            "time left", "stop studying", "pause", "resume",
            "study stats", "how many pomodoros",
        ]
        return any(p in text for p in patterns)
    
    def _is_notes_command(self, text: str) -> bool:
        patterns = [
            "quick note", "note:", "take note", "save note",
            "show notes", "my notes", "search notes", "recent notes",
        ]
        return any(p in text for p in patterns)
    
    def _is_assignment_command(self, text: str) -> bool:
        patterns = [
            "add assignment", "track assignment", "mark complete",
            "urgent assignment", "my assignments", "assignment tracker",
        ]
        return any(p in text for p in patterns)
    
    def _is_github_command(self, text: str) -> bool:
        patterns = [
            "github", "repo", "repository", "commit",
            "open issue", "pull request", "my repos",
        ]
        return any(p in text for p in patterns)
    
    def _is_arxiv_command(self, text: str) -> bool:
        patterns = [
            "arxiv", "paper", "research paper", "find paper",
            "reading list", "academic paper",
        ]
        return any(p in text for p in patterns)
    
    def _is_drive_command(self, text: str) -> bool:
        patterns = [
            "google drive", "drive", "my documents", "recent documents",
            "find document", "open document", "my doc", "google doc",
            "starred files", "starred documents",
        ]
        return any(p in text for p in patterns)
    
    def _is_explain_command(self, text: str) -> bool:
        patterns = [
            "explain", "what is", "what's", "how does",
            "how do", "tell me about", "define",
        ]
        # Check for ML/DS concepts
        ml_terms = [
            "gradient", "neural", "machine learning", "deep learning",
            "regression", "classification", "clustering", "overfitting",
            "backpropagation", "loss function", "activation", "optimizer",
            "regularization", "cross-validation", "bias", "variance",
            "random forest", "decision tree", "svm", "knn", "naive bayes",
            "cnn", "rnn", "lstm", "transformer", "attention", "embedding",
            "batch normalization", "dropout", "learning rate", "epoch",
            "precision", "recall", "f1", "accuracy", "auc", "roc",
        ]
        
        has_pattern = any(p in text for p in patterns)
        has_ml_term = any(t in text for t in ml_terms)
        
        return has_pattern or has_ml_term
    
    # =========================================================================
    # Command Handlers
    # =========================================================================
    
    async def _handle_briefing(self, text: str) -> str:
        """Handle briefing commands."""
        if "evening" in text or "accomplish" in text or "summary" in text:
            return await self.briefing.get_evening_summary()
        else:
            return await self.briefing.get_morning_briefing()
    
    async def _handle_canvas(self, text: str) -> str:
        """Handle Canvas commands."""
        if not self.canvas:
            return "Canvas integration is not enabled."
        
        if not self.canvas.is_configured:
            return "Canvas is not configured. Please set CANVAS_API_TOKEN in your .env file."
        
        try:
            # Grades
            if "grade" in text:
                # Specific course grade
                course_match = re.search(r"grade[s]?\s+(?:for\s+)?(.+)", text)
                if course_match:
                    course_name = course_match.group(1).strip()
                    grade = await self.canvas.get_course_grade(course_name)
                    if grade:
                        return f"Your grade in {grade.course_name}: {grade.current_grade or f'{grade.current_score:.1f}%' if grade.current_score else 'N/A'}"
                    return f"Couldn't find grades for '{course_name}'."
                
                # All grades
                grades = await self.canvas.get_grades()
                return "Your current grades:\n" + self.canvas.format_grades_summary(grades)
            
            # Announcements
            if "announcement" in text:
                announcements = await self.canvas.get_announcements(days=7)
                if not announcements:
                    return "No recent announcements."
                
                lines = ["Recent announcements:"]
                for a in announcements[:5]:
                    lines.append(f"• [{a.course_name}] {a.title}")
                return "\n".join(lines)
            
            # Due today
            if "due today" in text:
                assignments = await self.canvas.get_assignments_due_today()
                if not assignments:
                    return "No assignments due today!"
                return "Due today:\n" + self.canvas.format_assignments_summary(assignments)
            
            # Due tomorrow
            if "due tomorrow" in text:
                assignments = await self.canvas.get_assignments_due_tomorrow()
                if not assignments:
                    return "No assignments due tomorrow!"
                return "Due tomorrow:\n" + self.canvas.format_assignments_summary(assignments)
            
            # Due this week
            if "week" in text or "upcoming" in text:
                assignments = await self.canvas.get_upcoming_assignments(days=7)
                if not assignments:
                    return "No assignments due this week!"
                return "Due this week:\n" + self.canvas.format_assignments_summary(assignments)
            
            # Specific course assignments
            course_match = re.search(r"(?:assignment|due|homework)[s]?\s+(?:for\s+)?(.+)", text)
            if course_match:
                course_name = course_match.group(1).strip()
                course = await self.canvas.find_course(course_name)
                if course:
                    assignments = await self.canvas.get_assignments(course_id=course.id)
                    if not assignments:
                        return f"No upcoming assignments for {course.name}."
                    return f"Assignments for {course.name}:\n" + self.canvas.format_assignments_summary(assignments[:10])
                return f"Couldn't find course '{course_name}'."
            
            # Default: upcoming assignments
            assignments = await self.canvas.get_upcoming_assignments(days=7)
            if not assignments:
                return "No upcoming assignments!"
            return "Upcoming assignments:\n" + self.canvas.format_assignments_summary(assignments)
            
        except Exception as e:
            logger.error(f"Canvas error: {e}")
            return f"Error accessing Canvas: {str(e)}"
    
    async def _handle_pomodoro(self, text: str, original: str) -> str:
        """Handle Pomodoro commands."""
        # Start pomodoro
        if any(p in text for p in ["start pomodoro", "start focus", "start studying", "start study session"]):
            # Extract duration if specified
            duration_match = re.search(r"(\d+)\s*(?:min|minute)", text)
            duration = int(duration_match.group(1)) if duration_match else None
            
            # Extract subject if specified
            subject_match = re.search(r"(?:for|on)\s+(.+?)(?:\s+for\s+\d+|\s*$)", text)
            subject = subject_match.group(1).strip() if subject_match else None
            
            # Extract music preference if specified (e.g., "start pomodoro with lofi")
            music_playlist = None
            music_match = re.search(r"with\s+(lofi|lo-fi|hindi|focus|classical|chill|coding|ambient|gym|my mix|liked songs)", text)
            if music_match:
                music_playlist = music_match.group(1).strip()
                # Remove music part from subject if it got captured
                if subject and music_match.group(1) in subject:
                    subject = subject.replace(f"with {music_match.group(1)}", "").strip()
            
            result = await self.pomodoro.start(duration=duration, subject=subject)
            
            # Auto-play music if requested
            if music_playlist and self._on_pomodoro_music:
                music_result = self._on_pomodoro_music(music_playlist)
                result += f"\n{music_result}"
            
            return result
        
        # Start break
        if "take a break" in text or "start break" in text:
            long_break = "long" in text
            return await self.pomodoro.start_break(long_break=long_break)
        
        # Pause
        if "pause" in text:
            return self.pomodoro.pause()
        
        # Resume
        if "resume" in text:
            return await self.pomodoro.resume()
        
        # Stop
        if any(p in text for p in ["stop", "end", "cancel"]):
            return self.pomodoro.stop()
        
        # Time remaining
        if any(p in text for p in ["time left", "how much time", "remaining"]):
            return self.pomodoro.get_status()
        
        # Stats
        if any(p in text for p in ["stats", "statistics", "how many pomodoro"]):
            return self.pomodoro.format_stats()
        
        # Today summary
        if "today" in text:
            return self.pomodoro.get_today_summary()
        
        # Default status
        return self.pomodoro.get_status()
    
    async def _handle_notes(self, text: str, original: str) -> str:
        """Handle notes commands."""
        # Add note
        note_patterns = [
            r"(?:quick\s+)?note[:\s]+(.+)",
            r"take\s+note[:\s]+(.+)",
            r"save\s+note[:\s]+(.+)",
        ]
        
        for pattern in note_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                
                # Extract category if specified
                category = None
                cat_match = re.search(r"(?:for|category)\s+([^:]+?)(?:\s*:|$)", content)
                if cat_match:
                    category = cat_match.group(1).strip()
                    content = content.replace(cat_match.group(0), "").strip()
                
                note = self.notes.add(content, category=category)
                return f"Note saved: \"{content}\""
        
        # Search notes
        if "search" in text:
            search_match = re.search(r"search\s+(?:notes?\s+)?(?:for\s+)?(.+)", text)
            if search_match:
                query = search_match.group(1).strip()
                results = self.notes.search(query)
                if results:
                    return f"Found {len(results)} notes:\n" + self.notes.format_notes(results[:5])
                return f"No notes found for '{query}'."
        
        # Show recent notes
        if any(p in text for p in ["show notes", "my notes", "recent notes"]):
            notes = self.notes.get_recent(limit=5)
            if notes:
                return "Recent notes:\n" + self.notes.format_notes(notes)
            return "No notes yet. Say 'Quick note: [your note]' to add one."
        
        # Notes by category
        cat_match = re.search(r"notes?\s+(?:for|in)\s+(.+)", text)
        if cat_match:
            category = cat_match.group(1).strip()
            notes = self.notes.get_by_category(category)
            if notes:
                return f"Notes for {category}:\n" + self.notes.format_notes(notes)
            return f"No notes found for category '{category}'."
        
        return "Try: 'Quick note: [content]' or 'Show my notes'"
    
    async def _handle_assignment(self, text: str, original: str) -> str:
        """Handle assignment tracker commands."""
        # Add assignment
        if "add assignment" in text or "track assignment" in text:
            # Parse: "add assignment [name] due [date] for [course]"
            match = re.search(r"(?:add|track)\s+assignment[:\s]+(.+?)(?:\s+due\s+(.+?))?(?:\s+for\s+(.+))?$", text)
            if match:
                name = match.group(1).strip()
                due_str = match.group(2).strip() if match.group(2) else None
                course = match.group(3).strip() if match.group(3) else None
                
                # Parse due date
                due_date = None
                if due_str:
                    due_date = self._parse_due_date(due_str)
                
                assignment = self.assignments.add(
                    name=name,
                    course=course,
                    due_date=due_date,
                )
                return f"Added assignment: {assignment.name}"
            
            return "Try: 'Add assignment [name] due [date] for [course]'"
        
        # Mark complete
        if "mark" in text and "complete" in text:
            # Find assignment by name
            match = re.search(r"mark\s+(.+?)\s+(?:as\s+)?complete", text)
            if match:
                name = match.group(1).strip()
                assignments = self.assignments.get_all()
                for a in assignments:
                    if name.lower() in a.name.lower():
                        self.assignments.mark_complete(a.id)
                        return f"Marked '{a.name}' as complete!"
                return f"Couldn't find assignment '{name}'."
        
        # Urgent assignments
        if "urgent" in text or "most important" in text:
            urgent = self.assignments.get_urgent(limit=5)
            if urgent:
                return "Most urgent assignments:\n" + self.assignments.format_assignments(urgent)
            return "No urgent assignments!"
        
        # Show all assignments
        if "my assignment" in text or "show assignment" in text:
            assignments = self.assignments.get_upcoming(days=14)
            if assignments:
                return "Your assignments:\n" + self.assignments.format_assignments(assignments)
            return "No upcoming assignments tracked."
        
        return "Try: 'Add assignment [name]' or 'Show my assignments'"
    
    async def _handle_github(self, text: str) -> str:
        """Handle GitHub commands."""
        if not self.github:
            return "GitHub integration is not enabled."
        
        if not self.github.is_configured:
            return "GitHub is not configured. Please set GITHUB_TOKEN in your .env file."
        
        try:
            # List repos
            if any(p in text for p in ["my repo", "show repo", "list repo"]):
                repos = await self.github.get_repositories(limit=10)
                return "Your repositories:\n" + self.github.format_repositories(repos)
            
            # Open issues for a repo
            issue_match = re.search(r"(?:open\s+)?issues?\s+(?:on|for|in)\s+(.+)", text)
            if issue_match:
                repo_name = issue_match.group(1).strip()
                repo = await self.github.find_repository(repo_name)
                if repo:
                    issues = await self.github.get_open_issues(repo.full_name)
                    if issues:
                        return f"Open issues for {repo.name}:\n" + self.github.format_issues(issues)
                    return f"No open issues for {repo.name}."
                return f"Couldn't find repository '{repo_name}'."
            
            # Today's commits
            if "commit" in text and "today" in text:
                commits = await self.github.get_today_commits()
                if commits:
                    return f"Today's commits:\n" + self.github.format_commits(commits)
                return "No commits today."
            
            # Recent commits for a repo
            commit_match = re.search(r"commit[s]?\s+(?:on|for|in)\s+(.+)", text)
            if commit_match:
                repo_name = commit_match.group(1).strip()
                repo = await self.github.find_repository(repo_name)
                if repo:
                    commits = await self.github.get_recent_commits(repo.full_name, limit=5)
                    return f"Recent commits for {repo.name}:\n" + self.github.format_commits(commits)
                return f"Couldn't find repository '{repo_name}'."
            
            # Default: list repos
            repos = await self.github.get_repositories(limit=5)
            return "Your recent repositories:\n" + self.github.format_repositories(repos)
            
        except Exception as e:
            logger.error(f"GitHub error: {e}")
            return f"Error accessing GitHub: {str(e)}"
    
    async def _handle_arxiv(self, text: str, original: str) -> str:
        """Handle arXiv commands."""
        if not self.arxiv:
            return "arXiv integration is not enabled."
        
        try:
            # Search papers
            search_patterns = [
                r"(?:find|search)\s+(?:papers?|arxiv)\s+(?:about|on|for)\s+(.+)",
                r"papers?\s+(?:about|on)\s+(.+)",
                r"arxiv\s+(.+)",
            ]
            
            for pattern in search_patterns:
                match = re.search(pattern, text)
                if match:
                    query = match.group(1).strip()
                    papers = await self.arxiv.search_ml(query, max_results=5)
                    if papers:
                        return f"Papers about '{query}':\n\n" + self.arxiv.format_papers(papers)
                    return f"No papers found for '{query}'."
            
            # Reading list
            if "reading list" in text:
                if "add" in text:
                    # Would need paper context
                    return "To add a paper, first search for it, then say 'Add this to reading list'."
                
                items = self.arxiv.get_reading_list()
                return self.arxiv.format_reading_list(items)
            
            # Recent papers
            if "recent" in text or "new" in text or "latest" in text:
                papers = await self.arxiv.get_recent(max_results=5)
                return "Recent ML/AI papers:\n\n" + self.arxiv.format_papers(papers)
            
            return "Try: 'Find papers about transformers' or 'Show my reading list'"
            
        except Exception as e:
            logger.error(f"arXiv error: {e}")
            return f"Error searching arXiv: {str(e)}"
    
    async def _handle_drive(self, text: str, original: str) -> str:
        """Handle Google Drive commands."""
        if not self.google_drive:
            return "Google Drive integration is not enabled. Enable it in settings.yaml and configure Google credentials."
        
        if not self.google_drive.is_configured:
            return "Google Drive is not configured. Please set up Google credentials in config/google_credentials.json"
        
        try:
            # Search documents
            search_patterns = [
                r"(?:find|search|open)\s+(?:document|doc)\s+(?:about|called|named)?\s*(.+)",
                r"open\s+my\s+(.+?)\s+(?:notes?|doc)",
                r"find\s+(.+?)\s+(?:in\s+)?drive",
            ]
            
            for pattern in search_patterns:
                match = re.search(pattern, text)
                if match:
                    query = match.group(1).strip()
                    files = await self.google_drive.search(query, max_results=5)
                    if files:
                        # Open first result if "open" was in command
                        if "open" in text:
                            self.google_drive.open_file(files[0])
                            return f"Opening '{files[0].name}'..."
                        return f"Found documents:\n{self.google_drive.format_files(files)}"
                    return f"No documents found matching '{query}'."
            
            # Recent documents
            if "recent" in text:
                files = await self.google_drive.get_recent(max_results=10)
                return f"Recent documents:\n{self.google_drive.format_files(files)}"
            
            # Starred documents
            if "starred" in text:
                files = await self.google_drive.get_starred()
                if files:
                    return f"Starred documents:\n{self.google_drive.format_files(files)}"
                return "No starred documents."
            
            return "Try: 'Find document about [topic]' or 'Show recent documents'"
            
        except Exception as e:
            logger.error(f"Drive error: {e}")
            return f"Error accessing Google Drive: {str(e)}"
    
    async def _handle_explain(self, text: str, original: str) -> str:
        """Handle concept explanation requests."""
        if not self.llm_router:
            return "LLM is not available for explanations."
        
        # Extract the concept to explain
        explain_patterns = [
            r"explain\s+(.+?)(?:\s+like\s+i'm\s+\d+)?(?:\s+simply)?$",
            r"what\s+is\s+(.+?)\??$",
            r"what's\s+(.+?)\??$",
            r"how\s+does\s+(.+?)\s+work\??$",
            r"tell\s+me\s+about\s+(.+)$",
            r"define\s+(.+)$",
        ]
        
        concept = None
        for pattern in explain_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                concept = match.group(1).strip()
                break
        
        if not concept:
            concept = text  # Use full text as concept
        
        # Check for simplicity request
        simple = "like i'm" in text or "simply" in text or "simple" in text
        
        # Build prompt
        if simple:
            prompt = f"""Explain {concept} in very simple terms, as if explaining to someone new to the field.
Use analogies and avoid jargon. Keep it concise but clear.
Focus on the intuition rather than mathematical details."""
        else:
            prompt = f"""Explain {concept} clearly and concisely for a Data Science student.
Include:
1. A brief definition
2. Why it's important
3. A simple example if applicable
Keep the explanation focused and practical."""
        
        try:
            response = await self.llm_router.generate(prompt)
            return response
        except Exception as e:
            logger.error(f"Explanation error: {e}")
            return f"I couldn't generate an explanation right now. Error: {str(e)}"
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def _parse_due_date(self, date_str: str) -> Optional[datetime]:
        """Parse a natural language due date."""
        date_str = date_str.lower().strip()
        now = datetime.now()
        
        # Today/tomorrow
        if date_str == "today":
            return now.replace(hour=23, minute=59, second=0, microsecond=0)
        if date_str == "tomorrow":
            return (now + timedelta(days=1)).replace(hour=23, minute=59, second=0, microsecond=0)
        
        # Day of week
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for i, day in enumerate(days):
            if day in date_str:
                current_day = now.weekday()
                days_ahead = i - current_day
                if days_ahead <= 0:
                    days_ahead += 7
                return (now + timedelta(days=days_ahead)).replace(hour=23, minute=59, second=0, microsecond=0)
        
        # "next week"
        if "next week" in date_str:
            return (now + timedelta(days=7)).replace(hour=23, minute=59, second=0, microsecond=0)
        
        # "in X days"
        days_match = re.search(r"in\s+(\d+)\s+days?", date_str)
        if days_match:
            days = int(days_match.group(1))
            return (now + timedelta(days=days)).replace(hour=23, minute=59, second=0, microsecond=0)
        
        # Try parsing as date
        date_formats = ["%m/%d", "%m/%d/%Y", "%B %d", "%b %d"]
        for fmt in date_formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                if parsed.year == 1900:  # No year specified
                    parsed = parsed.replace(year=now.year)
                    if parsed < now:
                        parsed = parsed.replace(year=now.year + 1)
                return parsed.replace(hour=23, minute=59, second=0, microsecond=0)
            except ValueError:
                continue
        
        return None
    
    async def get_deadline_alerts(self) -> List[str]:
        """Get assignments needing deadline alerts."""
        alerts = []
        alert_hours = [48, 24, 2]  # Alert at 48h, 24h, 2h before due
        
        # Check Canvas assignments
        if self.canvas and self.canvas.is_configured:
            try:
                assignments = await self.canvas.get_upcoming_assignments(days=3)
                for a in assignments:
                    if a.due_at:
                        hours_until = (a.due_at - datetime.now()).total_seconds() / 3600
                        if hours_until <= 0:
                            continue  # Already past due
                        
                        # Check each alert threshold
                        for threshold in alert_hours:
                            if hours_until <= threshold and hours_until > threshold - 1:
                                if hours_until <= 2:
                                    alerts.append(f"🔴 URGENT: {a.name} ({a.course_name}) is due in {int(hours_until * 60)} minutes!")
                                elif hours_until <= 24:
                                    alerts.append(f"⚠️ {a.name} ({a.course_name}) is due in {int(hours_until)} hours!")
                                else:
                                    alerts.append(f"📋 Reminder: {a.name} ({a.course_name}) is due in {int(hours_until)} hours.")
                                break
            except Exception as e:
                logger.error(f"Error checking Canvas deadlines: {e}")
        
        # Check local assignments
        try:
            needing_reminder = self.assignments.get_needing_reminder(hours_before=48)
            for a in needing_reminder:
                if a.due_date:
                    hours_until = (a.due_date - datetime.now()).total_seconds() / 3600
                    if hours_until > 0:
                        if hours_until <= 2:
                            alerts.append(f"🔴 URGENT: {a.name} is due in {int(hours_until * 60)} minutes!")
                        elif hours_until <= 24:
                            alerts.append(f"⚠️ {a.name} is due in {int(hours_until)} hours!")
                        else:
                            alerts.append(f"📋 Reminder: {a.name} is due in {int(hours_until)} hours.")
                        self.assignments.mark_reminder_sent(a.id)
        except Exception as e:
            logger.error(f"Error checking local deadlines: {e}")
        
        return alerts
    
    async def start_deadline_monitor(
        self,
        check_interval_minutes: int = 60,
        on_alert: Optional[Callable[[str], None]] = None,
    ):
        """
        Start background deadline monitoring.
        
        Args:
            check_interval_minutes: How often to check (default: 60 min)
            on_alert: Callback for each alert (receives alert message)
        """
        self._deadline_monitor_running = True
        logger.info(f"Starting deadline monitor (checking every {check_interval_minutes} min)")
        
        while self._deadline_monitor_running:
            try:
                alerts = await self.get_deadline_alerts()
                for alert in alerts:
                    logger.info(f"Deadline alert: {alert}")
                    if on_alert:
                        on_alert(alert)
            except Exception as e:
                logger.error(f"Deadline monitor error: {e}")
            
            # Wait for next check
            await asyncio.sleep(check_interval_minutes * 60)
    
    def stop_deadline_monitor(self):
        """Stop the deadline monitor."""
        self._deadline_monitor_running = False
        logger.info("Deadline monitor stopped")
    
    async def close(self):
        """Close all clients."""
        if self.canvas:
            await self.canvas.close()
        if self.github:
            await self.github.close()
        if self.arxiv:
            await self.arxiv.close()
