"""
Enhanced Supervisor Agent for JARVIS.

Improvements over original:
- Better context engineering (only relevant context to each agent)
- Memory agent for long-term recall
- Conversation summarization for long contexts
- Intent classification for faster routing
- Tool integration with enhanced tools
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict, Annotated

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


class IntentType(Enum):
    """Types of user intents for fast routing."""
    GREETING = "greeting"
    QUESTION = "question"
    COMMAND = "command"
    RESEARCH = "research"
    WEATHER = "weather"
    CODING = "coding"
    SYSTEM = "system"
    IOT = "iot"
    COMMUNICATION = "communication"
    MEMORY = "memory"
    DOCUMENTS = "documents"
    UNKNOWN = "unknown"


@dataclass
class IntentClassification:
    """Result of intent classification."""
    intent: IntentType
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    suggested_agent: str = "direct"


class IntentClassifier:
    """
    Fast intent classification without LLM.
    
    Uses pattern matching for common intents to avoid
    unnecessary LLM calls for simple routing.
    """
    
    GREETING_PATTERNS = [
        r"^(hi|hello|hey|good\s*(morning|afternoon|evening)|howdy)",
        r"^(what'?s?\s*up|how\s*are\s*you)",
    ]
    
    QUESTION_PATTERNS = [
        r"^(what|who|where|when|why|how|is|are|do|does|can|could|would|will)",
    ]
    
    IOT_PATTERNS = [
        r"(turn\s*(on|off)|switch|toggle|dim|brighten)\s*(the\s*)?(light|lamp|bulb)",
        r"(lock|unlock|open|close)\s*(the\s*)?(door|gate|garage)",
        r"(set|adjust)\s*(the\s*)?(temperature|thermostat|ac|heater)",
    ]
    
    SYSTEM_PATTERNS = [
        r"(open|launch|start|run|close|quit|exit)\s*(the\s*)?(\w+)",
        r"(take\s*a?\s*)?screenshot",
        r"(volume|mute|unmute|brightness)",
        r"(copy|paste|clipboard)",
    ]
    
    CODING_PATTERNS = [
        r"(write|create|generate|debug|fix|refactor)\s*(a\s*)?(code|function|class|script|program)",
        r"(python|javascript|java|c\+\+|rust|go|typescript)",
        r"(git\s*(status|commit|push|pull|branch))",
        r"(explain|review)\s*(this\s*)?(code|function|error)",
    ]
    
    WEATHER_PATTERNS = [
        r"(weather|temperature|forecast|rain|snow|sunny|cloudy|humid)",
        r"(will\s*it\s*(rain|snow|be\s*(hot|cold|warm)))",
        r"(how\s*(hot|cold|warm)\s*(is|will))",
        r"(what'?s?\s*the\s*(weather|temperature|forecast))",
    ]
    
    RESEARCH_PATTERNS = [
        r"(search|look\s*up|find|research)\s*(for|about)?",
        r"(what\s*is|who\s*is|tell\s*me\s*about)",
        r"(summarize|explain)\s*(the\s*)?(article|page|website)",
    ]
    
    DOCUMENTS_PATTERNS = [
        r"(what\s*(does|did)\s*(the|my|this)\s*(document|pdf|file|paper)\s*say)",
        r"(in\s*(the|my)\s*(document|pdf|file))",
        r"(upload|ingest|add)\s*(a\s*)?(document|pdf|file)",
        r"(search|find|look)\s*(in|through)\s*(my\s*)?(documents|files)",
    ]
    
    MEMORY_PATTERNS = [
        r"(remember|recall|what\s*did\s*(i|we)|last\s*time)",
        r"(my\s*preference|i\s*(like|prefer|want))",
        r"(save|store|note)\s*(this|that)",
    ]
    
    COMMUNICATION_PATTERNS = [
        r"(send|compose|write)\s*(an?\s*)?(email|message|text)",
        r"(check|read)\s*(my\s*)?(email|messages|inbox)",
        r"(schedule|calendar|meeting|appointment)",
    ]
    
    @classmethod
    def classify(cls, text: str) -> IntentClassification:
        """
        Classify user intent using pattern matching.
        
        Args:
            text: User input text.
            
        Returns:
            IntentClassification with detected intent.
        """
        text_lower = text.lower().strip()
        
        # Check patterns in order of specificity
        pattern_checks = [
            (cls.WEATHER_PATTERNS, IntentType.WEATHER, "research"),  # Weather -> Research agent
            (cls.IOT_PATTERNS, IntentType.IOT, "iot"),
            (cls.SYSTEM_PATTERNS, IntentType.SYSTEM, "system"),
            (cls.CODING_PATTERNS, IntentType.CODING, "coding"),
            (cls.COMMUNICATION_PATTERNS, IntentType.COMMUNICATION, "communication"),
            (cls.DOCUMENTS_PATTERNS, IntentType.DOCUMENTS, "research"),  # Documents -> Research agent
            (cls.MEMORY_PATTERNS, IntentType.MEMORY, "memory"),
            (cls.RESEARCH_PATTERNS, IntentType.RESEARCH, "research"),
            (cls.GREETING_PATTERNS, IntentType.GREETING, "direct"),
            (cls.QUESTION_PATTERNS, IntentType.QUESTION, "research"),
        ]
        
        for patterns, intent_type, agent in pattern_checks:
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return IntentClassification(
                        intent=intent_type,
                        confidence=0.8,
                        suggested_agent=agent,
                    )
        
        return IntentClassification(
            intent=IntentType.UNKNOWN,
            confidence=0.5,
            suggested_agent="direct",
        )


class ContextEngineer:
    """
    Manages context passed to agents.
    
    Ensures each agent receives only relevant context
    to avoid confusion and reduce token usage.
    """
    
    MAX_CONTEXT_LENGTH = 4000  # Characters
    
    @staticmethod
    def prepare_context_for_agent(
        agent_name: str,
        task: str,
        conversation_history: List[BaseMessage],
        agent_outputs: Dict[str, Any],
        memory_context: Optional[str] = None,
    ) -> str:
        """
        Prepare context tailored for a specific agent.
        
        Args:
            agent_name: Name of the target agent.
            task: Current task.
            conversation_history: Recent messages.
            agent_outputs: Outputs from other agents.
            memory_context: Relevant memories.
            
        Returns:
            Formatted context string.
        """
        context_parts = []
        
        # Add relevant memory context
        if memory_context:
            context_parts.append(f"Relevant memories:\n{memory_context}")
        
        # Add relevant agent outputs
        relevant_outputs = ContextEngineer._filter_relevant_outputs(
            agent_name, agent_outputs
        )
        if relevant_outputs:
            context_parts.append(f"Previous findings:\n{relevant_outputs}")
        
        # Add recent conversation (summarized if too long)
        if conversation_history:
            conv_text = ContextEngineer._format_conversation(conversation_history)
            if len(conv_text) > ContextEngineer.MAX_CONTEXT_LENGTH:
                conv_text = ContextEngineer._summarize_conversation(conv_text)
            context_parts.append(f"Conversation:\n{conv_text}")
        
        return "\n\n".join(context_parts)
    
    @staticmethod
    def _filter_relevant_outputs(
        agent_name: str,
        agent_outputs: Dict[str, Any],
    ) -> str:
        """Filter outputs relevant to the target agent."""
        # Define which agents' outputs are relevant to each agent
        relevance_map = {
            "research": ["memory"],
            "coding": ["research", "memory"],
            "system": ["memory"],
            "iot": ["memory"],
            "communication": ["research", "memory"],
            "direct": ["research", "memory"],
        }
        
        relevant_agents = relevance_map.get(agent_name, [])
        relevant = {k: v for k, v in agent_outputs.items() if k in relevant_agents}
        
        if not relevant:
            return ""
        
        return "\n".join([f"[{k}]: {v}" for k, v in relevant.items()])
    
    @staticmethod
    def _format_conversation(messages: List[BaseMessage]) -> str:
        """Format conversation messages."""
        lines = []
        for msg in messages[-10:]:  # Last 10 messages
            if isinstance(msg, HumanMessage):
                lines.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                lines.append(f"Assistant: {msg.content[:200]}...")
        return "\n".join(lines)
    
    @staticmethod
    def _summarize_conversation(text: str) -> str:
        """Summarize long conversation (simple truncation for now)."""
        if len(text) > ContextEngineer.MAX_CONTEXT_LENGTH:
            return text[:ContextEngineer.MAX_CONTEXT_LENGTH] + "...[truncated]"
        return text


class EnhancedSupervisorState(TypedDict):
    """State for the enhanced supervisor graph."""
    messages: Annotated[List[BaseMessage], add_messages]
    task: str
    intent: str
    next_agent: str
    agent_outputs: Dict[str, Any]
    memory_context: str
    iteration: int
    max_iterations: int
    final_response: str
    completed: bool


ENHANCED_AGENT_DESCRIPTIONS = {
    "research": "Web searches, information gathering, fact-finding, summarization.",
    "coding": "Code generation, debugging, Git operations, technical tasks.",
    "system": "Opening apps, file management, screenshots, OS control.",
    "iot": "Smart home: lights, doors, temperature, device status.",
    "communication": "Emails, messages, calendar, notifications.",
    "memory": "Long-term recall, preferences, past conversations.",
    "direct": "Simple queries, greetings, basic questions.",
}


class EnhancedSupervisorAgent(BaseAgent):
    """
    Enhanced supervisor with better context engineering.
    
    Improvements:
    - Fast intent classification (no LLM for simple routing)
    - Context engineering (relevant context per agent)
    - Memory agent integration
    - Conversation summarization
    """
    
    def __init__(
        self,
        llm_manager: Any,
        agents: Optional[Dict[str, BaseAgent]] = None,
        max_iterations: int = 10,
        memory_store: Optional[Any] = None,
    ):
        """
        Initialize the enhanced supervisor.
        
        Args:
            llm_manager: LLM manager for generating responses.
            agents: Dictionary of specialized agents.
            max_iterations: Maximum routing iterations.
            memory_store: Optional memory store for context.
        """
        super().__init__(
            name="supervisor",
            agent_type=AgentType.SUPERVISOR,
            description="Routes tasks to specialized agents with context engineering.",
            llm_manager=llm_manager,
        )
        
        self.agents = agents or {}
        self.max_iterations = max_iterations
        self.memory_store = memory_store
        self.intent_classifier = IntentClassifier()
        self.context_engineer = ContextEngineer()
        self._graph = None
        
        if LANGGRAPH_AVAILABLE:
            self._build_graph()
    
    def _default_system_prompt(self) -> str:
        """Get the default system prompt for the supervisor agent."""
        agent_desc = "\n".join([f"- {k}: {v}" for k, v in ENHANCED_AGENT_DESCRIPTIONS.items()])
        return f"""You are JARVIS, an advanced AI assistant supervisor.

