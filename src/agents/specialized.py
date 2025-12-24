"""
Specialized Agents for JARVIS.

Implements specialized agents for different task domains:
- Research Agent: Web search and information gathering
- Coding Agent: Code generation and debugging
- System Agent: OS and application control
- IoT Agent: Smart home device control
- Communication Agent: Email, calendar, notifications
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from .base import AgentState, AgentResponse, AgentType, BaseAgent
from .tools import (
    WebSearchTool, WebPageReaderTool,
    OpenApplicationTool, RunCommandTool, TypeTextTool, TakeScreenshotTool,
    ReadFileTool, WriteFileTool, ListDirectoryTool,
    GetCurrentTimeTool, GetWeatherTool, GetWeatherForecastTool, CheckRainTool, CalculatorTool,
)


class ResearchAgent(BaseAgent):
    """
    Research agent for web searches and information gathering.
    
    Capabilities:
    - Web search using DuckDuckGo
    - Web page content extraction
    - Information summarization
    """
    
    def __init__(self, llm_manager: Any):
        tools = [
            WebSearchTool(),
            WebPageReaderTool(),
            GetWeatherTool(),
            GetWeatherForecastTool(),
            CheckRainTool(),
        ]
        
        super().__init__(
            name="research",
            agent_type=AgentType.RESEARCH,
            description="Handles web searches, information gathering, weather queries, and summarization.",
            llm_manager=llm_manager,
            tools=tools,
        )
    
    def _default_system_prompt(self) -> str:
        return """You are a research assistant specialized in finding and summarizing information.

Available tools:
{tools}

When researching:
1. Start with a web search to find relevant sources
2. Read promising web pages for detailed information
3. Synthesize findings into a clear, accurate summary
4. Cite sources when possible

For weather queries, use the weather tools to get real-time data.

Always verify information from multiple sources when possible.
Be thorough but concise in your responses."""
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from text using simple heuristics."""
        import re
        
        # Common patterns for location extraction
        patterns = [
            r"(?:in|at|for|of)\s+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z]{2})?)",  # "in Chicago", "at New York, NY"
            r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+weather",  # "Chicago weather"
            r"weather\s+(?:in|at|for)\s+([A-Z][a-zA-Z\s]+)",  # "weather in Chicago"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                location = match.group(1).strip()
                # Clean up common words that aren't locations
                stop_words = ["the", "today", "tomorrow", "this", "next", "week"]
                if location.lower() not in stop_words:
                    return location
        
        # Fallback: look for capitalized words that might be cities
        words = text.split()
        for i, word in enumerate(words):
            if word[0].isupper() and word.lower() not in ["what", "how", "will", "is", "the", "weather", "today", "tomorrow"]:
                # Check if next word is also capitalized (multi-word city)
                if i + 1 < len(words) and words[i + 1][0].isupper():
                    return f"{word} {words[i + 1]}"
                return word
        
        return None
    
    async def process(self, state: AgentState) -> AgentResponse:
        """Process a research task."""
        from ..core.llm import Message
        
        # Build prompt with tools
        system_prompt = self._default_system_prompt().format(
            tools=self.get_tool_descriptions()
        )
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=f"Research task: {state.task}"),
        ]
        
        # Add context if available
        if state.context:
            context_str = "\n".join([f"{k}: {v}" for k, v in state.context.items()])
            messages.append(Message(role="user", content=f"Context:\n{context_str}"))
        
        try:
            # Get initial response
            response = self.llm_manager.generate(messages)
            content = response.content
            
            # Check if tool calls are needed
            tool_calls = []
            task_lower = state.task.lower()
            
            # Weather query detection
            weather_keywords = ["weather", "temperature", "forecast", "rain", "snow", "sunny", "cloudy", "humid"]
            is_weather_query = any(kw in task_lower for kw in weather_keywords)
            
            if is_weather_query:
                # Extract location from task (simple heuristic)
                location = self._extract_location(state.task)
                if location:
                    # Determine which weather tool to use
                    if "forecast" in task_lower or "week" in task_lower or "days" in task_lower:
                        weather_tool = self.get_tool_by_name("get_weather_forecast")
                        if weather_tool:
                            weather_result = await weather_tool._arun(location)
                            tool_calls.append({"tool": "get_weather_forecast", "result": weather_result})
                            content = weather_result
                    elif "rain" in task_lower or "precipitation" in task_lower:
                        rain_tool = self.get_tool_by_name("check_rain")
                        if rain_tool:
                            rain_result = await rain_tool._arun(location)
                            tool_calls.append({"tool": "check_rain", "result": rain_result})
                            content = rain_result
                    else:
                        weather_tool = self.get_tool_by_name("get_weather")
                        if weather_tool:
                            weather_result = await weather_tool._arun(location)
                            tool_calls.append({"tool": "get_weather", "result": weather_result})
                            content = weather_result
            
            # Web search for non-weather queries
            elif "search" in task_lower or "find" in task_lower:
                # Execute web search
                search_tool = self.get_tool_by_name("web_search")
                if search_tool:
                    search_result = search_tool._run(state.task)
                    tool_calls.append({"tool": "web_search", "result": search_result})
                    
                    # Generate summary with search results
                    messages.append(Message(role="assistant", content=content))
                    messages.append(Message(role="user", content=f"Search results:\n{search_result}\n\nPlease summarize these findings."))
                    
                    response = self.llm_manager.generate(messages)
                    content = response.content
            
            return AgentResponse(
                content=content,
                agent_type=self.agent_type,
                tool_calls=tool_calls,
                completed=True,
            )
        
        except Exception as e:
            logger.error(f"Research agent error: {e}")
            return AgentResponse(
                content=f"Research failed: {e}",
                agent_type=self.agent_type,
                completed=True,
            )


