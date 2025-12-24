"""
Voice Authentication Module for JARVIS.

Provides speaker verification using voice embeddings from Resemblyzer.
Verifies that commands come from the authorized user, not just any voice.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import List, Optional, Tuple

from loguru import logger

# Optional numpy import
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    from resemblyzer import VoiceEncoder, preprocess_wav
    from resemblyzer.audio import sampling_rate as RESEMBLYZER_SR
    RESEMBLYZER_AVAILABLE = True
except ImportError:
    RESEMBLYZER_AVAILABLE = False
    RESEMBLYZER_SR = 16000
    logger.warning("Resemblyzer not available. Voice authentication disabled.")

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    sf = None


class VoiceAuthenticator:
    """
    Voice authentication using speaker embeddings.
    
    Uses Resemblyzer to create voice embeddings and compare them
    for speaker verification.
    """
    
    def __init__(
        self,
        voice_prints_dir: Path | str,
        similarity_threshold: float = 0.75,
        min_audio_duration: float = 1.5,
        sample_rate: int = 16000,
    ):
        """
        Initialize the voice authenticator.
        
        Args:
            voice_prints_dir: Directory to store voice prints.
            similarity_threshold: Minimum similarity for verification (0-1).
            min_audio_duration: Minimum audio duration in seconds.
            sample_rate: Audio sample rate.
        """
        self.voice_prints_dir = Path(voice_prints_dir)
        self.voice_prints_dir.mkdir(parents=True, exist_ok=True)
        
        self.similarity_threshold = similarity_threshold
        self.min_audio_duration = min_audio_duration
        self.sample_rate = sample_rate
        
        # Voice encoder (lazy loaded)
        self._encoder: Optional[VoiceEncoder] = None
        
        # Cache for voice prints
        self._voice_prints_cache: Optional[List[np.ndarray]] = None
        self._cache_valid = False
    
    @property
    def is_available(self) -> bool:
        """Check if voice authentication is available."""
        return RESEMBLYZER_AVAILABLE
    
    @property
    def voice_prints_file(self) -> Path:
        """Path to the voice prints file."""
        return self.voice_prints_dir / "user_voice_prints.pkl"
    
    def _get_encoder(self) -> Optional[VoiceEncoder]:
        """Get or create the voice encoder."""
        if not RESEMBLYZER_AVAILABLE:
            return None
        
        if self._encoder is None:
            logger.info("Loading voice encoder model...")
            self._encoder = VoiceEncoder()
            logger.info("Voice encoder loaded")
        
        return self._encoder
    
    def _load_voice_prints(self) -> List[np.ndarray]:
        """Load cached voice prints from disk."""
        if self._cache_valid and self._voice_prints_cache is not None:
            return self._voice_prints_cache
        
        if not self.voice_prints_file.exists():
            self._voice_prints_cache = []
            self._cache_valid = True
            return []
        
        try:
            with open(self.voice_prints_file, "rb") as f:
                self._voice_prints_cache = pickle.load(f)
            self._cache_valid = True
            logger.debug(f"Loaded {len(self._voice_prints_cache)} voice prints")
            return self._voice_prints_cache
        except Exception as e:
            logger.error(f"Failed to load voice prints: {e}")
            self._voice_prints_cache = []
            self._cache_valid = True
            return []
    
    def _save_voice_prints(self, voice_prints: List[np.ndarray]) -> bool:
        """Save voice prints to disk."""
        try:
            with open(self.voice_prints_file, "wb") as f:
                pickle.dump(voice_prints, f)
            self._voice_prints_cache = voice_prints
            self._cache_valid = True
            logger.info(f"Saved {len(voice_prints)} voice prints")
            return True
        except Exception as e:
            logger.error(f"Failed to save voice prints: {e}")
            return False
    
    def has_enrolled_voice(self) -> bool:
        """Check if any voice prints are enrolled."""
        return len(self._load_voice_prints()) > 0
    
    def _preprocess_audio(self, audio: np.ndarray, sr: int) -> Optional[np.ndarray]:
        """
        Preprocess audio for the voice encoder.
        
        Args:
            audio: Audio samples.
            sr: Sample rate.
            
        Returns:
            Preprocessed audio or None if invalid.
        """
        if not RESEMBLYZER_AVAILABLE:
            return None
        
        # Check duration
        duration = len(audio) / sr
        if duration < self.min_audio_duration:
            logger.warning(f"Audio too short: {duration:.2f}s < {self.min_audio_duration}s")
            return None
        
        # Resample if necessary
        if sr != RESEMBLYZER_SR:
            from scipy import signal
            num_samples = int(len(audio) * RESEMBLYZER_SR / sr)
            audio = signal.resample(audio, num_samples)
        
        # Preprocess using Resemblyzer
        try:
            processed = preprocess_wav(audio)
            return processed
        except Exception as e:
            logger.error(f"Audio preprocessing failed: {e}")
            return None
    
    def get_embedding(self, audio: np.ndarray, sr: int) -> Optional[np.ndarray]:
        """
        Get voice embedding from audio.
        
        Args:
            audio: Audio samples (mono).
            sr: Sample rate.
            
        Returns:
            Voice embedding or None if failed.
        """
        encoder = self._get_encoder()
        if encoder is None:
            return None
        
        processed = self._preprocess_audio(audio, sr)
        if processed is None:
            return None
        
        try:
            embedding = encoder.embed_utterance(processed)
            return embedding
        except Exception as e:
            logger.error(f"Failed to get voice embedding: {e}")
            return None
    
    def get_embedding_from_file(self, audio_path: Path | str) -> Optional[np.ndarray]:
        """
        Get voice embedding from an audio file.
        
        Args:
            audio_path: Path to audio file.
            
        Returns:
            Voice embedding or None if failed.
        """
        if not SOUNDFILE_AVAILABLE:
            logger.error("soundfile not available for loading audio")
            return None
        
        try:
            audio, sr = sf.read(str(audio_path))
            
            # Convert to mono if stereo
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)
            
            return self.get_embedding(audio, sr)
        except Exception as e:
            logger.error(f"Failed to load audio file: {e}")
            return None
    
    def enroll_voice(self, audio: np.ndarray, sr: int) -> bool:
        """
        Enroll a new voice print.
        
        Args:
            audio: Audio samples (mono).
            sr: Sample rate.
            
        Returns:
            True if enrollment successful.
        """
        embedding = self.get_embedding(audio, sr)
        if embedding is None:
            logger.warning("Failed to get embedding for enrollment")
            return False
        
        voice_prints = self._load_voice_prints()
        voice_prints.append(embedding)
        
        return self._save_voice_prints(voice_prints)
    
    def enroll_voice_from_file(self, audio_path: Path | str) -> bool:
        """
        Enroll a voice print from an audio file.
        
        Args:
            audio_path: Path to audio file.
            
        Returns:
            True if enrollment successful.
        """
        embedding = self.get_embedding_from_file(audio_path)
        if embedding is None:
            return False
        
        voice_prints = self._load_voice_prints()
        voice_prints.append(embedding)
        
        return self._save_voice_prints(voice_prints)
    
    def enroll_multiple(self, audio_samples: List[Tuple[np.ndarray, int]]) -> int:
        """
        Enroll multiple voice samples.
        
        Args:
            audio_samples: List of (audio, sample_rate) tuples.
            
        Returns:
            Number of successfully enrolled samples.
        """
        voice_prints = self._load_voice_prints()
        enrolled = 0
        
        for audio, sr in audio_samples:
            embedding = self.get_embedding(audio, sr)
            if embedding is not None:
                voice_prints.append(embedding)
                enrolled += 1
        
        if enrolled > 0:
            self._save_voice_prints(voice_prints)
        
        logger.info(f"Enrolled {enrolled}/{len(audio_samples)} voice samples")
        return enrolled
    
    def verify_voice(self, audio: np.ndarray, sr: int) -> Tuple[bool, float]:
        """
        Verify if audio matches enrolled voice prints.
        
        Args:
            audio: Audio samples (mono).
            sr: Sample rate.
            
        Returns:
            Tuple of (is_match, similarity_score).
        """
        known_prints = self._load_voice_prints()
        if not known_prints:
            logger.warning("No enrolled voice prints to verify against")
            return False, 0.0
        
        embedding = self.get_embedding(audio, sr)
        if embedding is None:
            logger.debug("Failed to get embedding for verification")
            return False, 0.0
        
        # Calculate similarity with all known prints
        similarities = []
        for known in known_prints:
            # Cosine similarity
            similarity = np.dot(embedding, known) / (
                np.linalg.norm(embedding) * np.linalg.norm(known)
            )
            similarities.append(similarity)
        
        # Use best match
        best_similarity = float(max(similarities))
        is_match = best_similarity >= self.similarity_threshold
        
        logger.debug(f"Voice verification: match={is_match}, similarity={best_similarity:.3f}")
        
        return is_match, best_similarity
    
    def verify_voice_from_file(self, audio_path: Path | str) -> Tuple[bool, float]:
        """
        Verify voice from an audio file.
        
        Args:
            audio_path: Path to audio file.
            
        Returns:
            Tuple of (is_match, similarity_score).
        """
        if not SOUNDFILE_AVAILABLE:
            return False, 0.0
        
        try:
            audio, sr = sf.read(str(audio_path))
            
            # Convert to mono if stereo
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)
            
            return self.verify_voice(audio, sr)
        except Exception as e:
            logger.error(f"Failed to load audio file for verification: {e}")
            return False, 0.0
    
    def clear_enrollments(self) -> bool:
        """Clear all enrolled voice prints."""
        try:
            if self.voice_prints_file.exists():
                self.voice_prints_file.unlink()
            self._voice_prints_cache = []
            self._cache_valid = True
            logger.info("Cleared all voice enrollments")
            return True
        except Exception as e:
            logger.error(f"Failed to clear voice enrollments: {e}")
            return False
    
    def get_enrollment_count(self) -> int:
        """Get the number of enrolled voice prints."""
        return len(self._load_voice_prints())


def record_voice_sample(
    duration: float = 3.0,
    sample_rate: int = 16000,
) -> Optional[Tuple[np.ndarray, int]]:
    """
    Record a voice sample from the microphone.
    
    Args:
        duration: Recording duration in seconds.
        sample_rate: Sample rate.
        
    Returns:
        Tuple of (audio, sample_rate) or None if failed.
    """
    try:
        import sounddevice as sd
    except ImportError:
        logger.error("sounddevice not available for recording")
        return None
    
    try:
        logger.info(f"Recording {duration}s of audio...")
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype=np.float32,
        )
        sd.wait()
        
        # Flatten to 1D
        audio = audio.flatten()
        
        logger.info("Recording complete")
        return audio, sample_rate
    except Exception as e:
        logger.error(f"Recording failed: {e}")
        return None
