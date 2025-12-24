"""
Quick Launch System for JARVIS.

Provides:
- Application Registry: Store and launch apps by friendly name
- Web Bookmarks: Store and open favorite websites
- YouTube/Media Search: Search and play media
- Unified Launch: Smart "Open" command routing
"""

from __future__ import annotations

import json
import os
import platform
import re
import sqlite3
import subprocess
import urllib.parse
import webbrowser
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


class LaunchType(Enum):
    """Type of launch target."""
    APPLICATION = "application"
    BOOKMARK = "bookmark"
    YOUTUBE = "youtube"
    WEB_SEARCH = "web_search"


@dataclass
class Application:
    """Registered application."""
    id: int
    name: str
    path: Optional[str] = None
    command: Optional[str] = None
    category: str = "general"
    platform: str = "all"
    use_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Bookmark:
    """Web bookmark."""
    id: int
    name: str
    url: str
    category: str = "general"
    keywords: List[str] = field(default_factory=list)
    use_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class LaunchResult:
    """Result of a launch operation."""
    success: bool
    message: str
    launch_type: LaunchType
    target: str


class QuickLaunchDB:
    """
    Database manager for Quick Launch system.
    
    Uses SQLite to store applications and bookmarks.
    Can share database with EpisodicMemory or use separate file.
    """
    
    def __init__(self, db_path: Path | str):
        """
        Initialize Quick Launch database.
        
        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_database(self) -> None:
        """Initialize database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Applications registry table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    path TEXT,
                    command TEXT,
                    category TEXT DEFAULT 'general',
                    platform TEXT DEFAULT 'all',
                    use_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Web bookmarks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    url TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    keywords TEXT DEFAULT '[]',
                    use_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_apps_name ON applications(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_apps_category ON applications(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_name ON bookmarks(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_category ON bookmarks(category)")
            
            logger.debug("Quick Launch database initialized")
    
    # =========================================================================
    # Applications CRUD
    # =========================================================================
    
    def add_application(
        self,
        name: str,
        path: Optional[str] = None,
        command: Optional[str] = None,
        category: str = "general",
        platform: str = "all",
    ) -> Tuple[bool, str]:
        """
        Add an application to the registry.
        
        Args:
            name: Friendly name for the application
            path: Full path to executable
            command: Command-line command (alternative to path)
            category: Application category
            platform: Target platform (windows/macos/linux/all)
            
        Returns:
            Tuple of (success, message)
        """
        if not path and not command:
            return False, "Either path or command must be provided"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO applications (name, path, command, category, platform)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, path, command, category, platform))
            
            logger.info(f"Added application: {name}")
            return True, f"Added {name} to applications"
        
        except sqlite3.IntegrityError:
            return False, f"Application '{name}' already exists"
        except Exception as e:
            logger.error(f"Failed to add application: {e}")
            return False, f"Failed to add application: {e}"
    
    def remove_application(self, name: str) -> Tuple[bool, str]:
        """Remove an application from the registry."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM applications WHERE name = ? COLLATE NOCASE", (name,))
                
                if cursor.rowcount == 0:
                    return False, f"Application '{name}' not found"
            
            logger.info(f"Removed application: {name}")
            return True, f"Removed {name} from applications"
        
        except Exception as e:
            logger.error(f"Failed to remove application: {e}")
            return False, f"Failed to remove application: {e}"
    
    def update_application(
        self,
        name: str,
        path: Optional[str] = None,
        command: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Update an existing application."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                updates = []
                params = []
                
                if path is not None:
                    updates.append("path = ?")
                    params.append(path)
                if command is not None:
                    updates.append("command = ?")
                    params.append(command)
                if category is not None:
                    updates.append("category = ?")
                    params.append(category)
                
                if not updates:
                    return False, "No updates provided"
                
                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.append(name)
                
                cursor.execute(f"""
                    UPDATE applications SET {', '.join(updates)}
                    WHERE name = ? COLLATE NOCASE
                """, params)
                
                if cursor.rowcount == 0:
                    return False, f"Application '{name}' not found"
            
            return True, f"Updated {name}"
        
        except Exception as e:
            logger.error(f"Failed to update application: {e}")
            return False, f"Failed to update application: {e}"
    
    def get_application(self, name: str) -> Optional[Application]:
        """Get an application by name."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM applications WHERE name = ? COLLATE NOCASE",
                    (name,)
                )
                row = cursor.fetchone()
                
                if row:
                    return Application(
                        id=row["id"],
                        name=row["name"],
                        path=row["path"],
                        command=row["command"],
                        category=row["category"],
                        platform=row["platform"],
                        use_count=row["use_count"],
                    )
                return None
        
        except Exception as e:
            logger.error(f"Failed to get application: {e}")
            return None
    
    def search_applications(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Application]:
        """Search applications by name or category."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                sql = "SELECT * FROM applications WHERE 1=1"
                params = []
                
                if query:
                    sql += " AND name LIKE ? COLLATE NOCASE"
                    params.append(f"%{query}%")
                
                if category:
                    sql += " AND category = ? COLLATE NOCASE"
                    params.append(category)
                
                sql += " ORDER BY use_count DESC, name ASC"
                
                cursor.execute(sql, params)
                
                return [
                    Application(
                        id=row["id"],
                        name=row["name"],
                        path=row["path"],
                        command=row["command"],
                        category=row["category"],
                        platform=row["platform"],
                        use_count=row["use_count"],
                    )
                    for row in cursor.fetchall()
                ]
        
        except Exception as e:
            logger.error(f"Failed to search applications: {e}")
            return []
    
    def list_applications(self) -> List[Application]:
        """List all registered applications."""
        return self.search_applications()
    
    def increment_app_usage(self, name: str) -> None:
        """Increment usage count for an application."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE applications 
                    SET use_count = use_count + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE name = ? COLLATE NOCASE
                """, (name,))
        except Exception as e:
            logger.debug(f"Failed to increment app usage: {e}")
    
    # =========================================================================
    # Bookmarks CRUD
    # =========================================================================
    
    def add_bookmark(
        self,
        name: str,
        url: str,
        category: str = "general",
        keywords: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """
        Add a web bookmark.
        
        Args:
            name: Friendly name for the bookmark
            url: Full URL
            category: Bookmark category
            keywords: Alternative names/aliases
            
        Returns:
            Tuple of (success, message)
        """
        # Ensure URL has scheme
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO bookmarks (name, url, category, keywords)
                    VALUES (?, ?, ?, ?)
                """, (name, url, category, json.dumps(keywords or [])))
            
            logger.info(f"Added bookmark: {name} -> {url}")
            return True, f"Added bookmark {name}"
        
        except sqlite3.IntegrityError:
            return False, f"Bookmark '{name}' already exists"
        except Exception as e:
            logger.error(f"Failed to add bookmark: {e}")
            return False, f"Failed to add bookmark: {e}"
    
    def remove_bookmark(self, name: str) -> Tuple[bool, str]:
        """Remove a bookmark."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM bookmarks WHERE name = ? COLLATE NOCASE", (name,))
                
                if cursor.rowcount == 0:
                    return False, f"Bookmark '{name}' not found"
            
            logger.info(f"Removed bookmark: {name}")
            return True, f"Removed bookmark {name}"
        
        except Exception as e:
            logger.error(f"Failed to remove bookmark: {e}")
            return False, f"Failed to remove bookmark: {e}"
    
    def update_bookmark(
        self,
        name: str,
        url: Optional[str] = None,
        category: Optional[str] = None,
        keywords: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """Update an existing bookmark."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                updates = []
                params = []
                
                if url is not None:
                    if not url.startswith(("http://", "https://")):
                        url = "https://" + url
                    updates.append("url = ?")
                    params.append(url)
                if category is not None:
                    updates.append("category = ?")
                    params.append(category)
                if keywords is not None:
                    updates.append("keywords = ?")
                    params.append(json.dumps(keywords))
                
                if not updates:
                    return False, "No updates provided"
                
                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.append(name)
                
                cursor.execute(f"""
                    UPDATE bookmarks SET {', '.join(updates)}
                    WHERE name = ? COLLATE NOCASE
                """, params)
                
                if cursor.rowcount == 0:
                    return False, f"Bookmark '{name}' not found"
            
            return True, f"Updated bookmark {name}"
        
        except Exception as e:
            logger.error(f"Failed to update bookmark: {e}")
            return False, f"Failed to update bookmark: {e}"
    
    def get_bookmark(self, name: str) -> Optional[Bookmark]:
        """Get a bookmark by name or keyword."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # First try exact name match
                cursor.execute(
                    "SELECT * FROM bookmarks WHERE name = ? COLLATE NOCASE",
                    (name,)
                )
                row = cursor.fetchone()
                
                # If not found, search keywords
                if not row:
                    cursor.execute("SELECT * FROM bookmarks")
                    for r in cursor.fetchall():
                        keywords = json.loads(r["keywords"] or "[]")
                        if name.lower() in [k.lower() for k in keywords]:
                            row = r
                            break
                
                if row:
                    return Bookmark(
                        id=row["id"],
                        name=row["name"],
                        url=row["url"],
                        category=row["category"],
                        keywords=json.loads(row["keywords"] or "[]"),
                        use_count=row["use_count"],
                    )
                return None
        
        except Exception as e:
            logger.error(f"Failed to get bookmark: {e}")
            return None
    
    def search_bookmarks(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Bookmark]:
        """Search bookmarks by name, keyword, or category."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                sql = "SELECT * FROM bookmarks WHERE 1=1"
                params = []
                
                if query:
                    sql += " AND (name LIKE ? COLLATE NOCASE OR keywords LIKE ? COLLATE NOCASE)"
                    params.extend([f"%{query}%", f"%{query}%"])
                
                if category:
                    sql += " AND category = ? COLLATE NOCASE"
                    params.append(category)
                
                sql += " ORDER BY use_count DESC, name ASC"
                
                cursor.execute(sql, params)
                
                return [
                    Bookmark(
                        id=row["id"],
                        name=row["name"],
                        url=row["url"],
                        category=row["category"],
                        keywords=json.loads(row["keywords"] or "[]"),
                        use_count=row["use_count"],
                    )
                    for row in cursor.fetchall()
                ]
        
        except Exception as e:
            logger.error(f"Failed to search bookmarks: {e}")
            return []
    
    def list_bookmarks(self) -> List[Bookmark]:
        """List all bookmarks."""
        return self.search_bookmarks()
    
    def increment_bookmark_usage(self, name: str) -> None:
        """Increment usage count for a bookmark."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE bookmarks 
                    SET use_count = use_count + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE name = ? COLLATE NOCASE
                """, (name,))
        except Exception as e:
            logger.debug(f"Failed to increment bookmark usage: {e}")


