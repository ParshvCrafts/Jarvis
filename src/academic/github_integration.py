"""
GitHub Integration for JARVIS.

Provides access to GitHub repositories:
- List repositories
- Show recent commits
- Check issues and PRs
- Repository statistics
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger


@dataclass
class Repository:
    """GitHub repository."""
    id: int
    name: str
    full_name: str
    description: Optional[str]
    html_url: str
    language: Optional[str]
    stars: int
    forks: int
    open_issues: int
    is_private: bool
    updated_at: datetime
    
    def __str__(self) -> str:
        return f"{self.name} ({self.language or 'No language'}) - ⭐ {self.stars}"


@dataclass
class Commit:
    """GitHub commit."""
    sha: str
    message: str
    author: str
    date: datetime
    html_url: str
    
    def __str__(self) -> str:
        short_sha = self.sha[:7]
        return f"[{short_sha}] {self.message}"


@dataclass
class Issue:
    """GitHub issue."""
    number: int
    title: str
    state: str
    author: str
    created_at: datetime
    html_url: str
    labels: List[str]
    is_pull_request: bool
    
    def __str__(self) -> str:
        type_str = "PR" if self.is_pull_request else "Issue"
        return f"#{self.number} [{type_str}] {self.title}"


class GitHubClient:
    """
    GitHub API client.
    
    Usage:
        client = GitHubClient()
        repos = await client.get_repositories()
        commits = await client.get_recent_commits("owner/repo")
        issues = await client.get_issues("owner/repo")
    """
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub client.
        
        Args:
            token: GitHub personal access token (from .env GITHUB_TOKEN)
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        
        if not self.token:
            logger.warning("GitHub token not configured. Set GITHUB_TOKEN in .env")
        
        self._client: Optional[httpx.AsyncClient] = None
        self._username: Optional[str] = None
    
    @property
    def is_configured(self) -> bool:
        """Check if GitHub is properly configured."""
        return bool(self.token)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {
                "Accept": "application/vnd.github.v3+json",
            }
            if self.token:
                headers["Authorization"] = f"token {self.token}"
            
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=headers,
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
        client = await self._get_client()
        
        try:
            response = await client.request(method, endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"GitHub request failed: {e}")
            raise
    
    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse GitHub datetime string."""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except ValueError:
            return None
    
    # =========================================================================
    # User
    # =========================================================================
    
    async def get_username(self) -> str:
        """Get authenticated user's username."""
        if self._username:
            return self._username
        
        if not self.is_configured:
            return "anonymous"
        
        try:
            data = await self._request("GET", "/user")
            self._username = data.get("login", "unknown")
            return self._username
        except Exception:
            return "unknown"
    
    # =========================================================================
    # Repositories
    # =========================================================================
    
    async def get_repositories(
        self,
        sort: str = "updated",
        limit: int = 30,
    ) -> List[Repository]:
        """
        Get user's repositories.
        
        Args:
            sort: Sort by (created, updated, pushed, full_name)
            limit: Maximum repositories to return
            
        Returns:
            List of repositories
        """
        if not self.is_configured:
            raise ValueError("GitHub token not configured")
        
        data = await self._request(
            "GET",
            "/user/repos",
            params={
                "sort": sort,
                "per_page": limit,
                "affiliation": "owner,collaborator",
            },
        )
        
        repos = []
        for item in data:
            repo = Repository(
                id=item["id"],
                name=item["name"],
                full_name=item["full_name"],
                description=item.get("description"),
                html_url=item["html_url"],
                language=item.get("language"),
                stars=item.get("stargazers_count", 0),
                forks=item.get("forks_count", 0),
                open_issues=item.get("open_issues_count", 0),
                is_private=item.get("private", False),
                updated_at=self._parse_datetime(item.get("updated_at")) or datetime.now(),
            )
            repos.append(repo)
        
        return repos
    
    async def get_repository(self, repo_name: str) -> Optional[Repository]:
        """
        Get a specific repository.
        
        Args:
            repo_name: Repository name (owner/repo or just repo for own repos)
            
        Returns:
            Repository if found
        """
        # If no owner specified, use authenticated user
        if "/" not in repo_name:
            username = await self.get_username()
            repo_name = f"{username}/{repo_name}"
        
        try:
            item = await self._request("GET", f"/repos/{repo_name}")
            
            return Repository(
                id=item["id"],
                name=item["name"],
                full_name=item["full_name"],
                description=item.get("description"),
                html_url=item["html_url"],
                language=item.get("language"),
                stars=item.get("stargazers_count", 0),
                forks=item.get("forks_count", 0),
                open_issues=item.get("open_issues_count", 0),
                is_private=item.get("private", False),
                updated_at=self._parse_datetime(item.get("updated_at")) or datetime.now(),
            )
        except Exception:
            return None
    
    async def find_repository(self, query: str) -> Optional[Repository]:
        """
        Find a repository by partial name match.
        
        Args:
            query: Repository name (partial match)
            
        Returns:
            Best matching repository
        """
        repos = await self.get_repositories()
        query_lower = query.lower()
        
        for repo in repos:
            if query_lower in repo.name.lower():
                return repo
        
        return None
    
    # =========================================================================
    # Commits
    # =========================================================================
    
    async def get_recent_commits(
        self,
        repo_name: str,
        limit: int = 10,
    ) -> List[Commit]:
        """
        Get recent commits for a repository.
        
        Args:
            repo_name: Repository name (owner/repo)
            limit: Maximum commits to return
            
        Returns:
            List of commits
        """
        if "/" not in repo_name:
            username = await self.get_username()
            repo_name = f"{username}/{repo_name}"
        
        data = await self._request(
            "GET",
            f"/repos/{repo_name}/commits",
            params={"per_page": limit},
        )
        
        commits = []
        for item in data:
            commit_data = item.get("commit", {})
            author_data = commit_data.get("author", {})
            
            commit = Commit(
                sha=item["sha"],
                message=commit_data.get("message", "").split("\n")[0],  # First line only
                author=author_data.get("name", "Unknown"),
                date=self._parse_datetime(author_data.get("date")) or datetime.now(),
                html_url=item["html_url"],
            )
            commits.append(commit)
        
        return commits
    
    async def get_today_commits(self, repo_name: Optional[str] = None) -> List[Commit]:
        """
        Get commits made today.
        
        Args:
            repo_name: Specific repo or None for all repos
            
        Returns:
            Today's commits
        """
        today = datetime.now().date()
        
        if repo_name:
            commits = await self.get_recent_commits(repo_name, limit=50)
            return [c for c in commits if c.date.date() == today]
        
        # Get commits from all recent repos
        repos = await self.get_repositories(limit=10)
        all_commits = []
        
        for repo in repos:
            try:
                commits = await self.get_recent_commits(repo.full_name, limit=20)
                today_commits = [c for c in commits if c.date.date() == today]
                for c in today_commits:
                    c.repo_name = repo.name  # Add repo name for context
                all_commits.extend(today_commits)
            except Exception:
                continue
        
        return all_commits
    
    # =========================================================================
    # Issues & Pull Requests
    # =========================================================================
    
    async def get_issues(
        self,
        repo_name: str,
        state: str = "open",
        limit: int = 20,
    ) -> List[Issue]:
        """
        Get issues for a repository.
        
        Args:
            repo_name: Repository name (owner/repo)
            state: Issue state (open, closed, all)
            limit: Maximum issues to return
            
        Returns:
            List of issues
        """
        if "/" not in repo_name:
            username = await self.get_username()
            repo_name = f"{username}/{repo_name}"
        
        data = await self._request(
            "GET",
            f"/repos/{repo_name}/issues",
            params={
                "state": state,
                "per_page": limit,
            },
        )
        
        issues = []
        for item in data:
            issue = Issue(
                number=item["number"],
                title=item["title"],
                state=item["state"],
                author=item.get("user", {}).get("login", "Unknown"),
                created_at=self._parse_datetime(item.get("created_at")) or datetime.now(),
                html_url=item["html_url"],
                labels=[l["name"] for l in item.get("labels", [])],
                is_pull_request="pull_request" in item,
            )
            issues.append(issue)
        
        return issues
    
    async def get_open_issues(self, repo_name: str) -> List[Issue]:
        """Get open issues (excluding PRs)."""
        issues = await self.get_issues(repo_name, state="open")
        return [i for i in issues if not i.is_pull_request]
    
    async def get_pull_requests(self, repo_name: str) -> List[Issue]:
        """Get open pull requests."""
        issues = await self.get_issues(repo_name, state="open")
        return [i for i in issues if i.is_pull_request]
    
    # =========================================================================
    # Formatting
    # =========================================================================
    
    def format_repositories(self, repos: List[Repository]) -> str:
        """Format repositories as readable string."""
        if not repos:
            return "No repositories found."
        
        lines = []
        for repo in repos:
            private_str = "🔒 " if repo.is_private else ""
            lang_str = f"[{repo.language}]" if repo.language else ""
            lines.append(f"• {private_str}{repo.name} {lang_str} - ⭐ {repo.stars}")
            if repo.description:
                lines.append(f"  {repo.description[:60]}...")
        
        return "\n".join(lines)
    
    def format_commits(self, commits: List[Commit]) -> str:
        """Format commits as readable string."""
        if not commits:
            return "No commits found."
        
        lines = []
        for commit in commits:
            short_sha = commit.sha[:7]
            date_str = commit.date.strftime("%b %d, %I:%M %p")
            lines.append(f"• [{short_sha}] {commit.message[:50]} ({date_str})")
        
        return "\n".join(lines)
    
    def format_issues(self, issues: List[Issue]) -> str:
        """Format issues as readable string."""
        if not issues:
            return "No issues found."
        
        lines = []
        for issue in issues:
            type_str = "PR" if issue.is_pull_request else "Issue"
            labels_str = f" [{', '.join(issue.labels)}]" if issue.labels else ""
            lines.append(f"• #{issue.number} [{type_str}] {issue.title}{labels_str}")
        
        return "\n".join(lines)
