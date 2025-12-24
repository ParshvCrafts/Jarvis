"""
Scholarly Search Engine for JARVIS Research Module.

Integrates multiple FREE academic APIs:
- Semantic Scholar (CS, AI, ML papers)
- OpenAlex (All disciplines)
- arXiv (Preprints, technical papers)
- CrossRef (DOI lookup, citation metadata)
"""

import asyncio
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx
from loguru import logger


class SearchDatabase(Enum):
    """Available academic databases."""
    SEMANTIC_SCHOLAR = "semantic_scholar"
    OPENALEX = "openalex"
    ARXIV = "arxiv"
    CROSSREF = "crossref"


@dataclass
class Author:
    """Paper author."""
    name: str
    affiliation: Optional[str] = None
    orcid: Optional[str] = None


@dataclass
class Paper:
    """Academic paper metadata."""
    title: str
    authors: List[Author]
    year: Optional[int]
    abstract: Optional[str]
    doi: Optional[str] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    citation_count: int = 0
    source_database: SearchDatabase = SearchDatabase.SEMANTIC_SCHOLAR
    venue: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    is_open_access: bool = False
    paper_id: Optional[str] = None  # Database-specific ID
    
    def __str__(self) -> str:
        authors_str = ", ".join(a.name for a in self.authors[:3])
        if len(self.authors) > 3:
            authors_str += " et al."
        return f"{authors_str} ({self.year}). {self.title}"


