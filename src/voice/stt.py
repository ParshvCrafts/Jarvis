"""
Speech-to-Text Module for JARVIS.

Uses Faster-Whisper for efficient local transcription with
Silero VAD for voice activity detection.
"""

from __future__ import annotations

import io
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, List, Optional, Tuple

from loguru import logger

# Optional numpy import
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    logger.warning("faster-whisper not available.")

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

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


@dataclass
class TranscriptionResult:
    """Result of speech transcription."""
    text: str
    language: str
    confidence: float
    duration: float
    segments: List[dict]


class SileroVAD:
    """
    Voice Activity Detection using Silero VAD.
    
    Detects speech segments in audio for efficient processing.
    """
    
    def __init__(
        self,
        threshold: float = 0.5,
        min_speech_duration: float = 0.25,
        min_silence_duration: float = 0.1,
        sample_rate: int = 16000,
    ):
        """
        Initialize Silero VAD.
        
        Args:
            threshold: Speech probability threshold.
            min_speech_duration: Minimum speech duration in seconds.
            min_silence_duration: Minimum silence duration to split.
            sample_rate: Audio sample rate (must be 16000 for Silero).
        """
        self.threshold = threshold
        self.min_speech_duration = min_speech_duration
        self.min_silence_duration = min_silence_duration
        self.sample_rate = sample_rate
        
        self._model = None
        self._get_speech_timestamps = None
    
    @property
    def is_available(self) -> bool:
        """Check if Silero VAD is available."""
        return TORCH_AVAILABLE
    
    def _load_model(self) -> bool:
        """Load the Silero VAD model."""
        if not TORCH_AVAILABLE:
            return False
        
        try:
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                trust_repo=True,
            )
            self._model = model
            self._get_speech_timestamps = utils[0]
            logger.info("Silero VAD model loaded")
            return True
        except Exception as e:
            logger.error(f"Failed to load Silero VAD: {e}")
            return False
    
    def detect_speech(
        self,
        audio: np.ndarray,
        return_seconds: bool = True,
    ) -> List[dict]:
        """
        Detect speech segments in audio.
        
        Args:
            audio: Audio samples (float32, mono).
            return_seconds: Return timestamps in seconds vs samples.
            
        Returns:
            List of speech segments with start/end times.
        """
        if self._model is None and not self._load_model():
            return []
        
        # Convert to torch tensor
        if isinstance(audio, np.ndarray):
            audio_tensor = torch.from_numpy(audio).float()
        else:
            audio_tensor = audio
        
        # Ensure 1D
        if audio_tensor.dim() > 1:
            audio_tensor = audio_tensor.squeeze()
        
        try:
            timestamps = self._get_speech_timestamps(
                audio_tensor,
                self._model,
                threshold=self.threshold,
                min_speech_duration_ms=int(self.min_speech_duration * 1000),
                min_silence_duration_ms=int(self.min_silence_duration * 1000),
                return_seconds=return_seconds,
                sampling_rate=self.sample_rate,
            )
            return timestamps
        except Exception as e:
            logger.error(f"VAD detection failed: {e}")
            return []
    
    def is_speech(self, audio: np.ndarray) -> Tuple[bool, float]:
        """
        Check if audio contains speech.
        
        Args:
            audio: Audio samples.
            
        Returns:
            Tuple of (contains_speech, confidence).
        """
        if self._model is None and not self._load_model():
            return False, 0.0
        
        if isinstance(audio, np.ndarray):
            audio_tensor = torch.from_numpy(audio).float()
        else:
            audio_tensor = audio
        
        if audio_tensor.dim() > 1:
            audio_tensor = audio_tensor.squeeze()
        
        try:
            # Get speech probability
            speech_prob = self._model(audio_tensor, self.sample_rate).item()
            return speech_prob >= self.threshold, speech_prob
        except Exception as e:
            logger.error(f"Speech detection failed: {e}")
            return False, 0.0