class ApplicationLauncher:
    """
    Launches applications from the registry.
    
    Features:
    - Registry-based launching
    - Fallback to system PATH
    - Cross-platform support
    - Usage tracking
    """
    
    def __init__(self, db: QuickLaunchDB):
        """
        Initialize application launcher.
        
        Args:
            db: QuickLaunchDB instance
        """
        self.db = db
        self.platform = platform.system().lower()
    
    def launch(self, name: str, args: Optional[List[str]] = None) -> LaunchResult:
        """
        Launch an application by name.
        
        Args:
            name: Application name
            args: Optional command-line arguments
            
        Returns:
            LaunchResult with success status
        """
        # Check registry first
        app = self.db.get_application(name)
        
        if app:
            # Check platform compatibility
            if app.platform != "all" and app.platform != self.platform:
                return LaunchResult(
                    success=False,
                    message=f"{name} is not available on {self.platform}",
                    launch_type=LaunchType.APPLICATION,
                    target=name,
                )
            
            # Launch from registry
            result = self._launch_app(app, args)
            
            if result.success:
                self.db.increment_app_usage(name)
            
            return result
        
        # Fallback: try launching by name directly
        return self._launch_by_name(name, args)
    
    def _launch_app(self, app: Application, args: Optional[List[str]] = None) -> LaunchResult:
        """Launch a registered application."""
        try:
            if app.command:
                # Launch by command
                cmd = [app.command] + (args or [])
                
                if self.platform == "windows":
                    subprocess.Popen(cmd, shell=True, start_new_session=True)
                else:
                    subprocess.Popen(cmd, start_new_session=True)
                
                logger.info(f"Launched {app.name} via command: {app.command}")
                return LaunchResult(
                    success=True,
                    message=f"Opened {app.name}",
                    launch_type=LaunchType.APPLICATION,
                    target=app.name,
                )
            
            elif app.path:
                # Launch by path
                if not os.path.exists(app.path):
                    return LaunchResult(
                        success=False,
                        message=f"Application path not found: {app.path}",
                        launch_type=LaunchType.APPLICATION,
                        target=app.name,
                    )
                
                if self.platform == "windows":
                    os.startfile(app.path)
                elif self.platform == "darwin":
                    subprocess.Popen(["open", app.path])
                else:
                    subprocess.Popen([app.path] + (args or []), start_new_session=True)
                
                logger.info(f"Launched {app.name} from path: {app.path}")
                return LaunchResult(
                    success=True,
                    message=f"Opened {app.name}",
                    launch_type=LaunchType.APPLICATION,
                    target=app.name,
                )
            
            return LaunchResult(
                success=False,
                message=f"No path or command for {app.name}",
                launch_type=LaunchType.APPLICATION,
                target=app.name,
            )
        
        except Exception as e:
            logger.error(f"Failed to launch {app.name}: {e}")
            return LaunchResult(
                success=False,
                message=f"Failed to open {app.name}: {e}",
                launch_type=LaunchType.APPLICATION,
                target=app.name,
            )
    
    def _launch_by_name(self, name: str, args: Optional[List[str]] = None) -> LaunchResult:
        """Try to launch an app by name (not in registry)."""
        try:
            if self.platform == "windows":
                cmd = f'start "" "{name}"'
                if args:
                    cmd += " " + " ".join(args)
                subprocess.Popen(cmd, shell=True)
            else:
                subprocess.Popen([name] + (args or []), start_new_session=True)
            
            logger.info(f"Launched {name} directly")
            return LaunchResult(
                success=True,
                message=f"Opened {name}",
                launch_type=LaunchType.APPLICATION,
                target=name,
            )
        
        except Exception as e:
            logger.warning(f"Could not launch {name}: {e}")
            return LaunchResult(
                success=False,
                message=f"Could not find application '{name}'. Try adding it with 'add application {name}'",
                launch_type=LaunchType.APPLICATION,
                target=name,
            )