class CodingAgent(BaseAgent):
    """
    Coding agent for code generation and debugging.
    
    Capabilities:
    - Code generation in multiple languages
    - Code explanation and debugging
    - File operations for code files
    """
    
    def __init__(self, llm_manager: Any):
        tools = [
            ReadFileTool(),
            WriteFileTool(),
            ListDirectoryTool(),
            RunCommandTool(),
        ]
        
        super().__init__(
            name="coding",
            agent_type=AgentType.CODING,
            description="Handles code generation, debugging, and technical tasks.",
            llm_manager=llm_manager,
            tools=tools,
        )
    
    def _default_system_prompt(self) -> str:
        return """You are an expert programmer and coding assistant.

Available tools:
{tools}

When coding:
1. Write clean, well-documented code
2. Follow best practices for the language
3. Include error handling
4. Explain your code when helpful

For debugging:
1. Analyze the error carefully
2. Identify the root cause
3. Provide a clear fix with explanation

Always prioritize code quality and maintainability."""
    
    async def process(self, state: AgentState) -> AgentResponse:
        """Process a coding task."""
        from ..core.llm import Message
        
        system_prompt = self._default_system_prompt().format(
            tools=self.get_tool_descriptions()
        )
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=f"Coding task: {state.task}"),
        ]
        
        if state.context:
            context_str = "\n".join([f"{k}: {v}" for k, v in state.context.items()])
            messages.append(Message(role="user", content=f"Context:\n{context_str}"))
        
        try:
            response = self.llm_manager.generate(messages)
            
            return AgentResponse(
                content=response.content,
                agent_type=self.agent_type,
                completed=True,
            )
        
        except Exception as e:
            logger.error(f"Coding agent error: {e}")
            return AgentResponse(
                content=f"Coding task failed: {e}",
                agent_type=self.agent_type,
                completed=True,
            )


