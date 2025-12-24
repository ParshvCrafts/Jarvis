"""
Audio cues for JARVIS voice pipeline.

Provides audio feedback for various events like wake word detection,
listening start/stop, errors, etc.
"""

import io
import math
import struct
import wave
from pathlib import Path
from typing import Optional

from loguru import logger

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False


class AudioCueType:
    """Types of audio cues."""
    WAKE_WORD = "wake_word"          # Heard wake word
    LISTENING = "listening"          # Started listening
    PROCESSING = "processing"        # Processing command
    SUCCESS = "success"              # Command succeeded
    ERROR = "error"                  # Error occurred
    GOODBYE = "goodbye"              # Ending conversation
    NOTIFICATION = "notification"    # General notification


class AudioCueGenerator:
    """
    Generates audio cues programmatically.
    
    Creates simple tones and beeps without requiring external audio files.
    """
    
    SAMPLE_RATE = 44100
    
    @classmethod
    def generate_tone(
        cls,
        frequency: float,
        duration: float,
        volume: float = 0.5,
        fade_in: float = 0.01,
        fade_out: float = 0.01,
    ) -> bytes:
        """
        Generate a pure tone.
        
        Args:
            frequency: Frequency in Hz.
            duration: Duration in seconds.
            volume: Volume 0.0 to 1.0.
            fade_in: Fade in duration in seconds.
            fade_out: Fade out duration in seconds.
            
        Returns:
            WAV audio bytes.
        """
        if not NUMPY_AVAILABLE:
            return b""
        
        num_samples = int(cls.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, num_samples, False)
        
        # Generate sine wave
        audio = np.sin(2 * np.pi * frequency * t) * volume
        
        # Apply fade in/out
        fade_in_samples = int(cls.SAMPLE_RATE * fade_in)
        fade_out_samples = int(cls.SAMPLE_RATE * fade_out)
        
        if fade_in_samples > 0:
            audio[:fade_in_samples] *= np.linspace(0, 1, fade_in_samples)
        if fade_out_samples > 0:
            audio[-fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        # Convert to 16-bit PCM
        audio = (audio * 32767).astype(np.int16)
        
        # Create WAV
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(cls.SAMPLE_RATE)
            wav.writeframes(audio.tobytes())
        
        return buffer.getvalue()
    
    @classmethod
    def generate_multi_tone(
        cls,
        frequencies: list,
        durations: list,
        volume: float = 0.5,
        gap: float = 0.05,
    ) -> bytes:
        """
        Generate multiple tones in sequence.
        
        Args:
            frequencies: List of frequencies in Hz.
            durations: List of durations in seconds.
            volume: Volume 0.0 to 1.0.
            gap: Gap between tones in seconds.
            
        Returns:
            WAV audio bytes.
        """
        if not NUMPY_AVAILABLE:
            return b""
        
        audio_parts = []
        gap_samples = int(cls.SAMPLE_RATE * gap)
        silence = np.zeros(gap_samples, dtype=np.int16)
        
        for freq, dur in zip(frequencies, durations):
            num_samples = int(cls.SAMPLE_RATE * dur)
            t = np.linspace(0, dur, num_samples, False)
            tone = np.sin(2 * np.pi * freq * t) * volume
            
            # Fade
            fade_samples = int(cls.SAMPLE_RATE * 0.01)
            if fade_samples > 0 and len(tone) > fade_samples * 2:
                tone[:fade_samples] *= np.linspace(0, 1, fade_samples)
                tone[-fade_samples:] *= np.linspace(1, 0, fade_samples)
            
            audio_parts.append((tone * 32767).astype(np.int16))
            audio_parts.append(silence)
        
        audio = np.concatenate(audio_parts)
        
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(cls.SAMPLE_RATE)
            wav.writeframes(audio.tobytes())
        
        return buffer.getvalue()


class AudioCuePlayer:
    """
    Plays audio cues for JARVIS events.
    
    Provides non-blocking audio feedback for various pipeline events.
    """
    
    # Default cue definitions (frequency, duration pairs)
    DEFAULT_CUES = {
        AudioCueType.WAKE_WORD: ([880, 1100], [0.1, 0.15]),      # Rising two-tone
        AudioCueType.LISTENING: ([660], [0.15]),                  # Single mid tone
        AudioCueType.PROCESSING: ([440, 550, 660], [0.08, 0.08, 0.08]),  # Rising arpeggio
        AudioCueType.SUCCESS: ([880, 1320], [0.1, 0.2]),         # Major third up
        AudioCueType.ERROR: ([440, 330], [0.15, 0.2]),           # Falling minor
        AudioCueType.GOODBYE: ([660, 550, 440], [0.1, 0.1, 0.2]), # Falling arpeggio
        AudioCueType.NOTIFICATION: ([880], [0.1]),               # Short high beep
    }
    
    def __init__(
        self,
        volume: float = 0.3,
        enabled: bool = True,
        custom_cues_dir: Optional[Path] = None,
    ):
        """
        Initialize the audio cue player.
        
        Args:
            volume: Default volume 0.0 to 1.0.
            enabled: Whether cues are enabled.
            custom_cues_dir: Directory for custom WAV files.
        """
        self.volume = volume
        self.enabled = enabled
        self.custom_cues_dir = custom_cues_dir
        
        self._cue_cache: dict = {}
        self._generator = AudioCueGenerator()
    
    def _get_cue_audio(self, cue_type: str) -> Optional[bytes]:
        """Get audio data for a cue type."""
        # Check cache
        if cue_type in self._cue_cache:
            return self._cue_cache[cue_type]
        
        # Check for custom WAV file
        if self.custom_cues_dir:
            wav_path = self.custom_cues_dir / f"{cue_type}.wav"
            if wav_path.exists():
                try:
                    audio = wav_path.read_bytes()
                    self._cue_cache[cue_type] = audio
                    return audio
                except Exception as e:
                    logger.warning(f"Failed to load custom cue {wav_path}: {e}")
        
        # Generate default cue
        if cue_type in self.DEFAULT_CUES:
            frequencies, durations = self.DEFAULT_CUES[cue_type]
            audio = self._generator.generate_multi_tone(
                frequencies, durations, self.volume
            )
            self._cue_cache[cue_type] = audio
            return audio
        
        return None
    
    def play(self, cue_type: str, blocking: bool = False) -> bool:
        """
        Play an audio cue.
        
        Args:
            cue_type: Type of cue to play.
            blocking: Wait for playback to complete.
            
        Returns:
            True if played successfully.
        """
        if not self.enabled or not SOUNDDEVICE_AVAILABLE or not NUMPY_AVAILABLE:
            return False
        
        audio_data = self._get_cue_audio(cue_type)
        if not audio_data:
            return False
        
        try:
            # Parse WAV
            buffer = io.BytesIO(audio_data)
            with wave.open(buffer, 'rb') as wav:
                sample_rate = wav.getframerate()
                audio = np.frombuffer(
                    wav.readframes(wav.getnframes()),
                    dtype=np.int16
                ).astype(np.float32) / 32767.0
            
            # Play
            if blocking:
                sd.play(audio, sample_rate)
                sd.wait()
            else:
                sd.play(audio, sample_rate)
            
            return True
        
        except Exception as e:
            logger.debug(f"Failed to play cue {cue_type}: {e}")
            return False
    
    def play_wake_word(self, blocking: bool = False) -> bool:
        """Play wake word detected cue."""
        return self.play(AudioCueType.WAKE_WORD, blocking)
    
    def play_listening(self, blocking: bool = False) -> bool:
        """Play listening started cue."""
        return self.play(AudioCueType.LISTENING, blocking)
    
    def play_processing(self, blocking: bool = False) -> bool:
        """Play processing cue."""
        return self.play(AudioCueType.PROCESSING, blocking)
    
    def play_success(self, blocking: bool = False) -> bool:
        """Play success cue."""
        return self.play(AudioCueType.SUCCESS, blocking)
    
    def play_error(self, blocking: bool = False) -> bool:
        """Play error cue."""
        return self.play(AudioCueType.ERROR, blocking)
    
    def play_goodbye(self, blocking: bool = False) -> bool:
        """Play goodbye cue."""
        return self.play(AudioCueType.GOODBYE, blocking)
    
    def play_notification(self, blocking: bool = False) -> bool:
        """Play notification cue."""
        return self.play(AudioCueType.NOTIFICATION, blocking)
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable audio cues."""
        self.enabled = enabled
    
    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)."""
        self.volume = max(0.0, min(1.0, volume))
        self._cue_cache.clear()  # Regenerate cues with new volume


# Global instance for easy access
_default_player: Optional[AudioCuePlayer] = None


def get_audio_cue_player() -> AudioCuePlayer:
    """Get the default audio cue player."""
    global _default_player
    if _default_player is None:
        _default_player = AudioCuePlayer()
    return _default_player


def play_cue(cue_type: str, blocking: bool = False) -> bool:
    """Play an audio cue using the default player."""
    return get_audio_cue_player().play(cue_type, blocking)
