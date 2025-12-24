"""
Tests for the enhanced voice pipeline.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPipelineState:
    """Tests for pipeline state enum."""
    
    def test_pipeline_states_exist(self):
        """Test all pipeline states exist."""
        from src.voice.pipeline_enhanced import PipelineState
        
        assert PipelineState.IDLE
        assert PipelineState.LISTENING_WAKE_WORD
        assert PipelineState.LISTENING_COMMAND
        assert PipelineState.PROCESSING
        assert PipelineState.SPEAKING
        assert PipelineState.CONVERSATION_MODE


class TestVoiceCommand:
    """Tests for VoiceCommand dataclass."""
    
    def test_voice_command_creation(self):
        """Test VoiceCommand can be created."""
        from src.voice.pipeline_enhanced import VoiceCommand
        
        cmd = VoiceCommand(
            text="turn on the lights",
            confidence=0.95,
            duration=2.5,
            timestamp=1234567890.0,
        )
        
        assert cmd.text == "turn on the lights"
        assert cmd.confidence == 0.95
        assert cmd.duration == 2.5


class TestConversationState:
    """Tests for ConversationState."""
    
    def test_conversation_state_expiry(self):
        """Test conversation state expiry detection."""
        from src.voice.pipeline_enhanced import ConversationState
        import time
        
        state = ConversationState(
            active=True,
            started_at=time.time(),
            last_interaction=time.time(),
            timeout_seconds=1.0,  # 1 second for testing
        )
        
        # Should not be expired immediately
        assert not state.is_expired()
        
        # Wait for expiry
        time.sleep(1.1)
        assert state.is_expired()
    
    def test_conversation_state_touch(self):
        """Test conversation state touch updates last_interaction."""
        from src.voice.pipeline_enhanced import ConversationState
        import time
        
        state = ConversationState(
            active=True,
            started_at=time.time() - 10,
            last_interaction=time.time() - 10,
            timeout_seconds=30.0,
        )
        
        old_interaction = state.last_interaction
        old_turn = state.turn_count
        
        state.touch()
        
        assert state.last_interaction > old_interaction
        assert state.turn_count == old_turn + 1


class TestWakeWordConfig:
    """Tests for WakeWordConfig."""
    
    def test_wake_word_config_defaults(self):
        """Test WakeWordConfig default values."""
        from src.voice.wake_word_enhanced import WakeWordConfig
        
        config = WakeWordConfig(phrase="hey jarvis")
        
        assert config.phrase == "hey jarvis"
        assert config.threshold == 0.5
        assert config.min_consecutive == 2
        assert config.cooldown_seconds == 2.0


class TestTranscriptionResult:
    """Tests for TranscriptionResult."""
    
    def test_transcription_result_is_empty(self):
        """Test is_empty property."""
        from src.voice.stt_enhanced import TranscriptionResult
        
        empty_result = TranscriptionResult(
            text="",
            language="en",
            confidence=0.0,
            duration=0.0,
        )
        assert empty_result.is_empty
        
        valid_result = TranscriptionResult(
            text="hello world",
            language="en",
            confidence=0.95,
            duration=1.5,
        )
        assert not valid_result.is_empty


class TestSTTProvider:
    """Tests for STT provider enum."""
    
    def test_stt_providers_exist(self):
        """Test all STT providers exist."""
        from src.voice.stt_enhanced import STTProvider
        
        assert STTProvider.FASTER_WHISPER
        assert STTProvider.GROQ_WHISPER
        assert STTProvider.LOCAL_WHISPER


class TestTextToSpeech:
    """Tests for TTS module."""
    
    def test_tts_import(self):
        """Test TTS can be imported."""
        from src.voice.tts import TextToSpeech, InterruptibleTTS
        
        assert TextToSpeech is not None
        assert InterruptibleTTS is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