class WebLauncher:
    """
    Opens web bookmarks and URLs.
    
    Features:
    - Bookmark-based opening
    - Direct URL opening
    - Usage tracking
    """
    
    # Common web services (fallback)
    COMMON_SITES = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "github": "https://github.com",
        "twitter": "https://twitter.com",
        "x": "https://x.com",
        "facebook": "https://www.facebook.com",
        "instagram": "https://www.instagram.com",
        "linkedin": "https://www.linkedin.com",
        "reddit": "https://www.reddit.com",
        "amazon": "https://www.amazon.com",
        "netflix": "https://www.netflix.com",
        "spotify": "https://open.spotify.com",
        "chatgpt": "https://chat.openai.com",
        "claude": "https://claude.ai",
    }
    
    def __init__(self, db: QuickLaunchDB, default_browser: Optional[str] = None):
        """
        Initialize web launcher.
        
        Args:
            db: QuickLaunchDB instance
            default_browser: Browser to use (None = system default)
        """
        self.db = db
        self.default_browser = default_browser
    
    def open(self, name_or_url: str) -> LaunchResult:
        """
        Open a bookmark or URL.
        
        Args:
            name_or_url: Bookmark name or direct URL
            
        Returns:
            LaunchResult with success status
        """
        # Check if it's a URL
        if self._is_url(name_or_url):
            return self._open_url(name_or_url)
        
        # Check bookmarks
        bookmark = self.db.get_bookmark(name_or_url)
        if bookmark:
            result = self._open_url(bookmark.url, bookmark.name)
            if result.success:
                self.db.increment_bookmark_usage(bookmark.name)
            return result
        
        # Check common sites
        name_lower = name_or_url.lower()
        if name_lower in self.COMMON_SITES:
            return self._open_url(self.COMMON_SITES[name_lower], name_or_url)
        
        # Not found
        return LaunchResult(
            success=False,
            message=f"Bookmark '{name_or_url}' not found. Add it with 'add bookmark {name_or_url}'",
            launch_type=LaunchType.BOOKMARK,
            target=name_or_url,
        )
    
    def _is_url(self, text: str) -> bool:
        """Check if text is a URL."""
        return bool(re.match(r'^https?://', text)) or "." in text and " " not in text
    
    def _open_url(self, url: str, name: Optional[str] = None) -> LaunchResult:
        """Open a URL in the browser."""
        try:
            # Ensure URL has scheme
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            
            if self.default_browser:
                webbrowser.get(self.default_browser).open(url)
            else:
                webbrowser.open(url)
            
            display_name = name or url
            logger.info(f"Opened {display_name} in browser")
            
            return LaunchResult(
                success=True,
                message=f"Opened {display_name} in your browser",
                launch_type=LaunchType.BOOKMARK,
                target=url,
            )
        
        except Exception as e:
            logger.error(f"Failed to open URL: {e}")
            return LaunchResult(
                success=False,
                message=f"Failed to open URL: {e}",
                launch_type=LaunchType.BOOKMARK,
                target=url,
            )


