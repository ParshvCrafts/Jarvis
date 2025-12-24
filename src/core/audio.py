"""
Audio Utilities for JARVIS

Provides audio playback functionality for:
- Startup sounds
- Notification sounds
- Audio feedback
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Optional

from loguru import logger

# Try to import audio libraries
PYGAME_AVAILABLE = False
PLAYSOUND_AVAILABLE = False
WINSOUND_AVAILABLE = False

try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except ImportError:
    pass
except Exception as e:
    logger.debug(f"pygame mixer init failed: {e}")

if not PYGAME_AVAILABLE:
    try:
        from playsound import playsound
        PLAYSOUND_AVAILABLE = True
    except ImportError:
        pass

if not PYGAME_AVAILABLE and not PLAYSOUND_AVAILABLE:
    try:
        import winsound
        WINSOUND_AVAILABLE = True
    except ImportError:
        pass


class AudioPlayer:
    """
    Simple audio player for JARVIS sounds.
    
    Supports multiple backends:
    - pygame (preferred)
    - playsound
    - winsound (Windows only, WAV files only)
    """
    
    def __init__(self, assets_dir: Optional[str] = None):
        """
        Initialize audio player.
        
        Args:
            assets_dir: Path to assets directory
        """
        if assets_dir:
            self.assets_dir = Path(assets_dir)
        else:
            # Default to project assets directory
            self.assets_dir = Path(__file__).parent.parent.parent / "assets" / "audio"
        
        self._volume = 0.7
        self._enabled = True
        
        # Log available backend
        if PYGAME_AVAILABLE:
            logger.debug("Audio backend: pygame")
        elif PLAYSOUND_AVAILABLE:
            logger.debug("Audio backend: playsound")
        elif WINSOUND_AVAILABLE:
            logger.debug("Audio backend: winsound")
        else:
            logger.warning("No audio backend available. Install pygame: pip install pygame")
    
    @property
    def available(self) -> bool:
        """Check if audio playback is available."""
        return PYGAME_AVAILABLE or PLAYSOUND_AVAILABLE or WINSOUND_AVAILABLE
    
    @property
    def volume(self) -> float:
        """Get current volume (0.0 to 1.0)."""
        return self._volume
    
    @volume.setter
    def volume(self, value: float):
        """Set volume (0.0 to 1.0)."""
        self._volume = max(0.0, min(1.0, value))
        if PYGAME_AVAILABLE:
            pygame.mixer.music.set_volume(self._volume)
    
    @property
    def enabled(self) -> bool:
        """Check if audio is enabled."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        """Enable or disable audio."""
        self._enabled = value
    
    def play(self, filename: str, blocking: bool = False) -> bool:
        """
        Play an audio file.
        
        Args:
            filename: Audio file name (relative to assets_dir) or absolute path
            blocking: If True, wait for playback to complete
            
        Returns:
            True if playback started successfully
        """
        if not self._enabled:
            logger.debug("Audio disabled, skipping playback")
            return False
        
        if not self.available:
            logger.warning("No audio backend available")
            return False
        
        # Resolve file path
        if os.path.isabs(filename):
            filepath = Path(filename)
        else:
            filepath = self.assets_dir / filename
        
        if not filepath.exists():
            logger.warning(f"Audio file not found: {filepath}")
            return False
        
        filepath_str = str(filepath)
        
        if blocking:
            return self._play_sync(filepath_str)
        else:
            # Play in background thread
            thread = threading.Thread(
                target=self._play_sync,
                args=(filepath_str,),
                daemon=True
            )
            thread.start()
            return True
    
    def _play_sync(self, filepath: str) -> bool:
        """Play audio synchronously."""
        try:
            if PYGAME_AVAILABLE:
                pygame.mixer.music.load(filepath)
                pygame.mixer.music.set_volume(self._volume)
                pygame.mixer.music.play()
                # Wait for playback to complete
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)
                return True
            
            elif PLAYSOUND_AVAILABLE:
                playsound(filepath)
                return True
            
            elif WINSOUND_AVAILABLE:
                import winsound
                # winsound only supports WAV files
                if filepath.lower().endswith('.wav'):
                    winsound.PlaySound(filepath, winsound.SND_FILENAME)
                    return True
                else:
                    logger.warning("winsound only supports WAV files")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
            return False
    
    def play_startup(self) -> bool:
        """Play the JARVIS startup sound."""
        return self.play("startup.wav", blocking=False)
    
    def play_ready(self) -> bool:
        """Play the ready/listening sound."""
        return self.play("ready.wav", blocking=False)
    
    def play_success(self) -> bool:
        """Play success notification sound."""
        return self.play("success.wav", blocking=False)
    
    def play_error(self) -> bool:
        """Play error notification sound."""
        return self.play("error.wav", blocking=False)
    
    def generate_tone(
        self,
        frequency: int = 440,
        duration_ms: int = 500,
    ) -> bool:
        """
        Generate and play a simple tone (Windows only).
        
        Args:
            frequency: Tone frequency in Hz
            duration_ms: Duration in milliseconds
            
        Returns:
            True if successful
        """
        if not self._enabled:
            return False
        
        try:
            import winsound
            winsound.Beep(frequency, duration_ms)
            return True
        except Exception as e:
            logger.debug(f"Tone generation failed: {e}")
            return False
    
    def play_startup_sequence(self) -> bool:
        """
        Play a startup sequence using tones (fallback if no audio file).
        
        Creates a distinctive JARVIS-like startup sound.
        """
        if not self._enabled:
            return False
        
        try:
            import winsound
            import time
            
            # JARVIS-like startup sequence
            # Rising tones suggesting "powering up"
            frequencies = [
                (300, 100),   # Low start
                (400, 100),   # Rising
                (500, 100),   # Rising
                (600, 150),   # Peak
                (800, 200),   # High confirmation
            ]
            
            for freq, duration in frequencies:
                winsound.Beep(freq, duration)
                time.sleep(0.05)
            
            return True
            
        except Exception as e:
            logger.debug(f"Startup sequence failed: {e}")
            return False


# Singleton instance
_audio_player: Optional[AudioPlayer] = None


def get_audio_player() -> AudioPlayer:
    """Get or create audio player singleton."""
    global _audio_player
    if _audio_player is None:
        _audio_player = AudioPlayer()
    return _audio_player


def play_startup_sound(config: Optional[dict] = None) -> bool:
    """
    Play JARVIS startup sound.
    
    Args:
        config: Optional configuration dict with:
            - enabled: bool
            - file: str (audio file path)
            - volume: float (0.0 to 1.0)
            
    Returns:
        True if sound played successfully
    """
    player = get_audio_player()
    
    if config:
        player.enabled = config.get("enabled", True)
        player.volume = config.get("volume", 0.7)
        
        custom_file = config.get("file")
        if custom_file and player.enabled:
            return player.play(custom_file, blocking=False)
    
    if not player.enabled:
        return False
    
    # Try startup.wav first
    if player.play("startup.wav", blocking=False):
        return True
    
    # Fallback to generated tone sequence
    logger.info("No startup.wav found, using generated tones")
    return player.play_startup_sequence()
