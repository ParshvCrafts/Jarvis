"""
Canvas LMS Integration for JARVIS.

Provides access to UC Berkeley's Canvas (bCourses) for:
- Assignments (upcoming, due dates, submission status)
- Grades (per course, per assignment)
- Announcements (course updates)
- Courses (enrolled courses, syllabus)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

import httpx
from loguru import logger


class SubmissionStatus(str, Enum):
    """Assignment submission status."""
    NOT_SUBMITTED = "not_submitted"
    SUBMITTED = "submitted"
    GRADED = "graded"
    LATE = "late"
    MISSING = "missing"


@dataclass
class Course:
    """Canvas course."""
    id: int
    name: str
    code: str
    term: Optional[str] = None
    enrollment_type: str = "student"
    
    def __str__(self) -> str:
        return f"{self.code}: {self.name}"


@dataclass
class Assignment:
    """Canvas assignment."""
    id: int
    course_id: int
    course_name: str
    name: str
    due_at: Optional[datetime] = None
    points_possible: float = 0
    description: Optional[str] = None
    submission_status: SubmissionStatus = SubmissionStatus.NOT_SUBMITTED
    score: Optional[float] = None
    html_url: Optional[str] = None
    
    @property
    def is_due_today(self) -> bool:
        if not self.due_at:
            return False
        today = datetime.now().date()
        return self.due_at.date() == today
    
    @property
    def is_due_tomorrow(self) -> bool:
        if not self.due_at:
            return False
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        return self.due_at.date() == tomorrow
    
    @property
    def is_overdue(self) -> bool:
        if not self.due_at:
            return False
        return datetime.now() > self.due_at and self.submission_status == SubmissionStatus.NOT_SUBMITTED
    
    @property
    def days_until_due(self) -> Optional[int]:
        if not self.due_at:
            return None
        delta = self.due_at.date() - datetime.now().date()
        return delta.days
    
    def __str__(self) -> str:
        due_str = self.due_at.strftime("%b %d, %I:%M %p") if self.due_at else "No due date"
        return f"{self.name} ({self.course_name}) - Due: {due_str}"


@dataclass
class Grade:
    """Canvas grade for a course."""
    course_id: int
    course_name: str
    current_score: Optional[float] = None
    current_grade: Optional[str] = None
    final_score: Optional[float] = None
    final_grade: Optional[str] = None
    
    def __str__(self) -> str:
        grade = self.current_grade or f"{self.current_score:.1f}%" if self.current_score else "N/A"
        return f"{self.course_name}: {grade}"


@dataclass
class Announcement:
    """Canvas course announcement."""
    id: int
    course_id: int
    course_name: str
    title: str
    message: str
    posted_at: datetime
    author: Optional[str] = None
    html_url: Optional[str] = None
    
    def __str__(self) -> str:
        return f"[{self.course_name}] {self.title}"


class CanvasClient:
    """
    Canvas LMS API client for UC Berkeley (bCourses).
    
    Usage:
        client = CanvasClient()
        assignments = await client.get_upcoming_assignments()
        grades = await client.get_grades()
    """
    
    DEFAULT_BASE_URL = "https://bcourses.berkeley.edu/api/v1"
    
    def __init__(
        self,
        api_token: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize Canvas client.
        
        Args:
            api_token: Canvas API token (from .env CANVAS_API_TOKEN)
            base_url: Canvas API base URL (defaults to UC Berkeley bCourses)
        """
        self.api_token = api_token or os.getenv("CANVAS_API_TOKEN")
        self.base_url = (base_url or os.getenv("CANVAS_BASE_URL") or self.DEFAULT_BASE_URL).rstrip("/")
        
        if not self.api_token:
            logger.warning("Canvas API token not configured. Set CANVAS_API_TOKEN in .env")
        
        self._client: Optional[httpx.AsyncClient] = None
        self._courses_cache: Dict[int, Course] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_duration = timedelta(minutes=30)
    
    @property
    def is_configured(self) -> bool:
        """Check if Canvas is properly configured."""
        return bool(self.api_token)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make an API request."""
        if not self.is_configured:
            raise ValueError("Canvas API token not configured")
        
        client = await self._get_client()
        
        try:
            response = await client.request(method, endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Canvas API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Canvas request failed: {e}")
            raise
    
    async def _get_all_pages(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        max_pages: int = 10,
    ) -> List[Any]:
        """Get all pages of a paginated response."""
        if not self.is_configured:
            raise ValueError("Canvas API token not configured")
        
        client = await self._get_client()
        all_items = []
        params = params or {}
        params["per_page"] = 100
        page = 1
        
        while page <= max_pages:
            params["page"] = page
            try:
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                items = response.json()
                
                if not items:
                    break
                
                all_items.extend(items)
                
                # Check for next page in Link header
                link_header = response.headers.get("Link", "")
                if 'rel="next"' not in link_header:
                    break
                
                page += 1
            except Exception as e:
                logger.error(f"Canvas pagination error: {e}")
                break
        
        return all_items
    
    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse Canvas datetime string."""
        if not dt_str:
            return None
        try:
            # Canvas uses ISO 8601 format
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except ValueError:
            return None
    
    # =========================================================================
    # Courses
    # =========================================================================
    
    async def get_courses(self, force_refresh: bool = False) -> List[Course]:
        """
        Get enrolled courses.
        
        Args:
            force_refresh: Force refresh cache
            
        Returns:
            List of enrolled courses
        """
        # Check cache
        if not force_refresh and self._courses_cache and self._cache_time:
            if datetime.now() - self._cache_time < self._cache_duration:
                return list(self._courses_cache.values())
        
        data = await self._get_all_pages(
            "/courses",
            params={
                "enrollment_state": "active",
                "include[]": ["term", "total_scores"],
            },
        )
        
        courses = []
        for item in data:
            if item.get("access_restricted_by_date"):
                continue
            
            course = Course(
                id=item["id"],
                name=item.get("name", "Unknown Course"),
                code=item.get("course_code", ""),
                term=item.get("term", {}).get("name") if item.get("term") else None,
                enrollment_type=item.get("enrollments", [{}])[0].get("type", "student"),
            )
            courses.append(course)
            self._courses_cache[course.id] = course
        
        self._cache_time = datetime.now()
        logger.info(f"Loaded {len(courses)} Canvas courses")
        return courses
    
    async def get_course_name(self, course_id: int) -> str:
        """Get course name by ID."""
        if course_id in self._courses_cache:
            return self._courses_cache[course_id].name
        
        await self.get_courses()
        return self._courses_cache.get(course_id, Course(course_id, "Unknown", "")).name
    
    # =========================================================================
    # Assignments
    # =========================================================================
    
    async def get_assignments(
        self,
        course_id: Optional[int] = None,
        include_past: bool = False,
    ) -> List[Assignment]:
        """
        Get assignments.
        
        Args:
            course_id: Specific course ID (None for all courses)
            include_past: Include past due assignments
            
        Returns:
            List of assignments sorted by due date
        """
        if course_id:
            courses = [self._courses_cache.get(course_id)]
            if not courses[0]:
                await self.get_courses()
                courses = [self._courses_cache.get(course_id)]
        else:
            courses = await self.get_courses()
        
        all_assignments = []
        
        for course in courses:
            if not course:
                continue
            
            try:
                data = await self._get_all_pages(
                    f"/courses/{course.id}/assignments",
                    params={
                        "include[]": ["submission"],
                        "order_by": "due_at",
                    },
                )
                
                for item in data:
                    due_at = self._parse_datetime(item.get("due_at"))
                    
                    # Skip past assignments unless requested
                    if not include_past and due_at and due_at < datetime.now():
                        continue
                    
                    # Determine submission status
                    submission = item.get("submission", {}) or {}
                    if submission.get("score") is not None:
                        status = SubmissionStatus.GRADED
                    elif submission.get("submitted_at"):
                        if submission.get("late"):
                            status = SubmissionStatus.LATE
                        else:
                            status = SubmissionStatus.SUBMITTED
                    elif submission.get("missing"):
                        status = SubmissionStatus.MISSING
                    else:
                        status = SubmissionStatus.NOT_SUBMITTED
                    
                    assignment = Assignment(
                        id=item["id"],
                        course_id=course.id,
                        course_name=course.name,
                        name=item.get("name", "Untitled"),
                        due_at=due_at,
                        points_possible=item.get("points_possible", 0) or 0,
                        description=item.get("description"),
                        submission_status=status,
                        score=submission.get("score"),
                        html_url=item.get("html_url"),
                    )
                    all_assignments.append(assignment)
            except Exception as e:
                logger.error(f"Error fetching assignments for {course.name}: {e}")
        
        # Sort by due date (None at end)
        all_assignments.sort(key=lambda a: (a.due_at is None, a.due_at or datetime.max))
        
        return all_assignments
    
    async def get_upcoming_assignments(
        self,
        days: int = 7,
        course_id: Optional[int] = None,
    ) -> List[Assignment]:
        """
        Get assignments due in the next N days.
        
        Args:
            days: Number of days to look ahead
            course_id: Specific course ID (None for all)
            
        Returns:
            List of upcoming assignments
        """
        assignments = await self.get_assignments(course_id=course_id)
        cutoff = datetime.now() + timedelta(days=days)
        
        return [a for a in assignments if a.due_at and a.due_at <= cutoff]
    
    async def get_assignments_due_today(self) -> List[Assignment]:
        """Get assignments due today."""
        assignments = await self.get_assignments()
        return [a for a in assignments if a.is_due_today]
    
    async def get_assignments_due_tomorrow(self) -> List[Assignment]:
        """Get assignments due tomorrow."""
        assignments = await self.get_assignments()
        return [a for a in assignments if a.is_due_tomorrow]
    
    # =========================================================================
    # Grades
    # =========================================================================
    
    async def get_grades(self) -> List[Grade]:
        """
        Get current grades for all courses.
        
        Returns:
            List of grades per course
        """
        courses = await self.get_courses()
        grades = []
        
        for course in courses:
            try:
                data = await self._request(
                    "GET",
                    f"/courses/{course.id}/enrollments",
                    params={
                        "user_id": "self",
                        "include[]": ["current_points", "total_scores"],
                    },
                )
                
                for enrollment in data:
                    if enrollment.get("type") == "StudentEnrollment":
                        grade_data = enrollment.get("grades", {})
                        grade = Grade(
                            course_id=course.id,
                            course_name=course.name,
                            current_score=grade_data.get("current_score"),
                            current_grade=grade_data.get("current_grade"),
                            final_score=grade_data.get("final_score"),
                            final_grade=grade_data.get("final_grade"),
                        )
                        grades.append(grade)
                        break
            except Exception as e:
                logger.error(f"Error fetching grade for {course.name}: {e}")
        
        return grades
    
    async def get_course_grade(self, course_name: str) -> Optional[Grade]:
        """
        Get grade for a specific course by name.
        
        Args:
            course_name: Course name or code (partial match)
            
        Returns:
            Grade if found
        """
        grades = await self.get_grades()
        course_lower = course_name.lower()
        
        for grade in grades:
            if (course_lower in grade.course_name.lower() or 
                course_lower in self._courses_cache.get(grade.course_id, Course(0, "", "")).code.lower()):
                return grade
        
        return None
    
    # =========================================================================
    # Announcements
    # =========================================================================
    
    async def get_announcements(
        self,
        course_id: Optional[int] = None,
        days: int = 7,
    ) -> List[Announcement]:
        """
        Get recent announcements.
        
        Args:
            course_id: Specific course ID (None for all)
            days: Number of days to look back
            
        Returns:
            List of announcements
        """
        courses = await self.get_courses()
        
        if course_id:
            course_ids = [str(course_id)]
        else:
            course_ids = [str(c.id) for c in courses]
        
        if not course_ids:
            return []
        
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        try:
            data = await self._request(
                "GET",
                "/announcements",
                params={
                    "context_codes[]": [f"course_{cid}" for cid in course_ids],
                    "start_date": start_date,
                    "per_page": 50,
                },
            )
            
            announcements = []
            for item in data:
                # Extract course ID from context_code
                context = item.get("context_code", "")
                cid = int(context.replace("course_", "")) if context.startswith("course_") else 0
                
                announcement = Announcement(
                    id=item["id"],
                    course_id=cid,
                    course_name=await self.get_course_name(cid),
                    title=item.get("title", "Untitled"),
                    message=item.get("message", ""),
                    posted_at=self._parse_datetime(item.get("posted_at")) or datetime.now(),
                    author=item.get("author", {}).get("display_name"),
                    html_url=item.get("html_url"),
                )
                announcements.append(announcement)
            
            # Sort by date (newest first)
            announcements.sort(key=lambda a: a.posted_at, reverse=True)
            return announcements
            
        except Exception as e:
            logger.error(f"Error fetching announcements: {e}")
            return []
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    async def find_course(self, query: str) -> Optional[Course]:
        """
        Find a course by name or code.
        
        Args:
            query: Course name or code (partial match)
            
        Returns:
            Course if found
        """
        courses = await self.get_courses()
        query_lower = query.lower()
        
        for course in courses:
            if query_lower in course.name.lower() or query_lower in course.code.lower():
                return course
        
        return None
    
    def format_assignments_summary(self, assignments: List[Assignment]) -> str:
        """Format assignments into a readable summary."""
        if not assignments:
            return "No upcoming assignments."
        
        lines = []
        for a in assignments:
            if a.due_at:
                if a.is_due_today:
                    due_str = f"TODAY at {a.due_at.strftime('%I:%M %p')}"
                elif a.is_due_tomorrow:
                    due_str = f"Tomorrow at {a.due_at.strftime('%I:%M %p')}"
                else:
                    due_str = a.due_at.strftime("%A, %b %d")
            else:
                due_str = "No due date"
            
            status_icon = ""
            if a.submission_status == SubmissionStatus.SUBMITTED:
                status_icon = "✓ "
            elif a.submission_status == SubmissionStatus.GRADED:
                status_icon = "✓✓ "
            elif a.submission_status == SubmissionStatus.LATE:
                status_icon = "⚠ "
            elif a.submission_status == SubmissionStatus.MISSING:
                status_icon = "❌ "
            
            lines.append(f"• {status_icon}{a.name} ({a.course_name}) - {due_str}")
        
        return "\n".join(lines)
    
    def format_grades_summary(self, grades: List[Grade]) -> str:
        """Format grades into a readable summary."""
        if not grades:
            return "No grades available."
        
        lines = []
        for g in grades:
            if g.current_grade:
                grade_str = g.current_grade
            elif g.current_score is not None:
                grade_str = f"{g.current_score:.1f}%"
            else:
                grade_str = "N/A"
            
            lines.append(f"• {g.course_name}: {grade_str}")
        
        return "\n".join(lines)
