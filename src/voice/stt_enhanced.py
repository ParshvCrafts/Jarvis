"""
Enhanced Speech-to-Text Module for JARVIS.

Provides multiple STT backends with automatic fallback:
- Faster-Whisper (Primary - local, GPU-accelerated)
- Groq Whisper API (Fast cloud transcription)
- Audio preprocessing with noise reduction
"""

from __future__ import annotations

import asyncio
import io
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from loguru import logger

# Optional numpy import
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None
    logger.warning("numpy not installed. STT features will be limited.")

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False

try:
    import torch
    import torchaudio
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

try:
    import noisereduce as nr
    NOISEREDUCE_AVAILABLE = True
except ImportError:
    NOISEREDUCE_AVAILABLE = False


class STTProvider(Enum):
    """Available STT providers."""
    FASTER_WHISPER = "faster_whisper"
    GROQ_WHISPER = "groq_whisper"
    LOCAL_WHISPER = "local_whisper"


@dataclass
class TranscriptionResult:
    """Result of speech transcription."""
    text: str
    language: str = "en"
    confidence: float = 1.0
    language_probability: float = 1.0
    duration: float = 0.0
    segments: List[Dict[str, Any]] = field(default_factory=list)
    provider: str = "unknown"
    processing_time: float = 0.0
    
    @property
    def is_empty(self) -> bool:
        return not self.text or self.text.strip() == ""
    
    @property
    def detected_language(self) -> str:
        """Get detected language code (2-letter)."""
        return self.language.split("-")[0].lower() if self.language else "en"
    
    @property
    def is_hindi(self) -> bool:
        """Check if detected language is Hindi."""
        return self.detected_language == "hi"
    
    @property
    def is_gujarati(self) -> bool:
        """Check if detected language is Gujarati."""
        return self.detected_language == "gu"
    
    @property
    def is_english(self) -> bool:
        """Check if detected language is English."""
        return self.detected_language == "en"


class AudioPreprocessor:
    """
    Audio preprocessing for improved transcription accuracy.
    
    Features:
    - Noise reduction
    - Normalization
    - Silence trimming
    - Resampling
    """
    
    def __init__(
        self,
        target_sample_rate: int = 16000,
        normalize: bool = True,
        reduce_noise: bool = True,
        trim_silence: bool = True,
        silence_threshold: float = 0.01,
    ):
        self.target_sample_rate = target_sample_rate
        self.normalize = normalize
        self.reduce_noise = reduce_noise
        self.trim_silence = trim_silence
        self.silence_threshold = silence_threshold
    
    def process(
        self,
        audio: np.ndarray,
        sample_rate: int,
    ) -> Tuple[np.ndarray, int]:
        """
        Preprocess audio for transcription.
        
        Args:
            audio: Audio data as numpy array.
            sample_rate: Original sample rate.
            
        Returns:
            Tuple of (processed_audio, new_sample_rate).
        """
        # Ensure float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        
        # Ensure mono
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
        
        # Resample if needed
        if sample_rate != self.target_sample_rate:
            audio = self._resample(audio, sample_rate, self.target_sample_rate)
            sample_rate = self.target_sample_rate
        
        # Noise reduction
        if self.reduce_noise and NOISEREDUCE_AVAILABLE:
            try:
                audio = nr.reduce_noise(y=audio, sr=sample_rate, prop_decrease=0.8)
            except Exception as e:
                logger.debug(f"Noise reduction failed: {e}")
        
        # Normalize
        if self.normalize:
            max_val = np.max(np.abs(audio))
            if max_val > 0:
                audio = audio / max_val * 0.95
        
        # Trim silence
        if self.trim_silence:
            audio = self._trim_silence(audio)
        
        return audio, sample_rate
    
    def _resample(
        self,
        audio: np.ndarray,
        orig_sr: int,
        target_sr: int,
    ) -> np.ndarray:
        """Resample audio to target sample rate."""
        if TORCH_AVAILABLE:
            try:
                audio_tensor = torch.from_numpy(audio).unsqueeze(0)
                resampler = torchaudio.transforms.Resample(orig_sr, target_sr)
                resampled = resampler(audio_tensor)
                return resampled.squeeze(0).numpy()
            except Exception:
                pass
        
        # Fallback: simple linear interpolation
        duration = len(audio) / orig_sr
        target_length = int(duration * target_sr)
        indices = np.linspace(0, len(audio) - 1, target_length)
        return np.interp(indices, np.arange(len(audio)), audio)
    
    def _trim_silence(self, audio: np.ndarray) -> np.ndarray:
        """Trim silence from beginning and end."""
        # Find non-silent regions
        energy = np.abs(audio)
        non_silent = energy > self.silence_threshold
        
        if not np.any(non_silent):
            return audio
        
        # Find first and last non-silent sample
        non_silent_indices = np.where(non_silent)[0]
        start = max(0, non_silent_indices[0] - 1600)  # 100ms padding
        end = min(len(audio), non_silent_indices[-1] + 1600)
        
        return audio[start:end]


