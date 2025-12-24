"""
arXiv Paper Search for JARVIS.

Provides research paper discovery:
- Search by keywords
- Search by author
- Get paper abstracts
- Save to reading list
"""

from __future__ import annotations

import sqlite3
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

import httpx
from loguru import logger


@dataclass
class Paper:
    """arXiv paper."""
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    published: datetime
    updated: Optional[datetime] = None
    categories: List[str] = field(default_factory=list)
    pdf_url: Optional[str] = None
    html_url: Optional[str] = None
    
    @property
    def short_id(self) -> str:
        """Get short arXiv ID (without version)."""
        return self.arxiv_id.split("v")[0]
    
    def __str__(self) -> str:
        authors_str = ", ".join(self.authors[:3])
        if len(self.authors) > 3:
            authors_str += " et al."
        return f"{self.title} ({authors_str})"


@dataclass
class ReadingListItem:
    """Paper in reading list."""
    id: Optional[int] = None
    arxiv_id: str = ""
    title: str = ""
    authors: str = ""
    added_at: datetime = field(default_factory=datetime.now)
    read: bool = False
    notes: Optional[str] = None


class ArxivClient:
    """
    arXiv API client for paper search.
    
    Usage:
        client = ArxivClient()
        papers = await client.search("transformer architecture")
        papers = await client.search_by_author("Vaswani")
        client.add_to_reading_list(paper)
    """
    
    BASE_URL = "http://export.arxiv.org/api/query"
    
    # Default categories for DS/ML/AI
    DEFAULT_CATEGORIES = ["cs.LG", "cs.AI", "stat.ML", "cs.CL", "cs.CV"]
    
    def __init__(self, db_path: str = "data/reading_list.db"):
        """
        Initialize arXiv client.
        
        Args:
            db_path: Path to SQLite database for reading list
        """
        self.db_path = Path(db_path)
        self._client: Optional[httpx.AsyncClient] = None
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for reading list."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reading_list (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    arxiv_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    authors TEXT,
                    added_at TIMESTAMP NOT NULL,
                    read BOOLEAN DEFAULT FALSE,
                    notes TEXT
                )
            """)
            conn.commit()
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse arXiv datetime string."""
        if not dt_str:
            return None
        try:
            # arXiv uses ISO format
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except ValueError:
            return None
    
    def _parse_response(self, xml_content: str) -> List[Paper]:
        """Parse arXiv API XML response."""
        papers = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # Define namespace
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom",
            }
            
            for entry in root.findall("atom:entry", ns):
                # Extract arXiv ID from id URL
                id_elem = entry.find("atom:id", ns)
                if id_elem is None or id_elem.text is None:
                    continue
                
                arxiv_id = id_elem.text.split("/abs/")[-1]
                
                # Title
                title_elem = entry.find("atom:title", ns)
                title = title_elem.text.strip().replace("\n", " ") if title_elem is not None and title_elem.text else "Untitled"
                
                # Authors
                authors = []
                for author in entry.findall("atom:author", ns):
                    name_elem = author.find("atom:name", ns)
                    if name_elem is not None and name_elem.text:
                        authors.append(name_elem.text)
                
                # Abstract
                summary_elem = entry.find("atom:summary", ns)
                abstract = summary_elem.text.strip().replace("\n", " ") if summary_elem is not None and summary_elem.text else ""
                
                # Dates
                published_elem = entry.find("atom:published", ns)
                published = self._parse_datetime(published_elem.text if published_elem is not None else None) or datetime.now()
                
                updated_elem = entry.find("atom:updated", ns)
                updated = self._parse_datetime(updated_elem.text if updated_elem is not None else None)
                
                # Categories
                categories = []
                for cat in entry.findall("arxiv:primary_category", ns):
                    term = cat.get("term")
                    if term:
                        categories.append(term)
                for cat in entry.findall("atom:category", ns):
                    term = cat.get("term")
                    if term and term not in categories:
                        categories.append(term)
                
                # Links
                pdf_url = None
                html_url = None
                for link in entry.findall("atom:link", ns):
                    href = link.get("href")
                    link_type = link.get("type", "")
                    title_attr = link.get("title", "")
                    
                    if title_attr == "pdf" or "pdf" in link_type:
                        pdf_url = href
                    elif link.get("rel") == "alternate":
                        html_url = href
                
                paper = Paper(
                    arxiv_id=arxiv_id,
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    published=published,
                    updated=updated,
                    categories=categories,
                    pdf_url=pdf_url,
                    html_url=html_url or f"https://arxiv.org/abs/{arxiv_id}",
                )
                papers.append(paper)
                
        except ET.ParseError as e:
            logger.error(f"Failed to parse arXiv response: {e}")
        
        return papers
    
    # =========================================================================
    # Search
    # =========================================================================
    
    async def search(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        max_results: int = 10,
        sort_by: str = "relevance",
    ) -> List[Paper]:
        """
        Search for papers by keywords.
        
        Args:
            query: Search query
            categories: arXiv categories to search (default: ML/AI categories)
            max_results: Maximum results to return
            sort_by: Sort order (relevance, lastUpdatedDate, submittedDate)
            
        Returns:
            List of matching papers
        """
        client = await self._get_client()
        
        # Build search query
        search_query = f"all:{quote(query)}"
        
        # Add category filter
        if categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
            search_query = f"({search_query}) AND ({cat_query})"
        
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": "descending",
        }
        
        try:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            papers = self._parse_response(response.text)
            logger.info(f"arXiv search '{query}' returned {len(papers)} results")
            return papers
            
        except Exception as e:
            logger.error(f"arXiv search failed: {e}")
            return []
    
    async def search_ml(self, query: str, max_results: int = 10) -> List[Paper]:
        """Search in ML/AI categories."""
        return await self.search(
            query,
            categories=self.DEFAULT_CATEGORIES,
            max_results=max_results,
        )
    
    async def search_by_author(
        self,
        author: str,
        max_results: int = 10,
    ) -> List[Paper]:
        """
        Search papers by author name.
        
        Args:
            author: Author name
            max_results: Maximum results
            
        Returns:
            Papers by the author
        """
        client = await self._get_client()
        
        params = {
            "search_query": f"au:{quote(author)}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        
        try:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            return self._parse_response(response.text)
            
        except Exception as e:
            logger.error(f"arXiv author search failed: {e}")
            return []
    
    async def get_paper(self, arxiv_id: str) -> Optional[Paper]:
        """
        Get a specific paper by arXiv ID.
        
        Args:
            arxiv_id: arXiv paper ID (e.g., "2106.09685")
            
        Returns:
            Paper if found
        """
        client = await self._get_client()
        
        # Clean up ID
        arxiv_id = arxiv_id.replace("arXiv:", "").strip()
        
        params = {
            "id_list": arxiv_id,
        }
        
        try:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            papers = self._parse_response(response.text)
            return papers[0] if papers else None
            
        except Exception as e:
            logger.error(f"arXiv get paper failed: {e}")
            return None
    
    async def get_recent(
        self,
        categories: Optional[List[str]] = None,
        max_results: int = 10,
    ) -> List[Paper]:
        """
        Get recent papers in specified categories.
        
        Args:
            categories: arXiv categories (default: ML/AI)
            max_results: Maximum results
            
        Returns:
            Recent papers
        """
        categories = categories or self.DEFAULT_CATEGORIES
        
        client = await self._get_client()
        
        cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
        
        params = {
            "search_query": cat_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        
        try:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            return self._parse_response(response.text)
            
        except Exception as e:
            logger.error(f"arXiv recent papers failed: {e}")
            return []
    
    # =========================================================================
    # Reading List
    # =========================================================================
    
    def add_to_reading_list(self, paper: Paper, notes: Optional[str] = None) -> bool:
        """
        Add a paper to the reading list.
        
        Args:
            paper: Paper to add
            notes: Optional notes
            
        Returns:
            True if added successfully
        """
        authors_str = ", ".join(paper.authors[:5])
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO reading_list 
                    (arxiv_id, title, authors, added_at, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    paper.arxiv_id,
                    paper.title,
                    authors_str,
                    datetime.now().isoformat(),
                    notes,
                ))
                conn.commit()
            
            logger.info(f"Added to reading list: {paper.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add to reading list: {e}")
            return False
    
    def get_reading_list(self, unread_only: bool = False) -> List[ReadingListItem]:
        """Get papers in reading list."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if unread_only:
                rows = conn.execute(
                    "SELECT * FROM reading_list WHERE read = FALSE ORDER BY added_at DESC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM reading_list ORDER BY added_at DESC"
                ).fetchall()
            
            items = []
            for row in rows:
                item = ReadingListItem(
                    id=row["id"],
                    arxiv_id=row["arxiv_id"],
                    title=row["title"],
                    authors=row["authors"],
                    added_at=datetime.fromisoformat(row["added_at"]),
                    read=bool(row["read"]),
                    notes=row["notes"],
                )
                items.append(item)
            
            return items
    
    def mark_as_read(self, arxiv_id: str) -> bool:
        """Mark a paper as read."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE reading_list SET read = TRUE WHERE arxiv_id = ?",
                (arxiv_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def remove_from_reading_list(self, arxiv_id: str) -> bool:
        """Remove a paper from reading list."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM reading_list WHERE arxiv_id = ?",
                (arxiv_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    # =========================================================================
    # Formatting
    # =========================================================================
    
    def format_papers(self, papers: List[Paper], include_abstract: bool = False) -> str:
        """Format papers as readable string."""
        if not papers:
            return "No papers found."
        
        lines = []
        for i, paper in enumerate(papers, 1):
            authors_str = ", ".join(paper.authors[:3])
            if len(paper.authors) > 3:
                authors_str += " et al."
            
            lines.append(f"{i}. {paper.title}")
            lines.append(f"   Authors: {authors_str}")
            lines.append(f"   arXiv: {paper.arxiv_id} | {paper.published.strftime('%b %Y')}")
            
            if include_abstract:
                # Truncate abstract
                abstract = paper.abstract[:300] + "..." if len(paper.abstract) > 300 else paper.abstract
                lines.append(f"   Abstract: {abstract}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def format_reading_list(self, items: List[ReadingListItem]) -> str:
        """Format reading list as readable string."""
        if not items:
            return "Your reading list is empty."
        
        lines = ["📚 Reading List:"]
        for item in items:
            status = "✓" if item.read else "○"
            lines.append(f"  {status} {item.title}")
            lines.append(f"    {item.authors}")
            if item.notes:
                lines.append(f"    Notes: {item.notes}")
        
        return "\n".join(lines)
    
    def summarize_abstract(self, paper: Paper) -> str:
        """Get a summary-ready abstract (for LLM processing)."""
        return f"""
Paper: {paper.title}
Authors: {', '.join(paper.authors)}
arXiv ID: {paper.arxiv_id}
Published: {paper.published.strftime('%B %Y')}

Abstract:
{paper.abstract}
"""
