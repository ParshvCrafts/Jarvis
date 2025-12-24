"""
Enhanced Voice Pipeline Module for JARVIS.

Features:
- Interruptible TTS (stops when user speaks)
- Conversation mode (stays listening after wake word)
- Graceful TTS cutoff
- Command queue management
- State machine for voice interaction
"""

from __future__ import annotations

import asyncio
import queue
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Any

from loguru import logger

# Optional numpy import
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None
    logger.warning("numpy not installed. Voice features will be limited.")

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    sd = None

from .wake_word_enhanced import EnhancedWakeWordDetector, WakeWordConfig, WakeWordDetection
from .stt_enhanced import EnhancedSpeechToText, TranscriptionResult, EnhancedSileroVAD
from .tts import TextToSpeech

# Optional multilingual support
try:
    from .multilingual import AmbientNoiseCalibrator
    MULTILINGUAL_AVAILABLE = True
except ImportError:
    MULTILINGUAL_AVAILABLE = False
    AmbientNoiseCalibrator = None


class PipelineState(Enum):
    """Voice pipeline states."""
    IDLE = "idle"
    LISTENING_WAKE_WORD = "listening_wake_word"
    LISTENING_COMMAND = "listening_command"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    CONVERSATION_MODE = "conversation_mode"
    INTERRUPTED = "interrupted"
    ERROR = "error"


@dataclass
class VoiceCommand:
    """A voice command from the user."""
    text: str
    confidence: float
    duration: float
    timestamp: float
    was_interrupted: bool = False
    language: str = "en"
    language_probability: float = 1.0


@dataclass
class ConversationState:
    """State for conversation mode."""
    active: bool = False
    started_at: float = 0.0
    last_interaction: float = 0.0
    timeout_seconds: float = 30.0
    turn_count: int = 0
    
    def is_expired(self) -> bool:
        if not self.active:
            return True
        return time.time() - self.last_interaction > self.timeout_seconds
    
    def touch(self) -> None:
        self.last_interaction = time.time()
        self.turn_count += 1


