"""
Scholarship Discovery for JARVIS Scholarship Module.

Handles:
- Multi-source scholarship search
- Eligibility matching
- Requirement extraction
- Deadline tracking
"""

import asyncio
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .models import (
    EligibilityProfile,
    Scholarship,
    ScholarshipQuestion,
    CitizenshipStatus,
    EducationLevel,
    FieldOfStudy,
)

# Try importing search/scraping libraries
HTTPX_AVAILABLE = False
TAVILY_AVAILABLE = False
FIRECRAWL_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    logger.debug("httpx not installed")

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    logger.debug("tavily not installed")


@dataclass
class SearchSource:
    """A scholarship search source."""
    name: str
    url: str
    search_url: str
    enabled: bool = True


class ScholarshipDiscovery:
    """
    Discover scholarships from multiple sources.
    
    Sources:
    - Scholarships.com
    - Bold.org
    - Going Merry
    - Fastweb
    - Cappex
    - UC Berkeley Financial Aid
    - Web search (Tavily/Serper)
    """
    
    # Known scholarship sources
    SOURCES = {
        "scholarships.com": SearchSource(
            name="Scholarships.com",
            url="https://www.scholarships.com",
            search_url="https://www.scholarships.com/scholarship-search",
        ),
        "bold.org": SearchSource(
            name="Bold.org",
            url="https://bold.org",
            search_url="https://bold.org/scholarships/",
        ),
        "going_merry": SearchSource(
            name="Going Merry",
            url="https://www.goingmerry.com",
            search_url="https://www.goingmerry.com/scholarships",
        ),
        "fastweb": SearchSource(
            name="Fastweb",
            url="https://www.fastweb.com",
            search_url="https://www.fastweb.com/college-scholarships",
        ),
        "cappex": SearchSource(
            name="Cappex",
            url="https://www.cappex.com",
            search_url="https://www.cappex.com/scholarships",
        ),
        "uc_berkeley": SearchSource(
            name="UC Berkeley Financial Aid",
            url="https://financialaid.berkeley.edu",
            search_url="https://financialaid.berkeley.edu/types-of-aid/scholarships/",
        ),
    }
    
    def __init__(
        self,
        profile: Optional[EligibilityProfile] = None,
        tavily_api_key: Optional[str] = None,
        serper_api_key: Optional[str] = None,
        match_threshold: float = 0.80,
    ):
        """
        Initialize scholarship discovery.
        
        Args:
            profile: User's eligibility profile
            tavily_api_key: Tavily API key for web search
            serper_api_key: Serper API key for Google search
            match_threshold: Minimum eligibility match (0-1)
        """
        self.profile = profile or EligibilityProfile()
        self.match_threshold = match_threshold
        
        # API clients
        self.tavily_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        self.serper_key = serper_api_key or os.getenv("SERPER_API_KEY")
        
        self._tavily_client = None
        if TAVILY_AVAILABLE and self.tavily_key:
            self._tavily_client = TavilyClient(api_key=self.tavily_key)
        
        # HTTP client for scraping
        self._http_client = None
        if HTTPX_AVAILABLE:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
        
        # Cache
        self._scholarship_cache: Dict[str, Scholarship] = {}
    
    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
    
    # =========================================================================
    # Eligibility Matching
    # =========================================================================
    
    def calculate_match(
        self,
        scholarship: Scholarship,
        profile: Optional[EligibilityProfile] = None,
    ) -> Tuple[float, Dict[str, bool]]:
        """
        Calculate eligibility match percentage.
        
        Args:
            scholarship: Scholarship to check
            profile: User profile (uses self.profile if not provided)
            
        Returns:
            (match_percentage, match_details)
        """
        profile = profile or self.profile
        requirements = scholarship.eligibility_requirements
        
        matches = {}
        required_matches = []
        preferred_matches = []
        
        # Check citizenship
        if "citizenship" in requirements:
            req_citizenship = requirements["citizenship"]
            user_citizenship = profile.citizenship.value if hasattr(profile.citizenship, 'value') else profile.citizenship
            
            if isinstance(req_citizenship, list):
                matches["citizenship"] = user_citizenship in req_citizenship
            else:
                matches["citizenship"] = user_citizenship == req_citizenship or req_citizenship == "any"
            
            if "citizenship" in scholarship.required_criteria:
                required_matches.append(matches["citizenship"])
            else:
                preferred_matches.append(matches["citizenship"])
        
        # Check education level
        if "education_level" in requirements:
            req_level = requirements["education_level"]
            user_level = profile.education_level.value if hasattr(profile.education_level, 'value') else profile.education_level
            
            if isinstance(req_level, list):
                matches["education_level"] = user_level in req_level
            else:
                matches["education_level"] = user_level == req_level
            
            if "education_level" in scholarship.required_criteria:
                required_matches.append(matches["education_level"])
            else:
                preferred_matches.append(matches["education_level"])
        
        # Check field of study
        if "field" in requirements:
            req_field = requirements["field"]
            user_field = profile.field_of_study.value if hasattr(profile.field_of_study, 'value') else profile.field_of_study
            
            if isinstance(req_field, list):
                matches["field"] = user_field in req_field or "any" in req_field
            else:
                matches["field"] = user_field == req_field or req_field == "any"
            
            if "field" in scholarship.required_criteria:
                required_matches.append(matches["field"])
            else:
                preferred_matches.append(matches["field"])
        
        # Check major
        if "major" in requirements:
            req_major = requirements["major"]
            if isinstance(req_major, list):
                matches["major"] = any(
                    m.lower() in profile.major.lower() or profile.major.lower() in m.lower()
                    for m in req_major
                )
            else:
                matches["major"] = req_major.lower() in profile.major.lower() or req_major == "any"
            
            if "major" in scholarship.required_criteria:
                required_matches.append(matches["major"])
            else:
                preferred_matches.append(matches["major"])
        
        # Check GPA
        if "min_gpa" in requirements:
            matches["gpa"] = profile.gpa >= requirements["min_gpa"]
            if "gpa" in scholarship.required_criteria:
                required_matches.append(matches["gpa"])
            else:
                preferred_matches.append(matches["gpa"])
        
        # Check state
        if "state" in requirements:
            req_state = requirements["state"]
            if isinstance(req_state, list):
                matches["state"] = profile.state in req_state or "any" in req_state
            else:
                matches["state"] = profile.state == req_state or req_state == "any"
            
            if "state" in scholarship.required_criteria:
                required_matches.append(matches["state"])
            else:
                preferred_matches.append(matches["state"])
        
        # Check ethnicity
        if "ethnicity" in requirements:
            req_ethnicity = requirements["ethnicity"]
            if isinstance(req_ethnicity, list):
                matches["ethnicity"] = profile.ethnicity in req_ethnicity or "any" in req_ethnicity
            else:
                matches["ethnicity"] = profile.ethnicity == req_ethnicity or req_ethnicity == "any"
            
            if "ethnicity" in scholarship.required_criteria:
                required_matches.append(matches["ethnicity"])
            else:
                preferred_matches.append(matches["ethnicity"])
        
        # Check gender
        if "gender" in requirements:
            req_gender = requirements["gender"]
            if isinstance(req_gender, list):
                matches["gender"] = profile.gender in req_gender or "any" in req_gender
            else:
                matches["gender"] = profile.gender == req_gender or req_gender == "any"
            
            if "gender" in scholarship.required_criteria:
                required_matches.append(matches["gender"])
            else:
                preferred_matches.append(matches["gender"])
        
        # Check first generation
        if "first_generation" in requirements and requirements["first_generation"]:
            matches["first_generation"] = profile.first_generation
            if "first_generation" in scholarship.required_criteria:
                required_matches.append(matches["first_generation"])
            else:
                preferred_matches.append(matches["first_generation"])
        
        # Check financial need
        if "financial_need" in requirements and requirements["financial_need"]:
            matches["financial_need"] = profile.financial_need
            if "financial_need" in scholarship.required_criteria:
                required_matches.append(matches["financial_need"])
            else:
                preferred_matches.append(matches["financial_need"])
        
        # Calculate match percentage
        # Required criteria must ALL match
        if required_matches and not all(required_matches):
            match_percentage = 0.0
        else:
            # Calculate from preferred matches
            if preferred_matches:
                match_percentage = sum(preferred_matches) / len(preferred_matches)
            elif required_matches:
                match_percentage = 1.0  # All required matched, no preferred
            else:
                match_percentage = 0.9  # No requirements specified
        
        return match_percentage, matches
    
    def filter_by_eligibility(
        self,
        scholarships: List[Scholarship],
        min_match: Optional[float] = None,
    ) -> List[Scholarship]:
        """
        Filter scholarships by eligibility match.
        
        Args:
            scholarships: List of scholarships to filter
            min_match: Minimum match percentage (uses self.match_threshold if not provided)
            
        Returns:
            Filtered and sorted list of scholarships
        """
        min_match = min_match or self.match_threshold
        eligible = []
        
        for scholarship in scholarships:
            match_pct, match_details = self.calculate_match(scholarship)
            scholarship.match_percentage = match_pct
            scholarship.match_details = match_details
            
            if match_pct >= min_match:
                eligible.append(scholarship)
        
        # Sort by match percentage (descending)
        eligible.sort(key=lambda s: s.match_percentage, reverse=True)
        
        return eligible
    
    # =========================================================================
    # Web Search
    # =========================================================================
    
    async def search_tavily(
        self,
        query: str,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for scholarships using Tavily.
        
        Args:
            query: Search query
            max_results: Maximum results
            
        Returns:
            List of search results
        """
        if not self._tavily_client:
            logger.warning("Tavily client not available")
            return []
        
        try:
            # Build search query
            search_query = f"{query} scholarship application deadline 2025"
            
            response = self._tavily_client.search(
                query=search_query,
                search_depth="advanced",
                max_results=max_results,
                include_domains=[
                    "scholarships.com",
                    "bold.org",
                    "fastweb.com",
                    "goingmerry.com",
                    "cappex.com",
                    "unigo.com",
                    "collegeboard.org",
                ],
            )
            
            return response.get("results", [])
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []
    
    async def search_serper(
        self,
        query: str,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for scholarships using Serper (Google Search).
        
        Args:
            query: Search query
            max_results: Maximum results
            
        Returns:
            List of search results
        """
        if not self.serper_key or not self._http_client:
            return []
        
        try:
            response = await self._http_client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": self.serper_key},
                json={
                    "q": f"{query} scholarship 2025",
                    "num": max_results,
                }
            )
            
            data = response.json()
            return data.get("organic", [])
        except Exception as e:
            logger.error(f"Serper search failed: {e}")
            return []
    
    # =========================================================================
    # Scholarship Parsing
    # =========================================================================
    
    def parse_scholarship_from_search(
        self,
        result: Dict[str, Any],
        source: str = "web_search",
    ) -> Optional[Scholarship]:
        """
        Parse a scholarship from search result.
        
        Args:
            result: Search result dictionary
            source: Source name
            
        Returns:
            Scholarship object or None
        """
        try:
            title = result.get("title", "") or result.get("name", "")
            url = result.get("url", "") or result.get("link", "")
            snippet = result.get("content", "") or result.get("snippet", "")
            
            if not title or not url:
                return None
            
            # Extract amount from title/snippet
            amount = 0.0
            amount_text = ""
            amount_match = re.search(r'\$[\d,]+(?:\.\d{2})?', title + " " + snippet)
            if amount_match:
                amount_text = amount_match.group()
                amount = float(amount_text.replace("$", "").replace(",", ""))
            
            # Extract deadline
            deadline = None
            deadline_patterns = [
                r'deadline[:\s]+(\w+\s+\d{1,2},?\s+\d{4})',
                r'due[:\s]+(\w+\s+\d{1,2},?\s+\d{4})',
                r'(\w+\s+\d{1,2},?\s+\d{4})\s+deadline',
            ]
            for pattern in deadline_patterns:
                match = re.search(pattern, snippet, re.IGNORECASE)
                if match:
                    try:
                        deadline = datetime.strptime(
                            match.group(1).replace(",", ""),
                            "%B %d %Y"
                        ).date()
                    except ValueError:
                        pass
                    break
            
            scholarship = Scholarship(
                name=title,
                description=snippet,
                amount=amount,
                amount_text=amount_text,
                deadline=deadline,
                url=url,
                source=source,
            )
            
            return scholarship
        except Exception as e:
            logger.debug(f"Failed to parse scholarship: {e}")
            return None
    
    # =========================================================================
    # Main Search Methods
    # =========================================================================
    
    async def search(
        self,
        query: Optional[str] = None,
        deadline_before: Optional[date] = None,
        deadline_after: Optional[date] = None,
        min_amount: float = 0,
        max_results: int = 50,
        sources: Optional[List[str]] = None,
    ) -> List[Scholarship]:
        """
        Search for scholarships matching criteria.
        
        Args:
            query: Search query (e.g., "STEM", "data science")
            deadline_before: Only scholarships due before this date
            deadline_after: Only scholarships due after this date
            min_amount: Minimum award amount
            max_results: Maximum results to return
            sources: Specific sources to search
            
        Returns:
            List of matching scholarships
        """
        scholarships = []
        
        # Build search query from profile if not provided
        if not query:
            query = f"{self.profile.major} {self.profile.field.value if hasattr(self.profile.field, 'value') else self.profile.field} {self.profile.university}"
        
        # Search using Tavily
        if self._tavily_client:
            logger.info(f"Searching Tavily for: {query}")
            results = await self.search_tavily(query, max_results=max_results)
            
            for result in results:
                scholarship = self.parse_scholarship_from_search(result, "tavily")
                if scholarship:
                    scholarships.append(scholarship)
        
        # Search using Serper
        if self.serper_key:
            logger.info(f"Searching Serper for: {query}")
            results = await self.search_serper(query, max_results=max_results)
            
            for result in results:
                scholarship = self.parse_scholarship_from_search(result, "serper")
                if scholarship:
                    scholarships.append(scholarship)
        
        # Filter by deadline
        if deadline_before:
            scholarships = [
                s for s in scholarships
                if s.deadline is None or s.deadline <= deadline_before
            ]
        
        if deadline_after:
            scholarships = [
                s for s in scholarships
                if s.deadline is None or s.deadline >= deadline_after
            ]
        
        # Filter by amount
        if min_amount > 0:
            scholarships = [s for s in scholarships if s.amount >= min_amount]
        
        # Deduplicate by URL
        seen_urls = set()
        unique = []
        for s in scholarships:
            if s.url not in seen_urls:
                seen_urls.add(s.url)
                unique.append(s)
        
        # Calculate eligibility matches
        for scholarship in unique:
            match_pct, match_details = self.calculate_match(scholarship)
            scholarship.match_percentage = match_pct
            scholarship.match_details = match_details
        
        # Sort by match percentage
        unique.sort(key=lambda s: (s.match_percentage, s.amount), reverse=True)
        
        return unique[:max_results]
    
    async def search_by_deadline(
        self,
        days: int = 30,
        min_match: float = 0.8,
    ) -> List[Scholarship]:
        """
        Search for scholarships due within a certain number of days.
        
        Args:
            days: Number of days from now
            min_match: Minimum eligibility match
            
        Returns:
            List of scholarships due soon
        """
        deadline = date.today() + timedelta(days=days)
        
        scholarships = await self.search(
            deadline_before=deadline,
            deadline_after=date.today(),
        )
        
        # Filter by eligibility
        eligible = self.filter_by_eligibility(scholarships, min_match)
        
        # Sort by deadline (soonest first)
        eligible.sort(key=lambda s: s.deadline or date.max)
        
        return eligible
    
    async def search_stem(self, max_results: int = 20) -> List[Scholarship]:
        """Search for STEM scholarships."""
        return await self.search(
            query="STEM science technology engineering mathematics scholarship",
            max_results=max_results,
        )
    
    async def search_uc_berkeley(self, max_results: int = 20) -> List[Scholarship]:
        """Search for UC Berkeley specific scholarships."""
        return await self.search(
            query="UC Berkeley scholarship undergraduate",
            max_results=max_results,
        )
    
    async def search_data_science(self, max_results: int = 20) -> List[Scholarship]:
        """Search for Data Science scholarships."""
        return await self.search(
            query="data science analytics machine learning AI scholarship",
            max_results=max_results,
        )
    
    def get_search_summary(self, scholarships: List[Scholarship]) -> str:
        """Get summary of search results."""
        if not scholarships:
            return "No scholarships found matching your criteria."
        
        total_amount = sum(s.amount for s in scholarships)
        avg_match = sum(s.match_percentage for s in scholarships) / len(scholarships)
        
        with_deadline = [s for s in scholarships if s.deadline]
        soonest = min(with_deadline, key=lambda s: s.deadline) if with_deadline else None
        
        lines = [
            f"🔍 **Found {len(scholarships)} scholarships**",
            "",
            f"💰 Total potential awards: ${total_amount:,.0f}",
            f"📊 Average eligibility match: {avg_match:.0%}",
        ]
        
        if soonest:
            days = (soonest.deadline - date.today()).days
            lines.append(f"⏰ Soonest deadline: {soonest.name} ({days} days)")
        
        lines.append("")
        lines.append("**Top Matches:**")
        
        for i, s in enumerate(scholarships[:5], 1):
            deadline_str = s.deadline.strftime("%b %d") if s.deadline else "TBD"
            lines.append(
                f"{i}. **{s.name}** - ${s.amount:,.0f}"
                f"\n   Match: {s.match_percentage:.0%} | Due: {deadline_str}"
            )
        
        return "\n".join(lines)
