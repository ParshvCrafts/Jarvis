"""
Tests for the audio cues module.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestAudioCueType:
    """Tests for AudioCueType."""
    
    def test_cue_types_defined(self):
        """Test all cue types are defined."""
        from src.voice.audio_cues import AudioCueType
        
        assert AudioCueType.WAKE_WORD == "wake_word"
        assert AudioCueType.LISTENING == "listening"
        assert AudioCueType.PROCESSING == "processing"
        assert AudioCueType.SUCCESS == "success"
        assert AudioCueType.ERROR == "error"
        assert AudioCueType.GOODBYE == "goodbye"
        assert AudioCueType.NOTIFICATION == "notification"


class TestAudioCueGenerator:
    """Tests for AudioCueGenerator."""
    
    def test_generate_tone(self):
        """Test tone generation."""
        from src.voice.audio_cues import AudioCueGenerator
        
        audio = AudioCueGenerator.generate_tone(
            frequency=440,
            duration=0.1,
            volume=0.5,
        )
        
        # Should return WAV bytes
        assert audio is not None
        assert len(audio) > 0
        # WAV files start with RIFF header
        assert audio[:4] == b'RIFF'
    
    def test_generate_multi_tone(self):
        """Test multi-tone generation."""
        from src.voice.audio_cues import AudioCueGenerator
        
        audio = AudioCueGenerator.generate_multi_tone(
            frequencies=[440, 550, 660],
            durations=[0.1, 0.1, 0.1],
            volume=0.3,
        )
        
        assert audio is not None
        assert len(audio) > 0
        assert audio[:4] == b'RIFF'


class TestAudioCuePlayer:
    """Tests for AudioCuePlayer."""
    
    def test_player_creation(self):
        """Test player can be created."""
        from src.voice.audio_cues import AudioCuePlayer
        
        player = AudioCuePlayer(volume=0.5, enabled=True)
        
        assert player.volume == 0.5
        assert player.enabled == True
    
    def test_player_disabled(self):
        """Test disabled player returns False."""
        from src.voice.audio_cues import AudioCuePlayer, AudioCueType
        
        player = AudioCuePlayer(enabled=False)
        
        result = player.play(AudioCueType.WAKE_WORD)
        assert result == False
    
    def test_set_volume(self):
        """Test volume setting."""
        from src.voice.audio_cues import AudioCuePlayer
        
        player = AudioCuePlayer()
        
        player.set_volume(0.8)
        assert player.volume == 0.8
        
        # Test clamping
        player.set_volume(1.5)
        assert player.volume == 1.0
        
        player.set_volume(-0.5)
        assert player.volume == 0.0
    
    def test_set_enabled(self):
        """Test enable/disable."""
        from src.voice.audio_cues import AudioCuePlayer
        
        player = AudioCuePlayer(enabled=True)
        
        player.set_enabled(False)
        assert player.enabled == False
        
        player.set_enabled(True)
        assert player.enabled == True
    
    def test_default_cues_defined(self):
        """Test default cues are defined."""
        from src.voice.audio_cues import AudioCuePlayer, AudioCueType
        
        assert AudioCueType.WAKE_WORD in AudioCuePlayer.DEFAULT_CUES
        assert AudioCueType.LISTENING in AudioCuePlayer.DEFAULT_CUES
        assert AudioCueType.ERROR in AudioCuePlayer.DEFAULT_CUES


class TestGlobalPlayer:
    """Tests for global player functions."""
    
    def test_get_audio_cue_player(self):
        """Test get_audio_cue_player returns singleton."""
        from src.voice.audio_cues import get_audio_cue_player
        
        player1 = get_audio_cue_player()
        player2 = get_audio_cue_player()
        
        assert player1 is player2
    
    def test_play_cue_function(self):
        """Test play_cue convenience function."""
        from src.voice.audio_cues import play_cue, get_audio_cue_player
        
        # Disable to avoid actual audio playback in tests
        get_audio_cue_player().set_enabled(False)
        
        result = play_cue("wake_word")
        assert result == False  # Disabled


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
