"""
GitHub Project Importer for JARVIS Internship Module.

Imports projects from user's GitHub repositories into the Resume RAG.
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from .models import Project
from .resume_rag import ResumeRAG


@dataclass
class GitHubRepo:
    """GitHub repository info."""
    name: str
    full_name: str
    description: str
    url: str
    homepage: str
    language: str
    languages: List[str]
    topics: List[str]
    stars: int
    forks: int
    created_at: datetime
    updated_at: datetime
    is_fork: bool


class GitHubImporter:
    """
    Import projects from GitHub repositories.
    
    Features:
    - List user's repositories
    - Extract project info (description, languages, topics)
    - Convert to Project objects for RAG
    - Generate resume bullets from repo info
    """
    
    def __init__(self, github_token: Optional[str] = None):
        self.token = github_token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "JARVIS/1.0",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
    
    @property
    def is_configured(self) -> bool:
        """Check if GitHub token is configured."""
        return bool(self.token)
    
    async def get_user_repos(
        self,
        username: Optional[str] = None,
        include_forks: bool = False,
        min_stars: int = 0,
    ) -> List[GitHubRepo]:
        """
        Get user's repositories.
        
        Args:
            username: GitHub username (None for authenticated user)
            include_forks: Include forked repositories
            min_stars: Minimum stars filter
            
        Returns:
            List of GitHubRepo objects
        """
        if not self.token and not username:
            logger.error("GitHub token required for authenticated requests")
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                if username:
                    url = f"{self.base_url}/users/{username}/repos"
                else:
                    url = f"{self.base_url}/user/repos"
                
                response = await client.get(
                    url,
                    headers=self.headers,
                    params={
                        "sort": "updated",
                        "per_page": 100,
                        "type": "owner" if not include_forks else "all",
                    },
                )
                
                if response.status_code != 200:
                    logger.error(f"GitHub API error: {response.status_code}")
                    return []
                
                repos_data = response.json()
                repos = []
                
                for repo in repos_data:
                    if repo.get("fork") and not include_forks:
                        continue
                    if repo.get("stargazers_count", 0) < min_stars:
                        continue
                    
                    # Get languages for this repo
                    languages = await self._get_repo_languages(client, repo["full_name"])
                    
                    repos.append(GitHubRepo(
                        name=repo["name"],
                        full_name=repo["full_name"],
                        description=repo.get("description") or "",
                        url=repo["html_url"],
                        homepage=repo.get("homepage") or "",
                        language=repo.get("language") or "",
                        languages=languages,
                        topics=repo.get("topics", []),
                        stars=repo.get("stargazers_count", 0),
                        forks=repo.get("forks_count", 0),
                        created_at=datetime.fromisoformat(repo["created_at"].replace("Z", "+00:00")),
                        updated_at=datetime.fromisoformat(repo["updated_at"].replace("Z", "+00:00")),
                        is_fork=repo.get("fork", False),
                    ))
                
                logger.info(f"Found {len(repos)} repositories")
                return repos
                
        except Exception as e:
            logger.error(f"Failed to fetch GitHub repos: {e}")
            return []
    
    async def _get_repo_languages(
        self,
        client: httpx.AsyncClient,
        full_name: str,
    ) -> List[str]:
        """Get languages used in a repository."""
        try:
            response = await client.get(
                f"{self.base_url}/repos/{full_name}/languages",
                headers=self.headers,
            )
            if response.status_code == 200:
                languages = response.json()
                return list(languages.keys())
        except Exception:
            pass
        return []
    
    def repo_to_project(self, repo: GitHubRepo) -> Project:
        """
        Convert a GitHub repo to a Project object.
        
        Generates resume bullets based on repo info.
        """
        # Build technologies list
        technologies = list(set(repo.languages + [repo.language] if repo.language else repo.languages))
        
        # Generate skills from topics and languages
        skills = []
        skill_map = {
            "python": "Python",
            "javascript": "JavaScript",
            "typescript": "TypeScript",
            "machine-learning": "Machine Learning",
            "deep-learning": "Deep Learning",
            "data-science": "Data Science",
            "react": "React",
            "nodejs": "Node.js",
            "api": "API Development",
            "database": "Database Design",
            "sql": "SQL",
            "docker": "Docker",
            "kubernetes": "Kubernetes",
            "aws": "AWS",
            "tensorflow": "TensorFlow",
            "pytorch": "PyTorch",
        }
        
        for topic in repo.topics:
            if topic.lower() in skill_map:
                skills.append(skill_map[topic.lower()])
        
        for lang in repo.languages:
            if lang.lower() in skill_map:
                skills.append(skill_map[lang.lower()])
        
        skills = list(set(skills))
        
        # Generate impact metrics
        impact_metrics = []
        if repo.stars > 0:
            impact_metrics.append(f"{repo.stars} GitHub stars")
        if repo.forks > 0:
            impact_metrics.append(f"{repo.forks} forks")
        if len(repo.languages) > 1:
            impact_metrics.append(f"Multi-language project ({len(repo.languages)} languages)")
        
        # Generate resume bullets
        resume_bullets = self._generate_resume_bullets(repo)
        
        return Project(
            name=self._format_project_name(repo.name),
            description=repo.description or f"A {repo.language or 'software'} project",
            detailed_description=self._generate_detailed_description(repo),
            technologies=technologies,
            skills_demonstrated=skills,
            impact_metrics=impact_metrics,
            start_date=repo.created_at.date(),
            end_date=None if self._is_recent(repo) else repo.updated_at.date(),
            is_ongoing=self._is_recent(repo),
            github_url=repo.url,
            demo_url=repo.homepage,
            resume_bullets=resume_bullets,
        )
    
    def _format_project_name(self, name: str) -> str:
        """Format repository name as project name."""
        # Convert kebab-case or snake_case to Title Case
        name = name.replace("-", " ").replace("_", " ")
        return name.title()
    
    def _generate_detailed_description(self, repo: GitHubRepo) -> str:
        """Generate a detailed description for the project."""
        parts = []
        
        if repo.description:
            parts.append(repo.description)
        
        if repo.languages:
            parts.append(f"Built with {', '.join(repo.languages[:5])}.")
        
        if repo.topics:
            parts.append(f"Topics: {', '.join(repo.topics[:5])}.")
        
        if repo.stars > 0 or repo.forks > 0:
            metrics = []
            if repo.stars > 0:
                metrics.append(f"{repo.stars} stars")
            if repo.forks > 0:
                metrics.append(f"{repo.forks} forks")
            parts.append(f"Community engagement: {', '.join(metrics)}.")
        
        return " ".join(parts)
    
    def _generate_resume_bullets(self, repo: GitHubRepo) -> List[str]:
        """Generate resume bullet points for a project."""
        bullets = []
        
        # Main bullet based on description
        if repo.description:
            action_verbs = ["Developed", "Built", "Created", "Engineered", "Designed"]
            verb = action_verbs[hash(repo.name) % len(action_verbs)]
            bullets.append(f"{verb} {repo.description.lower().rstrip('.')}")
        else:
            bullets.append(f"Developed {self._format_project_name(repo.name)} using {repo.language or 'modern technologies'}")
        
        # Technology bullet
        if len(repo.languages) > 1:
            bullets.append(f"Implemented using {', '.join(repo.languages[:4])} for robust functionality")
        
        # Impact bullet
        if repo.stars >= 10:
            bullets.append(f"Gained {repo.stars} GitHub stars demonstrating community value")
        elif repo.forks >= 5:
            bullets.append(f"Project forked {repo.forks} times by other developers")
        
        return bullets[:4]  # Max 4 bullets
    
    def _is_recent(self, repo: GitHubRepo) -> bool:
        """Check if repo was updated recently (within 3 months)."""
        from datetime import timezone
        now = datetime.now(timezone.utc)
        delta = now - repo.updated_at.replace(tzinfo=timezone.utc)
        return delta.days < 90
    
    async def import_to_rag(
        self,
        rag: ResumeRAG,
        username: Optional[str] = None,
        include_forks: bool = False,
        min_stars: int = 0,
        max_projects: int = 10,
    ) -> Dict[str, Any]:
        """
        Import GitHub repos to Resume RAG.
        
        Args:
            rag: ResumeRAG instance
            username: GitHub username (None for authenticated user)
            include_forks: Include forked repos
            min_stars: Minimum stars filter
            max_projects: Maximum projects to import
            
        Returns:
            Import summary
        """
        repos = await self.get_user_repos(username, include_forks, min_stars)
        
        if not repos:
            return {
                "success": False,
                "message": "No repositories found",
                "imported": 0,
            }
        
        # Sort by stars + recent activity
        repos.sort(key=lambda r: (r.stars, r.updated_at), reverse=True)
        repos = repos[:max_projects]
        
        imported = []
        for repo in repos:
            try:
                project = self.repo_to_project(repo)
                rag.add_project(project)
                imported.append(project.name)
                logger.info(f"Imported project: {project.name}")
            except Exception as e:
                logger.error(f"Failed to import {repo.name}: {e}")
        
        return {
            "success": True,
            "message": f"Imported {len(imported)} projects from GitHub",
            "imported": len(imported),
            "projects": imported,
        }


def get_github_import_summary(result: Dict[str, Any]) -> str:
    """Format GitHub import result as a message."""
    if not result.get("success"):
        return f"❌ GitHub import failed: {result.get('message', 'Unknown error')}"
    
    lines = [
        f"✅ **Imported {result['imported']} projects from GitHub**",
        "",
    ]
    
    projects = result.get("projects", [])
    for project in projects[:10]:
        lines.append(f"  📁 {project}")
    
    if len(projects) > 10:
        lines.append(f"  ... and {len(projects) - 10} more")
    
    return "\n".join(lines)


# CLI entry point
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    
    async def main():
        importer = GitHubImporter()
        
        if not importer.is_configured:
            print("❌ GITHUB_TOKEN not configured in .env")
            return
        
        repos = await importer.get_user_repos()
        
        print(f"\n📁 Found {len(repos)} repositories:\n")
        for repo in repos[:10]:
            stars = f"⭐{repo.stars}" if repo.stars > 0 else ""
            print(f"  {repo.name} - {repo.description[:50] if repo.description else 'No description'}... {stars}")
    
    asyncio.run(main())