class YouTubeLauncher:
    """
    Search and play YouTube videos.
    
    Features:
    - Search by query
    - Direct video URL
    - Auto-play first result (optional, via Playwright)
    """
    
    YOUTUBE_SEARCH_URL = "https://www.youtube.com/results?search_query="
    YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v="
    
    def __init__(self, auto_play: bool = False, use_playwright: bool = False):
        """
        Initialize YouTube launcher.
        
        Args:
            auto_play: Whether to auto-play first result
            use_playwright: Use Playwright for auto-play
        """
        self.auto_play = auto_play
        self.use_playwright = use_playwright
    
    def search(self, query: str) -> LaunchResult:
        """
        Search YouTube for a query.
        
        Args:
            query: Search query
            
        Returns:
            LaunchResult with success status
        """
        try:
            encoded_query = urllib.parse.quote(query)
            url = self.YOUTUBE_SEARCH_URL + encoded_query
            
            if self.auto_play and self.use_playwright:
                return self._auto_play_first(url, query)
            
            webbrowser.open(url)
            
            logger.info(f"Searching YouTube for: {query}")
            return LaunchResult(
                success=True,
                message=f"Searching YouTube for '{query}'",
                launch_type=LaunchType.YOUTUBE,
                target=query,
            )
        
        except Exception as e:
            logger.error(f"Failed to search YouTube: {e}")
            return LaunchResult(
                success=False,
                message=f"Failed to search YouTube: {e}",
                launch_type=LaunchType.YOUTUBE,
                target=query,
            )
    
    def play(self, query: str) -> LaunchResult:
        """
        Play a video on YouTube (search and optionally auto-play).
        
        Args:
            query: Video search query
            
        Returns:
            LaunchResult with success status
        """
        return self.search(query)
    
    def _auto_play_first(self, url: str, query: str) -> LaunchResult:
        """Auto-play first search result using Playwright."""
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                page = browser.new_page()
                page.goto(url)
                
                # Wait for results and click first video
                page.wait_for_selector("ytd-video-renderer", timeout=5000)
                page.click("ytd-video-renderer a#thumbnail")
                
                # Keep browser open
                logger.info(f"Auto-playing YouTube: {query}")
            
            return LaunchResult(
                success=True,
                message=f"Playing '{query}' on YouTube",
                launch_type=LaunchType.YOUTUBE,
                target=query,
            )
        
        except ImportError:
            logger.warning("Playwright not available, falling back to browser")
            webbrowser.open(url)
            return LaunchResult(
                success=True,
                message=f"Searching YouTube for '{query}'",
                launch_type=LaunchType.YOUTUBE,
                target=query,
            )
        except Exception as e:
            logger.error(f"Playwright auto-play failed: {e}")
            webbrowser.open(url)
            return LaunchResult(
                success=True,
                message=f"Searching YouTube for '{query}'",
                launch_type=LaunchType.YOUTUBE,
                target=query,
            )


