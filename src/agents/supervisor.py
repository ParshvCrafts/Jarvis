"""
Supervisor Agent for JARVIS.

The supervisor agent routes tasks to specialized sub-agents
and coordinates multi-step workflows using LangGraph.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Literal, Optional, TypedDict, Annotated

from loguru import logger

try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.warning("LangGraph not available")

from .base import AgentState, AgentResponse, AgentType, BaseAgent


class SupervisorState(TypedDict):
    """State for the supervisor graph."""
    messages: Annotated[List[BaseMessage], add_messages]
    task: str
    next_agent: str
    agent_outputs: Dict[str, Any]
    iteration: int
    max_iterations: int
    final_response: str
    completed: bool


AGENT_DESCRIPTIONS = {
    "research": "Handles web searches, information gathering, and summarization tasks.",
    "coding": "Handles code generation, debugging, and technical programming tasks.",
    "system": "Handles system operations like opening apps, file management, and OS control.",
    "iot": "Handles IoT device control like lights, door locks, and smart home devices.",
    "communication": "Handles emails, messages, calendar, and notification tasks.",
    "direct": "Handles simple queries that don't require specialized tools.",
}


class SupervisorAgent(BaseAgent):
    """
    Supervisor agent that routes tasks to specialized agents.
    
    Uses LangGraph to create a stateful workflow that:
    1. Analyzes the user's request
    2. Routes to the appropriate specialized agent
    3. Coordinates multi-agent tasks
    4. Synthesizes final responses
    """
    
    def __init__(
        self,
        llm_manager: Any,
        agents: Optional[Dict[str, BaseAgent]] = None,
        max_iterations: int = 10,
    ):
        """
        Initialize the supervisor agent.
        
        Args:
            llm_manager: LLM manager for generating responses.
            agents: Dictionary of specialized agents.
            max_iterations: Maximum routing iterations.
        """
        super().__init__(
            name="supervisor",
            agent_type=AgentType.SUPERVISOR,
            description="Routes tasks to specialized agents and coordinates workflows.",
            llm_manager=llm_manager,
        )
        
        self.agents = agents or {}
        self.max_iterations = max_iterations
        self._graph = None
        
        if LANGGRAPH_AVAILABLE:
            self._build_graph()
    
    def _default_system_prompt(self) -> str:
        return """You are JARVIS, an advanced AI assistant. You are the supervisor agent responsible for:
1. Understanding user requests
2. Routing tasks to the appropriate specialized agent
3. Coordinating multi-step workflows
4. Providing helpful, accurate responses

Available specialized agents:
{agent_descriptions}

When routing, respond with JSON containing:
- "reasoning": Brief explanation of your routing decision
- "next_agent": One of [{agent_names}] or "FINISH" if task is complete
- "task_for_agent": Specific instructions for the chosen agent

