"""
Tool Definitions for JARVIS Agents.

Provides a comprehensive set of tools for various agent capabilities.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Type

from loguru import logger

try:
    from langchain_core.tools import BaseTool, tool
    from pydantic import BaseModel, Field
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("LangChain tools not available")
    
    # Stub classes for when LangChain is not available
    class BaseTool:
        pass
    
    class BaseModel:
        pass
    
    def tool(func):
        return func
    
    class Field:
        def __init__(self, *args, **kwargs):
            pass


# =============================================================================
# Web Search Tools
# =============================================================================

class WebSearchInput(BaseModel):
    """Input for web search."""
    query: str = Field(description="The search query")
    max_results: int = Field(default=5, description="Maximum number of results")


class WebSearchTool(BaseTool):
    """Search the web using DuckDuckGo."""
    
    name: str = "web_search"
    description: str = "Search the web for information. Use this when you need current information or facts."
    args_schema: Type[BaseModel] = WebSearchInput
    
    def _run(self, query: str, max_results: int = 5) -> str:
        try:
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            
            if not results:
                return "No results found."
            
            formatted = []
            for r in results:
                formatted.append(f"Title: {r['title']}\nURL: {r['href']}\nSnippet: {r['body']}\n")
            
            return "\n---\n".join(formatted)
        except Exception as e:
            return f"Search failed: {e}"
    
    async def _arun(self, query: str, max_results: int = 5) -> str:
        return self._run(query, max_results)


class WebPageReaderInput(BaseModel):
    """Input for reading web pages."""
    url: str = Field(description="URL of the web page to read")


class WebPageReaderTool(BaseTool):
    """Read and extract content from a web page."""
    
    name: str = "read_webpage"
    description: str = "Read and extract the main content from a web page URL."
    args_schema: Type[BaseModel] = WebPageReaderInput
    
    def _run(self, url: str) -> str:
        try:
            import trafilatura
            
            downloaded = trafilatura.fetch_url(url)
            if downloaded is None:
                return "Failed to download page."
            
            text = trafilatura.extract(downloaded)
            if text is None:
                return "Failed to extract content."
            
            # Truncate if too long
            if len(text) > 5000:
                text = text[:5000] + "\n...[truncated]"
            
            return text
        except Exception as e:
            return f"Failed to read page: {e}"
    
    async def _arun(self, url: str) -> str:
        return self._run(url)


# =============================================================================
# System Control Tools
# =============================================================================

class OpenApplicationInput(BaseModel):
    """Input for opening applications."""
    app_name: str = Field(description="Name of the application to open")


class OpenApplicationTool(BaseTool):
    """Open an application on the system."""
    
    name: str = "open_application"
    description: str = "Open an application by name (e.g., 'notepad', 'chrome', 'vscode')"
    args_schema: Type[BaseModel] = OpenApplicationInput
    
    # Application mappings for Windows
    APP_MAPPINGS: ClassVar[Dict[str, str]] = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "chrome": "chrome",
        "firefox": "firefox",
        "edge": "msedge",
        "vscode": "code",
        "terminal": "wt",
        "cmd": "cmd",
        "powershell": "powershell",
        "explorer": "explorer",
        "spotify": "spotify",
        "discord": "discord",
    }
    
    def _run(self, app_name: str) -> str:
        try:
            app_lower = app_name.lower()
            executable = self.APP_MAPPINGS.get(app_lower, app_name)
            
            if os.name == 'nt':  # Windows
                subprocess.Popen(f'start {executable}', shell=True)
            else:  # Linux/Mac
                subprocess.Popen([executable], start_new_session=True)
            
            return f"Opened {app_name}"
        except Exception as e:
            return f"Failed to open {app_name}: {e}"
    
    async def _arun(self, app_name: str) -> str:
        return self._run(app_name)


class RunCommandInput(BaseModel):
    """Input for running shell commands."""
    command: str = Field(description="The command to execute")
    timeout: int = Field(default=30, description="Timeout in seconds")


class RunCommandTool(BaseTool):
    """Run a shell command (with safety restrictions)."""
    
    name: str = "run_command"
    description: str = "Run a shell command. Use with caution - only safe commands allowed."
    args_schema: Type[BaseModel] = RunCommandInput
    
    # Blocked commands for safety
    BLOCKED_PATTERNS: ClassVar[List[str]] = [
        "rm -rf", "del /f", "format", "mkfs",
        "shutdown", "reboot", "halt",
        ":(){", "fork bomb",
        "dd if=", "> /dev/",
    ]
    
    def _is_safe(self, command: str) -> bool:
        """Check if command is safe to execute."""
        cmd_lower = command.lower()
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in cmd_lower:
                return False
        return True
    
    def _run(self, command: str, timeout: int = 30) -> str:
        if not self._is_safe(command):
            return "Command blocked for safety reasons."
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\nStderr: {result.stderr}"
            
            return output or "Command completed with no output."
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout} seconds."
        except Exception as e:
            return f"Command failed: {e}"
    
    async def _arun(self, command: str, timeout: int = 30) -> str:
        return self._run(command, timeout)


class TypeTextInput(BaseModel):
    """Input for typing text."""
    text: str = Field(description="Text to type")


class TypeTextTool(BaseTool):
    """Type text using keyboard simulation."""
    
    name: str = "type_text"
    description: str = "Type text as if using the keyboard. Useful for filling forms or writing."
    args_schema: Type[BaseModel] = TypeTextInput
    
    def _run(self, text: str) -> str:
        try:
            import pyautogui
            pyautogui.typewrite(text, interval=0.02)
            return f"Typed: {text[:50]}..." if len(text) > 50 else f"Typed: {text}"
        except Exception as e:
            return f"Failed to type: {e}"
    
    async def _arun(self, text: str) -> str:
        return self._run(text)


class TakeScreenshotInput(BaseModel):
    """Input for taking screenshots."""
    save_path: Optional[str] = Field(default=None, description="Path to save screenshot")


class TakeScreenshotTool(BaseTool):
    """Take a screenshot of the screen."""
    
    name: str = "take_screenshot"
    description: str = "Take a screenshot of the current screen."
    args_schema: Type[BaseModel] = TakeScreenshotInput
    
    def _run(self, save_path: Optional[str] = None) -> str:
        try:
            import mss
            
            with mss.mss() as sct:
                if save_path:
                    path = Path(save_path)
                else:
                    path = Path.home() / "Desktop" / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                
                sct.shot(output=str(path))
                return f"Screenshot saved to: {path}"
        except Exception as e:
            return f"Failed to take screenshot: {e}"
    
    async def _arun(self, save_path: Optional[str] = None) -> str:
        return self._run(save_path)


# =============================================================================
# File Operations Tools
# =============================================================================

class ReadFileInput(BaseModel):
    """Input for reading files."""
    file_path: str = Field(description="Path to the file to read")


class ReadFileTool(BaseTool):
    """Read contents of a file."""
    
    name: str = "read_file"
    description: str = "Read the contents of a text file."
    args_schema: Type[BaseModel] = ReadFileInput
    
    def _run(self, file_path: str) -> str:
        try:
            path = Path(file_path).expanduser()
            
            if not path.exists():
                return f"File not found: {file_path}"
            
            if path.stat().st_size > 100000:  # 100KB limit
                return "File too large to read."
            
            content = path.read_text(encoding='utf-8')
            return content
        except Exception as e:
            return f"Failed to read file: {e}"
    
    async def _arun(self, file_path: str) -> str:
        return self._run(file_path)


class WriteFileInput(BaseModel):
    """Input for writing files."""
    file_path: str = Field(description="Path to the file to write")
    content: str = Field(description="Content to write to the file")


class WriteFileTool(BaseTool):
    """Write content to a file."""
    
    name: str = "write_file"
    description: str = "Write content to a text file. Creates the file if it doesn't exist."
    args_schema: Type[BaseModel] = WriteFileInput
    
    def _run(self, file_path: str, content: str) -> str:
        try:
            path = Path(file_path).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            return f"Written to: {file_path}"
        except Exception as e:
            return f"Failed to write file: {e}"
    
    async def _arun(self, file_path: str, content: str) -> str:
        return self._run(file_path, content)


class ListDirectoryInput(BaseModel):
    """Input for listing directories."""
    directory_path: str = Field(description="Path to the directory to list")


class ListDirectoryTool(BaseTool):
    """List contents of a directory."""
    
    name: str = "list_directory"
    description: str = "List files and folders in a directory."
    args_schema: Type[BaseModel] = ListDirectoryInput
    
    def _run(self, directory_path: str) -> str:
        try:
            path = Path(directory_path).expanduser()
            
            if not path.exists():
                return f"Directory not found: {directory_path}"
            
            if not path.is_dir():
                return f"Not a directory: {directory_path}"
            
            items = []
            for item in sorted(path.iterdir()):
                prefix = "[DIR]" if item.is_dir() else "[FILE]"
                items.append(f"{prefix} {item.name}")
            
            return "\n".join(items) if items else "Directory is empty."
        except Exception as e:
            return f"Failed to list directory: {e}"
    
    async def _arun(self, directory_path: str) -> str:
        return self._run(directory_path)


# =============================================================================
# Date/Time Tools
# =============================================================================

class GetCurrentTimeTool(BaseTool):
    """Get the current date and time."""
    
    name: str = "get_current_time"
    description: str = "Get the current date and time."
    
    def _run(self) -> str:
        now = datetime.now()
        return now.strftime("%A, %B %d, %Y at %I:%M %p")
    
    async def _arun(self) -> str:
        return self._run()


# =============================================================================
# Weather Tools
# =============================================================================

class GetWeatherInput(BaseModel):
    """Input for weather lookup."""
    location: str = Field(description="City name or location")


class GetWeatherTool(BaseTool):
    """Get current weather and forecast for a location using Open-Meteo (FREE API)."""
    
    name: str = "get_weather"
    description: str = "Get current weather conditions and forecast for a city. Returns temperature, conditions, humidity, wind, and 3-day forecast."
    args_schema: Type[BaseModel] = GetWeatherInput
    
    def _run(self, location: str) -> str:
        """Synchronous weather lookup."""
        import asyncio
        try:
            # Try to use the new Open-Meteo service
            from ..tools.weather import get_current_weather
            
            # Run async function in sync context
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(get_current_weather(location))
                return result
            finally:
                loop.close()
        except ImportError:
            # Fallback to wttr.in if new service not available
            return self._fallback_weather(location)
        except Exception as e:
            logger.error(f"Weather lookup failed: {e}")
            return self._fallback_weather(location)
    
    def _fallback_weather(self, location: str) -> str:
        """Fallback weather using wttr.in."""
        try:
            import httpx
            
            response = httpx.get(
                f"https://wttr.in/{location}?format=j1",
                timeout=10,
            )
            
            if response.status_code != 200:
                return f"Failed to get weather for {location}"
            
            data = response.json()
            current = data["current_condition"][0]
            
            return (
                f"Weather in {location}:\n"
                f"Temperature: {current['temp_F']}°F ({current['temp_C']}°C)\n"
                f"Condition: {current['weatherDesc'][0]['value']}\n"
                f"Humidity: {current['humidity']}%\n"
                f"Wind: {current['windspeedMiles']} mph {current['winddir16Point']}"
            )
        except Exception as e:
            return f"Failed to get weather: {e}"
    
    async def _arun(self, location: str) -> str:
        """Async weather lookup using Open-Meteo."""
        try:
            from ..tools.weather import get_current_weather
            return await get_current_weather(location)
        except ImportError:
            return self._fallback_weather(location)
        except Exception as e:
            logger.error(f"Async weather lookup failed: {e}")
            return self._fallback_weather(location)


class GetWeatherForecastInput(BaseModel):
    """Input for weather forecast."""
    location: str = Field(description="City name or location")
    days: int = Field(default=7, description="Number of days to forecast (1-7)")


class GetWeatherForecastTool(BaseTool):
    """Get extended weather forecast for a location using Open-Meteo (FREE API)."""
    
    name: str = "get_weather_forecast"
    description: str = "Get extended weather forecast for a city (up to 7 days). Use this for future weather predictions."
    args_schema: Type[BaseModel] = GetWeatherForecastInput
    
    def _run(self, location: str, days: int = 7) -> str:
        """Synchronous forecast lookup."""
        import asyncio
        try:
            from ..tools.weather import get_weather_forecast
            
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(get_weather_forecast(location, days))
                return result
            finally:
                loop.close()
        except ImportError:
            return f"Weather forecast service not available. Please try again later."
        except Exception as e:
            logger.error(f"Forecast lookup failed: {e}")
            return f"Failed to get forecast for {location}: {e}"
    
    async def _arun(self, location: str, days: int = 7) -> str:
        """Async forecast lookup."""
        try:
            from ..tools.weather import get_weather_forecast
            return await get_weather_forecast(location, days)
        except ImportError:
            return f"Weather forecast service not available."
        except Exception as e:
            logger.error(f"Async forecast lookup failed: {e}")
            return f"Failed to get forecast for {location}: {e}"


class CheckRainInput(BaseModel):
    """Input for rain check."""
    location: str = Field(description="City name or location")
    hours: int = Field(default=24, description="Hours to check ahead")


class CheckRainTool(BaseTool):
    """Check if it will rain in a location using Open-Meteo (FREE API)."""
    
    name: str = "check_rain"
    description: str = "Check if it will rain in a city within the next 24 hours. Use this when user asks about rain or precipitation."
    args_schema: Type[BaseModel] = CheckRainInput
    
    def _run(self, location: str, hours: int = 24) -> str:
        """Synchronous rain check."""
        import asyncio
        try:
            from ..tools.weather import check_rain
            
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(check_rain(location, hours))
                return result
            finally:
                loop.close()
        except ImportError:
            return f"Rain check service not available."
        except Exception as e:
            logger.error(f"Rain check failed: {e}")
            return f"Failed to check rain for {location}: {e}"
    
    async def _arun(self, location: str, hours: int = 24) -> str:
        """Async rain check."""
        try:
            from ..tools.weather import check_rain
            return await check_rain(location, hours)
        except ImportError:
            return f"Rain check service not available."
        except Exception as e:
            logger.error(f"Async rain check failed: {e}")
            return f"Failed to check rain for {location}: {e}"


# =============================================================================
# Calculator Tool
# =============================================================================

class CalculatorInput(BaseModel):
    """Input for calculator."""
    expression: str = Field(description="Mathematical expression to evaluate")


class CalculatorTool(BaseTool):
    """Evaluate mathematical expressions."""
    
    name: str = "calculator"
    description: str = "Evaluate a mathematical expression. Supports basic math, powers, sqrt, etc."
    args_schema: Type[BaseModel] = CalculatorInput
    
    def _run(self, expression: str) -> str:
        try:
            import math
            
            # Safe evaluation with limited functions
            allowed_names = {
                "abs": abs, "round": round, "min": min, "max": max,
                "sum": sum, "pow": pow, "sqrt": math.sqrt,
                "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "log": math.log, "log10": math.log10, "exp": math.exp,
                "pi": math.pi, "e": math.e,
            }
            
            # Remove potentially dangerous characters
            safe_expr = expression.replace("__", "")
            
            result = eval(safe_expr, {"__builtins__": {}}, allowed_names)
            return f"{expression} = {result}"
        except Exception as e:
            return f"Calculation error: {e}"
    
    async def _arun(self, expression: str) -> str:
        return self._run(expression)


# =============================================================================
# Reminder/Note Tools
# =============================================================================

class CreateReminderInput(BaseModel):
    """Input for creating reminders."""
    message: str = Field(description="Reminder message")
    time_description: str = Field(description="When to remind (e.g., 'in 10 minutes', 'at 3pm')")


class CreateReminderTool(BaseTool):
    """Create a reminder."""
    
    name: str = "create_reminder"
    description: str = "Create a reminder for later. Specify the message and when to remind."
    args_schema: Type[BaseModel] = CreateReminderInput
    
    def _run(self, message: str, time_description: str) -> str:
        # This would integrate with a reminder system
        # For now, just acknowledge
        return f"Reminder set: '{message}' for {time_description}"
    
    async def _arun(self, message: str, time_description: str) -> str:
        return self._run(message, time_description)


# =============================================================================
# Tool Factory
# =============================================================================

def get_all_tools() -> List[BaseTool]:
    """Get all available tools."""
    if not LANGCHAIN_AVAILABLE:
        return []
    
    return [
        WebSearchTool(),
        WebPageReaderTool(),
        OpenApplicationTool(),
        RunCommandTool(),
        TypeTextTool(),
        TakeScreenshotTool(),
        ReadFileTool(),
        WriteFileTool(),
        ListDirectoryTool(),
        GetCurrentTimeTool(),
        GetWeatherTool(),
        GetWeatherForecastTool(),
        CheckRainTool(),
        CalculatorTool(),
        CreateReminderTool(),
    ]


def get_tools_by_category(category: str) -> List[BaseTool]:
    """Get tools by category."""
    if not LANGCHAIN_AVAILABLE:
        return []
    
    categories = {
        "search": [WebSearchTool(), WebPageReaderTool()],
        "system": [OpenApplicationTool(), RunCommandTool(), TypeTextTool(), TakeScreenshotTool()],
        "files": [ReadFileTool(), WriteFileTool(), ListDirectoryTool()],
        "weather": [GetWeatherTool(), GetWeatherForecastTool(), CheckRainTool()],
        "utility": [GetCurrentTimeTool(), GetWeatherTool(), GetWeatherForecastTool(), CheckRainTool(), CalculatorTool(), CreateReminderTool()],
    }
    
    return categories.get(category, [])