class EnhancedSileroVAD:
    """
    Enhanced Voice Activity Detection using Silero VAD.
    
    Improvements:
    - Configurable thresholds
    - Speech probability smoothing
    - Pre-speech padding
    - Ambient noise adaptation
    """
    
    def __init__(
        self,
        threshold: float = 0.5,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 500,
        pre_speech_pad_ms: int = 300,
        post_speech_pad_ms: int = 300,
        sample_rate: int = 16000,
    ):
        self.threshold = threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_silence_duration_ms = min_silence_duration_ms
        self.pre_speech_pad_ms = pre_speech_pad_ms
        self.post_speech_pad_ms = post_speech_pad_ms
        self.sample_rate = sample_rate
        
        self._model = None
        self._ambient_level = 0.0
        self._speech_probs_history = []
    
    @property
    def is_available(self) -> bool:
        return TORCH_AVAILABLE
    
    def _load_model(self) -> bool:
        if not TORCH_AVAILABLE:
            return False
        
        if self._model is not None:
            return True
        
        try:
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                trust_repo=True,
            )
            self._model = model
            logger.info("Silero VAD model loaded")
            return True
        except Exception as e:
            logger.error(f"Failed to load Silero VAD: {e}")
            return False
    
    def reset_states(self) -> None:
        """Reset VAD states for new audio stream."""
        if self._model is not None:
            self._model.reset_states()
        self._speech_probs_history = []
    
    def is_speech(
        self,
        audio_chunk: np.ndarray,
        return_probability: bool = False,
    ) -> Union[bool, Tuple[bool, float]]:
        """
        Check if audio chunk contains speech.
        
        Args:
            audio_chunk: Audio data (16kHz, mono, float32).
            return_probability: Return speech probability.
            
        Returns:
            Boolean or tuple of (is_speech, probability).
        """
        if not self._load_model():
            return (False, 0.0) if return_probability else False
        
        try:
            # Ensure correct format
            if audio_chunk.dtype != np.float32:
                audio_chunk = audio_chunk.astype(np.float32)
            
            # Convert to tensor
            audio_tensor = torch.from_numpy(audio_chunk)
            
            # Get speech probability
            speech_prob = self._model(audio_tensor, self.sample_rate).item()
            
            # Smooth probability
            self._speech_probs_history.append(speech_prob)
            if len(self._speech_probs_history) > 5:
                self._speech_probs_history.pop(0)
            
            smoothed_prob = np.mean(self._speech_probs_history)
            is_speech = smoothed_prob > self.threshold
            
            if return_probability:
                return is_speech, smoothed_prob
            return is_speech
        
        except Exception as e:
            logger.error(f"VAD error: {e}")
            return (False, 0.0) if return_probability else False
    
    def get_speech_segments(
        self,
        audio: np.ndarray,
    ) -> List[Tuple[int, int]]:
        """
        Get speech segments from audio.
        
        Args:
            audio: Full audio data.
            
        Returns:
            List of (start_sample, end_sample) tuples.
        """
        if not self._load_model():
            return [(0, len(audio))]
        
        try:
            audio_tensor = torch.from_numpy(audio.astype(np.float32))
            
            # Get speech timestamps
            speech_timestamps = self._model.get_speech_timestamps(
                audio_tensor,
                self._model,
                sampling_rate=self.sample_rate,
                threshold=self.threshold,
                min_speech_duration_ms=self.min_speech_duration_ms,
                min_silence_duration_ms=self.min_silence_duration_ms,
            )
            
            # Add padding
            segments = []
            pre_pad = int(self.pre_speech_pad_ms * self.sample_rate / 1000)
            post_pad = int(self.post_speech_pad_ms * self.sample_rate / 1000)
            
            for ts in speech_timestamps:
                start = max(0, ts['start'] - pre_pad)
                end = min(len(audio), ts['end'] + post_pad)
                segments.append((start, end))
            
            return segments if segments else [(0, len(audio))]
        
        except Exception as e:
            logger.error(f"Failed to get speech segments: {e}")
            return [(0, len(audio))]


