"""
Internship Module Diagnostics for JARVIS.

Tests all APIs and provides status reports.
"""

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger


@dataclass
class APIStatus:
    """Status of an API."""
    name: str
    available: bool
    configured: bool
    message: str
    jobs_found: int = 0


async def test_remoteok() -> APIStatus:
    """Test RemoteOK API (no key required)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://remoteok.com/api",
                headers={"User-Agent": "JARVIS/1.0"}
            )
            if response.status_code == 200:
                data = response.json()
                # First item is metadata
                jobs = [j for j in data if isinstance(j, dict) and j.get("position")]
                return APIStatus(
                    name="RemoteOK",
                    available=True,
                    configured=True,
                    message=f"Working ({len(jobs)} jobs available)",
                    jobs_found=len(jobs),
                )
            return APIStatus(
                name="RemoteOK",
                available=False,
                configured=True,
                message=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return APIStatus(
            name="RemoteOK",
            available=False,
            configured=True,
            message=str(e)[:50],
        )


async def test_themuse() -> APIStatus:
    """Test The Muse API (no key required)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://www.themuse.com/api/public/jobs",
                params={"page": 1, "category": "Data Science"},
            )
            if response.status_code == 200:
                data = response.json()
                jobs = data.get("results", [])
                return APIStatus(
                    name="The Muse",
                    available=True,
                    configured=True,
                    message=f"Working ({len(jobs)} jobs/page)",
                    jobs_found=len(jobs),
                )
            return APIStatus(
                name="The Muse",
                available=False,
                configured=True,
                message=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return APIStatus(
            name="The Muse",
            available=False,
            configured=True,
            message=str(e)[:50],
        )


async def test_adzuna(app_id: str, api_key: str) -> APIStatus:
    """Test Adzuna API."""
    if not app_id or not api_key:
        return APIStatus(
            name="Adzuna",
            available=False,
            configured=False,
            message="Not configured (need ADZUNA_APP_ID and ADZUNA_API_KEY)",
        )
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://api.adzuna.com/v1/api/jobs/us/search/1",
                params={
                    "app_id": app_id,
                    "app_key": api_key,
                    "what": "data science intern",
                    "results_per_page": 10,
                },
            )
            if response.status_code == 200:
                data = response.json()
                jobs = data.get("results", [])
                total = data.get("count", 0)
                return APIStatus(
                    name="Adzuna",
                    available=True,
                    configured=True,
                    message=f"Working ({total} total jobs)",
                    jobs_found=len(jobs),
                )
            elif response.status_code == 401:
                return APIStatus(
                    name="Adzuna",
                    available=False,
                    configured=True,
                    message="Invalid API key",
                )
            return APIStatus(
                name="Adzuna",
                available=False,
                configured=True,
                message=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return APIStatus(
            name="Adzuna",
            available=False,
            configured=True,
            message=str(e)[:50],
        )


async def test_jsearch(rapidapi_key: str) -> APIStatus:
    """Test JSearch API (RapidAPI)."""
    if not rapidapi_key:
        return APIStatus(
            name="JSearch",
            available=False,
            configured=False,
            message="Not configured (need RAPIDAPI_KEY)",
        )
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://jsearch.p.rapidapi.com/search",
                params={
                    "query": "data science intern",
                    "num_pages": 1,
                },
                headers={
                    "X-RapidAPI-Key": rapidapi_key,
                    "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
                },
            )
            if response.status_code == 200:
                data = response.json()
                jobs = data.get("data", [])
                return APIStatus(
                    name="JSearch",
                    available=True,
                    configured=True,
                    message=f"Working ({len(jobs)} jobs)",
                    jobs_found=len(jobs),
                )
            elif response.status_code == 403:
                return APIStatus(
                    name="JSearch",
                    available=False,
                    configured=True,
                    message="Invalid or expired API key",
                )
            return APIStatus(
                name="JSearch",
                available=False,
                configured=True,
                message=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return APIStatus(
            name="JSearch",
            available=False,
            configured=True,
            message=str(e)[:50],
        )


async def test_tavily(api_key: str) -> APIStatus:
    """Test Tavily API."""
    if not api_key:
        return APIStatus(
            name="Tavily",
            available=False,
            configured=False,
            message="Not configured (need TAVILY_API_KEY)",
        )
    
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": "data science internship 2025",
                    "max_results": 5,
                },
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                return APIStatus(
                    name="Tavily",
                    available=True,
                    configured=True,
                    message=f"Working ({len(results)} results)",
                    jobs_found=len(results),
                )
            elif response.status_code == 401:
                return APIStatus(
                    name="Tavily",
                    available=False,
                    configured=True,
                    message="Invalid API key",
                )
            return APIStatus(
                name="Tavily",
                available=False,
                configured=True,
                message=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return APIStatus(
            name="Tavily",
            available=False,
            configured=True,
            message=str(e)[:50],
        )


async def test_serper(api_key: str) -> APIStatus:
    """Test Serper API."""
    if not api_key:
        return APIStatus(
            name="Serper",
            available=False,
            configured=False,
            message="Not configured (need SERPER_API_KEY)",
        )
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://google.serper.dev/search",
                json={"q": "data science internship 2025"},
                headers={"X-API-KEY": api_key},
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("organic", [])
                return APIStatus(
                    name="Serper",
                    available=True,
                    configured=True,
                    message=f"Working ({len(results)} results)",
                    jobs_found=len(results),
                )
            elif response.status_code == 401:
                return APIStatus(
                    name="Serper",
                    available=False,
                    configured=True,
                    message="Invalid API key",
                )
            return APIStatus(
                name="Serper",
                available=False,
                configured=True,
                message=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return APIStatus(
            name="Serper",
            available=False,
            configured=True,
            message=str(e)[:50],
        )


async def run_all_diagnostics() -> List[APIStatus]:
    """Run diagnostics on all APIs."""
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get API keys
    adzuna_app_id = os.getenv("ADZUNA_APP_ID", "")
    adzuna_api_key = os.getenv("ADZUNA_API_KEY", "")
    rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
    tavily_api_key = os.getenv("TAVILY_API_KEY", "")
    serper_api_key = os.getenv("SERPER_API_KEY", "")
    
    # Run all tests concurrently
    results = await asyncio.gather(
        test_remoteok(),
        test_themuse(),
        test_adzuna(adzuna_app_id, adzuna_api_key),
        test_jsearch(rapidapi_key),
        test_tavily(tavily_api_key),
        test_serper(serper_api_key),
    )
    
    return list(results)


def format_diagnostics_report(results: List[APIStatus]) -> str:
    """Format diagnostics results as a report."""
    lines = [
        "📊 **Internship API Status**",
        "",
    ]
    
    working = 0
    configured = 0
    
    for status in results:
        if status.available:
            emoji = "✅"
            working += 1
        elif status.configured:
            emoji = "❌"
        else:
            emoji = "⚠️"
        
        if status.configured:
            configured += 1
        
        lines.append(f"{emoji} **{status.name}**: {status.message}")
    
    lines.extend([
        "",
        f"**Summary:** {working}/{len(results)} APIs working, {configured}/{len(results)} configured",
    ])
    
    # Recommendations
    not_configured = [s for s in results if not s.configured]
    if not_configured:
        lines.extend([
            "",
            "**To configure missing APIs:**",
        ])
        for status in not_configured:
            if status.name == "Adzuna":
                lines.append("  - Adzuna: Add ADZUNA_APP_ID and ADZUNA_API_KEY to .env")
            elif status.name == "JSearch":
                lines.append("  - JSearch: Add RAPIDAPI_KEY to .env (from rapidapi.com)")
            elif status.name == "Tavily":
                lines.append("  - Tavily: Add TAVILY_API_KEY to .env (from tavily.com)")
            elif status.name == "Serper":
                lines.append("  - Serper: Add SERPER_API_KEY to .env (from serper.dev)")
    
    return "\n".join(lines)


async def diagnose_internship_apis() -> str:
    """Run diagnostics and return formatted report."""
    results = await run_all_diagnostics()
    return format_diagnostics_report(results)


# CLI entry point
if __name__ == "__main__":
    report = asyncio.run(diagnose_internship_apis())
    print(report)