class InterruptibleTTSPlayer:
    """
    TTS player that can be interrupted by user speech.
    
    Features:
    - Real-time speech detection during playback
    - Graceful audio fadeout on interruption
    - Non-blocking playback
    """
    
    def __init__(
        self,
        tts: TextToSpeech,
        vad: Optional[EnhancedSileroVAD] = None,
        interrupt_threshold: float = 0.6,
        fadeout_duration: float = 0.1,
    ):
        self.tts = tts
        self.vad = vad or EnhancedSileroVAD(threshold=interrupt_threshold)
        self.interrupt_threshold = interrupt_threshold
        self.fadeout_duration = fadeout_duration
        
        self._playing = False
        self._interrupted = False
        self._stop_event = threading.Event()
        self._playback_thread: Optional[threading.Thread] = None
        self._monitor_thread: Optional[threading.Thread] = None
        
        self._on_interrupt: Optional[Callable[[], None]] = None
        self._on_complete: Optional[Callable[[], None]] = None
    
    def speak(
        self,
        text: str,
        on_interrupt: Optional[Callable[[], None]] = None,
        on_complete: Optional[Callable[[], None]] = None,
        blocking: bool = False,
    ) -> bool:
        """
        Speak text with interruption support.
        
        Args:
            text: Text to speak.
            on_interrupt: Callback when interrupted.
            on_complete: Callback when completed.
            blocking: Wait for completion.
            
        Returns:
            True if started successfully.
        """
        if self._playing:
            self.stop()
        
        self._on_interrupt = on_interrupt
        self._on_complete = on_complete
        self._interrupted = False
        self._stop_event.clear()
        
        # Start playback thread
        self._playback_thread = threading.Thread(
            target=self._playback_loop,
            args=(text,),
            daemon=True,
        )
        self._playback_thread.start()
        
        # Start monitor thread
        if self.vad.is_available:
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True,
            )
            self._monitor_thread.start()
        
        if blocking:
            self.wait()
        
        return True
    
    def _playback_loop(self, text: str) -> None:
        """Playback loop with interruption checking."""
        self._playing = True
        
        try:
            # Synthesize audio
            audio_data = self.tts.synthesize(text)
            
            if not audio_data:
                return
            
            # Play with interruption checking
            import tempfile
            import soundfile as sf
            
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name
            
            try:
                audio, sr = sf.read(temp_path)
                
                # Play in chunks for interruptibility
                chunk_size = int(sr * 0.1)  # 100ms chunks
                position = 0
                
                with sd.OutputStream(samplerate=sr, channels=1 if len(audio.shape) == 1 else audio.shape[1]) as stream:
                    while position < len(audio) and not self._stop_event.is_set():
                        end = min(position + chunk_size, len(audio))
                        chunk = audio[position:end]
                        
                        # Apply fadeout if stopping
                        if self._stop_event.is_set() or self._interrupted:
                            fadeout_samples = int(self.fadeout_duration * sr)
                            if len(chunk) > fadeout_samples:
                                fade = np.linspace(1, 0, fadeout_samples)
                                if len(chunk.shape) > 1:
                                    fade = fade.reshape(-1, 1)
                                chunk[-fadeout_samples:] *= fade
                            stream.write(chunk.astype(np.float32))
                            break
                        
                        stream.write(chunk.astype(np.float32))
                        position = end
                
                # Completed without interruption
                if not self._interrupted and self._on_complete:
                    self._on_complete()
            
            finally:
                import os
                os.unlink(temp_path)
        
        except Exception as e:
            logger.error(f"Playback error: {e}")
        
        finally:
            self._playing = False
    
    def _monitor_loop(self) -> None:
        """Monitor for speech to interrupt playback."""
        if not SOUNDDEVICE_AVAILABLE:
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
                while self._playing and not self._stop_event.is_set():
                    audio, _ = stream.read(chunk_size)
                    
                    is_speech, prob = self.vad.is_speech(audio.flatten(), return_probability=True)
                    
                    if is_speech and prob > self.interrupt_threshold:
                        logger.info(f"Speech detected during TTS (prob: {prob:.2f}), interrupting")
                        self._interrupted = True
                        self._stop_event.set()
                        
                        if self._on_interrupt:
                            self._on_interrupt()
                        break
        
        except Exception as e:
            logger.debug(f"Monitor error: {e}")
    
    def stop(self) -> None:
        """Stop playback."""
        self._stop_event.set()
        self._playing = False
    
    def wait(self) -> None:
        """Wait for playback to complete."""
        if self._playback_thread:
            self._playback_thread.join()
    
    @property
    def is_playing(self) -> bool:
        return self._playing
    
    @property
    def was_interrupted(self) -> bool:
        return self._interrupted