class QuickLaunchManager:
    """
    Unified Quick Launch manager.
    
    Combines applications, bookmarks, and media into one smart system.
    Handles "Open [something]" commands intelligently.
    """
    
    def __init__(
        self,
        db_path: Path | str,
        youtube_auto_play: bool = False,
        default_browser: Optional[str] = None,
    ):
        """
        Initialize Quick Launch manager.
        
        Args:
            db_path: Path to database
            youtube_auto_play: Auto-play YouTube videos
            default_browser: Default browser for web
        """
        self.db = QuickLaunchDB(db_path)
        self.app_launcher = ApplicationLauncher(self.db)
        self.web_launcher = WebLauncher(self.db, default_browser)
        self.youtube = YouTubeLauncher(auto_play=youtube_auto_play)
    
    def open(self, target: str) -> LaunchResult:
        """
        Smart open command - routes to appropriate launcher.
        
        Priority:
        1. Registered applications
        2. Bookmarks
        3. Common web services
        4. Direct URL
        5. Fallback app launch
        
        Args:
            target: What to open
            
        Returns:
            LaunchResult with success status
        """
        target = target.strip()
        
        # 1. Check applications registry
        app = self.db.get_application(target)
        if app:
            return self.app_launcher.launch(target)
        
        # 2. Check bookmarks
        bookmark = self.db.get_bookmark(target)
        if bookmark:
            return self.web_launcher.open(target)
        
        # 3. Check common web services
        if target.lower() in WebLauncher.COMMON_SITES:
            return self.web_launcher.open(target)
        
        # 4. Check if it's a URL
        if "." in target and " " not in target:
            return self.web_launcher.open(target)
        
        # 5. Try launching as application
        return self.app_launcher.launch(target)
    
    def play_youtube(self, query: str) -> LaunchResult:
        """Play something on YouTube."""
        return self.youtube.play(query)
    
    def search_youtube(self, query: str) -> LaunchResult:
        """Search YouTube."""
        return self.youtube.search(query)
    
    # =========================================================================
    # Application Management
    # =========================================================================
    
    def add_application(
        self,
        name: str,
        path: Optional[str] = None,
        command: Optional[str] = None,
        category: str = "general",
    ) -> Tuple[bool, str]:
        """Add an application to the registry."""
        return self.db.add_application(name, path, command, category)
    
    def remove_application(self, name: str) -> Tuple[bool, str]:
        """Remove an application from the registry."""
        return self.db.remove_application(name)
    
    def list_applications(self) -> List[Application]:
        """List all registered applications."""
        return self.db.list_applications()
    
    # =========================================================================
    # Bookmark Management
    # =========================================================================
    
    def add_bookmark(
        self,
        name: str,
        url: str,
        category: str = "general",
        keywords: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """Add a bookmark."""
        return self.db.add_bookmark(name, url, category, keywords)
    
    def remove_bookmark(self, name: str) -> Tuple[bool, str]:
        """Remove a bookmark."""
        return self.db.remove_bookmark(name)
    
    def list_bookmarks(self) -> List[Bookmark]:
        """List all bookmarks."""
        return self.db.list_bookmarks()
    
    # =========================================================================
    # Query Parsing
    # =========================================================================
    
    def parse_command(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Parse a voice command to extract action and target.
        
        Args:
            text: Voice command text
            
        Returns:
            Tuple of (action, target)
        """
        text_lower = text.lower().strip()
        
        # YouTube patterns
        youtube_patterns = [
            r"play (.+) on youtube",
            r"search youtube for (.+)",
            r"youtube (.+)",
            r"play (.+) on yt",
        ]
        
        for pattern in youtube_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return "youtube", match.group(1).strip()
        
        # Open patterns
        open_patterns = [
            r"open (.+)",
            r"launch (.+)",
            r"start (.+)",
            r"run (.+)",
        ]
        
        for pattern in open_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return "open", match.group(1).strip()
        
        # Add application patterns
        add_app_patterns = [
            r"add application (.+) (?:at|path) (.+)",
            r"add app (.+) (?:at|path) (.+)",
            r"register (.+) (?:at|path) (.+)",
        ]
        
        for pattern in add_app_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return "add_app", f"{match.group(1).strip()}|{match.group(2).strip()}"
        
        # Add bookmark patterns
        add_bookmark_patterns = [
            r"add bookmark (.+) (?:at|url) (.+)",
            r"bookmark (.+) (?:at|url) (.+)",
            r"save (.+) (?:at|url) (.+)",
        ]
        
        for pattern in add_bookmark_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return "add_bookmark", f"{match.group(1).strip()}|{match.group(2).strip()}"
        
        # List patterns
        if any(p in text_lower for p in ["list apps", "list applications", "my apps", "what apps"]):
            return "list_apps", None
        
        if any(p in text_lower for p in ["list bookmarks", "my bookmarks", "show bookmarks"]):
            return "list_bookmarks", None
        
        return "unknown", text
    
    def handle_command(self, text: str) -> str:
        """
        Handle a voice command and return response.
        
        Args:
            text: Voice command text
            
        Returns:
            Response message
        """
        action, target = self.parse_command(text)
        
        if action == "youtube" and target:
            result = self.play_youtube(target)
            return result.message
        
        elif action == "open" and target:
            result = self.open(target)
            return result.message
        
        elif action == "add_app" and target:
            parts = target.split("|")
            if len(parts) == 2:
                name, path = parts
                success, msg = self.add_application(name, path=path)
                return msg
            return "Please specify: add application [name] at [path]"
        
        elif action == "add_bookmark" and target:
            parts = target.split("|")
            if len(parts) == 2:
                name, url = parts
                success, msg = self.add_bookmark(name, url)
                return msg
            return "Please specify: add bookmark [name] at [url]"
        
        elif action == "list_apps":
            apps = self.list_applications()
            if apps:
                names = [app.name for app in apps]
                return f"You have {len(apps)} registered applications: {', '.join(names)}"
            return "No applications registered yet. Add one with 'add application [name] at [path]'"
        
        elif action == "list_bookmarks":
            bookmarks = self.list_bookmarks()
            if bookmarks:
                names = [b.name for b in bookmarks]
                return f"You have {len(bookmarks)} bookmarks: {', '.join(names)}"
            return "No bookmarks saved yet. Add one with 'add bookmark [name] at [url]'"
        
        return f"I didn't understand that command: {text}"


# Convenience function to get manager instance
_manager_instance: Optional[QuickLaunchManager] = None


def get_quick_launch_manager(
    db_path: Optional[Path | str] = None,
    **kwargs,
) -> QuickLaunchManager:
    """
    Get or create the Quick Launch manager singleton.
    
    Args:
        db_path: Path to database (default: data/quick_launch.db)
        **kwargs: Additional arguments for QuickLaunchManager
        
    Returns:
        QuickLaunchManager instance
    """
    global _manager_instance
    
    if _manager_instance is None:
        if db_path is None:
            db_path = Path("data/quick_launch.db")
        _manager_instance = QuickLaunchManager(db_path, **kwargs)
    
    return _manager_instance