For simple queries (greetings, time, basic questions), use "direct" to respond yourself.
Always be helpful, concise, and professional."""
    
    def _build_graph(self) -> None:
        """Build the LangGraph workflow."""
        if not LANGGRAPH_AVAILABLE:
            return
        
        # Create the graph
        workflow = StateGraph(SupervisorState)
        
        # Add nodes
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("research", self._agent_node("research"))
        workflow.add_node("coding", self._agent_node("coding"))
        workflow.add_node("system", self._agent_node("system"))
        workflow.add_node("iot", self._agent_node("iot"))
        workflow.add_node("communication", self._agent_node("communication"))
        workflow.add_node("direct", self._direct_response_node)
        
        # Add edges
        workflow.set_entry_point("supervisor")
        
        # Conditional routing from supervisor
        workflow.add_conditional_edges(
            "supervisor",
            self._route_to_agent,
            {
                "research": "research",
                "coding": "coding",
                "system": "system",
                "iot": "iot",
                "communication": "communication",
                "direct": "direct",
                "FINISH": END,
            }
        )
        
        # All agents return to supervisor for coordination
        for agent_name in ["research", "coding", "system", "iot", "communication", "direct"]:
            workflow.add_edge(agent_name, "supervisor")
        
        self._graph = workflow.compile()
    
    def _supervisor_node(self, state: SupervisorState) -> SupervisorState:
        """Supervisor decision node."""
        # Check iteration limit
        if state["iteration"] >= state["max_iterations"]:
            return {
                **state,
                "next_agent": "FINISH",
                "final_response": "I apologize, but I wasn't able to complete this task within the allowed steps.",
                "completed": True,
            }
        
        # Build prompt with agent descriptions
        agent_names = list(AGENT_DESCRIPTIONS.keys())
        agent_desc = "\n".join([f"- {k}: {v}" for k, v in AGENT_DESCRIPTIONS.items()])
        
        system_prompt = self._default_system_prompt().format(
            agent_descriptions=agent_desc,
            agent_names=", ".join(agent_names),
        )
        
        # Add context from previous agent outputs
        context = ""
        if state["agent_outputs"]:
            context = "\n\nPrevious agent outputs:\n"
            for agent, output in state["agent_outputs"].items():
                context += f"\n{agent}: {output}\n"
        
        # Get routing decision from LLM
        from ..core.llm import Message
        
        messages = [
            Message(role="system", content=system_prompt + context),
        ]
        
        # Add conversation history
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage):
                messages.append(Message(role="user", content=msg.content))
            elif isinstance(msg, AIMessage):
                messages.append(Message(role="assistant", content=msg.content))
        
        try:
            response = self.llm_manager.generate(messages)
            content = response.content
            
            # Parse routing decision
            try:
                # Try to extract JSON from response
                if "{" in content and "}" in content:
                    json_start = content.index("{")
                    json_end = content.rindex("}") + 1
                    decision = json.loads(content[json_start:json_end])
                else:
                    # Default to direct response
                    decision = {"next_agent": "direct", "reasoning": content}
            except json.JSONDecodeError:
                decision = {"next_agent": "direct", "reasoning": content}
            
            next_agent = decision.get("next_agent", "direct")
            
            # Validate agent name
            if next_agent not in agent_names and next_agent != "FINISH":
                next_agent = "direct"
            
            # Check if we should finish
            if next_agent == "FINISH" or (
                state["agent_outputs"] and 
                decision.get("reasoning", "").lower().find("complete") != -1
            ):
                # Generate final response
                final_response = decision.get("final_response", content)
                if not final_response or final_response == content:
                    # Synthesize from agent outputs
                    if state["agent_outputs"]:
                        final_response = list(state["agent_outputs"].values())[-1]
                    else:
                        final_response = content
                
                return {
                    **state,
                    "next_agent": "FINISH",
                    "final_response": final_response,
                    "completed": True,
                    "iteration": state["iteration"] + 1,
                }
            
            return {
                **state,
                "next_agent": next_agent,
                "iteration": state["iteration"] + 1,
                "messages": state["messages"] + [AIMessage(content=content)],
            }
        
        except Exception as e:
            logger.error(f"Supervisor error: {e}")
            return {
                **state,
                "next_agent": "FINISH",
                "final_response": f"I encountered an error: {e}",
                "completed": True,
            }
    
    def _agent_node(self, agent_name: str):
        """Create a node for a specialized agent."""
        def node(state: SupervisorState) -> SupervisorState:
            agent = self.agents.get(agent_name)
            
            if agent is None:
                output = f"Agent '{agent_name}' not available."
            else:
                try:
                    # Create agent state
                    agent_state = AgentState(
                        messages=[m for m in state["messages"]],
                        task=state["task"],
                        context=state["agent_outputs"],
                    )
                    
                    # Process with agent (sync wrapper for async)
                    import asyncio
                    loop = asyncio.new_event_loop()
                    try:
                        response = loop.run_until_complete(agent.process(agent_state))
                        output = response.content
                    finally:
                        loop.close()
                
                except Exception as e:
                    logger.error(f"Agent {agent_name} error: {e}")
                    output = f"Agent error: {e}"
            
            # Update agent outputs
            agent_outputs = state["agent_outputs"].copy()
            agent_outputs[agent_name] = output
            
            return {
                **state,
                "agent_outputs": agent_outputs,
                "messages": state["messages"] + [AIMessage(content=f"[{agent_name}]: {output}")],
            }
        
        return node
    
    def _direct_response_node(self, state: SupervisorState) -> SupervisorState:
        """Handle direct responses without specialized agents."""
        from ..core.llm import Message
        
        messages = [
            Message(role="system", content="You are JARVIS, a helpful AI assistant. Respond directly and concisely."),
        ]
        
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage):
                messages.append(Message(role="user", content=msg.content))
            elif isinstance(msg, AIMessage):
                messages.append(Message(role="assistant", content=msg.content))
        
        try:
            response = self.llm_manager.generate(messages)
            output = response.content
        except Exception as e:
            output = f"I apologize, I encountered an error: {e}"
        
        agent_outputs = state["agent_outputs"].copy()
        agent_outputs["direct"] = output
        
        return {
            **state,
            "agent_outputs": agent_outputs,
            "final_response": output,
            "completed": True,
            "next_agent": "FINISH",
        }
    
    def _route_to_agent(self, state: SupervisorState) -> str:
        """Route to the next agent based on state."""
        return state["next_agent"]
    
    async def process(self, state: AgentState) -> AgentResponse:
        """Process a request through the supervisor workflow."""
        if not LANGGRAPH_AVAILABLE or self._graph is None:
            # Fallback to direct LLM response
            from ..core.llm import Message
            
            messages = [
                Message(role="system", content="You are JARVIS, a helpful AI assistant."),
                Message(role="user", content=state.task),
            ]
            
            response = self.llm_manager.generate(messages)
            
            return AgentResponse(
                content=response.content,
                agent_type=self.agent_type,
                completed=True,
            )
        
        # Run the graph
        initial_state: SupervisorState = {
            "messages": [HumanMessage(content=state.task)],
            "task": state.task,
            "next_agent": "",
            "agent_outputs": {},
            "iteration": 0,
            "max_iterations": self.max_iterations,
            "final_response": "",
            "completed": False,
        }
        
        try:
            final_state = self._graph.invoke(initial_state)
            
            return AgentResponse(
                content=final_state["final_response"],
                agent_type=self.agent_type,
                completed=final_state["completed"],
                metadata={
                    "iterations": final_state["iteration"],
                    "agents_used": list(final_state["agent_outputs"].keys()),
                },
            )
        except Exception as e:
            logger.error(f"Graph execution error: {e}")
            return AgentResponse(
                content=f"I encountered an error processing your request: {e}",
                agent_type=self.agent_type,
                completed=True,
            )
    
    def register_agent(self, name: str, agent: BaseAgent) -> None:
        """Register a specialized agent."""
        self.agents[name] = agent
        logger.info(f"Registered agent: {name}")
    
    def run_sync(self, task: str) -> str:
        """
        Run the supervisor synchronously.
        
        Args:
            task: User's task/query.
            
        Returns:
            Response string.
        """
        import asyncio
        
        state = AgentState(task=task)
        
        loop = asyncio.new_event_loop()
        try:
            response = loop.run_until_complete(self.process(state))
            return response.content
        finally:
            loop.close()
