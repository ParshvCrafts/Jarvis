"""
Notion Integration for JARVIS.

Basic integration with Notion workspace:
- URL-based quick access (default)
- API integration (optional, requires API key)
"""

import sqlite3
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class NotionPage:
    id: Optional[int] = None
    name: str = ""
    url: str = ""
    category: str = "general"
    description: str = ""
    is_favorite: bool = False
    last_accessed: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "NotionPage":
        return cls(
            id=row["id"],
            name=row["name"],
            url=row["url"],
            category=row["category"] or "general",
            description=row["description"] or "",
            is_favorite=bool(row["is_favorite"]),
            last_accessed=datetime.fromisoformat(row["last_accessed"]) if row["last_accessed"] else None,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
        )


class NotionIntegration:
    """
    Notion workspace integration.
    
    Features:
    - Save and quick-access Notion pages
    - Organize by category
    - Track frequently used pages
    - Optional API integration
    """
    
    # Default Notion URLs
    NOTION_BASE = "https://www.notion.so"
    
    def __init__(
        self,
        data_dir: str = "data",
        integration_type: str = "url",
        api_key: Optional[str] = None,
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "notion.db"
        
        self.integration_type = integration_type
        self.api_key = api_key
        self._api_client = None
        
        self._init_db()
        
        if integration_type == "api" and api_key:
            self._init_api_client()
        
        logger.info(f"Notion Integration initialized (type: {integration_type})")
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    description TEXT,
                    is_favorite INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
    
    def _init_api_client(self):
        """Initialize Notion API client if available."""
        try:
            from notion_client import Client
            self._api_client = Client(auth=self.api_key)
            logger.info("Notion API client initialized")
        except ImportError:
            logger.warning("notion-client not installed. Using URL-based integration.")
            self.integration_type = "url"
        except Exception as e:
            logger.error(f"Failed to initialize Notion API: {e}")
            self.integration_type = "url"
    
    def open_notion(self) -> str:
        """Open Notion in browser."""
        try:
            webbrowser.open(self.NOTION_BASE)
            return "🔗 Opening Notion..."
        except Exception as e:
            return f"Failed to open Notion: {e}"
    
    def open_page(self, name: str) -> str:
        """Open a saved Notion page by name."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM pages WHERE LOWER(name) LIKE ? ORDER BY is_favorite DESC, last_accessed DESC LIMIT 1",
                (f"%{name.lower()}%",)
            ).fetchone()
            
            if not row:
                return f"No saved page found matching '{name}'. Use 'save notion page' to add one."
            
            page = NotionPage.from_row(row)
            
            # Update last accessed
            conn.execute(
                "UPDATE pages SET last_accessed = ? WHERE id = ?",
                (datetime.now().isoformat(), page.id)
            )
            conn.commit()
        
        try:
            webbrowser.open(page.url)
            return f"🔗 Opening '{page.name}' in Notion..."
        except Exception as e:
            return f"Failed to open page: {e}"
    
    def save_page(
        self,
        name: str,
        url: str,
        category: str = "general",
        description: str = "",
    ) -> str:
        """Save a Notion page for quick access."""
        # Validate URL
        if not url.startswith(("https://notion.so", "https://www.notion.so", "notion.so")):
            if not url.startswith("http"):
                url = f"https://www.notion.so/{url}"
        
        with sqlite3.connect(self.db_path) as conn:
            # Check if page with same name exists
            existing = conn.execute(
                "SELECT id FROM pages WHERE LOWER(name) = ?",
                (name.lower(),)
            ).fetchone()
            
            if existing:
                conn.execute(
                    "UPDATE pages SET url = ?, category = ?, description = ? WHERE id = ?",
                    (url, category, description, existing[0])
                )
                conn.commit()
                return f"✅ Updated '{name}' page URL"
            
            conn.execute("""
                INSERT INTO pages (name, url, category, description, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (name, url, category, description, datetime.now().isoformat()))
            conn.commit()
        
        return f"✅ Saved Notion page: '{name}'"
    
    def get_pages(self, category: Optional[str] = None) -> List[NotionPage]:
        """Get saved Notion pages."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if category:
                rows = conn.execute(
                    "SELECT * FROM pages WHERE category = ? ORDER BY is_favorite DESC, name",
                    (category,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM pages ORDER BY is_favorite DESC, last_accessed DESC, name"
                ).fetchall()
        
        return [NotionPage.from_row(row) for row in rows]
    
    def list_pages(self) -> str:
        """List all saved Notion pages."""
        pages = self.get_pages()
        
        if not pages:
            return "No Notion pages saved yet. Use 'save notion page: [name] at [url]' to add one."
        
        lines = ["📓 **Your Notion Pages**\n"]
        
        by_category = {}
        for page in pages:
            if page.category not in by_category:
                by_category[page.category] = []
            by_category[page.category].append(page)
        
        for category, cat_pages in by_category.items():
            lines.append(f"\n**{category.title()}:**")
            for page in cat_pages:
                star = "⭐ " if page.is_favorite else ""
                lines.append(f"  • {star}{page.name}")
                if page.description:
                    lines.append(f"    {page.description}")
        
        return "\n".join(lines)
    
    def toggle_favorite(self, name: str) -> str:
        """Toggle favorite status for a page."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, is_favorite FROM pages WHERE LOWER(name) LIKE ?",
                (f"%{name.lower()}%",)
            ).fetchone()
            
            if not row:
                return f"No page found matching '{name}'."
            
            new_status = 0 if row[1] else 1
            conn.execute(
                "UPDATE pages SET is_favorite = ? WHERE id = ?",
                (new_status, row[0])
            )
            conn.commit()
        
        status = "favorited" if new_status else "unfavorited"
        return f"⭐ Page '{name}' {status}"
    
    def delete_page(self, name: str) -> str:
        """Delete a saved page."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "DELETE FROM pages WHERE LOWER(name) LIKE ?",
                (f"%{name.lower()}%",)
            )
            conn.commit()
            
            if result.rowcount > 0:
                return f"✅ Deleted page '{name}'"
            return f"No page found matching '{name}'."
    
    # =========================================================================
    # API-based methods (require notion-client)
    # =========================================================================
    
    def search_notion(self, query: str) -> str:
        """Search Notion workspace (requires API)."""
        if not self._api_client:
            return "Notion API not configured. Using URL-based integration."
        
        try:
            results = self._api_client.search(query=query, page_size=5)
            
            if not results.get("results"):
                return f"No results found for '{query}'"
            
            lines = [f"🔍 **Notion Search: '{query}'**\n"]
            
            for item in results["results"][:5]:
                title = "Untitled"
                if item.get("properties", {}).get("title"):
                    title_prop = item["properties"]["title"]
                    if title_prop.get("title"):
                        title = title_prop["title"][0].get("plain_text", "Untitled")
                
                item_type = item.get("object", "page")
                url = item.get("url", "")
                
                lines.append(f"  • [{item_type}] {title}")
                if url:
                    lines.append(f"    {url}")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Notion search failed: {e}")
            return f"Search failed: {e}"
    
    def create_page(self, title: str, content: str = "") -> str:
        """Create a new Notion page (requires API)."""
        if not self._api_client:
            return "Notion API not configured. Please add NOTION_API_KEY to .env"
        
        try:
            # This requires a parent page/database ID
            # For simplicity, we'll just inform the user
            return "Page creation requires a parent page ID. Please create pages directly in Notion."
            
        except Exception as e:
            logger.error(f"Failed to create page: {e}")
            return f"Failed to create page: {e}"
    
    def get_quick_links(self) -> Dict[str, str]:
        """Get dictionary of page names to URLs for quick access."""
        pages = self.get_pages()
        return {page.name.lower(): page.url for page in pages}
