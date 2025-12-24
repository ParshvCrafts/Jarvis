"""
Integration tests for JARVIS Phase 3.

Tests the unified application flow and module integration.
"""

import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestConfigValidation:
    """Tests for configuration validation."""
    
    def test_config_validation_result_str(self):
        """Test ConfigValidationResult string representation."""
        from src.jarvis_unified import ConfigValidationResult
        
        result = ConfigValidationResult(
            valid=True,
            features_enabled={"LLM: Groq": True, "Telegram Bot": False}
        )
        
        output = str(result)
        assert "Configuration valid" in output
        assert "LLM: Groq" in output
    
    def test_config_validation_with_errors(self):
        """Test ConfigValidationResult with errors."""
        from src.jarvis_unified import ConfigValidationResult
        
        result = ConfigValidationResult(
            valid=False,
            errors=["Missing API key"],
            warnings=["Feature disabled"],
        )
        
        output = str(result)
        assert "Configuration invalid" in output
        assert "Missing API key" in output
        assert "Feature disabled" in output


class TestModuleImports:
    """Test that all modules can be imported."""
    
    def test_voice_module_imports(self):
        """Test voice module imports."""
        from src.voice import (
            TextToSpeech,
            InterruptibleTTS,
            LegacyVoicePipeline,
        )
        
        assert TextToSpeech is not None
        assert InterruptibleTTS is not None
    
    def test_telegram_module_imports(self):
        """Test telegram module imports."""
        from src import telegram
        
        # Should not raise even if telegram not installed
        assert hasattr(telegram, 'EnhancedTelegramBot')
    
    def test_iot_module_imports(self):
        """Test IoT module imports."""
        from src import iot
        
        # Should not raise even if dependencies missing
        assert hasattr(iot, 'EnhancedESP32Controller')
    
    def test_agents_module_imports(self):
        """Test agents module imports."""
        from src import agents
        
        assert hasattr(agents, 'SupervisorAgent')
        assert hasattr(agents, 'ToolRegistry')
    
    def test_system_module_imports(self):
        """Test system module imports."""
        from src import system
        
        assert hasattr(system, 'SystemController')
        assert hasattr(system, 'BrowserManager')
        assert hasattr(system, 'GitController')


class TestJarvisUnified:
    """Tests for the unified Jarvis application."""
    
    @patch('src.jarvis_unified.config')
    @patch('src.jarvis_unified.env')
    @patch('src.jarvis_unified.ensure_directories')
    @patch('src.jarvis_unified.setup_logging')
    def test_jarvis_initialization(self, mock_logging, mock_dirs, mock_env, mock_config):
        """Test Jarvis can be initialized."""
        # Setup mocks
        mock_config.return_value = MagicMock()
        mock_env.return_value = MagicMock(
            groq_api_key="test",
            gemini_api_key=None,
            mistral_api_key=None,
            openrouter_api_key=None,
            anthropic_api_key=None,
            ollama_base_url=None,
            telegram_bot_token=None,
            iot_shared_secret=None,
            jwt_secret="test-secret",
        )
        
        from src.jarvis_unified import JarvisUnified
        
        jarvis = JarvisUnified()
        assert jarvis is not None
        assert jarvis.VERSION == "2.0.0"
    
    @patch('src.jarvis_unified.config')
    @patch('src.jarvis_unified.env')
    @patch('src.jarvis_unified.ensure_directories')
    @patch('src.jarvis_unified.setup_logging')
    def test_config_validation(self, mock_logging, mock_dirs, mock_env, mock_config):
        """Test configuration validation."""
        mock_config.return_value = MagicMock()
        mock_config.return_value.telegram.enabled = False
        mock_config.return_value.telegram.allowed_users = []
        
        mock_env.return_value = MagicMock(
            groq_api_key="test-key",
            gemini_api_key=None,
            mistral_api_key=None,
            openrouter_api_key=None,
            anthropic_api_key=None,
            ollama_base_url=None,
            telegram_bot_token=None,
            iot_shared_secret=None,
            jwt_secret="test-secret",
        )
        
        from src.jarvis_unified import JarvisUnified
        
        jarvis = JarvisUnified()
        result = jarvis.validate_config()
        
        # Should be valid with at least one LLM provider
        assert result.valid == True
        assert result.features_enabled.get("LLM: Groq") == True


class TestStartupState:
    """Tests for startup state enum."""
    
    def test_startup_states_exist(self):
        """Test all startup states exist."""
        from src.jarvis_unified import StartupState
        
        assert StartupState.INITIALIZING
        assert StartupState.LOADING_CONFIG
        assert StartupState.VALIDATING_CONFIG
        assert StartupState.READY
        assert StartupState.ERROR


class TestHelpSystem:
    """Tests for the help system."""
    
    @patch('src.jarvis_unified.config')
    @patch('src.jarvis_unified.env')
    @patch('src.jarvis_unified.ensure_directories')
    @patch('src.jarvis_unified.setup_logging')
    def test_get_help(self, mock_logging, mock_dirs, mock_env, mock_config):
        """Test help message generation."""
        mock_config.return_value = MagicMock()
        mock_env.return_value = MagicMock(
            groq_api_key=None,
            gemini_api_key=None,
            mistral_api_key=None,
            openrouter_api_key=None,
            anthropic_api_key=None,
            ollama_base_url=None,
            telegram_bot_token=None,
            iot_shared_secret=None,
            jwt_secret=None,
        )
        
        from src.jarvis_unified import JarvisUnified
        
        jarvis = JarvisUnified()
        help_text = jarvis._get_help()
        
        assert "Voice Commands" in help_text
        assert "System Control" in help_text
        assert "Authentication" in help_text


class TestCommandProcessing:
    """Tests for command processing."""
    
    def test_exit_phrases(self):
        """Test exit phrases are recognized."""
        exit_phrases = ["that's all", "thanks jarvis", "goodbye", "nevermind", "cancel"]
        
        for phrase in exit_phrases:
            assert phrase in ["that's all", "thanks jarvis", "goodbye", "nevermind", "cancel"]


class TestProactiveIntelligence:
    """Tests for proactive intelligence integration."""
    
    def test_proactive_module_import(self):
        """Test proactive module can be imported."""
        from src.proactive import ProactiveIntelligence
        
        assert ProactiveIntelligence is not None
    
    def test_proactive_initialization(self):
        """Test proactive intelligence initialization."""
        from src.proactive import ProactiveIntelligence
        
        with tempfile.TemporaryDirectory() as tmpdir:
            pi = ProactiveIntelligence(Path(tmpdir))
            
            assert pi.geofence is not None
            assert pi.routines is not None
            assert pi.context is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