class SpeechToText:
    """
    Speech-to-Text using Faster-Whisper.
    
    Provides efficient local transcription with GPU acceleration
    when available.
    """
    
    def __init__(
        self,
        model_size: str = "base.en",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "en",
        vad_enabled: bool = True,
        vad_threshold: float = 0.5,
    ):
        """
        Initialize the STT engine.
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large).
            device: Device to use (cpu, cuda).
            compute_type: Compute type (float16, int8, float32).
            language: Language code for transcription.
            vad_enabled: Enable voice activity detection.
            vad_threshold: VAD threshold.
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.vad_enabled = vad_enabled
        
        self._model: Optional[WhisperModel] = None
        self._vad = SileroVAD(threshold=vad_threshold) if vad_enabled else None
    
    @property
    def is_available(self) -> bool:
        """Check if STT is available."""
        return FASTER_WHISPER_AVAILABLE
    
    def _load_model(self) -> bool:
        """Load the Whisper model."""
        if not FASTER_WHISPER_AVAILABLE:
            return False
        
        try:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info("Whisper model loaded")
            return True
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            return False
    
    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
    ) -> TranscriptionResult:
        """
        Transcribe audio to text.
        
        Args:
            audio: Audio samples (float32, mono).
            sample_rate: Audio sample rate.
            
        Returns:
            TranscriptionResult with transcription.
        """
        if self._model is None and not self._load_model():
            return TranscriptionResult(
                text="",
                language="",
                confidence=0.0,
                duration=0.0,
                segments=[],
            )
        
        # Resample if needed
        if sample_rate != 16000:
            from scipy import signal
            num_samples = int(len(audio) * 16000 / sample_rate)
            audio = signal.resample(audio, num_samples)
        
        # Apply VAD if enabled
        if self._vad and self._vad.is_available:
            speech_segments = self._vad.detect_speech(audio, return_seconds=False)
            if not speech_segments:
                return TranscriptionResult(
                    text="",
                    language=self.language,
                    confidence=0.0,
                    duration=len(audio) / 16000,
                    segments=[],
                )
        
        try:
            segments, info = self._model.transcribe(
                audio,
                language=self.language if self.language else None,
                beam_size=5,
                vad_filter=self.vad_enabled,
            )
            
            # Collect segments
            segment_list = []
            full_text = []
            
            for segment in segments:
                segment_list.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "confidence": segment.avg_logprob,
                })
                full_text.append(segment.text)
            
            return TranscriptionResult(
                text=" ".join(full_text).strip(),
                language=info.language,
                confidence=info.language_probability,
                duration=info.duration,
                segments=segment_list,
            )
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return TranscriptionResult(
                text="",
                language="",
                confidence=0.0,
                duration=0.0,
                segments=[],
            )
    
    def transcribe_file(self, audio_path: Path | str) -> TranscriptionResult:
        """
        Transcribe an audio file.
        
        Args:
            audio_path: Path to audio file.
            
        Returns:
            TranscriptionResult with transcription.
        """
        if not SOUNDFILE_AVAILABLE:
            logger.error("soundfile not available")
            return TranscriptionResult("", "", 0.0, 0.0, [])
        
        try:
            audio, sr = sf.read(str(audio_path))
            
            # Convert to mono if stereo
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)
            
            return self.transcribe(audio.astype(np.float32), sr)
        except Exception as e:
            logger.error(f"Failed to load audio file: {e}")
            return TranscriptionResult("", "", 0.0, 0.0, [])


class AudioRecorder:
    """
    Audio recorder with VAD-based automatic stopping.
    
    Records audio until silence is detected or timeout.
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        silence_duration: float = 1.5,
        max_duration: float = 30.0,
        input_device: Optional[int] = None,
        vad_threshold: float = 0.5,
    ):
        """
        Initialize the audio recorder.
        
        Args:
            sample_rate: Audio sample rate.
            channels: Number of audio channels.
            chunk_size: Audio chunk size.
            silence_duration: Silence duration to stop recording.
            max_duration: Maximum recording duration.
            input_device: Input device index.
            vad_threshold: VAD threshold for speech detection.
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.silence_duration = silence_duration
        self.max_duration = max_duration
        self.input_device = input_device
        
        self._vad = SileroVAD(threshold=vad_threshold)
        self._recording = False
        self._audio_queue: queue.Queue = queue.Queue()
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream."""
        if status:
            logger.warning(f"Audio status: {status}")
        self._audio_queue.put(indata.copy())
    
    def record(
        self,
        on_speech_start: Optional[Callable] = None,
        on_speech_end: Optional[Callable] = None,
    ) -> Optional[np.ndarray]:
        """
        Record audio with VAD-based stopping.
        
        Args:
            on_speech_start: Callback when speech starts.
            on_speech_end: Callback when speech ends.
            
        Returns:
            Recorded audio as numpy array, or None if failed.
        """
        if not SOUNDDEVICE_AVAILABLE:
            logger.error("sounddevice not available")
            return None
        
        self._recording = True
        audio_chunks = []
        speech_started = False
        silence_start = None
        start_time = time.time()
        
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.float32,
                blocksize=self.chunk_size,
                device=self.input_device,
                callback=self._audio_callback,
            ):
                logger.debug("Recording started")
                
                while self._recording:
                    # Check timeout
                    if time.time() - start_time > self.max_duration:
                        logger.debug("Max duration reached")
                        break
                    
                    try:
                        chunk = self._audio_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    
                    audio_chunks.append(chunk)
                    
                    # Check for speech
                    is_speech, prob = self._vad.is_speech(chunk.flatten())
                    
                    if is_speech:
                        if not speech_started:
                            speech_started = True
                            silence_start = None
                            if on_speech_start:
                                on_speech_start()
                            logger.debug("Speech detected")
                        else:
                            silence_start = None
                    else:
                        if speech_started:
                            if silence_start is None:
                                silence_start = time.time()
                            elif time.time() - silence_start >= self.silence_duration:
                                logger.debug("Silence detected, stopping")
                                if on_speech_end:
                                    on_speech_end()
                                break
        
        except Exception as e:
            logger.error(f"Recording failed: {e}")
            return None
        finally:
            self._recording = False
        
        if not audio_chunks:
            return None
        
        # Concatenate chunks
        audio = np.concatenate(audio_chunks, axis=0)
        return audio.flatten()
    
    def stop(self) -> None:
        """Stop recording."""
        self._recording = False


