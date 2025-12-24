"""
Text-to-Speech Module for JARVIS.

Provides natural-sounding speech synthesis using:
- Edge-TTS (Primary - free, high quality)
- Piper TTS (Offline fallback)
"""

from __future__ import annotations

import asyncio
import io
import os
import tempfile
import threading
from pathlib import Path
from typing import AsyncIterator, Iterator, Optional

from loguru import logger

# Optional numpy import
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.warning("edge-tts not available.")

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False


class EdgeTTS:
    """
    Text-to-Speech using Microsoft Edge TTS.
    
    Free, high-quality voices with natural prosody.
    """
    
    # Popular voice options
    VOICES = {
        # English voices
        "male_us": "en-US-GuyNeural",
        "female_us": "en-US-JennyNeural",
        "male_uk": "en-GB-RyanNeural",
        "female_uk": "en-GB-SoniaNeural",
        "male_au": "en-AU-WilliamNeural",
        "female_au": "en-AU-NatashaNeural",
        # Indian English voices
        "male_in": "en-IN-PrabhatNeural",
        "female_in": "en-IN-NeerjaNeural",
        # Hindi voices
        "male_hi": "hi-IN-MadhurNeural",
        "female_hi": "hi-IN-SwaraNeural",
        # Gujarati voices
        "male_gu": "gu-IN-NiranjanNeural",
        "female_gu": "gu-IN-DhwaniNeural",
    }
    
    # Language to voice mapping
    LANGUAGE_VOICES = {
        "en": {"male": "en-IN-PrabhatNeural", "female": "en-IN-NeerjaNeural"},
        "hi": {"male": "hi-IN-MadhurNeural", "female": "hi-IN-SwaraNeural"},
        "gu": {"male": "gu-IN-NiranjanNeural", "female": "gu-IN-DhwaniNeural"},
    }
    
    def __init__(
        self,
        voice: str = "en-US-GuyNeural",
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
    ):
        """
        Initialize Edge TTS.
        
        Args:
            voice: Voice name (e.g., "en-US-GuyNeural").
            rate: Speech rate (e.g., "+10%", "-20%").
            volume: Volume adjustment.
            pitch: Pitch adjustment.
        """
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.pitch = pitch
    
    @property
    def is_available(self) -> bool:
        """Check if Edge TTS is available."""
        return EDGE_TTS_AVAILABLE
    
    def set_voice_for_language(self, language: str, gender: str = "male") -> str:
        """
        Set voice based on language code.
        
        Args:
            language: Language code (en, hi, gu)
            gender: Voice gender (male, female)
            
        Returns:
            Selected voice name
        """
        lang_code = language.lower().split("-")[0]  # Handle en-IN, hi-IN, etc.
        
        if lang_code in self.LANGUAGE_VOICES:
            voice_map = self.LANGUAGE_VOICES[lang_code]
            self.voice = voice_map.get(gender, voice_map.get("male"))
        else:
            # Default to English
            self.voice = self.LANGUAGE_VOICES["en"].get(gender, "en-IN-PrabhatNeural")
        
        logger.debug(f"TTS voice set to {self.voice} for language {language}")
        return self.voice
    
    def get_voice_for_language(self, language: str, gender: str = "male") -> str:
        """
        Get voice name for a language without changing current voice.
        
        Args:
            language: Language code (en, hi, gu)
            gender: Voice gender (male, female)
            
        Returns:
            Voice name
        """
        lang_code = language.lower().split("-")[0]
        
        if lang_code in self.LANGUAGE_VOICES:
            voice_map = self.LANGUAGE_VOICES[lang_code]
            return voice_map.get(gender, voice_map.get("male"))
        
        return self.LANGUAGE_VOICES["en"].get(gender, "en-IN-PrabhatNeural")
    
    @staticmethod
    async def list_voices() -> list:
        """List available voices."""
        if not EDGE_TTS_AVAILABLE:
            return []
        
        voices = await edge_tts.list_voices()
        return voices
    
    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to audio bytes.
        
        Args:
            text: Text to synthesize.
            
        Returns:
            Audio data as bytes (MP3 format).
        """
        if not EDGE_TTS_AVAILABLE:
            raise RuntimeError("Edge TTS not available")
        
        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self.rate,
            volume=self.volume,
            pitch=self.pitch,
        )
        
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        
        return audio_data
    
    async def synthesize_to_file(self, text: str, output_path: Path | str) -> bool:
        """
        Synthesize text to an audio file.
        
        Args:
            text: Text to synthesize.
            output_path: Output file path.
            
        Returns:
            True if successful.
        """
        if not EDGE_TTS_AVAILABLE:
            return False
        
        try:
            communicate = edge_tts.Communicate(
                text,
                self.voice,
                rate=self.rate,
                volume=self.volume,
                pitch=self.pitch,
            )
            await communicate.save(str(output_path))
            return True
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return False
    
    async def stream_audio(self, text: str) -> AsyncIterator[bytes]:
        """
        Stream synthesized audio chunks.
        
        Args:
            text: Text to synthesize.
            
        Yields:
            Audio data chunks.
        """
        if not EDGE_TTS_AVAILABLE:
            return
        
        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self.rate,
            volume=self.volume,
            pitch=self.pitch,
        )
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]


class TextToSpeech:
    """
    Unified Text-to-Speech interface for JARVIS.
    
    Provides synchronous and asynchronous speech synthesis
    with automatic playback support.
    """
    
    def __init__(
        self,
        engine: str = "edge_tts",
        voice: str = "en-US-GuyNeural",
        rate: float = 1.0,
        volume: float = 1.0,
        output_device: Optional[int] = None,
    ):
        """
        Initialize the TTS engine.
        
        Args:
            engine: TTS engine to use ("edge_tts", "piper").
            voice: Voice name.
            rate: Speech rate multiplier (0.5-2.0).
            volume: Volume multiplier (0.0-1.0).
            output_device: Audio output device index.
        """
        self.engine_name = engine
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.output_device = output_device
        
        # Convert rate to percentage string for Edge TTS
        rate_percent = int((rate - 1.0) * 100)
        rate_str = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"
        
        # Initialize engine
        if engine == "edge_tts":
            self._engine = EdgeTTS(
                voice=voice,
                rate=rate_str,
                volume=f"+{int((volume - 1.0) * 100)}%",
            )
        else:
            self._engine = EdgeTTS(voice=voice, rate=rate_str)
        
        # Playback state
        self._playing = False
        self._stop_event = threading.Event()
        self._playback_thread: Optional[threading.Thread] = None
    
    @property
    def is_available(self) -> bool:
        """Check if TTS is available."""
        return self._engine.is_available
    
    def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to audio bytes (synchronous).
        
        Args:
            text: Text to synthesize.
            
        Returns:
            Audio data as bytes.
        """
        return asyncio.run(self._engine.synthesize(text))
    
    async def asynthesize(self, text: str) -> bytes:
        """
        Synthesize text to audio bytes (asynchronous).
        
        Args:
            text: Text to synthesize.
            
        Returns:
            Audio data as bytes.
        """
        return await self._engine.synthesize(text)
    
    def speak(self, text: str, blocking: bool = True) -> bool:
        """
        Synthesize and play text.
        
        Args:
            text: Text to speak.
            blocking: Wait for playback to complete.
            
        Returns:
            True if successful.
        """
        if not SOUNDDEVICE_AVAILABLE or not SOUNDFILE_AVAILABLE:
            logger.error("Audio playback not available")
            return False
        
        try:
            # Synthesize
            audio_data = self.synthesize(text)
            
            if blocking:
                self._play_audio(audio_data)
            else:
                self._playback_thread = threading.Thread(
                    target=self._play_audio,
                    args=(audio_data,),
                    daemon=True,
                )
                self._playback_thread.start()
            
            return True
        except Exception as e:
            logger.error(f"TTS playback failed: {e}")
            return False
    
    async def aspeak(self, text: str) -> bool:
        """
        Synthesize and play text (asynchronous).
        
        Args:
            text: Text to speak.
            
        Returns:
            True if successful.
        """
        if not SOUNDDEVICE_AVAILABLE or not SOUNDFILE_AVAILABLE:
            return False
        
        try:
            audio_data = await self.asynthesize(text)
            
            # Run playback in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._play_audio, audio_data)
            
            return True
        except Exception as e:
            logger.error(f"TTS playback failed: {e}")
            return False
    
    def _play_audio(self, audio_data: bytes) -> None:
        """Play audio data."""
        self._playing = True
        self._stop_event.clear()
        
        try:
            # Save to temp file and read with soundfile
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name
            
            try:
                # Read audio file
                audio, sr = sf.read(temp_path)
                
                # Apply volume
                audio = audio * self.volume
                
                # Play
                sd.play(audio, sr, device=self.output_device)
                
                # Wait for completion or stop
                while sd.get_stream().active:
                    if self._stop_event.is_set():
                        sd.stop()
                        break
                    sd.sleep(100)
            finally:
                # Clean up temp file
                os.unlink(temp_path)
        
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
        finally:
            self._playing = False
    
    def stop(self) -> None:
        """Stop current playback."""
        self._stop_event.set()
        if SOUNDDEVICE_AVAILABLE:
            sd.stop()
    
    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._playing
    
    def wait(self) -> None:
        """Wait for current playback to complete."""
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join()


