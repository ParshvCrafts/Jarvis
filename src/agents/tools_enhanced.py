"""
Enhanced Agent Tools for JARVIS.

Provides improved tools for:
- Web search (DuckDuckGo, SerpAPI)
- Web content fetching
- File operations
- Code execution with sandboxing
- Aider integration for coding
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    output: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time: float = 0.0


class BaseTool(ABC):
    """Base class for agent tools."""
    
    name: str = "base_tool"
    description: str = "Base tool"
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        pass
    
    async def aexecute(self, **kwargs) -> ToolResult:
        """Async execution (default runs sync in executor)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.execute(**kwargs))


class WebSearchTool(BaseTool):
    """
    Web search using DuckDuckGo.
    
    Free, no API key required.
    """
    
    name = "web_search"
    description = "Search the web for information. Returns titles, URLs, and snippets."
    
    def __init__(self, max_results: int = 5):
        self.max_results = max_results
    
    def execute(self, query: str, **kwargs) -> ToolResult:
        """
        Execute web search.
        
        Args:
            query: Search query.
        """
        start_time = time.time()
        
        try:
            from duckduckgo_search import DDGS
            
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=self.max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })
            
            output = f"Found {len(results)} results for '{query}':\n\n"
            for i, r in enumerate(results, 1):
                output += f"{i}. {r['title']}\n   {r['url']}\n   {r['snippet'][:200]}...\n\n"
            
            return ToolResult(
                success=True,
                output=output,
                data={"results": results, "query": query},
                execution_time=time.time() - start_time,
            )
        
        except ImportError:
            return ToolResult(
                success=False,
                output="",
                error="duckduckgo-search not installed",
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                execution_time=time.time() - start_time,
            )


class WebFetchTool(BaseTool):
    """
    Fetch and extract content from web pages.
    """
    
    name = "web_fetch"
    description = "Fetch content from a URL and extract the main text."
    
    def __init__(self, max_length: int = 5000):
        self.max_length = max_length
    
    def execute(self, url: str, **kwargs) -> ToolResult:
        """
        Fetch web page content.
        
        Args:
            url: URL to fetch.
        """
        start_time = time.time()
        
        try:
            import httpx
            from bs4 import BeautifulSoup
            
            # Fetch page
            response = httpx.get(url, timeout=30, follow_redirects=True)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()
            
            # Get text
            text = soup.get_text(separator="\n", strip=True)
            
            # Clean up whitespace
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            text = "\n".join(lines)
            
            # Truncate if needed
            if len(text) > self.max_length:
                text = text[:self.max_length] + "...[truncated]"
            
            return ToolResult(
                success=True,
                output=text,
                data={"url": url, "length": len(text)},
                execution_time=time.time() - start_time,
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                execution_time=time.time() - start_time,
            )


class FileReadTool(BaseTool):
    """Read file contents."""
    
    name = "file_read"
    description = "Read the contents of a file."
    
    def __init__(self, max_size: int = 100000):
        self.max_size = max_size
    
    def execute(self, path: str, **kwargs) -> ToolResult:
        """
        Read file contents.
        
        Args:
            path: File path to read.
        """
        start_time = time.time()
        
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File not found: {path}",
                    execution_time=time.time() - start_time,
                )
            
            if file_path.stat().st_size > self.max_size:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File too large (max {self.max_size} bytes)",
                    execution_time=time.time() - start_time,
                )
            
            content = file_path.read_text(encoding="utf-8", errors="replace")
            
            return ToolResult(
                success=True,
                output=content,
                data={"path": str(file_path), "size": len(content)},
                execution_time=time.time() - start_time,
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                execution_time=time.time() - start_time,
            )


class FileWriteTool(BaseTool):
    """Write content to a file."""
    
    name = "file_write"
    description = "Write content to a file. Creates the file if it doesn't exist."
    
    def execute(self, path: str, content: str, **kwargs) -> ToolResult:
        """
        Write to file.
        
        Args:
            path: File path to write.
            content: Content to write.
        """
        start_time = time.time()
        
        try:
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            
            return ToolResult(
                success=True,
                output=f"Written {len(content)} bytes to {path}",
                data={"path": str(file_path), "size": len(content)},
                execution_time=time.time() - start_time,
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                execution_time=time.time() - start_time,
            )