class ContinuousTranscriber:
    """
    Continuous speech transcription with streaming output.
    
    Combines wake word detection, VAD, and STT for a complete
    voice input pipeline.
    """
    
    def __init__(
        self,
        stt: SpeechToText,
        recorder: AudioRecorder,
        on_transcription: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the continuous transcriber.
        
        Args:
            stt: SpeechToText instance.
            recorder: AudioRecorder instance.
            on_transcription: Callback for transcription results.
        """
        self.stt = stt
        self.recorder = recorder
        self.on_transcription = on_transcription
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def transcribe_once(self) -> Optional[str]:
        """
        Record and transcribe a single utterance.
        
        Returns:
            Transcribed text or None if failed.
        """
        logger.info("Listening...")
        audio = self.recorder.record()
        
        if audio is None or len(audio) == 0:
            return None
        
        logger.info("Transcribing...")
        result = self.stt.transcribe(audio, self.recorder.sample_rate)
        
        if result.text:
            logger.info(f"Transcribed: {result.text}")
            if self.on_transcription:
                self.on_transcription(result.text)
        
        return result.text
    
    def start_continuous(self) -> None:
        """Start continuous transcription in background."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._continuous_loop, daemon=True)
        self._thread.start()
    
    def _continuous_loop(self) -> None:
        """Main loop for continuous transcription."""
        while self._running:
            try:
                self.transcribe_once()
            except Exception as e:
                logger.error(f"Transcription error: {e}")
                time.sleep(1)
    
    def stop_continuous(self) -> None:
        """Stop continuous transcription."""
        self._running = False
        self.recorder.stop()
        
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