Your role is to:
1. Understand user requests and classify their intent
2. Route tasks to the most appropriate specialized agent
3. Coordinate responses from multiple agents when needed
4. Provide helpful, accurate, and concise information

Available specialized agents:
{agent_desc}

Guidelines:
- For simple greetings or questions, respond directly
- For complex tasks, delegate to specialized agents
- Always be helpful, professional, and efficient
- If uncertain, ask for clarification
"""
    
    def _build_graph(self) -> None:
        """Build the enhanced LangGraph workflow."""
        if not LANGGRAPH_AVAILABLE:
            return
        
        workflow = StateGraph(EnhancedSupervisorState)
        
        # Add nodes
        workflow.add_node("classify", self._classify_node)
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("research", self._agent_node("research"))
        workflow.add_node("coding", self._agent_node("coding"))
        workflow.add_node("system", self._agent_node("system"))
        workflow.add_node("iot", self._agent_node("iot"))
        workflow.add_node("communication", self._agent_node("communication"))
        workflow.add_node("memory", self._memory_node)
        workflow.add_node("direct", self._direct_response_node)
        workflow.add_node("synthesize", self._synthesize_node)
        
        # Entry point is classification
        workflow.set_entry_point("classify")
        
        # Classification routes to supervisor or direct agent
        workflow.add_conditional_edges(
            "classify",
            self._route_from_classify,
            {
                "supervisor": "supervisor",
                "direct": "direct",
                "iot": "iot",
                "system": "system",
            }
        )
        
        # Supervisor routes to agents
        workflow.add_conditional_edges(
            "supervisor",
            self._route_to_agent,
            {
                "research": "research",
                "coding": "coding",
                "system": "system",
                "iot": "iot",
                "communication": "communication",
                "memory": "memory",
                "direct": "direct",
                "synthesize": "synthesize",
                "FINISH": END,
            }
        )
        
        # Agents return to supervisor
        for agent_name in ["research", "coding", "system", "iot", "communication", "memory"]:
            workflow.add_edge(agent_name, "supervisor")
        
        # Direct and synthesize go to END
        workflow.add_edge("direct", END)
        workflow.add_edge("synthesize", END)
        
        self._graph = workflow.compile()
    
    def _classify_node(self, state: EnhancedSupervisorState) -> EnhancedSupervisorState:
        """Fast intent classification node."""
        classification = self.intent_classifier.classify(state["task"])
        
        # For high-confidence simple intents, skip supervisor
        if classification.confidence >= 0.8 and classification.intent in [
            IntentType.GREETING, IntentType.IOT, IntentType.SYSTEM
        ]:
            return {
                **state,
                "intent": classification.intent.value,
                "next_agent": classification.suggested_agent,
            }
        
        # Otherwise, go to supervisor for complex routing
        return {
            **state,
            "intent": classification.intent.value,
            "next_agent": "supervisor",
        }
    
    def _route_from_classify(self, state: EnhancedSupervisorState) -> str:
        """Route based on classification."""
        next_agent = state["next_agent"]
        if next_agent in ["direct", "iot", "system"]:
            return next_agent
        return "supervisor"
    
    def _supervisor_node(self, state: EnhancedSupervisorState) -> EnhancedSupervisorState:
        """Supervisor decision node with context engineering."""
        if state["iteration"] >= state["max_iterations"]:
            return {
                **state,
                "next_agent": "synthesize",
                "completed": True,
            }
        
        # Build agent descriptions
        agent_names = list(ENHANCED_AGENT_DESCRIPTIONS.keys())
        agent_desc = "\n".join([f"- {k}: {v}" for k, v in ENHANCED_AGENT_DESCRIPTIONS.items()])
        
        system_prompt = f"""You are JARVIS supervisor. Route the task to the best agent.