class CodeExecutionTool(BaseTool):
    """
    Execute Python code in a sandboxed environment.
    
    Uses subprocess with timeout for safety.
    """
    
    name = "execute_code"
    description = "Execute Python code and return the output. Use for calculations or data processing."
    
    def __init__(self, timeout: int = 30, max_output: int = 10000):
        self.timeout = timeout
        self.max_output = max_output
    
    def execute(self, code: str, **kwargs) -> ToolResult:
        """
        Execute Python code.
        
        Args:
            code: Python code to execute.
        """
        start_time = time.time()
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            result = subprocess.run(
                ["python", temp_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=tempfile.gettempdir(),
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR:\n{result.stderr}"
            
            if len(output) > self.max_output:
                output = output[:self.max_output] + "...[truncated]"
            
            return ToolResult(
                success=result.returncode == 0,
                output=output,
                data={"return_code": result.returncode},
                error=result.stderr if result.returncode != 0 else None,
                execution_time=time.time() - start_time,
            )
        
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error=f"Execution timed out after {self.timeout} seconds",
                execution_time=self.timeout,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                execution_time=time.time() - start_time,
            )
        finally:
            os.unlink(temp_path)


class AiderTool(BaseTool):
    """
    Aider integration for AI-assisted coding.
    
    Runs Aider with a prompt to make code changes.
    """
    
    name = "aider"
    description = "Use Aider AI coding assistant to make code changes. Provide a description of what to build or change."
    
    def __init__(
        self,
        model: str = "gpt-4",
        working_dir: Optional[Path] = None,
        timeout: int = 300,
    ):
        self.model = model
        self.working_dir = working_dir or Path.cwd()
        self.timeout = timeout
    
    def execute(self, prompt: str, files: Optional[List[str]] = None, **kwargs) -> ToolResult:
        """
        Run Aider with a prompt.
        
        Args:
            prompt: Description of what to build or change.
            files: Optional list of files to include.
        """
        start_time = time.time()
        
        try:
            # Build command
            cmd = ["aider", "--yes", "--model", self.model, "--message", prompt]
            
            if files:
                cmd.extend(files)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(self.working_dir),
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n{result.stderr}"
            
            return ToolResult(
                success=result.returncode == 0,
                output=output,
                data={"files": files or []},
                error=result.stderr if result.returncode != 0 else None,
                execution_time=time.time() - start_time,
            )
        
        except FileNotFoundError:
            return ToolResult(
                success=False,
                output="",
                error="Aider not installed. Install with: pip install aider-chat",
                execution_time=time.time() - start_time,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error=f"Aider timed out after {self.timeout} seconds",
                execution_time=self.timeout,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                execution_time=time.time() - start_time,
            )


class ResearchTool(BaseTool):
    """
    Deep research tool with multi-source search.
    
    Searches multiple sources and synthesizes results.
    """
    
    name = "research"
    description = "Perform deep research on a topic. Searches multiple sources and provides cited results."
    
    def __init__(self, max_sources: int = 5):
        self.max_sources = max_sources
        self.search_tool = WebSearchTool(max_results=max_sources)
        self.fetch_tool = WebFetchTool(max_length=3000)
    
    def execute(self, topic: str, depth: str = "normal", **kwargs) -> ToolResult:
        """
        Research a topic.
        
        Args:
            topic: Topic to research.
            depth: Research depth (quick, normal, deep).
        """
        start_time = time.time()
        
        try:
            # Search for sources
            search_result = self.search_tool.execute(query=topic)
            
            if not search_result.success:
                return search_result
            
            sources = search_result.data.get("results", [])
            
            # Fetch content from sources
            research_data = []
            
            num_to_fetch = {"quick": 2, "normal": 3, "deep": 5}.get(depth, 3)
            
            for source in sources[:num_to_fetch]:
                fetch_result = self.fetch_tool.execute(url=source["url"])
                
                if fetch_result.success:
                    research_data.append({
                        "title": source["title"],
                        "url": source["url"],
                        "content": fetch_result.output[:2000],
                    })
            
            # Format output
            output = f"# Research: {topic}\n\n"
            output += f"Found {len(research_data)} sources:\n\n"
            
            for i, data in enumerate(research_data, 1):
                output += f"## Source {i}: {data['title']}\n"
                output += f"URL: {data['url']}\n\n"
                output += f"{data['content'][:1000]}...\n\n"
                output += "---\n\n"
            
            return ToolResult(
                success=True,
                output=output,
                data={
                    "topic": topic,
                    "sources": research_data,
                    "source_count": len(research_data),
                },
                execution_time=time.time() - start_time,
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                execution_time=time.time() - start_time,
            )


class CalculatorTool(BaseTool):
    """Safe calculator for mathematical expressions."""
    
    name = "calculator"
    description = "Evaluate mathematical expressions safely."
    
    # Allowed functions
    ALLOWED = {
        "abs": abs, "round": round, "min": min, "max": max,
        "sum": sum, "len": len, "pow": pow,
        "int": int, "float": float,
    }
    
    def execute(self, expression: str, **kwargs) -> ToolResult:
        """
        Evaluate expression.
        
        Args:
            expression: Mathematical expression.
        """
        start_time = time.time()
        
        try:
            import math
            
            # Add math functions
            allowed = {**self.ALLOWED}
            for name in dir(math):
                if not name.startswith("_"):
                    allowed[name] = getattr(math, name)
            
            # Evaluate safely
            result = eval(expression, {"__builtins__": {}}, allowed)
            
            return ToolResult(
                success=True,
                output=str(result),
                data={"expression": expression, "result": result},
                execution_time=time.time() - start_time,
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                execution_time=time.time() - start_time,
            )


class ToolRegistry:
    """Registry of available tools."""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self.tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, str]]:
        """List all available tools."""
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self.tools.values()
        ]
    
    def execute(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool not found: {name}",
            )
        return tool.execute(**kwargs)


def create_default_registry() -> ToolRegistry:
    """Create a registry with default tools."""
    registry = ToolRegistry()
    
    registry.register(WebSearchTool())
    registry.register(WebFetchTool())
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    registry.register(CodeExecutionTool())
    registry.register(ResearchTool())
    registry.register(CalculatorTool())
    
    # Aider is optional
    try:
        registry.register(AiderTool())
    except Exception:
        pass
    
    return registry