class SystemAgent(BaseAgent):
    """
    System agent for OS and application control.
    
    Capabilities:
    - Open/close applications
    - File system operations
    - System commands
    - Screenshots
    """
    
    def __init__(self, llm_manager: Any, allowed_apps: Optional[List[str]] = None):
        tools = [
            OpenApplicationTool(),
            RunCommandTool(),
            TypeTextTool(),
            TakeScreenshotTool(),
            ReadFileTool(),
            WriteFileTool(),
            ListDirectoryTool(),
        ]
        
        super().__init__(
            name="system",
            agent_type=AgentType.SYSTEM,
            description="Handles system operations, app control, and file management.",
            llm_manager=llm_manager,
            tools=tools,
        )
        
        self.allowed_apps = allowed_apps or [
            "notepad", "calculator", "chrome", "firefox", "edge",
            "vscode", "terminal", "explorer", "spotify",
        ]
    
    def _default_system_prompt(self) -> str:
        return """You are a system control assistant with access to OS operations.

Available tools:
{tools}

Allowed applications: {allowed_apps}

Guidelines:
1. Only perform requested operations
2. Confirm destructive actions before executing
3. Use safe commands only
4. Report results clearly

Always prioritize system safety and user data protection."""
    
    async def process(self, state: AgentState) -> AgentResponse:
        """Process a system control task."""
        from ..core.llm import Message
        
        system_prompt = self._default_system_prompt().format(
            tools=self.get_tool_descriptions(),
            allowed_apps=", ".join(self.allowed_apps),
        )
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=f"System task: {state.task}"),
        ]
        
        try:
            # Analyze the task
            response = self.llm_manager.generate(messages)
            content = response.content
            
            tool_calls = []
            
            # Check for app opening requests
            task_lower = state.task.lower()
            for app in self.allowed_apps:
                if app in task_lower and ("open" in task_lower or "launch" in task_lower or "start" in task_lower):
                    open_tool = self.get_tool_by_name("open_application")
                    if open_tool:
                        result = open_tool._run(app)
                        tool_calls.append({"tool": "open_application", "app": app, "result": result})
                        content = result
                    break
            
            # Check for screenshot requests
            if "screenshot" in task_lower:
                screenshot_tool = self.get_tool_by_name("take_screenshot")
                if screenshot_tool:
                    result = screenshot_tool._run()
                    tool_calls.append({"tool": "take_screenshot", "result": result})
                    content = result
            
            return AgentResponse(
                content=content,
                agent_type=self.agent_type,
                tool_calls=tool_calls,
                completed=True,
            )
        
        except Exception as e:
            logger.error(f"System agent error: {e}")
            return AgentResponse(
                content=f"System operation failed: {e}",
                agent_type=self.agent_type,
                completed=True,
            )