Available agents:
{agent_desc}

Respond with JSON:
{{"next_agent": "<agent_name or FINISH>", "reasoning": "<brief reason>"}}

If task is complete, use "synthesize" to generate final response."""
        
        # Prepare context
        context = self.context_engineer.prepare_context_for_agent(
            "supervisor",
            state["task"],
            state["messages"],
            state["agent_outputs"],
            state.get("memory_context"),
        )
        
        from ..core.llm import Message
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=f"Task: {state['task']}\n\nContext:\n{context}"),
        ]
        
        try:
            response = self.llm_manager.generate(messages)
            content = response.content
            
            # Parse JSON
            try:
                if "{" in content:
                    json_str = content[content.index("{"):content.rindex("}")+1]
                    decision = json.loads(json_str)
                else:
                    decision = {"next_agent": "direct"}
            except (json.JSONDecodeError, ValueError):
                decision = {"next_agent": "direct"}
            
            next_agent = decision.get("next_agent", "direct")
            
            # Validate
            if next_agent not in agent_names + ["FINISH", "synthesize"]:
                next_agent = "direct"
            
            if next_agent == "FINISH":
                next_agent = "synthesize"
            
            return {
                **state,
                "next_agent": next_agent,
                "iteration": state["iteration"] + 1,
            }
        
        except Exception as e:
            logger.error(f"Supervisor error: {e}")
            return {
                **state,
                "next_agent": "direct",
                "iteration": state["iteration"] + 1,
            }
    
    def _agent_node(self, agent_name: str):
        """Create a node for a specialized agent."""
        def node(state: EnhancedSupervisorState) -> EnhancedSupervisorState:
            agent = self.agents.get(agent_name)
            
            if agent is None:
                output = f"Agent '{agent_name}' not available."
            else:
                try:
                    # Prepare context for this specific agent
                    context = self.context_engineer.prepare_context_for_agent(
                        agent_name,
                        state["task"],
                        state["messages"],
                        state["agent_outputs"],
                        state.get("memory_context"),
                    )
                    
                    agent_state = AgentState(
                        messages=state["messages"],
                        task=state["task"],
                        context={"prepared_context": context, **state["agent_outputs"]},
                    )
                    
                    import asyncio
                    loop = asyncio.new_event_loop()
                    try:
                        response = loop.run_until_complete(agent.process(agent_state))
                        output = response.content
                    finally:
                        loop.close()
                
                except Exception as e:
                    logger.error(f"Agent {agent_name} error: {e}")
                    output = f"Error: {e}"
            
            agent_outputs = state["agent_outputs"].copy()
            agent_outputs[agent_name] = output
            
            return {
                **state,
                "agent_outputs": agent_outputs,
            }
        
        return node
    
    def _memory_node(self, state: EnhancedSupervisorState) -> EnhancedSupervisorState:
        """Memory agent node for long-term recall."""
        if self.memory_store is None:
            return {
                **state,
                "agent_outputs": {**state["agent_outputs"], "memory": "No memory store configured."},
            }
        
        try:
            # Search memory for relevant context
            results = self.memory_store.search(state["task"], k=3)
            memory_context = "\n".join([r.content for r in results]) if results else ""
            
            return {
                **state,
                "memory_context": memory_context,
                "agent_outputs": {**state["agent_outputs"], "memory": memory_context or "No relevant memories found."},
            }
        except Exception as e:
            logger.error(f"Memory error: {e}")
            return {
                **state,
                "agent_outputs": {**state["agent_outputs"], "memory": f"Memory error: {e}"},
            }
    
    def _direct_response_node(self, state: EnhancedSupervisorState) -> EnhancedSupervisorState:
        """Handle direct responses."""
        from ..core.llm import Message
        
        messages = [
            Message(role="system", content="You are JARVIS, a helpful AI assistant. Be concise and helpful."),
            Message(role="user", content=state["task"]),
        ]
        
        try:
            response = self.llm_manager.generate(messages)
            output = response.content
        except Exception as e:
            output = f"I apologize, I encountered an error: {e}"
        
        return {
            **state,
            "final_response": output,
            "completed": True,
        }
    
    def _synthesize_node(self, state: EnhancedSupervisorState) -> EnhancedSupervisorState:
        """Synthesize final response from agent outputs."""
        from ..core.llm import Message
        
        # Collect all agent outputs
        outputs = state["agent_outputs"]
        
        if not outputs:
            return {
                **state,
                "final_response": "I wasn't able to complete this task.",
                "completed": True,
            }
        
        # If only one agent, use its output directly
        if len(outputs) == 1:
            return {
                **state,
                "final_response": list(outputs.values())[0],
                "completed": True,
            }
        
        # Synthesize from multiple agents
        outputs_text = "\n\n".join([f"[{k}]: {v}" for k, v in outputs.items()])
        
        messages = [
            Message(role="system", content="Synthesize the following agent outputs into a coherent response for the user. Be concise."),
            Message(role="user", content=f"Task: {state['task']}\n\nAgent outputs:\n{outputs_text}"),
        ]
        
        try:
            response = self.llm_manager.generate(messages)
            final = response.content
        except Exception as e:
            final = list(outputs.values())[-1]  # Use last output
        
        return {
            **state,
            "final_response": final,
            "completed": True,
        }
    
    def _route_to_agent(self, state: EnhancedSupervisorState) -> str:
        """Route to the next agent."""
        return state["next_agent"]
    
    async def process(self, state: AgentState) -> AgentResponse:
        """Process a request through the enhanced supervisor."""
        if not LANGGRAPH_AVAILABLE or self._graph is None:
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
        
        initial_state: EnhancedSupervisorState = {
            "messages": [HumanMessage(content=state.task)],
            "task": state.task,
            "intent": "",
            "next_agent": "",
            "agent_outputs": {},
            "memory_context": "",
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
                    "intent": final_state["intent"],
                    "iterations": final_state["iteration"],
                    "agents_used": list(final_state["agent_outputs"].keys()),
                },
            )
        except Exception as e:
            logger.error(f"Graph execution error: {e}")
            return AgentResponse(
                content=f"I encountered an error: {e}",
                agent_type=self.agent_type,
                completed=True,
            )
    
    def run_sync(self, task: str) -> str:
        """Run the supervisor synchronously."""
        import asyncio
        
        state = AgentState(task=task)
        
        loop = asyncio.new_event_loop()
        try:
            response = loop.run_until_complete(self.process(state))
            return response.content
        finally:
            loop.close()
