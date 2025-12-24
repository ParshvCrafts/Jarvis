"""
Voice Pipeline Module for JARVIS.

Integrates wake word detection, speech-to-text, and text-to-speech
into a unified voice interaction pipeline.
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from loguru import logger

from .wake_word import WakeWordDetector
from .stt import AudioRecorder, SpeechToText, TranscriptionResult
from .tts import InterruptibleTTS, TextToSpeech


class PipelineState(Enum):
    """Voice pipeline states."""
    IDLE = "idle"
    LISTENING_WAKE_WORD = "listening_wake_word"
    LISTENING_COMMAND = "listening_command"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass
class VoiceCommand:
    """A voice command from the user."""
    text: str
    confidence: float
    duration: float
    timestamp: float


class VoicePipeline:
    """
    Complete voice interaction pipeline for JARVIS.
    
    Handles the full flow:
    1. Wake word detection
    2. Speech recording with VAD
    3. Speech-to-text transcription
    4. Response generation (via callback)
    5. Text-to-speech response
    
    Supports:
    - Continuous conversation mode
    - Interruptible responses
    - State management
    """
    
    def __init__(
        self,
        wake_word_config: dict | None = None,
        stt_config: dict | None = None,
        tts_config: dict | None = None,
        audio_config: dict | None = None,
    ):
        """
        Initialize the voice pipeline.
        
        Args:
            wake_word_config: Wake word detector configuration.
            stt_config: Speech-to-text configuration.
            tts_config: Text-to-speech configuration.
            audio_config: Audio device configuration.
        """
        wake_word_config = wake_word_config or {}
        stt_config = stt_config or {}
        tts_config = tts_config or {}
        audio_config = audio_config or {}
        
        # Initialize components
        self.wake_word = WakeWordDetector(
            wake_word=wake_word_config.get("phrase", "hey jarvis"),
            threshold=wake_word_config.get("threshold", 0.5),
            model_path=wake_word_config.get("model_path"),
            sample_rate=audio_config.get("sample_rate", 16000),
            input_device=audio_config.get("input_device"),
        )
        
        self.stt = SpeechToText(
            model_size=stt_config.get("model", "base.en"),
            device=stt_config.get("device", "cpu"),
            compute_type=stt_config.get("compute_type", "int8"),
            language=stt_config.get("language", "en"),
            vad_enabled=True,
        )
        
        self.recorder = AudioRecorder(
            sample_rate=audio_config.get("sample_rate", 16000),
            channels=audio_config.get("channels", 1),
            chunk_size=audio_config.get("chunk_size", 1024),
            silence_duration=stt_config.get("silence_duration", 1.5),
            max_duration=30.0,
            input_device=audio_config.get("input_device"),
        )
        
        self.tts = InterruptibleTTS(
            engine=tts_config.get("engine", "edge_tts"),
            voice=tts_config.get("voice", "en-US-GuyNeural"),
            rate=tts_config.get("rate", 1.0),
            volume=tts_config.get("volume", 1.0),
            output_device=audio_config.get("output_device"),
        )
        
        # State
        self._state = PipelineState.IDLE
        self._running = False
        self._conversation_mode = False
        self._conversation_timeout = 30.0  # Seconds before exiting conversation mode
        self._last_interaction_time = 0.0
        
        # Callbacks
        self._on_wake_word: Optional[Callable[[], None]] = None
        self._on_command: Optional[Callable[[VoiceCommand], str]] = None
        self._on_state_change: Optional[Callable[[PipelineState], None]] = None
        self._on_error: Optional[Callable[[Exception], None]] = None
        
        # Threading
        self._main_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    @property
    def state(self) -> PipelineState:
        """Get current pipeline state."""
        return self._state
    
    @property
    def is_running(self) -> bool:
        """Check if pipeline is running."""
        return self._running
    
    @property
    def in_conversation(self) -> bool:
        """Check if in conversation mode."""
        return self._conversation_mode
    
    def _set_state(self, state: PipelineState) -> None:
        """Update pipeline state."""
        if self._state != state:
            self._state = state
            logger.debug(f"Pipeline state: {state.value}")
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
        """
        Set pipeline callbacks.
        
        Args:
            on_wake_word: Called when wake word is detected.
            on_command: Called with voice command, should return response text.
            on_state_change: Called when pipeline state changes.
            on_error: Called when an error occurs.
        """
        self._on_wake_word = on_wake_word
        self._on_command = on_command
        self._on_state_change = on_state_change
        self._on_error = on_error
    
    def start(self) -> bool:
        """
        Start the voice pipeline.
        
        Returns:
            True if started successfully.
        """
        if self._running:
            logger.warning("Pipeline already running")
            return True
        
        self._running = True
        self._set_state(PipelineState.LISTENING_WAKE_WORD)
        
        # Start wake word detection
        if self.wake_word.is_available:
            if not self.wake_word.start(self._on_wake_word_detected):
                logger.warning("Wake word detection failed to start")
        else:
            logger.warning("Wake word detection not available")
        
        # Start main processing thread
        self._main_thread = threading.Thread(target=self._main_loop, daemon=True)
        self._main_thread.start()
        
        logger.info("Voice pipeline started")
        return True
    
    def stop(self) -> None:
        """Stop the voice pipeline."""
        self._running = False
        self._conversation_mode = False
        
        # Stop components
        self.wake_word.stop()
        self.recorder.stop()
        self.tts.stop()
        
        # Wait for thread
        if self._main_thread:
            self._main_thread.join(timeout=2)
            self._main_thread = None
        
        self._set_state(PipelineState.IDLE)
        logger.info("Voice pipeline stopped")
    
    def _on_wake_word_detected(self) -> None:
        """Handle wake word detection."""
        logger.info("Wake word detected!")
        
        if self._on_wake_word:
            try:
                self._on_wake_word()
            except Exception as e:
                logger.error(f"Wake word callback error: {e}")
        
        # Enter conversation mode
        self._conversation_mode = True
        self._last_interaction_time = time.time()
        
        # Signal to process command
        self._set_state(PipelineState.LISTENING_COMMAND)
    
    def _main_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            try:
                current_state = self._state
                
                if current_state == PipelineState.LISTENING_WAKE_WORD:
                    # Check conversation mode timeout
                    if self._conversation_mode:
                        if time.time() - self._last_interaction_time > self._conversation_timeout:
                            logger.info("Conversation mode timeout")
                            self._conversation_mode = False
                    
                    time.sleep(0.1)
                
                elif current_state == PipelineState.LISTENING_COMMAND:
                    self._process_command()
                
                elif current_state == PipelineState.PROCESSING:
                    # Waiting for response generation
                    time.sleep(0.1)
                
                elif current_state == PipelineState.SPEAKING:
                    # Wait for TTS to complete
                    while self.tts.is_playing():
                        time.sleep(0.1)
                    
                    # Return to appropriate state
                    if self._conversation_mode:
                        self._set_state(PipelineState.LISTENING_COMMAND)
                    else:
                        self._set_state(PipelineState.LISTENING_WAKE_WORD)
                
                else:
                    time.sleep(0.1)
            
            except Exception as e:
                logger.error(f"Pipeline error: {e}")
                self._set_state(PipelineState.ERROR)
                
                if self._on_error:
                    self._on_error(e)
                
                time.sleep(1)
                self._set_state(PipelineState.LISTENING_WAKE_WORD)
    
    def _process_command(self) -> None:
        """Record and process a voice command."""
        logger.info("Listening for command...")
        
        # Play acknowledgment sound (optional)
        # self._play_acknowledgment()
        
        # Record audio
        audio = self.recorder.record(
            on_speech_start=lambda: logger.debug("Speech started"),
            on_speech_end=lambda: logger.debug("Speech ended"),
        )
        
        if audio is None or len(audio) == 0:
            logger.debug("No audio recorded")
            if self._conversation_mode:
                self._set_state(PipelineState.LISTENING_COMMAND)
            else:
                self._set_state(PipelineState.LISTENING_WAKE_WORD)
            return
        
        # Transcribe
        self._set_state(PipelineState.PROCESSING)
        result = self.stt.transcribe(audio, self.recorder.sample_rate)
        
        if not result.text:
            logger.debug("No speech transcribed")
            if self._conversation_mode:
                self._set_state(PipelineState.LISTENING_COMMAND)
            else:
                self._set_state(PipelineState.LISTENING_WAKE_WORD)
            return
        
        logger.info(f"Transcribed: {result.text}")
        
        # Update interaction time
        self._last_interaction_time = time.time()
        
        # Create command object
        command = VoiceCommand(
            text=result.text,
            confidence=result.confidence,
            duration=result.duration,
            timestamp=time.time(),
        )
        
        # Process command via callback
        if self._on_command:
            try:
                response = self._on_command(command)
                
                if response:
                    # Speak response
                    self._set_state(PipelineState.SPEAKING)
                    self.tts.speak_interruptible(
                        response,
                        on_interrupt=self._on_speech_interrupted,
                    )
                else:
                    if self._conversation_mode:
                        self._set_state(PipelineState.LISTENING_COMMAND)
                    else:
                        self._set_state(PipelineState.LISTENING_WAKE_WORD)
            
            except Exception as e:
                logger.error(f"Command processing error: {e}")
                if self._on_error:
                    self._on_error(e)
                self._set_state(PipelineState.LISTENING_WAKE_WORD)
        else:
            # No command handler, just return to listening
            if self._conversation_mode:
                self._set_state(PipelineState.LISTENING_COMMAND)
            else:
                self._set_state(PipelineState.LISTENING_WAKE_WORD)
    
    def _on_speech_interrupted(self) -> None:
        """Handle TTS interruption."""
        logger.info("Speech interrupted by user")
        self._last_interaction_time = time.time()
        self._set_state(PipelineState.LISTENING_COMMAND)
    
    def trigger_listen(self) -> None:
        """
        Manually trigger listening mode.
        
        Useful for button-triggered activation.
        """
        self._conversation_mode = True
        self._last_interaction_time = time.time()
        self._set_state(PipelineState.LISTENING_COMMAND)
    
    def say(self, text: str, blocking: bool = True) -> None:
        """
        Speak text directly.
        
        Args:
            text: Text to speak.
            blocking: Wait for completion.
        """
        previous_state = self._state
        self._set_state(PipelineState.SPEAKING)
        
        self.tts.speak(text, blocking=blocking)
        
        if blocking:
            self._set_state(previous_state)
    
    def enter_conversation_mode(self) -> None:
        """Enter continuous conversation mode."""
        self._conversation_mode = True
        self._last_interaction_time = time.time()
        logger.info("Entered conversation mode")
    
    def exit_conversation_mode(self) -> None:
        """Exit conversation mode."""
        self._conversation_mode = False
        self._set_state(PipelineState.LISTENING_WAKE_WORD)
        logger.info("Exited conversation mode")
    
    def set_conversation_timeout(self, seconds: float) -> None:
        """Set conversation mode timeout."""
        self._conversation_timeout = max(5.0, seconds)


class VoicePipelineAsync:
    """
    Async wrapper for the voice pipeline.
    
    Provides async/await interface for integration with
    async applications.
    """
    
    def __init__(self, pipeline: VoicePipeline):
        """
        Initialize async wrapper.
        
        Args:
            pipeline: VoicePipeline instance to wrap.
        """
        self.pipeline = pipeline
        self._command_queue: asyncio.Queue = asyncio.Queue()
        self._response_futures: dict = {}
    
    async def start(self) -> bool:
        """Start the pipeline asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.pipeline.start)
    
    async def stop(self) -> None:
        """Stop the pipeline asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.pipeline.stop)
    
    async def wait_for_command(self) -> VoiceCommand:
        """
        Wait for the next voice command.
        
        Returns:
            VoiceCommand when received.
        """
        return await self._command_queue.get()
    
    async def say(self, text: str) -> None:
        """
        Speak text asynchronously.
        
        Args:
            text: Text to speak.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.pipeline.say, text, True)
