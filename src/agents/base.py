"""
Base Agent Module for JARVIS.

Provides the foundation for all specialized agents using LangGraph
for stateful, multi-step workflows.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar

from loguru import logger

try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
    from langchain_core.tools import BaseTool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("LangChain not available")


class AgentType(Enum):
    """Types of specialized agents."""
    SUPERVISOR = "supervisor"
    RESEARCH = "research"
    CODING = "coding"
    SYSTEM = "system"
    IOT = "iot"
    COMMUNICATION = "communication"


@dataclass
class AgentState:
    """State for agent execution."""
    messages: List[BaseMessage] = field(default_factory=list)
    current_agent: Optional[str] = None
    task: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    results: List[Dict[str, Any]] = field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 10
    error: Optional[str] = None
    completed: bool = False
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the state."""
        self.messages.append(message)
    
    def add_result(self, result: Dict[str, Any]) -> None:
        """Add a result to the state."""
        self.results.append({
            **result,
            "timestamp": datetime.now().isoformat(),
            "iteration": self.iteration,
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "messages": [
                {"role": m.type, "content": m.content}
                for m in self.messages
            ],
            "current_agent": self.current_agent,
            "task": self.task,
            "context": self.context,
            "results": self.results,
            "iteration": self.iteration,
            "completed": self.completed,
            "error": self.error,
        }


@dataclass
class AgentResponse:
    """Response from an agent."""
    content: str
    agent_type: AgentType
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    next_agent: Optional[str] = None
    completed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base class for all JARVIS agents.
    
    Provides common functionality for:
    - Tool management
    - State handling
    - LLM interaction
    """
    
    def __init__(
        self,
        name: str,
        agent_type: AgentType,
        description: str,
        llm_manager: Any,
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize the base agent.
        
        Args:
            name: Agent name.
            agent_type: Type of agent.
            description: Agent description for routing.
            llm_manager: LLM manager for generating responses.
            tools: List of tools available to this agent.
            system_prompt: Custom system prompt.
        """
        self.name = name
        self.agent_type = agent_type
        self.description = description
        self.llm_manager = llm_manager
        self.tools = tools or []
        self.system_prompt = system_prompt or self._default_system_prompt()
        
        logger.debug(f"Initialized agent: {name} ({agent_type.value})")
    
    @abstractmethod
    def _default_system_prompt(self) -> str:
        """Get the default system prompt for this agent."""
        pass
    
    @abstractmethod
    async def process(self, state: AgentState) -> AgentResponse:
        """
        Process the current state and return a response.
        
        Args:
            state: Current agent state.
            
        Returns:
            AgentResponse with results.
        """
        pass
    
    def get_tool_descriptions(self) -> str:
        """Get formatted tool descriptions."""
        if not self.tools:
            return "No tools available."
        
        descriptions = []
        for tool in self.tools:
            descriptions.append(f"- {tool.name}: {tool.description}")
        
        return "\n".join(descriptions)
    
    def get_tool_by_name(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
    
    async def execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> Any:
        """
        Execute a tool by name.
        
        Args:
            tool_name: Name of the tool to execute.
            tool_input: Input arguments for the tool.
            
        Returns:
            Tool execution result.
        """
        tool = self.get_tool_by_name(tool_name)
        if tool is None:
            raise ValueError(f"Tool not found: {tool_name}")
        
        try:
            result = await tool.ainvoke(tool_input)
            logger.debug(f"Tool {tool_name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            raise


class ToolRegistry:
    """
    Registry for managing tools across agents.
    
    Provides centralized tool management and discovery.
    """
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._tool_agents: Dict[str, List[str]] = {}
    
    def register(
        self,
        tool: BaseTool,
        agent_types: Optional[List[AgentType]] = None,
    ) -> None:
        """
        Register a tool.
        
        Args:
            tool: Tool to register.
            agent_types: Agent types that can use this tool.
        """
        self._tools[tool.name] = tool
        
        if agent_types:
            for agent_type in agent_types:
                if agent_type.value not in self._tool_agents:
                    self._tool_agents[agent_type.value] = []
                self._tool_agents[agent_type.value].append(tool.name)
        
        logger.debug(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_tools_for_agent(self, agent_type: AgentType) -> List[BaseTool]:
        """Get all tools available for an agent type."""
        tool_names = self._tool_agents.get(agent_type.value, [])
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())


# Global tool registry
tool_registry = ToolRegistry()
