"""
Productivity Manager for JARVIS.

Central manager for all productivity features:
- Music control
- Learning journal
- Habit tracking
- Project management
- Code snippets
- Study planning
- Weekly reviews
- Focus mode
- Dataset exploration
- Break reminders
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from .music import MusicController, MusicService, Playlist
from .learning_journal import LearningJournal, JournalEntry
from .habits import HabitTracker, Habit, HabitFrequency
from .projects import ProjectTracker, Project, ProjectStatus
from .snippets import SnippetLibrary, CodeSnippet
from .study_planner import StudyPlanner, StudyTask, Difficulty
from .weekly_review import WeeklyReview
from .focus_mode import FocusMode
from .dataset_explorer import DatasetExplorer
from .breaks import BreakReminder


class ProductivityManager:
    """
    Central manager for all productivity features.
    
    Handles voice command routing and feature orchestration.
    
    Usage:
        manager = ProductivityManager(config)
        response = await manager.handle_command("Play focus music")
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        data_dir: str = "data",
        pomodoro_timer=None,
        canvas_client=None,
        assignment_tracker=None,
        calendar_service=None,
        on_break_due: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize productivity manager.
        
        Args:
            config: Productivity configuration from settings.yaml
            data_dir: Directory for data storage
            pomodoro_timer: Pomodoro timer instance (from academic module)
            canvas_client: Canvas client (from academic module)
            assignment_tracker: Assignment tracker (from academic module)
            calendar_service: Calendar service
            on_break_due: Callback when break is due
        """
        self.config = config or {}
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # External integrations
        self.pomodoro = pomodoro_timer
        self.canvas = canvas_client
        self.assignment_tracker = assignment_tracker
        self.calendar = calendar_service
        
        # Initialize components
        self._init_music()
        self._init_journal()
        self._init_habits()
        self._init_projects()
        self._init_snippets()
        self._init_planner()
        self._init_review()
        self._init_focus()
        self._init_dataset()
        self._init_breaks(on_break_due)
        
        logger.info("Productivity Manager initialized")
    
    def _init_music(self):
        """Initialize music controller."""
        music_config = self.config.get("music", {})
        preferred = music_config.get("preferred_service", "youtube_music")
        service = MusicService.YOUTUBE_MUSIC if "youtube" in preferred.lower() else MusicService.SPOTIFY
        
        self.music = MusicController(preferred_service=service)
        
        # Add custom playlists from config
        custom_playlists = music_config.get("playlists", {})
        for name, urls in custom_playlists.items():
            if isinstance(urls, dict):
                self.music.add_playlist(
                    name=name,
                    youtube_url=urls.get("youtube"),
                    spotify_url=urls.get("spotify"),
                )
    
    def _init_journal(self):
        """Initialize learning journal."""
        self.journal = LearningJournal(
            db_path=str(self.data_dir / "learning_journal.db")
        )
    
    def _init_habits(self):
        """Initialize habit tracker."""
        self.habits = HabitTracker(
            db_path=str(self.data_dir / "habits.db")
        )
        
        # Add default habits if none exist
        if not self.habits.get_all_habits():
            habits_config = self.config.get("habits", {})
            if habits_config.get("add_defaults", True):
                self.habits.add_default_habits()
    
    def _init_projects(self):
        """Initialize project tracker."""
        self.projects = ProjectTracker(
            db_path=str(self.data_dir / "projects.db")
        )
    
    def _init_snippets(self):
        """Initialize snippet library."""
        self.snippets = SnippetLibrary(
            db_path=str(self.data_dir / "snippets.db")
        )
        
        # Load default snippets
        snippets_config = self.config.get("snippets", {})
        if snippets_config.get("load_defaults", True):
            self.snippets.load_defaults()
    
    def _init_planner(self):
        """Initialize study planner."""
        self.planner = StudyPlanner(
            canvas_client=self.canvas,
            assignment_tracker=self.assignment_tracker,
            calendar_service=self.calendar,
        )
    
    def _init_review(self):
        """Initialize weekly review."""
        self.review = WeeklyReview(
            pomodoro_timer=self.pomodoro,
            learning_journal=self.journal,
            habit_tracker=self.habits,
            project_tracker=self.projects,
            assignment_tracker=self.assignment_tracker,
            canvas_client=self.canvas,
        )
    
    def _init_focus(self):
        """Initialize focus mode."""
        focus_config = self.config.get("focus_mode", {})
        custom_blocklist = set(focus_config.get("blocked_sites", []))
        
        self.focus = FocusMode(
            db_path=str(self.data_dir / "focus.db"),
            custom_blocklist=custom_blocklist,
        )
    
    def _init_dataset(self):
        """Initialize dataset explorer."""
        self.dataset = DatasetExplorer()
    
    def _init_breaks(self, on_break_due: Optional[Callable[[str], None]]):
        """Initialize break reminders."""
        breaks_config = self.config.get("breaks", {})
        
        self.breaks = BreakReminder(
            work_duration_minutes=breaks_config.get("work_duration", 50),
            short_break_minutes=breaks_config.get("short_break", 5),
            long_break_minutes=breaks_config.get("long_break", 15),
            on_break_due=on_break_due,
        )
    
    # =========================================================================
    # Command Handling
    # =========================================================================
    
    async def handle_command(self, text: str) -> Optional[str]:
        """
        Handle a productivity-related command.
        
        Args:
            text: Voice command text
            
        Returns:
            Response string or None if not a productivity command
        """
        text_lower = text.lower().strip()
        
        # Music commands
        if self._is_music_command(text_lower):
            return self._handle_music(text_lower, text)
        
        # Learning journal commands
        if self._is_journal_command(text_lower):
            return self._handle_journal(text_lower, text)
        
        # Habit commands
        if self._is_habit_command(text_lower):
            return self._handle_habits(text_lower, text)
        
        # Project commands
        if self._is_project_command(text_lower):
            return self._handle_projects(text_lower, text)
        
        # Snippet commands
        if self._is_snippet_command(text_lower):
            return self._handle_snippets(text_lower, text)
        
        # Study planner commands
        if self._is_planner_command(text_lower):
            return await self._handle_planner(text_lower, text)
        
        # Weekly review commands
        if self._is_review_command(text_lower):
            return self._handle_review(text_lower)
        
        # Focus mode commands
        if self._is_focus_command(text_lower):
            return self._handle_focus(text_lower, text)
        
        # Dataset commands
        if self._is_dataset_command(text_lower):
            return self._handle_dataset(text_lower, text)
        
        # Break commands
        if self._is_break_command(text_lower):
            return await self._handle_breaks(text_lower)
        
        return None
    
    # =========================================================================
    # Command Detection
    # =========================================================================
    
    def _is_music_command(self, text: str) -> bool:
        patterns = [
            "play music", "play focus", "play study", "play lofi", "play lo-fi",
            "play hindi", "play bollywood", "play gym", "play workout",
            "play classical", "play chill", "play coding", "play ambient",
            "pause music", "stop music", "what's playing", "show playlists",
            "play playlist", "music",
            # Personal library commands (YouTube Music Premium)
            "play my liked", "liked songs", "my library", "play my mix",
            "my mix", "discover mix", "play history", "recently played",
            "new releases", "music charts", "browse moods",
            # Search commands
            "search on youtube music", "search youtube music", "find song",
        ]
        return any(p in text for p in patterns)
    
    def _is_journal_command(self, text: str) -> bool:
        # Learning journal - distinct from voice journal in career module
        patterns = [
            "log learning", "learned today", "learning journal", "what did i learn",
            "learning summary", "add takeaway", "learning streak",
            "log what i learned", "today i learned", "til:",
        ]
        # Exclude voice journal patterns (handled by career module)
        exclude_patterns = ["voice journal", "diary", "mood", "grateful", "reflect", "feeling"]
        if any(p in text for p in exclude_patterns):
            return False
        return any(p in text for p in patterns)
    
    def _is_habit_command(self, text: str) -> bool:
        patterns = [
            "log habit", "habit done", "did i", "show habits", "my habits",
            "add habit", "habit streak", "habit report", "today's habits",
            "mark habit", "complete habit", "habit check", "exercise done",
            "meditate done", "study done", "water done", "read done",
        ]
        return any(p in text for p in patterns)
    
    def _is_project_command(self, text: str) -> bool:
        patterns = [
            "create project", "new project", "show projects", "my projects",
            "update project", "log time", "add milestone", "mark milestone",
            "project status", "active project",
        ]
        return any(p in text for p in patterns)
    
    def _is_snippet_command(self, text: str) -> bool:
        patterns = [
            "save snippet", "find snippet", "show snippet", "search snippet",
            "code snippet", "my snippets", "get snippet",
        ]
        return any(p in text for p in patterns)
    
    def _is_planner_command(self, text: str) -> bool:
        patterns = [
            "plan my", "study plan", "what should i", "study schedule",
            "generate schedule", "i have", "hours free", "work on",
            "suggest task", "next task",
        ]
        return any(p in text for p in patterns)
    
    def _is_review_command(self, text: str) -> bool:
        patterns = [
            "weekly review", "how was my week", "week summary",
            "what did i accomplish", "weekly summary",
        ]
        return any(p in text for p in patterns)
    
    def _is_focus_command(self, text: str) -> bool:
        patterns = [
            "focus mode", "start focus", "end focus", "stop focus",
            "block site", "unblock site", "blocked sites", "blocklist",
            "focus stats", "focus status",
        ]
        return any(p in text for p in patterns)
    
    def _is_dataset_command(self, text: str) -> bool:
        patterns = [
            "analyze dataset", "load dataset", "describe data", "show missing",
            "data shape", "column types", "data stats", "explore data",
            "analyze csv", "load csv",
        ]
        return any(p in text for p in patterns)
    
    def _is_break_command(self, text: str) -> bool:
        patterns = [
            "take a break", "break reminder", "skip break", "break status",
            "enable break", "disable break", "suggest stretch",
            "need a break", "time for break",
        ]
        return any(p in text for p in patterns)
    
    # =========================================================================
    # Command Handlers
    # =========================================================================
    
    def _handle_music(self, text: str, original: str) -> str:
        """Handle music commands."""
        # =====================================================================
        # YouTube Music Personal Library Commands (Premium)
        # =====================================================================
        
        # Play liked songs
        if "liked songs" in text or "play my liked" in text:
            return self.music.play_liked_songs()
        
        # Play library
        if "my library" in text or "open library" in text:
            return self.music.play_library()
        
        # Play history / recently played
        if "play history" in text or "recently played" in text:
            return self.music.play_history()
        
        # Play my mix
        if "my mix" in text or "play my mix" in text or "youtube mix" in text:
            return self.music.play_my_mix()
        
        # Discover mix
        if "discover mix" in text or "discover weekly" in text:
            return self.music.play_discover_mix()
        
        # New releases
        if "new releases" in text or "new music" in text:
            return self.music.play_new_releases()
        
        # Charts
        if "music charts" in text or "top charts" in text:
            return self.music.play_charts()
        
        # Browse moods
        if "browse moods" in text or "moods and genres" in text:
            return self.music.browse_moods()
        
        # =====================================================================
        # Search Commands
        # =====================================================================
        
        # Search on YouTube Music
        search_yt_match = re.search(r"search\s+(?:on\s+)?youtube\s+music\s+(?:for\s+)?(.+)", text)
        if search_yt_match:
            query = search_yt_match.group(1).strip()
            return self.music.search_youtube_music(query)
        
        # Find song
        find_match = re.search(r"find\s+(?:song|music)\s+(.+)", text)
        if find_match:
            query = find_match.group(1).strip()
            return self.music.search_youtube_music(query)
        
        # =====================================================================
        # Standard Playlist Commands
        # =====================================================================
        
        # Play specific playlist
        play_patterns = [
            (r"play\s+(focus|study|concentration)", "focus"),
            (r"play\s+(lofi|lo-fi|lo fi)", "lofi"),
            (r"play\s+(hindi|bollywood)", "hindi"),
            (r"play\s+(gym|workout|exercise)", "gym"),
            (r"play\s+(classical|piano)", "classical"),
            (r"play\s+(chill|relax)", "chill"),
            (r"play\s+(coding|programming)", "coding"),
            (r"play\s+(ambient|background)", "ambient"),
            (r"play\s+(nature|rain)", "nature"),
        ]
        
        for pattern, playlist in play_patterns:
            if re.search(pattern, text):
                return self.music.play(playlist)
        
        # Play by search query
        search_match = re.search(r"play\s+(.+?)(?:\s+music)?$", text)
        if search_match:
            query = search_match.group(1).strip()
            # Check if it's a known playlist
            if query in self.music.playlists:
                return self.music.play(query)
            # Otherwise search
            return self.music.play_search(query)
        
        # Show playlists
        if "show playlist" in text or "list playlist" in text:
            return self.music.list_playlists()
        
        # What's playing
        if "what's playing" in text or "currently playing" in text:
            return self.music.get_current()
        
        # Default: play focus music
        if "play music" in text:
            return self.music.play("focus")
        
        return self.music.list_playlists()
    
    def _handle_journal(self, text: str, original: str) -> str:
        """Handle learning journal commands."""
        # Log learning
        log_patterns = [
            r"log\s+learning[:\s]+(.+)",
            r"learned\s+(?:about\s+)?(.+?)(?:\s+in\s+(.+))?$",
            r"i\s+learned\s+(.+)",
        ]
        
        for pattern in log_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                subject = match.group(2).strip() if match.lastindex >= 2 and match.group(2) else None
                
                # Try to extract subject from content
                if not subject:
                    subject_match = re.search(r"in\s+([\w\s]+?)(?:\s+class|\s+course)?$", content)
                    if subject_match:
                        subject = subject_match.group(1).strip()
                        content = content[:subject_match.start()].strip()
                
                entry = self.journal.log(content, subject=subject)
                return f"📝 Learning logged!\n\nSubject: {entry.subject}\nContent: {content}"
        
        # Add takeaway
        if "add takeaway" in text:
            takeaway_match = re.search(r"add\s+takeaway[:\s]+(.+)", text)
            if takeaway_match:
                takeaway = takeaway_match.group(1).strip()
                # Add to most recent entry
                entries = self.journal.get_today()
                if entries:
                    self.journal.add_takeaway(entries[0].id, takeaway)
                    return f"💡 Takeaway added: {takeaway}"
                return "No journal entries today to add takeaway to."
        
        # Show this week's learning
        if "this week" in text or "what did i learn" in text:
            return self.journal.get_weekly_summary()
        
        # Show by subject
        subject_match = re.search(r"learning\s+(?:for|about|in)\s+(.+)", text)
        if subject_match:
            subject = subject_match.group(1).strip()
            entries = self.journal.get_by_subject(subject)
            if entries:
                return f"Learning entries for {subject}:\n\n" + self.journal.format_entries(entries)
            return f"No learning entries found for '{subject}'."
        
        # Show streak
        if "streak" in text:
            streak = self.journal.get_streak()
            return f"🔥 Learning streak: {streak} consecutive days!"
        
        # Default: show recent
        entries = self.journal.get_recent(limit=5)
        return "Recent learning:\n\n" + self.journal.format_entries(entries)
    
    def _handle_habits(self, text: str, original: str) -> str:
        """Handle habit commands."""
        # Log habit completion
        log_patterns = [
            r"(?:log|mark|complete)\s+(.+?)\s+(?:done|complete|finished)",
            r"(.+?)\s+done",
            r"did\s+(.+)",
        ]
        
        for pattern in log_patterns:
            match = re.search(pattern, text)
            if match:
                habit_name = match.group(1).strip()
                return self.habits.log_completion(habit_name)
        
        # Check if habit done today
        check_match = re.search(r"did\s+i\s+(.+?)(?:\s+today)?", text)
        if check_match:
            habit_name = check_match.group(1).strip()
            is_done = self.habits.is_completed_today(habit_name)
            if is_done:
                return f"✅ Yes, you completed '{habit_name}' today!"
            return f"❌ Not yet! '{habit_name}' is not marked complete today."
        
        # Add new habit
        add_match = re.search(r"add\s+habit[:\s]+(.+)", text)
        if add_match:
            habit_name = add_match.group(1).strip()
            habit = self.habits.add_habit(habit_name)
            return f"✅ Added habit: {habit.name}"
        
        # Show streak
        streak_match = re.search(r"(?:habit\s+)?streak\s+(?:for\s+)?(.+)", text)
        if streak_match:
            habit_name = streak_match.group(1).strip()
            streak = self.habits.get_streak(habit_name)
            return f"🔥 {habit_name} streak: {streak} days!"
        
        # Weekly report
        if "report" in text or "how am i doing" in text:
            return self.habits.get_weekly_report()
        
        # Today's checklist
        if "today" in text or "checklist" in text:
            return self.habits.get_today_checklist()
        
        # Default: show all habits
        return self.habits.get_today_checklist()
    
    def _handle_projects(self, text: str, original: str) -> str:
        """Handle project commands."""
        # Create project
        create_match = re.search(r"(?:create|new)\s+project[:\s]+(.+)", text)
        if create_match:
            name = create_match.group(1).strip()
            project = self.projects.create(name)
            return f"🚀 Created project: {project.name}"
        
        # Log time
        time_match = re.search(r"log\s+(\d+)\s*(?:hours?|h|minutes?|m)\s+(?:on|to)\s+(.+)", text)
        if time_match:
            amount = int(time_match.group(1))
            project_name = time_match.group(2).strip()
            
            # Convert hours to minutes if needed
            if "hour" in text or text.count("h") > 0:
                amount *= 60
            
            project = self.projects.get_by_name(project_name)
            if project:
                return self.projects.log_time(project.id, amount)
            return f"Project '{project_name}' not found."
        
        # Add milestone
        milestone_match = re.search(r"add\s+milestone[:\s]+(.+?)(?:\s+to\s+(.+))?$", text)
        if milestone_match:
            milestone_name = milestone_match.group(1).strip()
            project_name = milestone_match.group(2).strip() if milestone_match.group(2) else None
            
            if project_name:
                project = self.projects.get_by_name(project_name)
            else:
                # Use most recent active project
                active = self.projects.get_active()
                project = active[0] if active else None
            
            if project:
                self.projects.add_milestone(project.id, milestone_name)
                return f"✅ Added milestone '{milestone_name}' to {project.name}"
            return "No project found. Specify project name or create one first."
        
        # Mark milestone complete
        if "mark milestone" in text or "complete milestone" in text:
            match = re.search(r"(?:mark|complete)\s+milestone[:\s]+(.+)", text)
            if match:
                milestone_name = match.group(1).strip()
                active = self.projects.get_active()
                if active:
                    return self.projects.complete_milestone(active[0].id, milestone_name)
            return "Specify milestone name to complete."
        
        # Show active projects
        if "active" in text:
            projects = self.projects.get_active()
            return self.projects.format_projects(projects)
        
        # Default: show all projects
        projects = self.projects.get_all()
        return self.projects.format_projects(projects)
    
    def _handle_snippets(self, text: str, original: str) -> str:
        """Handle code snippet commands."""
        # Save snippet
        save_match = re.search(r"save\s+snippet[:\s]+(.+)", text)
        if save_match:
            name = save_match.group(1).strip()
            return f"To save a snippet, provide the code. Use: save_snippet('{name}', code)"
        
        # Find/search snippet
        find_match = re.search(r"(?:find|search|get)\s+snippet\s+(?:for\s+)?(.+)", text)
        if find_match:
            query = find_match.group(1).strip()
            snippets = self.snippets.search(query)
            
            if snippets:
                # Return first match with code
                snippet = snippets[0]
                return self.snippets.format_snippet(snippet, show_code=True)
            return f"No snippets found for '{query}'."
        
        # Show by category
        cat_match = re.search(r"(?:show\s+)?(\w+)\s+snippets?", text)
        if cat_match:
            category = cat_match.group(1).strip()
            snippets = self.snippets.get_by_category(category)
            if snippets:
                return self.snippets.format_snippets(snippets)
        
        # Most used
        if "most used" in text or "popular" in text:
            snippets = self.snippets.get_most_used(limit=10)
            return self.snippets.format_snippets(snippets)
        
        # Default: list all
        snippets = self.snippets.get_all()
        return self.snippets.format_snippets(snippets)
    
    async def _handle_planner(self, text: str, original: str) -> str:
        """Handle study planner commands."""
        # Fetch tasks from Canvas
        if self.canvas:
            await self.planner.fetch_canvas_tasks(days=7)
        
        # Fetch local tasks
        if self.assignment_tracker:
            self.planner.fetch_local_tasks(days=7)
        
        # Generate schedule for specific duration
        duration_match = re.search(r"(?:i\s+have\s+)?(\d+)\s*(?:hours?|h)", text)
        if duration_match:
            hours = int(duration_match.group(1))
            schedule = self.planner.generate_schedule(available_minutes=hours * 60)
            return self.planner.format_schedule(schedule)
        
        # What should I work on
        if "what should i" in text or "suggest" in text or "next task" in text:
            task = self.planner.suggest_next_task()
            return self.planner.format_suggestion(task)
        
        # Plan my week/day
        if "plan my" in text:
            schedule = self.planner.generate_schedule(available_minutes=240)  # 4 hours default
            return self.planner.format_schedule(schedule)
        
        # Default: suggest next task
        task = self.planner.suggest_next_task()
        return self.planner.format_suggestion(task)
    
    def _handle_review(self, text: str) -> str:
        """Handle weekly review commands."""
        return self.review.generate(include_details=True)
    
    def _handle_focus(self, text: str, original: str) -> str:
        """Handle focus mode commands."""
        # Start focus mode
        if "start focus" in text or "enable focus" in text:
            return self.focus.start()
        
        # Stop focus mode
        if "stop focus" in text or "end focus" in text or "disable focus" in text:
            return self.focus.stop()
        
        # Block site
        block_match = re.search(r"block\s+(?:site\s+)?(.+)", text)
        if block_match and "unblock" not in text:
            site = block_match.group(1).strip()
            return self.focus.add_to_blocklist(site)
        
        # Unblock site
        unblock_match = re.search(r"unblock\s+(?:site\s+)?(.+)", text)
        if unblock_match:
            site = unblock_match.group(1).strip()
            return self.focus.remove_from_blocklist(site)
        
        # Show blocklist
        if "blocklist" in text or "blocked sites" in text:
            return self.focus.format_blocklist()
        
        # Stats
        if "stats" in text:
            return self.focus.get_weekly_stats()
        
        # Status
        return self.focus.get_status()
    
    def _handle_dataset(self, text: str, original: str) -> str:
        """Handle dataset commands."""
        if not self.dataset.is_available:
            return "Dataset explorer requires pandas. Install with: pip install pandas"
        
        # Load/analyze dataset
        load_match = re.search(r"(?:analyze|load|explore)\s+(?:dataset|data|csv)\s+(.+)", text)
        if load_match:
            path = load_match.group(1).strip()
            return self.dataset.load(path)
        
        # Describe
        if "describe" in text or "stats" in text:
            return self.dataset.describe()
        
        # Missing values
        if "missing" in text:
            return self.dataset.show_missing()
        
        # Shape
        if "shape" in text or "how many rows" in text:
            return self.dataset.show_shape()
        
        # Column types
        if "column" in text or "dtype" in text:
            return self.dataset.show_dtypes()
        
        # Sample
        if "sample" in text or "head" in text:
            return self.dataset.show_sample()
        
        return "Load a dataset first with 'Analyze dataset [filename]'"
    
    async def _handle_breaks(self, text: str) -> str:
        """Handle break commands."""
        # Enable break reminders
        if "enable" in text or "start" in text or "remind" in text:
            return await self.breaks.start()
        
        # Disable break reminders
        if "disable" in text or "stop" in text:
            return self.breaks.stop()
        
        # Take a break
        if "take" in text:
            return self.breaks.take_break()
        
        # Skip break
        if "skip" in text:
            return self.breaks.skip_break()
        
        # Suggest stretch
        if "stretch" in text:
            return self.breaks.suggest_stretch()
        
        # Status
        return self.breaks.get_status()
    
    # =========================================================================
    # Integration Methods
    # =========================================================================
    
    def on_pomodoro_start(self, auto_play_music: bool = True):
        """Called when Pomodoro session starts."""
        if auto_play_music:
            self.music.play_focus_music()
        
        # Enable focus mode
        self.focus.start()
    
    def on_pomodoro_end(self):
        """Called when Pomodoro session ends."""
        # Disable focus mode
        self.focus.stop()
    
    async def close(self):
        """Clean up resources."""
        if self.breaks.is_active:
            self.breaks.stop()
        if self.focus.is_active:
            self.focus.stop()