class EnhancedVoicePipeline:
    """
    Enhanced voice pipeline with conversation mode and interruptibility.
    
    Features:
    - Wake word detection with anti-false-positive
    - Conversation mode (stays listening for 30s)
    - Interruptible TTS
    - Command queue management
    - State machine for clean transitions
    """
    
    def __init__(
        self,
        wake_word_config: Optional[Dict[str, Any]] = None,
        stt_config: Optional[Dict[str, Any]] = None,
        tts_config: Optional[Dict[str, Any]] = None,
        conversation_timeout: float = 30.0,
        groq_api_key: Optional[str] = None,
    ):
        """
        Initialize the enhanced voice pipeline.
        
        Args:
            wake_word_config: Wake word configuration.
            stt_config: Speech-to-text configuration.
            tts_config: Text-to-speech configuration.
            conversation_timeout: Seconds before exiting conversation mode.
            groq_api_key: Groq API key for STT.
        """
        wake_word_config = wake_word_config or {}
        stt_config = stt_config or {}
        tts_config = tts_config or {}
        
        # Initialize wake word detector
        self.wake_word = EnhancedWakeWordDetector(
            wake_words=[WakeWordConfig(
                phrase=wake_word_config.get("phrase", "hey jarvis"),
                threshold=wake_word_config.get("threshold", 0.5),
                min_consecutive=wake_word_config.get("min_consecutive", 2),
                model_path=wake_word_config.get("model_path"),
            )],
            sample_rate=16000,
            input_device=wake_word_config.get("input_device"),
        )
        
        # Initialize STT
        self.stt = EnhancedSpeechToText(
            model_size=stt_config.get("model", "base.en"),
            device=stt_config.get("device", "auto"),
            language=stt_config.get("language", "en"),
            groq_api_key=groq_api_key,
            enable_preprocessing=True,
            enable_vad=True,
        )
        
        # Initialize TTS
        self.tts = TextToSpeech(
            engine=tts_config.get("engine", "edge_tts"),
            voice=tts_config.get("voice", "en-US-GuyNeural"),
            rate=tts_config.get("rate", 1.0),
        )
        
        # Initialize interruptible player
        self.player = InterruptibleTTSPlayer(self.tts)
        
        # Conversation state
        self.conversation = ConversationState(timeout_seconds=conversation_timeout)
        
        # Multilingual state
        self._current_language = "en"
        self._preferred_gender = tts_config.get("preferred_gender", "male")
        
        # Ambient noise calibration
        self._noise_calibrator = None
        if MULTILINGUAL_AVAILABLE and AmbientNoiseCalibrator:
            self._noise_calibrator = AmbientNoiseCalibrator(
                calibration_duration=1.0,
                energy_threshold_multiplier=1.5,
            )
        
        # Pipeline state
        self._state = PipelineState.IDLE
        self._running = False
        self._command_queue: queue.Queue = queue.Queue()
        
        # Callbacks
        self._on_wake_word: Optional[Callable[[], None]] = None
        self._on_command: Optional[Callable[[VoiceCommand], str]] = None
        self._on_state_change: Optional[Callable[[PipelineState], None]] = None
        self._on_error: Optional[Callable[[Exception], None]] = None
        
        # Threading
        self._main_thread: Optional[threading.Thread] = None
        self._recording = False
    
    @property
    def state(self) -> PipelineState:
        return self._state
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def in_conversation(self) -> bool:
        return self.conversation.active and not self.conversation.is_expired()
    
    def _set_state(self, state: PipelineState) -> None:
        if self._state != state:
            old_state = self._state
            self._state = state
            logger.debug(f"Pipeline state: {old_state.value} -> {state.value}")
            
            if self._on_state_change:
                try:
                    self._on_state_change(state)
                except Exception as e:
                    logger.error(f"State change callback error: {e}")
    
    def set_callbacks(
        self,
        on_wake_word: Optional[Callable[[], None]] = None,
        on_command: Optional[Callable[[VoiceCommand], str]] = None,
        on_state_change: Optional[Callable[[PipelineState], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        """Set pipeline callbacks."""
        self._on_wake_word = on_wake_word
        self._on_command = on_command
        self._on_state_change = on_state_change
        self._on_error = on_error
    
    def calibrate_microphone(self, duration: float = 1.0) -> bool:
        """
        Calibrate microphone for ambient noise.
        
        Args:
            duration: Seconds to sample ambient noise
            
        Returns:
            True if calibration successful
        """
        if not self._noise_calibrator:
            logger.warning("Noise calibrator not available")
            return False
        
        logger.info(f"Calibrating microphone for {duration}s...")
        
        try:
            # Sample ambient noise
            if SOUNDDEVICE_AVAILABLE and NUMPY_AVAILABLE:
                samples = int(16000 * duration)
                audio = sd.rec(samples, samplerate=16000, channels=1, dtype=np.float32)
                sd.wait()
                
                # Calibrate
                threshold = self._noise_calibrator.calibrate(audio.flatten().tolist())
                logger.info(f"Microphone calibrated. Threshold: {threshold:.4f}")
                return True
            else:
                # Use default calibration
                self._noise_calibrator.calibrate()
                return True
                
        except Exception as e:
            logger.error(f"Calibration failed: {e}")
            return False
    
    def _on_wake_word_detected(self, detection: WakeWordDetection) -> None:
        """Handle wake word detection."""
        logger.info(f"Wake word detected: {detection.wake_word} (confidence: {detection.confidence:.2f})")
        
        # Stop any current playback
        self.player.stop()
        
        # Enter conversation mode
        self.conversation.active = True
        self.conversation.started_at = time.time()
        self.conversation.touch()
        
        if self._on_wake_word:
            try:
                self._on_wake_word()
            except Exception as e:
                logger.error(f"Wake word callback error: {e}")
        
        self._set_state(PipelineState.LISTENING_COMMAND)
    
    def _record_command(self) -> Optional[np.ndarray]:
        """Record audio for command."""
        if not SOUNDDEVICE_AVAILABLE:
            return None
        
        self._recording = True
        sample_rate = 16000
        max_duration = 10.0  # Maximum recording duration
        silence_duration = 1.5  # Silence to end recording
        
        audio_chunks = []
        silence_start = None
        vad = EnhancedSileroVAD(threshold=0.5)
        
        try:
            with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype=np.float32,
                blocksize=1024,
            ) as stream:
                start_time = time.time()
                
                while self._recording and (time.time() - start_time) < max_duration:
                    audio, _ = stream.read(1024)
                    audio = audio.flatten()
                    audio_chunks.append(audio)
                    
                    # Check for speech
                    is_speech, _ = vad.is_speech(audio, return_probability=True)
                    
                    if is_speech:
                        silence_start = None
                    else:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > silence_duration:
                            # End of speech
                            break
            
            if audio_chunks:
                return np.concatenate(audio_chunks)
            return None
        
        except Exception as e:
            logger.error(f"Recording error: {e}")
            return None
        
        finally:
            self._recording = False
    
    def _process_command(self) -> None:
        """Record and process a voice command."""
        logger.info("Listening for command...")
        
        # Record audio
        audio = self._record_command()
        
        if audio is None or len(audio) < 16000 * 0.3:  # Less than 300ms
            logger.debug("No audio recorded")
            if self.in_conversation:
                self._set_state(PipelineState.CONVERSATION_MODE)
            else:
                self._set_state(PipelineState.LISTENING_WAKE_WORD)
            return
        
        # Transcribe
        self._set_state(PipelineState.PROCESSING)
        result = self.stt.transcribe(audio, 16000)
        
        if result.is_empty:
            logger.debug("No speech transcribed")
            if self.in_conversation:
                self._set_state(PipelineState.CONVERSATION_MODE)
            else:
                self._set_state(PipelineState.LISTENING_WAKE_WORD)
            return
        
        logger.info(f"Transcribed: {result.text} (lang={result.language}, prob={result.language_probability:.2f})")
        
        # Update conversation
        self.conversation.touch()
        
        # Create command with language info
        command = VoiceCommand(
            text=result.text,
            confidence=result.confidence,
            duration=result.duration,
            timestamp=time.time(),
            language=result.language,
            language_probability=result.language_probability,
        )
        
        # Store detected language for TTS
        self._current_language = command.language
        
        # Process command
        if self._on_command:
            try:
                response = self._on_command(command)
                
                if response:
                    self._speak_response(response, language=command.language)
                else:
                    if self.in_conversation:
                        self._set_state(PipelineState.CONVERSATION_MODE)
                    else:
                        self._set_state(PipelineState.LISTENING_WAKE_WORD)
            
            except Exception as e:
                logger.error(f"Command processing error: {e}")
                if self._on_error:
                    self._on_error(e)
                self._set_state(PipelineState.LISTENING_WAKE_WORD)
        else:
            if self.in_conversation:
                self._set_state(PipelineState.CONVERSATION_MODE)
            else:
                self._set_state(PipelineState.LISTENING_WAKE_WORD)
    
    def _speak_response(self, text: str, language: Optional[str] = None) -> None:
        """Speak response with interruption support and language-aware voice."""
        self._set_state(PipelineState.SPEAKING)
        
        # Set voice based on language
        lang = language or self._current_language
        if hasattr(self.tts, 'engine') and hasattr(self.tts.engine, 'set_voice_for_language'):
            self.tts.engine.set_voice_for_language(lang, self._preferred_gender)
            logger.debug(f"TTS voice set for language: {lang}")
        
        def on_interrupt():
            logger.info("Response interrupted")
            self._set_state(PipelineState.INTERRUPTED)
            self.conversation.touch()
            # Go back to listening
            self._set_state(PipelineState.LISTENING_COMMAND)
        
        def on_complete():
            if self.in_conversation:
                self._set_state(PipelineState.CONVERSATION_MODE)
            else:
                self._set_state(PipelineState.LISTENING_WAKE_WORD)
        
        self.player.speak(
            text,
            on_interrupt=on_interrupt,
            on_complete=on_complete,
            blocking=True,
        )
    
    def _main_loop(self) -> None:
        """Main pipeline loop."""
        while self._running:
            try:
                current_state = self._state
                
                if current_state == PipelineState.LISTENING_WAKE_WORD:
                    # Check if conversation mode expired
                    if self.conversation.active and self.conversation.is_expired():
                        logger.info("Conversation mode expired")
                        self.conversation.active = False
                    
                    time.sleep(0.1)
                
                elif current_state == PipelineState.CONVERSATION_MODE:
                    # In conversation mode, listen for commands
                    if self.conversation.is_expired():
                        logger.info("Conversation mode timeout")
                        self.conversation.active = False
                        self._set_state(PipelineState.LISTENING_WAKE_WORD)
                    else:
                        self._set_state(PipelineState.LISTENING_COMMAND)
                
                elif current_state == PipelineState.LISTENING_COMMAND:
                    self._process_command()
                
                elif current_state == PipelineState.PROCESSING:
                    time.sleep(0.1)
                
                elif current_state == PipelineState.SPEAKING:
                    # Wait for TTS to complete
                    while self.player.is_playing:
                        time.sleep(0.1)
                
                elif current_state == PipelineState.INTERRUPTED:
                    # User interrupted, go back to listening
                    self._set_state(PipelineState.LISTENING_COMMAND)
                
                else:
                    time.sleep(0.1)
            
            except Exception as e:
                logger.error(f"Pipeline error: {e}")
                self._set_state(PipelineState.ERROR)
                
                if self._on_error:
                    self._on_error(e)
                
                time.sleep(1)
                self._set_state(PipelineState.LISTENING_WAKE_WORD)
    
    def start(self) -> bool:
        """Start the voice pipeline."""
        if self._running:
            return True
        
        self._running = True
        self._set_state(PipelineState.LISTENING_WAKE_WORD)
        
        # Start wake word detection
        if self.wake_word.is_available:
            if not self.wake_word.start(self._on_wake_word_detected):
                logger.warning("Wake word detection failed to start")
        else:
            logger.warning("Wake word detection not available")
        
        # Start main loop
        self._main_thread = threading.Thread(target=self._main_loop, daemon=True)
        self._main_thread.start()
        
        logger.info("Enhanced voice pipeline started")
        return True
    
    def stop(self) -> None:
        """Stop the voice pipeline."""
        self._running = False
        self._recording = False
        self.conversation.active = False
        
        self.wake_word.stop()
        self.player.stop()
        
        if self._main_thread:
            self._main_thread.join(timeout=2)
            self._main_thread = None
        
        self._set_state(PipelineState.IDLE)
        logger.info("Enhanced voice pipeline stopped")
    
    def trigger_listen(self) -> None:
        """Manually trigger listening mode."""
        self.conversation.active = True
        self.conversation.touch()
        self._set_state(PipelineState.LISTENING_COMMAND)
    
    def say(self, text: str, interruptible: bool = True) -> None:
        """Speak text."""
        if interruptible:
            self.player.speak(text, blocking=True)
        else:
            self.tts.speak(text, blocking=True)
    
    def enter_conversation_mode(self) -> None:
        """Enter conversation mode."""
        self.conversation.active = True
        self.conversation.started_at = time.time()
        self.conversation.touch()
        logger.info("Entered conversation mode")
    
    def exit_conversation_mode(self) -> None:
        """Exit conversation mode."""
        self.conversation.active = False
        self._set_state(PipelineState.LISTENING_WAKE_WORD)
        logger.info("Exited conversation mode")
    
    def set_conversation_timeout(self, seconds: float) -> None:
        """Set conversation mode timeout."""
        self.conversation.timeout_seconds = max(5.0, seconds)