class InterruptibleTTS(TextToSpeech):
    """
    TTS with interruption support.
    
    Automatically stops speaking when the user starts talking.
    """
    
    def __init__(
        self,
        vad_threshold: float = 0.5,
        **kwargs,
    ):
        """
        Initialize interruptible TTS.
        
        Args:
            vad_threshold: VAD threshold for interruption detection.
            **kwargs: Arguments passed to TextToSpeech.
        """
        super().__init__(**kwargs)
        self.vad_threshold = vad_threshold
        
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitoring = False
    
    def speak_interruptible(
        self,
        text: str,
        on_interrupt: Optional[callable] = None,
    ) -> bool:
        """
        Speak with interruption support.
        
        Args:
            text: Text to speak.
            on_interrupt: Callback when interrupted.
            
        Returns:
            True if completed without interruption.
        """
        if not SOUNDDEVICE_AVAILABLE:
            return self.speak(text)
        
        # Start monitoring for interruption
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_for_speech,
            args=(on_interrupt,),
            daemon=True,
        )
        self._monitor_thread.start()
        
        try:
            # Speak (non-blocking)
            self.speak(text, blocking=False)
            
            # Wait for completion
            while self.is_playing():
                if not self._monitoring:
                    # Was interrupted
                    return False
                threading.Event().wait(0.1)
            
            return True
        finally:
            self._monitoring = False
    
    def _monitor_for_speech(self, on_interrupt: Optional[callable]) -> None:
        """Monitor microphone for speech to interrupt."""
        from .stt import SileroVAD
        
        vad = SileroVAD(threshold=self.vad_threshold)
        if not vad.is_available:
            return
        
        chunk_size = 1024
        sample_rate = 16000
        
        try:
            with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype=np.float32,
                blocksize=chunk_size,
            ) as stream:
                while self._monitoring and self.is_playing():
                    audio, _ = stream.read(chunk_size)
                    
                    is_speech, prob = vad.is_speech(audio.flatten())
                    
                    if is_speech and prob > self.vad_threshold + 0.1:
                        logger.info("Speech detected, interrupting TTS")
                        self.stop()
                        self._monitoring = False
                        
                        if on_interrupt:
                            on_interrupt()
                        break
        except Exception as e:
            logger.error(f"Speech monitoring error: {e}")


