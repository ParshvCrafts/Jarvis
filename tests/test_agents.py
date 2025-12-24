"""
Tests for the agent system including enhanced supervisor.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestIntentClassifier:
    """Tests for the intent classifier."""
    
    def test_greeting_intent(self):
        """Test greeting detection."""
        from src.agents.supervisor_enhanced import IntentClassifier, IntentType
        
        greetings = ["hello", "hi there", "hey", "good morning", "what's up"]
        
        for greeting in greetings:
            result = IntentClassifier.classify(greeting)
            assert result.intent == IntentType.GREETING, f"Failed for: {greeting}"
            assert result.suggested_agent == "direct"
    
    def test_iot_intent(self):
        """Test IoT command detection."""
        from src.agents.supervisor_enhanced import IntentClassifier, IntentType
        
        iot_commands = [
            "turn on the lights",
            "turn off the lamp",
            "lock the door",
            "unlock the garage",
            "set the temperature to 72",
        ]
        
        for cmd in iot_commands:
            result = IntentClassifier.classify(cmd)
            assert result.intent == IntentType.IOT, f"Failed for: {cmd}"
            assert result.suggested_agent == "iot"
    
    def test_system_intent(self):
        """Test system command detection."""
        from src.agents.supervisor_enhanced import IntentClassifier, IntentType
        
        system_commands = [
            "open chrome",
            "take a screenshot",
            "launch notepad",
            "close the browser",
        ]
        
        for cmd in system_commands:
            result = IntentClassifier.classify(cmd)
            assert result.intent == IntentType.SYSTEM, f"Failed for: {cmd}"
            assert result.suggested_agent == "system"
    
    def test_coding_intent(self):
        """Test coding task detection."""
        from src.agents.supervisor_enhanced import IntentClassifier, IntentType
        
        coding_tasks = [
            "write a python function",
            "debug this code",
            "git status",
            "explain this error",
        ]
        
        for task in coding_tasks:
            result = IntentClassifier.classify(task)
            assert result.intent == IntentType.CODING, f"Failed for: {task}"
            assert result.suggested_agent == "coding"
    
    def test_research_intent(self):
        """Test research task detection."""
        from src.agents.supervisor_enhanced import IntentClassifier, IntentType
        
        research_tasks = [
            "search for python tutorials",
            "what is machine learning",
            "tell me about quantum computing",
        ]
        
        for task in research_tasks:
            result = IntentClassifier.classify(task)
            assert result.intent == IntentType.RESEARCH, f"Failed for: {task}"
            assert result.suggested_agent == "research"
    
    def test_unknown_intent(self):
        """Test unknown intent fallback."""
        from src.agents.supervisor_enhanced import IntentClassifier, IntentType
        
        result = IntentClassifier.classify("asdfghjkl random gibberish")
        assert result.intent == IntentType.UNKNOWN
        assert result.suggested_agent == "direct"


class TestContextEngineer:
    """Tests for context engineering."""
    
    def test_context_preparation(self):
        """Test context preparation for agents."""
        from src.agents.supervisor_enhanced import ContextEngineer
        
        context = ContextEngineer.prepare_context_for_agent(
            agent_name="research",
            task="Find information about AI",
            conversation_history=[],
            agent_outputs={"memory": "User previously asked about ML"},
            memory_context="User is interested in AI topics",
        )
        
        assert "Relevant memories" in context
        assert "AI topics" in context
    
    def test_context_filtering(self):
        """Test that irrelevant outputs are filtered."""
        from src.agents.supervisor_enhanced import ContextEngineer
        
        # Research agent should get memory outputs but not system outputs
        relevant = ContextEngineer._filter_relevant_outputs(
            "research",
            {"memory": "relevant", "system": "irrelevant", "iot": "also irrelevant"}
        )
        
        assert "memory" in relevant
        assert "system" not in relevant
        assert "iot" not in relevant
    
    def test_conversation_truncation(self):
        """Test long conversation truncation."""
        from src.agents.supervisor_enhanced import ContextEngineer
        
        long_text = "x" * 10000
        truncated = ContextEngineer._summarize_conversation(long_text)
        
        assert len(truncated) <= ContextEngineer.MAX_CONTEXT_LENGTH + 20  # Allow for suffix


class TestIntentType:
    """Tests for IntentType enum."""
    
    def test_all_intent_types_exist(self):
        """Test all intent types are defined."""
        from src.agents.supervisor_enhanced import IntentType
        
        expected = [
            "GREETING", "QUESTION", "COMMAND", "RESEARCH",
            "CODING", "SYSTEM", "IOT", "COMMUNICATION",
            "MEMORY", "UNKNOWN"
        ]
        
        for intent_name in expected:
            assert hasattr(IntentType, intent_name)


class TestEnhancedSupervisorAgent:
    """Tests for the enhanced supervisor agent."""
    
    def test_supervisor_import(self):
        """Test enhanced supervisor can be imported."""
        from src.agents.supervisor_enhanced import EnhancedSupervisorAgent
        
        assert EnhancedSupervisorAgent is not None
    
    def test_agent_descriptions(self):
        """Test agent descriptions are defined."""
        from src.agents.supervisor_enhanced import ENHANCED_AGENT_DESCRIPTIONS
        
        expected_agents = ["research", "coding", "system", "iot", "communication", "memory", "direct"]
        
        for agent in expected_agents:
            assert agent in ENHANCED_AGENT_DESCRIPTIONS


class TestIntentClassification:
    """Tests for IntentClassification dataclass."""
    
    def test_classification_creation(self):
        """Test IntentClassification can be created."""
        from src.agents.supervisor_enhanced import IntentClassification, IntentType
        
        classification = IntentClassification(
            intent=IntentType.GREETING,
            confidence=0.9,
            suggested_agent="direct",
        )
        
        assert classification.intent == IntentType.GREETING
        assert classification.confidence == 0.9
        assert classification.suggested_agent == "direct"
        assert classification.entities == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
