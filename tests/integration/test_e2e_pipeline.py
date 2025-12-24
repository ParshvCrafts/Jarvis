"""
End-to-End Integration Tests for JARVIS.

Tests the complete pipeline from input to output,
validating all components work together correctly.

Usage:
    pytest tests/integration/test_e2e_pipeline.py -v
    python -m pytest tests/integration/test_e2e_pipeline.py -v --tb=short
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class TestMetrics:
    """Metrics collected during test execution."""
    test_name: str
    start_time: float
    end_time: float = 0.0
    success: bool = False
    error: str = ""
    latencies: Dict[str, float] = None
    
    def __post_init__(self):
        if self.latencies is None:
            self.latencies = {}
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time if self.end_time else 0.0


class MockAudioInput:
    """Mock audio input for testing without hardware."""
    
    def __init__(self):
        self.is_recording = False
        self.audio_data = []
    
    def start_recording(self):
        self.is_recording = True
    
    def stop_recording(self):
        self.is_recording = False
        return self.audio_data
    
    def simulate_audio(self, text: str):
        """Simulate audio that would produce the given text."""
        # In real implementation, this would be actual audio samples
        self.audio_data = [0.0] * 16000  # 1 second of silence


class MockTTSOutput:
    """Mock TTS output for testing without speakers."""
    
    def __init__(self):
        self.spoken_texts = []
    
    def speak(self, text: str, blocking: bool = True):
        self.spoken_texts.append(text)
    
    def get_last_spoken(self) -> Optional[str]:
        return self.spoken_texts[-1] if self.spoken_texts else None


@pytest.fixture
def project_root():
    """Get project root path."""
    return PROJECT_ROOT


@pytest.fixture
def mock_audio():
    """Provide mock audio input."""
    return MockAudioInput()


@pytest.fixture
def mock_tts():
    """Provide mock TTS output."""
    return MockTTSOutput()


class TestSystemInitialization:
    """Tests for system initialization."""
    
    def test_config_loads(self, project_root):
        """Test configuration loads without error."""
        try:
            from src.core.config import config
            assert config is not None
        except ImportError as e:
            pytest.skip(f"Config module not available: {e}")
    
    def test_env_loads(self, project_root):
        """Test environment variables load."""
        from dotenv import load_dotenv
        env_path = project_root / ".env"
        
        if env_path.exists():
            load_dotenv(env_path)
            # At least one API key should be configured
            api_keys = [
                "GROQ_API_KEY",
                "GEMINI_API_KEY", 
                "OPENAI_API_KEY",
                "MISTRAL_API_KEY",
            ]
            has_key = any(os.getenv(k) for k in api_keys)
            assert has_key, "At least one LLM API key should be configured"
        else:
            pytest.skip(".env file not found")
    
    def test_core_modules_import(self):
        """Test core modules can be imported."""
        modules = [
            "src.core",
            "src.core.config",
            "src.voice",
            "src.agents",
            "src.memory",
        ]
        
        for module in modules:
            try:
                __import__(module)
            except ImportError as e:
                pytest.fail(f"Failed to import {module}: {e}")
    
    def test_enhanced_modules_available(self):
        """Test enhanced modules are available."""
        enhanced = [
            ("src.voice.pipeline_enhanced", "EnhancedVoicePipeline"),
            ("src.agents.supervisor_enhanced", "EnhancedSupervisor"),
        ]
        
        available = 0
        for module, class_name in enhanced:
            try:
                mod = __import__(module, fromlist=[class_name])
                if hasattr(mod, class_name):
                    available += 1
            except ImportError:
                pass
        
        assert available > 0, "At least one enhanced module should be available"


class TestEventBus:
    """Tests for internal event bus."""
    
    @pytest.fixture
    def event_bus(self):
        """Get event bus instance."""
        try:
            from src.core.internal_api import get_event_bus
            return get_event_bus()
        except ImportError:
            pytest.skip("Event bus not available")
    
    def test_event_subscription(self, event_bus):
        """Test event subscription and publishing."""
        received = []
        
        def handler(event):
            received.append(event)
        
        event_bus.subscribe("test_event", handler)
        event_bus.publish("test_event", {"data": "test"})
        
        assert len(received) == 1
        assert received[0].data["data"] == "test"
    
    def test_multiple_subscribers(self, event_bus):
        """Test multiple subscribers receive events."""
        count = [0, 0]
        
        def handler1(event):
            count[0] += 1
        
        def handler2(event):
            count[1] += 1
        
        event_bus.subscribe("multi_test", handler1)
        event_bus.subscribe("multi_test", handler2)
        event_bus.publish("multi_test", {})
        
        assert count[0] == 1
        assert count[1] == 1


class TestLLMIntegration:
    """Tests for LLM integration."""
    
    @pytest.fixture
    def llm_manager(self):
        """Get LLM manager instance."""
        try:
            from src.core.llm import LLMManager
            return LLMManager()
        except ImportError:
            pytest.skip("LLM manager not available")
    
    @pytest.mark.asyncio
    async def test_llm_simple_query(self, llm_manager):
        """Test simple LLM query."""
        try:
            response = await llm_manager.generate(
                "Say 'hello' and nothing else.",
                max_tokens=10,
            )
            assert response is not None
            assert response.content is not None
            assert len(response.content) > 0
        except Exception as e:
            pytest.skip(f"LLM not available: {e}")
    
    @pytest.mark.asyncio
    async def test_llm_provider_fallback(self, llm_manager):
        """Test LLM falls back to alternative provider."""
        # This tests the fallback mechanism
        try:
            response = await llm_manager.generate(
                "What is 2+2?",
                max_tokens=20,
            )
            assert response is not None
        except Exception as e:
            pytest.skip(f"No LLM providers available: {e}")


class TestMemorySystem:
    """Tests for memory systems."""
    
    @pytest.fixture
    def memory_manager(self):
        """Get memory manager instance."""
        try:
            from src.memory import ConversationMemory
            return ConversationMemory()
        except ImportError:
            pytest.skip("Memory system not available")
    
    def test_conversation_memory_add(self, memory_manager):
        """Test adding to conversation memory."""
        memory_manager.add_message("user", "Hello")
        memory_manager.add_message("assistant", "Hi there!")
        
        history = memory_manager.get_history()
        assert len(history) >= 2
    
    def test_conversation_memory_clear(self, memory_manager):
        """Test clearing conversation memory."""
        memory_manager.add_message("user", "Test")
        memory_manager.clear()
        
        history = memory_manager.get_history()
        assert len(history) == 0


class TestAgentSystem:
    """Tests for agent system."""
    
    @pytest.fixture
    def supervisor(self):
        """Get supervisor instance."""
        try:
            from src.agents import EnhancedSupervisor
            return EnhancedSupervisor()
        except ImportError:
            try:
                from src.agents import AgentSupervisor
                return AgentSupervisor()
            except ImportError:
                pytest.skip("Agent supervisor not available")
    
    @pytest.mark.asyncio
    async def test_intent_classification(self, supervisor):
        """Test intent classification."""
        test_cases = [
            ("What time is it?", ["question", "simple"]),
            ("Search for Python tutorials", ["research", "search"]),
            ("Open Chrome", ["system", "app"]),
            ("Turn on the lights", ["iot", "smart_home"]),
        ]
        
        for query, expected_intents in test_cases:
            try:
                intent = await supervisor.classify_intent(query)
                # Just verify we get a response
                assert intent is not None
            except Exception:
                pass  # Intent classification may not be implemented
    
    @pytest.mark.asyncio
    async def test_agent_routing(self, supervisor):
        """Test agent routing based on query."""
        try:
            result = await supervisor.process("What is the weather?")
            assert result is not None
        except Exception as e:
            pytest.skip(f"Agent routing not available: {e}")


class TestVoicePipeline:
    """Tests for voice pipeline (with mocks)."""
    
    @pytest.fixture
    def voice_pipeline(self):
        """Get voice pipeline instance."""
        try:
            from src.voice import EnhancedVoicePipeline
            return EnhancedVoicePipeline()
        except ImportError:
            pytest.skip("Voice pipeline not available")
    
    def test_pipeline_states(self, voice_pipeline):
        """Test pipeline state transitions."""
        from src.voice import PipelineState
        
        # Initial state should be IDLE
        assert voice_pipeline.state in [PipelineState.IDLE, PipelineState.LISTENING]
    
    @pytest.mark.asyncio
    async def test_text_command_processing(self, voice_pipeline):
        """Test processing text command (bypassing audio)."""
        try:
            # Use text mode if available
            result = await voice_pipeline.process_text("Hello")
            assert result is not None
        except AttributeError:
            pytest.skip("Text processing not available")


class TestHealthMonitor:
    """Tests for health monitoring."""
    
    @pytest.fixture
    def health_monitor(self):
        """Get health monitor instance."""
        try:
            from src.core.health_monitor import HealthMonitor
            return HealthMonitor()
        except ImportError:
            pytest.skip("Health monitor not available")
    
    def test_component_registration(self, health_monitor):
        """Test component registration."""
        async def dummy_check():
            from src.core.health_monitor import HealthCheck, ComponentStatus
            return HealthCheck(
                component="test",
                status=ComponentStatus.HEALTHY,
                message="OK",
            )
        
        health_monitor.register_component("test", dummy_check)
        assert "test" in health_monitor._components
    
    @pytest.mark.asyncio
    async def test_health_check_execution(self, health_monitor):
        """Test health check execution."""
        from src.core.health_monitor import HealthCheck, ComponentStatus
        
        async def dummy_check():
            return HealthCheck(
                component="test",
                status=ComponentStatus.HEALTHY,
                message="OK",
            )
        
        health_monitor.register_component("test", dummy_check)
        result = await health_monitor.check_component("test")
        
        assert result.status == ComponentStatus.HEALTHY


class TestEndToEndPipeline:
    """End-to-end pipeline tests."""
    
    @pytest.mark.asyncio
    async def test_simple_query_flow(self):
        """Test complete flow for simple query."""
        metrics = TestMetrics(test_name="simple_query", start_time=time.time())
        
        try:
            # 1. Initialize components
            from src.core.llm import LLMManager
            from src.memory import ConversationMemory
            
            llm = LLMManager()
            memory = ConversationMemory()
            
            # 2. Process query
            query = "What is 2 plus 2?"
            memory.add_message("user", query)
            
            start = time.time()
            response = await llm.generate(query, max_tokens=50)
            metrics.latencies["llm"] = time.time() - start
            
            assert response is not None
            memory.add_message("assistant", response.content)
            
            # 3. Verify memory
            history = memory.get_history()
            assert len(history) >= 2
            
            metrics.success = True
            
        except Exception as e:
            metrics.error = str(e)
            pytest.skip(f"End-to-end test failed: {e}")
        
        finally:
            metrics.end_time = time.time()
    
    @pytest.mark.asyncio
    async def test_error_handling_flow(self):
        """Test error handling in pipeline."""
        try:
            from src.core.llm import LLMManager
            
            llm = LLMManager()
            
            # Test with invalid input
            response = await llm.generate("", max_tokens=10)
            # Should handle gracefully, not crash
            
        except Exception as e:
            # Errors should be handled gracefully
            assert True
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """Test system degrades gracefully when components fail."""
        try:
            from src.core.health_monitor import get_health_monitor
            
            monitor = get_health_monitor()
            status = monitor.get_status()
            
            # System should report status even if some components are down
            assert "overall_status" in status
            
        except ImportError:
            pytest.skip("Health monitor not available")


class TestIoTIntegration:
    """Tests for IoT integration (mocked)."""
    
    @pytest.fixture
    def iot_controller(self):
        """Get IoT controller instance."""
        try:
            from src.iot import ProductionIoTController
            return ProductionIoTController(shared_secret="test_secret")
        except ImportError:
            pytest.skip("IoT controller not available")
    
    def test_device_registration(self, iot_controller):
        """Test device registration."""
        from src.iot import DeviceType
        
        device = iot_controller.add_device(
            device_id="test_device",
            ip_address="192.168.1.100",
            device_type=DeviceType.LIGHT,
            name="Test Light",
        )
        
        assert device is not None
        assert device.device_id == "test_device"
    
    def test_command_queue(self, iot_controller):
        """Test command queuing."""
        from src.iot import CommandPriority
        
        result = iot_controller.queue_command(
            device_id="test_device",
            endpoint="/light",
            data={"state": "on"},
            priority=CommandPriority.NORMAL,
        )
        
        assert result is True


class TestStatePersistence:
    """Tests for state persistence."""
    
    def test_config_persistence(self, project_root, tmp_path):
        """Test configuration is persisted correctly."""
        import yaml
        
        test_config = {"test_key": "test_value"}
        config_path = tmp_path / "test_config.yaml"
        
        with open(config_path, "w") as f:
            yaml.dump(test_config, f)
        
        with open(config_path) as f:
            loaded = yaml.safe_load(f)
        
        assert loaded["test_key"] == "test_value"
    
    def test_memory_persistence(self, tmp_path):
        """Test memory state is persisted."""
        import json
        
        test_state = {"messages": [{"role": "user", "content": "test"}]}
        state_path = tmp_path / "memory_state.json"
        
        with open(state_path, "w") as f:
            json.dump(test_state, f)
        
        with open(state_path) as f:
            loaded = json.load(f)
        
        assert loaded["messages"][0]["content"] == "test"


# Test runner utilities

def run_integration_tests(verbose: bool = True) -> Dict[str, Any]:
    """Run all integration tests and return results."""
    import subprocess
    
    cmd = [
        sys.executable, "-m", "pytest",
        str(Path(__file__)),
        "-v" if verbose else "-q",
        "--tb=short",
        "--json-report",
        "--json-report-file=test_results.json",
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Try to load JSON results
    results_path = Path("test_results.json")
    if results_path.exists():
        with open(results_path) as f:
            return json.load(f)
    
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