class ConversationTTS:
    """
    TTS optimized for conversational interactions.
    
    Provides sentence-by-sentence synthesis for lower latency
    and natural conversation flow.
    """
    
    def __init__(self, tts: TextToSpeech):
        """
        Initialize conversational TTS.
        
        Args:
            tts: TextToSpeech instance to use.
        """
        self.tts = tts
        self._sentence_queue: list = []
        self._speaking = False
    
    def speak_streaming(
        self,
        text_iterator: Iterator[str],
        sentence_callback: Optional[callable] = None,
    ) -> None:
        """
        Speak text as it streams in.
        
        Buffers text and speaks complete sentences for
        natural pacing.
        
        Args:
            text_iterator: Iterator yielding text chunks.
            sentence_callback: Called with each sentence before speaking.
        """
        buffer = ""
        sentence_endings = ".!?"
        
        for chunk in text_iterator:
            buffer += chunk
            
            # Check for complete sentences
            while any(end in buffer for end in sentence_endings):
                # Find first sentence ending
                min_idx = len(buffer)
                for end in sentence_endings:
                    idx = buffer.find(end)
                    if idx != -1 and idx < min_idx:
                        min_idx = idx
                
                if min_idx < len(buffer):
                    sentence = buffer[:min_idx + 1].strip()
                    buffer = buffer[min_idx + 1:].strip()
                    
                    if sentence:
                        if sentence_callback:
                            sentence_callback(sentence)
                        self.tts.speak(sentence, blocking=True)
        
        # Speak remaining text
        if buffer.strip():
            if sentence_callback:
                sentence_callback(buffer.strip())
            self.tts.speak(buffer.strip(), blocking=True)