class IoTAgent(BaseAgent):
    """
    IoT agent for smart home device control.
    
    Capabilities:
    - Light control
    - Door lock control
    - Device status monitoring
    """
    
    def __init__(self, llm_manager: Any, iot_controller: Any = None):
        super().__init__(
            name="iot",
            agent_type=AgentType.IOT,
            description="Handles IoT device control for smart home automation.",
            llm_manager=llm_manager,
        )
        
        self.iot_controller = iot_controller
    
    def _default_system_prompt(self) -> str:
        return """You are an IoT control assistant for smart home devices.

Available devices:
- Light switch: Can turn lights on/off
- Door lock: Can lock/unlock doors (requires high authorization)

Guidelines:
1. Confirm device actions before executing
2. Report device status after operations
3. Handle errors gracefully
4. Prioritize security for sensitive operations like door locks"""
    
    async def process(self, state: AgentState) -> AgentResponse:
        """Process an IoT control task."""
        from ..core.llm import Message
        
        task_lower = state.task.lower()
        
        # Check for light control
        if "light" in task_lower:
            if "on" in task_lower or "turn on" in task_lower:
                if self.iot_controller:
                    result = await self.iot_controller.control_light(True)
                    return AgentResponse(
                        content=f"Light turned on. {result}",
                        agent_type=self.agent_type,
                        completed=True,
                    )
                return AgentResponse(
                    content="Light control requested: ON (IoT controller not configured)",
                    agent_type=self.agent_type,
                    completed=True,
                )
            
            elif "off" in task_lower or "turn off" in task_lower:
                if self.iot_controller:
                    result = await self.iot_controller.control_light(False)
                    return AgentResponse(
                        content=f"Light turned off. {result}",
                        agent_type=self.agent_type,
                        completed=True,
                    )
                return AgentResponse(
                    content="Light control requested: OFF (IoT controller not configured)",
                    agent_type=self.agent_type,
                    completed=True,
                )
        
        # Check for door control
        if "door" in task_lower or "lock" in task_lower:
            if "unlock" in task_lower or "open" in task_lower:
                # This requires high authorization - should be checked by auth manager
                return AgentResponse(
                    content="Door unlock requested. This requires high-level authorization.",
                    agent_type=self.agent_type,
                    metadata={"requires_auth": "high"},
                    completed=True,
                )
            
            elif "lock" in task_lower or "close" in task_lower:
                if self.iot_controller:
                    result = await self.iot_controller.control_door(False)
                    return AgentResponse(
                        content=f"Door locked. {result}",
                        agent_type=self.agent_type,
                        completed=True,
                    )
                return AgentResponse(
                    content="Door lock requested (IoT controller not configured)",
                    agent_type=self.agent_type,
                    completed=True,
                )
        
        # General IoT query
        messages = [
            Message(role="system", content=self._default_system_prompt()),
            Message(role="user", content=state.task),
        ]
        
        try:
            response = self.llm_manager.generate(messages)
            return AgentResponse(
                content=response.content,
                agent_type=self.agent_type,
                completed=True,
            )
        except Exception as e:
            return AgentResponse(
                content=f"IoT operation failed: {e}",
                agent_type=self.agent_type,
                completed=True,
            )


class CommunicationAgent(BaseAgent):
    """
    Communication agent for emails, calendar, and notifications.
    
    Capabilities:
    - Email composition and sending
    - Calendar event management
    - Notification handling
    """
    
    def __init__(self, llm_manager: Any):
        super().__init__(
            name="communication",
            agent_type=AgentType.COMMUNICATION,
            description="Handles emails, calendar, and notification tasks.",
            llm_manager=llm_manager,
        )
    
    def _default_system_prompt(self) -> str:
        return """You are a communication assistant for managing emails, calendar, and notifications.

Capabilities:
- Draft and send emails
- Create and manage calendar events
- Set reminders and notifications

Guidelines:
1. Confirm email content before sending
2. Double-check dates and times for calendar events
3. Be professional in all communications
4. Protect user privacy"""
    
    async def process(self, state: AgentState) -> AgentResponse:
        """Process a communication task."""
        from ..core.llm import Message
        
        messages = [
            Message(role="system", content=self._default_system_prompt()),
            Message(role="user", content=state.task),
        ]
        
        try:
            response = self.llm_manager.generate(messages)
            
            return AgentResponse(
                content=response.content,
                agent_type=self.agent_type,
                completed=True,
            )
        
        except Exception as e:
            logger.error(f"Communication agent error: {e}")
            return AgentResponse(
                content=f"Communication task failed: {e}",
                agent_type=self.agent_type,
                completed=True,
            )


def create_all_agents(llm_manager: Any) -> Dict[str, BaseAgent]:
    """
    Create all specialized agents.
    
    Args:
        llm_manager: LLM manager for the agents.
        
    Returns:
        Dictionary of agent name to agent instance.
    """
    return {
        "research": ResearchAgent(llm_manager),
        "coding": CodingAgent(llm_manager),
        "system": SystemAgent(llm_manager),
        "iot": IoTAgent(llm_manager),
        "communication": CommunicationAgent(llm_manager),
    }
