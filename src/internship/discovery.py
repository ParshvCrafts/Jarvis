"""
Internship Discovery for JARVIS Internship Automation Module.

Multi-source job search integrating:
- Adzuna API
- The Muse API
- RemoteOK API
- JSearch (RapidAPI)
- Tavily/Serper web search
"""

import asyncio
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus

from loguru import logger

from .models import (
    InternshipListing,
    JobType,
    LocationType,
    UserProfile,
)

# Try importing HTTP client
HTTPX_AVAILABLE = False
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    logger.debug("httpx not installed - using requests")
    try:
        import requests
    except ImportError:
        logger.warning("Neither httpx nor requests installed")

# Try importing Tavily
TAVILY_AVAILABLE = False
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    logger.debug("tavily not installed")


@dataclass
class SearchCriteria:
    """Search criteria for internship discovery."""
    query: str = "data science intern"
    location: str = "remote"
    job_type: JobType = JobType.INTERNSHIP
    keywords: List[str] = None
    posted_within_days: int = 30
    min_salary: int = 0
    max_results: int = 50
    company: Optional[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = ["python", "machine learning", "data analysis"]


class InternshipDiscovery:
    """
    Discover internships from multiple sources.
    
    Sources:
    - Adzuna (API key required)
    - The Muse (free, no key)
    - RemoteOK (free, no key)
    - JSearch via RapidAPI (API key required)
    - Tavily/Serper web search
    """
    
    def __init__(
        self,
        profile: Optional[UserProfile] = None,
        adzuna_app_id: Optional[str] = None,
        adzuna_api_key: Optional[str] = None,
        rapidapi_key: Optional[str] = None,
        tavily_api_key: Optional[str] = None,
        serper_api_key: Optional[str] = None,
    ):
        self.profile = profile or UserProfile()
        
        # API credentials
        self.adzuna_app_id = adzuna_app_id or os.getenv("ADZUNA_APP_ID")
        self.adzuna_api_key = adzuna_api_key or os.getenv("ADZUNA_API_KEY")
        self.rapidapi_key = rapidapi_key or os.getenv("RAPIDAPI_KEY")
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        self.serper_api_key = serper_api_key or os.getenv("SERPER_API_KEY")
        
        # Initialize Tavily client
        self._tavily_client = None
        if TAVILY_AVAILABLE and self.tavily_api_key:
            try:
                self._tavily_client = TavilyClient(api_key=self.tavily_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Tavily: {e}")
        
        # HTTP client
        self._client = None
    
    def _get_client(self):
        """Get HTTP client."""
        if self._client is None:
            if HTTPX_AVAILABLE:
                self._client = httpx.AsyncClient(timeout=30.0)
            else:
                self._client = requests
        return self._client
    
    async def _async_get(self, url: str, headers: Dict = None, params: Dict = None) -> Dict:
        """Make async GET request."""
        try:
            if HTTPX_AVAILABLE:
                client = self._get_client()
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                return response.json()
            else:
                # Fallback to sync requests
                import requests
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            return {}
    
    # =========================================================================
    # Adzuna API
    # =========================================================================
    
    async def search_adzuna(
        self,
        query: str,
        location: str = "us",
        max_results: int = 50,
    ) -> List[InternshipListing]:
        """
        Search Adzuna for internships.
        
        API: https://developer.adzuna.com/
        Free tier: 250 requests/day
        """
        if not self.adzuna_app_id or not self.adzuna_api_key:
            logger.debug("Adzuna credentials not configured")
            return []
        
        listings = []
        
        try:
            # Adzuna API endpoint
            url = f"https://api.adzuna.com/v1/api/jobs/{location}/search/1"
            
            params = {
                "app_id": self.adzuna_app_id,
                "app_key": self.adzuna_api_key,
                "results_per_page": min(max_results, 50),
                "what": query,
                "what_or": "intern internship",
                "max_days_old": 30,
                "sort_by": "relevance",
            }
            
            data = await self._async_get(url, params=params)
            
            for job in data.get("results", []):
                listing = InternshipListing(
                    company=job.get("company", {}).get("display_name", "Unknown"),
                    role=job.get("title", ""),
                    location=job.get("location", {}).get("display_name", ""),
                    location_type=self._detect_location_type(job.get("location", {}).get("display_name", "")),
                    description=job.get("description", ""),
                    salary_min=int(job.get("salary_min", 0)) if job.get("salary_min") else None,
                    salary_max=int(job.get("salary_max", 0)) if job.get("salary_max") else None,
                    url=job.get("redirect_url", ""),
                    source_api="adzuna",
                    source_id=job.get("id", ""),
                    posted_date=self._parse_date(job.get("created")),
                )
                listings.append(listing)
            
            logger.info(f"Adzuna returned {len(listings)} internships")
            
        except Exception as e:
            logger.error(f"Adzuna search failed: {e}")
        
        return listings
    
    # =========================================================================
    # The Muse API
    # =========================================================================
    
    async def search_themuse(
        self,
        query: str = "",
        location: str = "",
        max_results: int = 50,
    ) -> List[InternshipListing]:
        """
        Search The Muse for internships.
        
        API: https://www.themuse.com/developers/api/v2
        Free, no API key required for basic access.
        """
        listings = []
        
        try:
            url = "https://www.themuse.com/api/public/jobs"
            
            params = {
                "page": 0,
                "descending": "true",
            }
            
            # Add category filter for internships
            if "intern" in query.lower():
                params["category"] = "Data Science"
                params["level"] = "Internship"
            
            if location:
                params["location"] = location
            
            data = await self._async_get(url, params=params)
            
            for job in data.get("results", [])[:max_results]:
                # Extract location
                locations = job.get("locations", [])
                location_str = locations[0].get("name", "") if locations else ""
                
                # Extract company info
                company_info = job.get("company", {})
                
                listing = InternshipListing(
                    company=company_info.get("name", "Unknown"),
                    role=job.get("name", ""),
                    location=location_str,
                    location_type=self._detect_location_type(location_str),
                    description=job.get("contents", ""),
                    url=f"https://www.themuse.com/jobs/{job.get('id', '')}",
                    source_api="themuse",
                    source_id=str(job.get("id", "")),
                    posted_date=self._parse_date(job.get("publication_date")),
                )
                
                # Extract levels
                levels = job.get("levels", [])
                if any("intern" in l.get("name", "").lower() for l in levels):
                    listing.job_type = JobType.INTERNSHIP
                
                listings.append(listing)
            
            logger.info(f"The Muse returned {len(listings)} jobs")
            
        except Exception as e:
            logger.error(f"The Muse search failed: {e}")
        
        return listings
    
    # =========================================================================
    # RemoteOK API
    # =========================================================================
    
    async def search_remoteok(
        self,
        query: str = "",
        max_results: int = 50,
    ) -> List[InternshipListing]:
        """
        Search RemoteOK for remote internships.
        
        API: https://remoteok.com/api
        Free, no API key required.
        """
        listings = []
        
        try:
            # RemoteOK returns JSON array
            url = "https://remoteok.com/api"
            
            headers = {
                "User-Agent": "JARVIS/1.0"
            }
            
            data = await self._async_get(url, headers=headers)
            
            # First item is metadata, skip it
            jobs = data[1:] if isinstance(data, list) and len(data) > 1 else []
            
            # Filter by query
            query_lower = query.lower()
            keywords = query_lower.split()
            
            for job in jobs[:max_results * 2]:  # Get more to filter
                if not isinstance(job, dict):
                    continue
                
                # Check if matches query
                job_text = f"{job.get('position', '')} {job.get('description', '')} {' '.join(job.get('tags', []))}".lower()
                
                if query and not any(kw in job_text for kw in keywords):
                    continue
                
                # Check for internship
                is_intern = "intern" in job_text
                
                listing = InternshipListing(
                    company=job.get("company", "Unknown"),
                    role=job.get("position", ""),
                    location="Remote",
                    location_type=LocationType.REMOTE,
                    job_type=JobType.INTERNSHIP if is_intern else JobType.FULL_TIME,
                    description=job.get("description", ""),
                    url=job.get("url", ""),
                    application_url=job.get("apply_url", ""),
                    source_api="remoteok",
                    source_id=str(job.get("id", "")),
                    keywords=job.get("tags", []),
                    posted_date=self._parse_timestamp(job.get("epoch")),
                )
                
                # Salary
                salary = job.get("salary_min")
                if salary:
                    listing.salary_min = int(salary)
                    listing.salary_type = "annual"
                
                listings.append(listing)
                
                if len(listings) >= max_results:
                    break
            
            logger.info(f"RemoteOK returned {len(listings)} jobs")
            
        except Exception as e:
            logger.error(f"RemoteOK search failed: {e}")
        
        return listings
    
    # =========================================================================
    # JSearch (RapidAPI)
    # =========================================================================
    
    async def search_jsearch(
        self,
        query: str,
        location: str = "",
        max_results: int = 50,
    ) -> List[InternshipListing]:
        """
        Search JSearch via RapidAPI.
        
        Aggregates LinkedIn, Indeed, Glassdoor, etc.
        Free tier: 500 requests/month
        """
        if not self.rapidapi_key:
            logger.debug("RapidAPI key not configured")
            return []
        
        listings = []
        
        try:
            url = "https://jsearch.p.rapidapi.com/search"
            
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
            }
            
            params = {
                "query": f"{query} {location}".strip(),
                "page": "1",
                "num_pages": "1",
                "employment_types": "INTERN",
            }
            
            data = await self._async_get(url, headers=headers, params=params)
            
            for job in data.get("data", [])[:max_results]:
                listing = InternshipListing(
                    company=job.get("employer_name", "Unknown"),
                    role=job.get("job_title", ""),
                    location=f"{job.get('job_city', '')}, {job.get('job_state', '')}".strip(", "),
                    location_type=LocationType.REMOTE if job.get("job_is_remote") else LocationType.ONSITE,
                    job_type=JobType.INTERNSHIP,
                    description=job.get("job_description", ""),
                    url=job.get("job_apply_link", ""),
                    application_url=job.get("job_apply_link", ""),
                    source_api="jsearch",
                    source_id=job.get("job_id", ""),
                    posted_date=self._parse_date(job.get("job_posted_at_datetime_utc")),
                )
                
                # Salary
                if job.get("job_min_salary"):
                    listing.salary_min = int(job.get("job_min_salary"))
                if job.get("job_max_salary"):
                    listing.salary_max = int(job.get("job_max_salary"))
                
                # Requirements
                highlights = job.get("job_highlights", {})
                if highlights.get("Qualifications"):
                    listing.requirements = highlights["Qualifications"]
                if highlights.get("Responsibilities"):
                    listing.responsibilities = highlights["Responsibilities"]
                
                listings.append(listing)
            
            logger.info(f"JSearch returned {len(listings)} internships")
            
        except Exception as e:
            logger.error(f"JSearch search failed: {e}")
        
        return listings
    
    # =========================================================================
    # Tavily Web Search
    # =========================================================================
    
    async def search_tavily(
        self,
        query: str,
        max_results: int = 20,
    ) -> List[InternshipListing]:
        """
        Search for internships using Tavily web search.
        
        Good for finding specific company internships.
        """
        if not self._tavily_client:
            logger.debug("Tavily not available")
            return []
        
        listings = []
        
        try:
            # Construct search query
            search_query = f"{query} internship application 2025"
            
            response = self._tavily_client.search(
                query=search_query,
                search_depth="advanced",
                max_results=max_results,
            )
            
            for result in response.get("results", []):
                # Try to extract company and role from title
                title = result.get("title", "")
                url = result.get("url", "")
                content = result.get("content", "")
                
                # Parse title for company/role
                company, role = self._parse_job_title(title)
                
                if not company or not role:
                    continue
                
                listing = InternshipListing(
                    company=company,
                    role=role,
                    description=content,
                    url=url,
                    source_api="tavily",
                    source_id=url,
                    location_type=LocationType.REMOTE if "remote" in content.lower() else LocationType.ONSITE,
                )
                
                listings.append(listing)
            
            logger.info(f"Tavily returned {len(listings)} results")
            
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
        
        return listings
    
    # =========================================================================
    # Serper Web Search
    # =========================================================================
    
    async def search_serper(
        self,
        query: str,
        max_results: int = 20,
    ) -> List[InternshipListing]:
        """Search for internships using Serper (Google Search API)."""
        if not self.serper_api_key:
            logger.debug("Serper API key not configured")
            return []
        
        listings = []
        
        try:
            url = "https://google.serper.dev/search"
            
            headers = {
                "X-API-KEY": self.serper_api_key,
                "Content-Type": "application/json"
            }
            
            search_query = f"{query} internship apply 2025"
            
            if HTTPX_AVAILABLE:
                client = self._get_client()
                response = await client.post(
                    url,
                    headers=headers,
                    json={"q": search_query, "num": max_results}
                )
                data = response.json()
            else:
                import requests
                response = requests.post(
                    url,
                    headers=headers,
                    json={"q": search_query, "num": max_results},
                    timeout=30
                )
                data = response.json()
            
            for result in data.get("organic", []):
                title = result.get("title", "")
                url = result.get("link", "")
                snippet = result.get("snippet", "")
                
                company, role = self._parse_job_title(title)
                
                if not company:
                    continue
                
                listing = InternshipListing(
                    company=company,
                    role=role or "Internship",
                    description=snippet,
                    url=url,
                    source_api="serper",
                    source_id=url,
                )
                
                listings.append(listing)
            
            logger.info(f"Serper returned {len(listings)} results")
            
        except Exception as e:
            logger.error(f"Serper search failed: {e}")
        
        return listings
    
    # =========================================================================
    # Main Search Methods
    # =========================================================================
    
    async def search(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        company: Optional[str] = None,
        max_results: int = 50,
        sources: Optional[List[str]] = None,
    ) -> List[InternshipListing]:
        """
        Search for internships across all configured sources.
        
        Args:
            query: Search query (e.g., "data science intern")
            location: Location filter
            company: Specific company to search
            max_results: Maximum results per source
            sources: List of sources to use (default: all available)
            
        Returns:
            List of InternshipListing objects
        """
        # Build query
        if not query:
            query = " ".join(self.profile.target_roles[:2])
        
        if company:
            query = f"{company} {query}"
        
        if not location:
            location = self.profile.preferred_location.value
        
        # Determine sources
        if sources is None:
            sources = ["remoteok", "themuse", "tavily", "serper"]
            if self.adzuna_app_id:
                sources.append("adzuna")
            if self.rapidapi_key:
                sources.append("jsearch")
        
        logger.info(f"Searching for: {query} in {location}")
        
        # Search all sources concurrently
        tasks = []
        
        if "adzuna" in sources:
            tasks.append(self.search_adzuna(query, "us", max_results))
        if "themuse" in sources:
            tasks.append(self.search_themuse(query, location, max_results))
        if "remoteok" in sources:
            tasks.append(self.search_remoteok(query, max_results))
        if "jsearch" in sources:
            tasks.append(self.search_jsearch(query, location, max_results))
        if "tavily" in sources:
            tasks.append(self.search_tavily(query, max_results // 2))
        if "serper" in sources:
            tasks.append(self.search_serper(query, max_results // 2))
        
        # Gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine and deduplicate
        all_listings = []
        seen_urls = set()
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Search source failed: {result}")
                continue
            
            for listing in result:
                # Deduplicate by URL
                if listing.url and listing.url in seen_urls:
                    continue
                seen_urls.add(listing.url)
                
                # Calculate match score
                listing.match_score = self._calculate_match_score(listing)
                
                all_listings.append(listing)
        
        # Sort by match score
        all_listings.sort(key=lambda x: x.match_score, reverse=True)
        
        logger.info(f"Total unique internships found: {len(all_listings)}")
        
        return all_listings[:max_results]
    
    async def search_by_company(
        self,
        company: str,
        role_type: str = "intern",
    ) -> List[InternshipListing]:
        """Search for internships at a specific company."""
        query = f"{company} {role_type}"
        return await self.search(query=query, company=company)
    
    async def search_remote(
        self,
        query: str = "data science",
    ) -> List[InternshipListing]:
        """Search specifically for remote internships."""
        results = await self.search(query=f"{query} remote intern")
        return [r for r in results if r.location_type == LocationType.REMOTE]
    
    async def search_faang(self) -> List[InternshipListing]:
        """Search for internships at FAANG companies."""
        companies = ["Google", "Meta", "Amazon", "Apple", "Netflix", "Microsoft"]
        
        all_results = []
        for company in companies:
            results = await self.search_by_company(company)
            all_results.extend(results[:5])  # Top 5 per company
        
        return sorted(all_results, key=lambda x: x.match_score, reverse=True)
    
    # =========================================================================
    # Matching and Scoring
    # =========================================================================
    
    def _calculate_match_score(self, listing: InternshipListing) -> float:
        """Calculate how well a listing matches the user profile."""
        score = 0.0
        max_score = 100.0
        
        # Combine all text for matching
        listing_text = f"{listing.role} {listing.description} {' '.join(listing.requirements)}".lower()
        
        # Skill matching (40 points)
        matched_skills = []
        for skill in self.profile.primary_skills:
            if skill.lower() in listing_text:
                matched_skills.append(skill)
                score += 10
        
        listing.matched_skills = matched_skills
        score = min(score, 40)  # Cap at 40
        
        # Role match (20 points)
        for target_role in self.profile.target_roles:
            if any(word.lower() in listing.role.lower() for word in target_role.split()):
                score += 20
                break
        
        # Location preference (20 points)
        if self.profile.preferred_location == LocationType.REMOTE:
            if listing.location_type == LocationType.REMOTE:
                score += 20
            elif listing.location_type == LocationType.HYBRID:
                score += 10
        else:
            score += 15  # Neutral for on-site preference
        
        # Internship type (10 points)
        if listing.job_type == JobType.INTERNSHIP:
            score += 10
        
        # Company preference (10 points)
        if listing.company in self.profile.target_companies:
            score += 10
        
        # Normalize to percentage
        return min(score / max_score * 100, 100)
    
    def _extract_keywords(self, listing: InternshipListing) -> List[str]:
        """Extract keywords from job listing."""
        text = f"{listing.description} {' '.join(listing.requirements)}"
        
        # Common tech keywords
        tech_keywords = [
            "python", "sql", "java", "javascript", "c++", "r",
            "machine learning", "ml", "ai", "artificial intelligence",
            "data science", "data analysis", "analytics",
            "tensorflow", "pytorch", "keras", "scikit-learn",
            "pandas", "numpy", "spark", "hadoop",
            "aws", "gcp", "azure", "cloud",
            "docker", "kubernetes", "git",
            "statistics", "mathematics", "linear algebra",
        ]
        
        found = []
        text_lower = text.lower()
        
        for keyword in tech_keywords:
            if keyword in text_lower:
                found.append(keyword)
        
        return found
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _detect_location_type(self, location: str) -> LocationType:
        """Detect location type from location string."""
        location_lower = location.lower()
        
        if "remote" in location_lower:
            return LocationType.REMOTE
        elif "hybrid" in location_lower:
            return LocationType.HYBRID
        else:
            return LocationType.ONSITE
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        
        try:
            # Try various formats
            for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    return datetime.strptime(date_str[:19], fmt).date()
                except ValueError:
                    continue
        except Exception:
            pass
        
        return None
    
    def _parse_timestamp(self, timestamp: Optional[int]) -> Optional[date]:
        """Parse Unix timestamp to date."""
        if not timestamp:
            return None
        try:
            return datetime.fromtimestamp(timestamp).date()
        except Exception:
            return None
    
    def _parse_job_title(self, title: str) -> Tuple[str, str]:
        """Parse job title to extract company and role."""
        # Common patterns:
        # "Data Science Intern at Google"
        # "Google - Data Science Intern"
        # "Data Science Intern | Google"
        
        company = ""
        role = ""
        
        # Pattern: "Role at Company"
        if " at " in title:
            parts = title.split(" at ")
            role = parts[0].strip()
            company = parts[1].strip() if len(parts) > 1 else ""
        
        # Pattern: "Company - Role"
        elif " - " in title:
            parts = title.split(" - ")
            company = parts[0].strip()
            role = parts[1].strip() if len(parts) > 1 else ""
        
        # Pattern: "Role | Company"
        elif " | " in title:
            parts = title.split(" | ")
            role = parts[0].strip()
            company = parts[1].strip() if len(parts) > 1 else ""
        
        else:
            role = title
        
        return company, role
    
    # =========================================================================
    # Summary Methods
    # =========================================================================
    
    def get_search_summary(self, listings: List[InternshipListing]) -> str:
        """Get formatted summary of search results."""
        if not listings:
            return "No internships found matching your criteria."
        
        lines = [
            f"🔍 **Found {len(listings)} Internships**",
            "",
        ]
        
        for i, listing in enumerate(listings[:10], 1):
            salary = listing.get_salary_display()
            deadline = listing.deadline.strftime("%b %d") if listing.deadline else "Rolling"
            location_icon = "🏠" if listing.location_type == LocationType.REMOTE else "📍"
            
            lines.extend([
                f"**{i}. {listing.role}**",
                f"   🏢 {listing.company}",
                f"   {location_icon} {listing.location or listing.location_type.value}",
                f"   💰 {salary}",
                f"   📅 Deadline: {deadline}",
                f"   ⭐ Match: {listing.match_score:.0f}%",
                "",
            ])
        
        if len(listings) > 10:
            lines.append(f"... and {len(listings) - 10} more")
        
        return "\n".join(lines)