class FasterWhisperSTT:
    """
    Faster-Whisper based speech-to-text.
    
    Local, GPU-accelerated transcription.
    """
    
    def __init__(
        self,
        model_size: str = "base.en",
        device: str = "auto",
        compute_type: str = "auto",
        language: str = "en",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self._model = None
    
    @property
    def is_available(self) -> bool:
        return FASTER_WHISPER_AVAILABLE
    
    def _load_model(self) -> bool:
        if not FASTER_WHISPER_AVAILABLE:
            return False
        
        if self._model is not None:
            return True
        
        try:
            # Auto-detect device
            device = self.device
            compute_type = self.compute_type
            
            if device == "auto":
                device = "cuda" if TORCH_AVAILABLE and torch.cuda.is_available() else "cpu"
            
            if compute_type == "auto":
                compute_type = "float16" if device == "cuda" else "int8"
            
            logger.info(f"Loading Faster-Whisper model: {self.model_size} on {device}")
            self._model = WhisperModel(
                self.model_size,
                device=device,
                compute_type=compute_type,
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            return False
    
    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
    ) -> TranscriptionResult:
        """Transcribe audio to text."""
        if not self._load_model():
            return TranscriptionResult(text="", provider="faster_whisper")
        
        start_time = time.time()
        
        try:
            # Ensure correct format
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
            
            # Transcribe
            segments, info = self._model.transcribe(
                audio,
                language=self.language if self.language != "auto" else None,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_speech_duration_ms=250,
                    min_silence_duration_ms=500,
                ),
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
            
            text = " ".join(full_text).strip()
            duration = info.duration if hasattr(info, 'duration') else len(audio) / sample_rate
            
            detected_lang = info.language if hasattr(info, 'language') else self.language
            lang_prob = info.language_probability if hasattr(info, 'language_probability') else 1.0
            
            logger.debug(f"Transcribed: lang={detected_lang}, prob={lang_prob:.2f}, text={text[:50]}...")
            
            return TranscriptionResult(
                text=text,
                language=detected_lang,
                confidence=lang_prob,
                language_probability=lang_prob,
                duration=duration,
                segments=segment_list,
                provider="faster_whisper",
                processing_time=time.time() - start_time,
            )
        
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return TranscriptionResult(
                text="",
                provider="faster_whisper",
                processing_time=time.time() - start_time,
            )
    
    def transcribe_file(self, file_path: Path) -> TranscriptionResult:
        """Transcribe audio file."""
        if not SOUNDFILE_AVAILABLE:
            return TranscriptionResult(text="", provider="faster_whisper")
        
        try:
            audio, sample_rate = sf.read(str(file_path))
            return self.transcribe(audio, sample_rate)
        except Exception as e:
            logger.error(f"Failed to read audio file: {e}")
            return TranscriptionResult(text="", provider="faster_whisper")


class GroqWhisperSTT:
    """
    Groq Whisper API for fast cloud transcription.
    
    Uses Groq's hosted Whisper for fast transcription.
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "whisper-large-v3",
        language: str = "en",
    ):
        self.api_key = api_key
        self.model = model
        self.language = language
    
    @property
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
    ) -> TranscriptionResult:
        """Transcribe audio using Groq Whisper API."""
        if not self.is_available:
            return TranscriptionResult(text="", provider="groq_whisper")
        
        start_time = time.time()
        
        try:
            from groq import Groq
            
            # Save audio to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                sf.write(f.name, audio, sample_rate)
                temp_path = Path(f.name)
            
            try:
                client = Groq(api_key=self.api_key)
                
                with open(temp_path, "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        file=(temp_path.name, audio_file.read()),
                        model=self.model,
                        language=self.language if self.language != "auto" else None,
                        response_format="verbose_json",
                    )
                
                return TranscriptionResult(
                    text=transcription.text,
                    language=transcription.language if hasattr(transcription, 'language') else self.language,
                    confidence=1.0,
                    duration=transcription.duration if hasattr(transcription, 'duration') else len(audio) / sample_rate,
                    segments=[],
                    provider="groq_whisper",
                    processing_time=time.time() - start_time,
                )
            
            finally:
                temp_path.unlink(missing_ok=True)
        
        except Exception as e:
            logger.error(f"Groq Whisper transcription failed: {e}")
            return TranscriptionResult(
                text="",
                provider="groq_whisper",
                processing_time=time.time() - start_time,
            )


class EnhancedSpeechToText:
    """
    Enhanced Speech-to-Text with multiple backends and preprocessing.
    
    Features:
    - Multiple STT backends with automatic fallback
    - Audio preprocessing (noise reduction, normalization)
    - VAD-based speech detection
    - Automatic provider selection based on availability
    """
    
    def __init__(
        self,
        primary_provider: STTProvider = STTProvider.FASTER_WHISPER,
        model_size: str = "base.en",
        device: str = "auto",
        language: str = "en",
        groq_api_key: Optional[str] = None,
        enable_preprocessing: bool = True,
        enable_vad: bool = True,
    ):
        self.primary_provider = primary_provider
        self.language = language
        self.enable_preprocessing = enable_preprocessing
        self.enable_vad = enable_vad
        
        # Initialize preprocessor
        self.preprocessor = AudioPreprocessor() if enable_preprocessing else None
        
        # Initialize VAD
        self.vad = EnhancedSileroVAD() if enable_vad else None
        
        # Initialize STT backends
        self._backends: Dict[STTProvider, Any] = {}
        
        # Faster-Whisper (local)
        if FASTER_WHISPER_AVAILABLE:
            self._backends[STTProvider.FASTER_WHISPER] = FasterWhisperSTT(
                model_size=model_size,
                device=device,
                language=language,
            )
        
        # Groq Whisper (cloud)
        if groq_api_key:
            self._backends[STTProvider.GROQ_WHISPER] = GroqWhisperSTT(
                api_key=groq_api_key,
                language=language,
            )
        
        logger.info(f"Enhanced STT initialized with backends: {list(self._backends.keys())}")
    
    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        provider: Optional[STTProvider] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio to text.
        
        Args:
            audio: Audio data as numpy array.
            sample_rate: Audio sample rate.
            provider: Specific provider to use (auto-selects if None).
            
        Returns:
            TranscriptionResult with transcribed text.
        """
        # Preprocess audio
        if self.preprocessor:
            audio, sample_rate = self.preprocessor.process(audio, sample_rate)
        
        # Extract speech segments if VAD enabled
        if self.vad and self.vad.is_available:
            segments = self.vad.get_speech_segments(audio)
            if segments:
                # Concatenate speech segments
                speech_audio = np.concatenate([audio[start:end] for start, end in segments])
                audio = speech_audio
        
        # Check if audio is too short
        if len(audio) < sample_rate * 0.3:  # Less than 300ms
            return TranscriptionResult(text="", provider="none")
        
        # Select provider
        if provider and provider in self._backends:
            backend = self._backends[provider]
            if backend.is_available:
                return backend.transcribe(audio, sample_rate)
        
        # Try primary provider first
        if self.primary_provider in self._backends:
            backend = self._backends[self.primary_provider]
            if backend.is_available:
                result = backend.transcribe(audio, sample_rate)
                if not result.is_empty:
                    return result
        
        # Fallback to other providers
        for provider_type, backend in self._backends.items():
            if provider_type != self.primary_provider and backend.is_available:
                result = backend.transcribe(audio, sample_rate)
                if not result.is_empty:
                    return result
        
        return TranscriptionResult(text="", provider="none")
    
    def transcribe_file(
        self,
        file_path: Path,
        provider: Optional[STTProvider] = None,
    ) -> TranscriptionResult:
        """Transcribe audio file."""
        if not SOUNDFILE_AVAILABLE:
            return TranscriptionResult(text="", provider="none")
        
        try:
            audio, sample_rate = sf.read(str(file_path))
            return self.transcribe(audio, sample_rate, provider)
        except Exception as e:
            logger.error(f"Failed to read audio file: {e}")
            return TranscriptionResult(text="", provider="none")
    
    def get_available_providers(self) -> List[STTProvider]:
        """Get list of available STT providers."""
        return [p for p, b in self._backends.items() if b.is_available]