class SemanticScholarClient:
    """
    Semantic Scholar API client.
    
    Free API with 100 requests per 5 minutes.
    Best for: CS, AI, ML papers.
    
    Docs: https://api.semanticscholar.org/
    """
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize client with optional API key for higher rate limits."""
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None
        self._request_count = 0
        self._window_start = datetime.now()
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["x-api-key"] = self.api_key
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=headers,
                timeout=30.0,
            )
        return self._client
    
    async def _check_rate_limit(self):
        """Check and handle rate limiting."""
        now = datetime.now()
        elapsed = (now - self._window_start).total_seconds()
        
        if elapsed > 300:  # 5 minute window
            self._request_count = 0
            self._window_start = now
        
        if self._request_count >= 95:  # Leave buffer
            wait_time = 300 - elapsed
            if wait_time > 0:
                logger.warning(f"Rate limit approaching, waiting {wait_time:.0f}s")
                await asyncio.sleep(wait_time)
                self._request_count = 0
                self._window_start = datetime.now()
        
        self._request_count += 1
    
    async def search(
        self,
        query: str,
        limit: int = 20,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        fields_of_study: Optional[List[str]] = None,
    ) -> List[Paper]:
        """
        Search for papers.
        
        Args:
            query: Search query
            limit: Maximum results (max 100)
            year_start: Filter by start year
            year_end: Filter by end year
            fields_of_study: Filter by fields (e.g., ["Computer Science"])
            
        Returns:
            List of Paper objects
        """
        await self._check_rate_limit()
        client = await self._get_client()
        
        # Build query parameters
        params = {
            "query": query,
            "limit": min(limit, 100),
            "fields": "title,abstract,year,citationCount,authors,url,openAccessPdf,venue,fieldsOfStudy,externalIds",
        }
        
        # Add year filter
        if year_start or year_end:
            year_filter = ""
            if year_start:
                year_filter += f"{year_start}-"
            else:
                year_filter += "-"
            if year_end:
                year_filter += str(year_end)
            params["year"] = year_filter
        
        # Add field of study filter
        if fields_of_study:
            params["fieldsOfStudy"] = ",".join(fields_of_study)
        
        try:
            response = await client.get("/paper/search", params=params)
            response.raise_for_status()
            data = response.json()
            
            papers = []
            for item in data.get("data", []):
                paper = self._parse_paper(item)
                if paper:
                    papers.append(paper)
            
            logger.info(f"Semantic Scholar: Found {len(papers)} papers for '{query}'")
            return papers
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Semantic Scholar API error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            return []
    
    def _parse_paper(self, data: Dict[str, Any]) -> Optional[Paper]:
        """Parse API response into Paper object."""
        try:
            # Parse authors
            authors = []
            for author_data in data.get("authors", []):
                authors.append(Author(
                    name=author_data.get("name", "Unknown"),
                ))
            
            # Get PDF URL if open access
            pdf_url = None
            oa_pdf = data.get("openAccessPdf")
            if oa_pdf:
                pdf_url = oa_pdf.get("url")
            
            # Get DOI
            doi = None
            external_ids = data.get("externalIds", {})
            if external_ids:
                doi = external_ids.get("DOI")
            
            return Paper(
                title=data.get("title", ""),
                authors=authors,
                year=data.get("year"),
                abstract=data.get("abstract"),
                doi=doi,
                url=data.get("url"),
                pdf_url=pdf_url,
                citation_count=data.get("citationCount", 0),
                source_database=SearchDatabase.SEMANTIC_SCHOLAR,
                venue=data.get("venue"),
                keywords=data.get("fieldsOfStudy", []) or [],
                is_open_access=pdf_url is not None,
                paper_id=data.get("paperId"),
            )
        except Exception as e:
            logger.debug(f"Failed to parse paper: {e}")
            return None
    
    async def get_paper(self, paper_id: str) -> Optional[Paper]:
        """Get paper by Semantic Scholar ID."""
        await self._check_rate_limit()
        client = await self._get_client()
        
        try:
            response = await client.get(
                f"/paper/{paper_id}",
                params={"fields": "title,abstract,year,citationCount,authors,url,openAccessPdf,venue,fieldsOfStudy,externalIds"}
            )
            response.raise_for_status()
            return self._parse_paper(response.json())
        except Exception as e:
            logger.error(f"Failed to get paper {paper_id}: {e}")
            return None
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class OpenAlexClient:
    """
    OpenAlex API client.
    
    Free API with 100K requests/day.
    Best for: All academic disciplines.
    
    Docs: https://docs.openalex.org/
    """
    
    BASE_URL = "https://api.openalex.org"
    
    def __init__(self, email: Optional[str] = None):
        """Initialize client with optional email for polite pool."""
        self.email = email
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {"Content-Type": "application/json"}
            if self.email:
                headers["User-Agent"] = f"mailto:{self.email}"
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=headers,
                timeout=30.0,
            )
        return self._client
    
    async def search(
        self,
        query: str,
        limit: int = 25,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        sort_by_citations: bool = True,
    ) -> List[Paper]:
        """
        Search for works.
        
        Args:
            query: Search query
            limit: Maximum results (max 200)
            year_start: Filter by start year
            year_end: Filter by end year
            sort_by_citations: Sort by citation count
            
        Returns:
            List of Paper objects
        """
        client = await self._get_client()
        
        # Build query parameters
        params = {
            "search": query,
            "per-page": min(limit, 200),
        }
        
        if sort_by_citations:
            params["sort"] = "cited_by_count:desc"
        
        # Build filter
        filters = []
        if year_start:
            filters.append(f"publication_year:>{year_start-1}")
        if year_end:
            filters.append(f"publication_year:<{year_end+1}")
        
        if filters:
            params["filter"] = ",".join(filters)
        
        try:
            response = await client.get("/works", params=params)
            response.raise_for_status()
            data = response.json()
            
            papers = []
            for item in data.get("results", []):
                paper = self._parse_work(item)
                if paper:
                    papers.append(paper)
            
            logger.info(f"OpenAlex: Found {len(papers)} papers for '{query}'")
            return papers
            
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAlex API error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"OpenAlex search failed: {e}")
            return []
    
    def _parse_work(self, data: Dict[str, Any]) -> Optional[Paper]:
        """Parse API response into Paper object."""
        try:
            # Parse authors
            authors = []
            for authorship in data.get("authorships", [])[:10]:
                author_data = authorship.get("author", {})
                institution = None
                institutions = authorship.get("institutions", [])
                if institutions:
                    institution = institutions[0].get("display_name")
                authors.append(Author(
                    name=author_data.get("display_name", "Unknown"),
                    affiliation=institution,
                    orcid=author_data.get("orcid"),
                ))
            
            # Get best open access URL
            pdf_url = None
            oa_url = data.get("open_access", {}).get("oa_url")
            if oa_url:
                pdf_url = oa_url
            
            # Get primary location URL
            url = None
            primary_location = data.get("primary_location", {})
            if primary_location:
                url = primary_location.get("landing_page_url")
            
            # Get DOI
            doi = data.get("doi")
            if doi and doi.startswith("https://doi.org/"):
                doi = doi.replace("https://doi.org/", "")
            
            # Get keywords from concepts
            keywords = []
            for concept in data.get("concepts", [])[:5]:
                keywords.append(concept.get("display_name", ""))
            
            return Paper(
                title=data.get("title", ""),
                authors=authors,
                year=data.get("publication_year"),
                abstract=data.get("abstract"),
                doi=doi,
                url=url,
                pdf_url=pdf_url,
                citation_count=data.get("cited_by_count", 0),
                source_database=SearchDatabase.OPENALEX,
                venue=primary_location.get("source", {}).get("display_name") if primary_location else None,
                keywords=keywords,
                is_open_access=data.get("open_access", {}).get("is_oa", False),
                paper_id=data.get("id"),
            )
        except Exception as e:
            logger.debug(f"Failed to parse work: {e}")
            return None
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class ArxivClient:
    """
    arXiv API client.
    
    Free API with no key required.
    Best for: Preprints, technical papers in science/math/CS.
    
    Docs: https://arxiv.org/help/api/
    """
    
    BASE_URL = "http://export.arxiv.org/api/query"
    
    def __init__(self):
        """Initialize client."""
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def search(
        self,
        query: str,
        limit: int = 20,
        sort_by: str = "relevance",
        categories: Optional[List[str]] = None,
    ) -> List[Paper]:
        """
        Search for papers.
        
        Args:
            query: Search query
            limit: Maximum results
            sort_by: Sort order (relevance, lastUpdatedDate, submittedDate)
            categories: Filter by arXiv categories (e.g., ["cs.AI", "cs.LG"])
            
        Returns:
            List of Paper objects
        """
        client = await self._get_client()
        
        # Build search query
        search_query = f"all:{quote_plus(query)}"
        if categories:
            cat_query = " OR ".join(f"cat:{cat}" for cat in categories)
            search_query = f"({search_query}) AND ({cat_query})"
        
        params = {
            "search_query": search_query,
            "max_results": limit,
            "sortBy": sort_by,
            "sortOrder": "descending",
        }
        
        try:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            papers = self._parse_response(response.text)
            logger.info(f"arXiv: Found {len(papers)} papers for '{query}'")
            return papers
            
        except httpx.HTTPStatusError as e:
            logger.error(f"arXiv API error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"arXiv search failed: {e}")
            return []
    
    def _parse_response(self, xml_text: str) -> List[Paper]:
        """Parse arXiv XML response."""
        papers = []
        
        try:
            root = ET.fromstring(xml_text)
            ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
            
            for entry in root.findall("atom:entry", ns):
                paper = self._parse_entry(entry, ns)
                if paper:
                    papers.append(paper)
        except Exception as e:
            logger.error(f"Failed to parse arXiv response: {e}")
        
        return papers
    
    def _parse_entry(self, entry: ET.Element, ns: Dict[str, str]) -> Optional[Paper]:
        """Parse single arXiv entry."""
        try:
            # Get title
            title_elem = entry.find("atom:title", ns)
            title = title_elem.text.strip().replace("\n", " ") if title_elem is not None else ""
            
            # Get authors
            authors = []
            for author_elem in entry.findall("atom:author", ns):
                name_elem = author_elem.find("atom:name", ns)
                if name_elem is not None:
                    authors.append(Author(name=name_elem.text))
            
            # Get abstract
            abstract_elem = entry.find("atom:summary", ns)
            abstract = abstract_elem.text.strip().replace("\n", " ") if abstract_elem is not None else None
            
            # Get published date
            published_elem = entry.find("atom:published", ns)
            year = None
            if published_elem is not None:
                year = int(published_elem.text[:4])
            
            # Get URLs
            url = None
            pdf_url = None
            for link in entry.findall("atom:link", ns):
                link_type = link.get("type", "")
                link_title = link.get("title", "")
                href = link.get("href", "")
                
                if link_title == "pdf" or link_type == "application/pdf":
                    pdf_url = href
                elif link_type == "text/html":
                    url = href
            
            # Get arXiv ID
            id_elem = entry.find("atom:id", ns)
            paper_id = None
            if id_elem is not None:
                paper_id = id_elem.text.split("/abs/")[-1]
            
            # Get categories
            keywords = []
            for category in entry.findall("arxiv:primary_category", ns):
                keywords.append(category.get("term", ""))
            for category in entry.findall("atom:category", ns):
                term = category.get("term", "")
                if term and term not in keywords:
                    keywords.append(term)
            
            return Paper(
                title=title,
                authors=authors,
                year=year,
                abstract=abstract,
                doi=None,  # arXiv papers may not have DOI
                url=url,
                pdf_url=pdf_url,
                citation_count=0,  # arXiv doesn't provide this
                source_database=SearchDatabase.ARXIV,
                venue="arXiv",
                keywords=keywords[:5],
                is_open_access=True,  # All arXiv papers are open access
                paper_id=paper_id,
            )
        except Exception as e:
            logger.debug(f"Failed to parse arXiv entry: {e}")
            return None
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class CrossRefClient:
    """
    CrossRef API client.
    
    Free API with no key required.
    Best for: DOI lookup, citation metadata, accurate bibliographic info.
    
    Docs: https://api.crossref.org/swagger-ui/index.html
    """
    
    BASE_URL = "https://api.crossref.org"
    
    def __init__(self, email: Optional[str] = None):
        """Initialize client with optional email for polite pool."""
        self.email = email
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {"Content-Type": "application/json"}
            if self.email:
                headers["User-Agent"] = f"JARVIS/2.0 (mailto:{self.email})"
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=headers,
                timeout=30.0,
            )
        return self._client
    
    async def search(
        self,
        query: str,
        limit: int = 20,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
    ) -> List[Paper]:
        """
        Search for works.
        
        Args:
            query: Search query
            limit: Maximum results
            year_start: Filter by start year
            year_end: Filter by end year
            
        Returns:
            List of Paper objects
        """
        client = await self._get_client()
        
        params = {
            "query": query,
            "rows": limit,
            "sort": "relevance",
        }
        
        # Add date filter
        if year_start or year_end:
            filter_parts = []
            if year_start:
                filter_parts.append(f"from-pub-date:{year_start}")
            if year_end:
                filter_parts.append(f"until-pub-date:{year_end}")
            params["filter"] = ",".join(filter_parts)
        
        try:
            response = await client.get("/works", params=params)
            response.raise_for_status()
            data = response.json()
            
            papers = []
            for item in data.get("message", {}).get("items", []):
                paper = self._parse_work(item)
                if paper:
                    papers.append(paper)
            
            logger.info(f"CrossRef: Found {len(papers)} papers for '{query}'")
            return papers
            
        except httpx.HTTPStatusError as e:
            logger.error(f"CrossRef API error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"CrossRef search failed: {e}")
            return []
    
    async def get_by_doi(self, doi: str) -> Optional[Paper]:
        """
        Get paper metadata by DOI.
        
        Args:
            doi: Digital Object Identifier
            
        Returns:
            Paper object or None
        """
        client = await self._get_client()
        
        # Clean DOI
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        
        try:
            response = await client.get(f"/works/{doi}")
            response.raise_for_status()
            data = response.json()
            return self._parse_work(data.get("message", {}))
        except Exception as e:
            logger.error(f"Failed to get DOI {doi}: {e}")
            return None
    
    def _parse_work(self, data: Dict[str, Any]) -> Optional[Paper]:
        """Parse CrossRef work into Paper object."""
        try:
            # Get title
            titles = data.get("title", [])
            title = titles[0] if titles else ""
            
            # Parse authors
            authors = []
            for author_data in data.get("author", []):
                name_parts = []
                if author_data.get("given"):
                    name_parts.append(author_data["given"])
                if author_data.get("family"):
                    name_parts.append(author_data["family"])
                
                if name_parts:
                    authors.append(Author(
                        name=" ".join(name_parts),
                        affiliation=author_data.get("affiliation", [{}])[0].get("name") if author_data.get("affiliation") else None,
                        orcid=author_data.get("ORCID"),
                    ))
            
            # Get year
            year = None
            published = data.get("published", {}).get("date-parts", [[]])
            if published and published[0]:
                year = published[0][0]
            
            # Get abstract
            abstract = data.get("abstract", "")
            if abstract:
                # Clean HTML tags from abstract
                import re
                abstract = re.sub(r'<[^>]+>', '', abstract)
            
            # Get URL
            url = data.get("URL")
            
            # Get venue
            venue = None
            container = data.get("container-title", [])
            if container:
                venue = container[0]
            
            return Paper(
                title=title,
                authors=authors,
                year=year,
                abstract=abstract if abstract else None,
                doi=data.get("DOI"),
                url=url,
                pdf_url=None,
                citation_count=data.get("is-referenced-by-count", 0),
                source_database=SearchDatabase.CROSSREF,
                venue=venue,
                keywords=[],
                is_open_access=False,
                paper_id=data.get("DOI"),
            )
        except Exception as e:
            logger.debug(f"Failed to parse CrossRef work: {e}")
            return None
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


@dataclass
class SearchResult:
    """Result from a search operation with status."""
    database: SearchDatabase
    papers: List[Paper]
    success: bool
    error: Optional[str] = None
    response_time_ms: float = 0.0


class ScholarlySearch:
    """
    Unified scholarly search across multiple databases.
    
    Aggregates results from:
    - Semantic Scholar
    - OpenAlex
    - arXiv
    - CrossRef
    
    Features:
    - Parallel search across all databases
    - Automatic fallback if one API fails
    - Rate limit handling
    - Deduplication
    - Status reporting
    """
    
    def __init__(
        self,
        semantic_scholar_key: Optional[str] = None,
        email: Optional[str] = None,
        core_api_key: Optional[str] = None,
    ):
        """
        Initialize unified search.
        
        Args:
            semantic_scholar_key: Optional API key for higher rate limits
            email: Email for polite pool access
            core_api_key: Optional CORE API key
        """
        self.semantic_scholar = SemanticScholarClient(api_key=semantic_scholar_key)
        self.openalex = OpenAlexClient(email=email)
        self.arxiv = ArxivClient()
        self.crossref = CrossRefClient(email=email)
        self.core_api_key = core_api_key
        
        # Track API status
        self._api_status: Dict[SearchDatabase, bool] = {
            SearchDatabase.SEMANTIC_SCHOLAR: True,
            SearchDatabase.OPENALEX: True,
            SearchDatabase.ARXIV: True,
            SearchDatabase.CROSSREF: True,
        }
        self._last_search_results: List[SearchResult] = []
    
    async def search_all(
        self,
        query: str,
        limit_per_source: int = 15,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        databases: Optional[List[SearchDatabase]] = None,
    ) -> List[Paper]:
        """
        Search all databases in parallel.
        
        Args:
            query: Search query
            limit_per_source: Max results per database
            year_start: Filter by start year
            year_end: Filter by end year
            databases: Specific databases to search (default: all)
            
        Returns:
            Combined list of papers (deduplicated by title similarity)
        """
        if databases is None:
            databases = list(SearchDatabase)
        
        # Create search tasks with database tracking
        import time
        
        async def timed_search(db: SearchDatabase, coro) -> SearchResult:
            """Wrap search with timing and error handling."""
            start = time.time()
            try:
                papers = await coro
                elapsed = (time.time() - start) * 1000
                self._api_status[db] = True
                return SearchResult(
                    database=db,
                    papers=papers,
                    success=True,
                    response_time_ms=elapsed,
                )
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                self._api_status[db] = False
                logger.warning(f"{db.value} search failed: {e}")
                return SearchResult(
                    database=db,
                    papers=[],
                    success=False,
                    error=str(e),
                    response_time_ms=elapsed,
                )
        
        tasks = []
        
        if SearchDatabase.SEMANTIC_SCHOLAR in databases:
            tasks.append(timed_search(
                SearchDatabase.SEMANTIC_SCHOLAR,
                self.semantic_scholar.search(
                    query, limit=limit_per_source,
                    year_start=year_start, year_end=year_end
                )
            ))
        
        if SearchDatabase.OPENALEX in databases:
            tasks.append(timed_search(
                SearchDatabase.OPENALEX,
                self.openalex.search(
                    query, limit=limit_per_source,
                    year_start=year_start, year_end=year_end
                )
            ))
        
        if SearchDatabase.ARXIV in databases:
            tasks.append(timed_search(
                SearchDatabase.ARXIV,
                self.arxiv.search(query, limit=limit_per_source)
            ))
        
        if SearchDatabase.CROSSREF in databases:
            tasks.append(timed_search(
                SearchDatabase.CROSSREF,
                self.crossref.search(
                    query, limit=limit_per_source,
                    year_start=year_start, year_end=year_end
                )
            ))
        
        # Run searches in parallel
        self._last_search_results = await asyncio.gather(*tasks)
        
        # Combine results
        all_papers = []
        successful_dbs = []
        failed_dbs = []
        
        for result in self._last_search_results:
            if result.success:
                all_papers.extend(result.papers)
                successful_dbs.append(result.database.value)
            else:
                failed_dbs.append(result.database.value)
        
        # Log status
        if failed_dbs:
            logger.warning(f"Some APIs failed: {', '.join(failed_dbs)}. Used: {', '.join(successful_dbs)}")
        
        # Deduplicate by title similarity
        unique_papers = self._deduplicate(all_papers)
        
        logger.info(f"Total unique papers found: {len(unique_papers)} from {len(successful_dbs)} databases")
        return unique_papers
    
    def get_search_status(self) -> str:
        """Get status of last search operation."""
        if not self._last_search_results:
            return "No searches performed yet."
        
        lines = ["**Search Status:**"]
        for result in self._last_search_results:
            status = "✅" if result.success else "❌"
            papers = f"{len(result.papers)} papers" if result.success else result.error
            lines.append(f"  {status} {result.database.value}: {papers} ({result.response_time_ms:.0f}ms)")
        
        return "\n".join(lines)
    
    def get_api_health(self) -> Dict[str, bool]:
        """Get health status of all APIs."""
        return {db.value: status for db, status in self._api_status.items()}
    
    def _deduplicate(self, papers: List[Paper]) -> List[Paper]:
        """Remove duplicate papers based on title similarity."""
        seen_titles = set()
        unique = []
        
        for paper in papers:
            # Normalize title for comparison
            normalized = paper.title.lower().strip()
            normalized = "".join(c for c in normalized if c.isalnum() or c.isspace())
            normalized = " ".join(normalized.split())
            
            # Check if similar title exists
            is_duplicate = False
            for seen in seen_titles:
                if self._title_similarity(normalized, seen) > 0.85:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_titles.add(normalized)
                unique.append(paper)
        
        return unique
    
    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate simple title similarity."""
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    async def get_by_doi(self, doi: str) -> Optional[Paper]:
        """Get paper by DOI using CrossRef."""
        return await self.crossref.get_by_doi(doi)
    
    async def close(self):
        """Close all clients."""
        await asyncio.gather(
            self.semantic_scholar.close(),
            self.openalex.close(),
            self.arxiv.close(),
            self.crossref.close(),
        )
