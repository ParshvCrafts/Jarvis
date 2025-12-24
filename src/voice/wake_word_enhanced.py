"""
Enhanced Wake Word Detection Module for JARVIS.

Features:
- Custom wake word training support
- Anti-false-positive measures (consecutive detections)
- Confidence threshold tuning
- Multiple wake word support
- Training data generation guidance
"""

from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from loguru import logger

# Optional numpy import
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None
    logger.warning("numpy not installed. Wake word detection will be limited.")

try:
    import openwakeword
    from openwakeword.model import Model as OWWModel
    OPENWAKEWORD_AVAILABLE = True
except ImportError:
    OPENWAKEWORD_AVAILABLE = False
    logger.warning("openwakeword not available")

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False


@dataclass
class WakeWordDetection:
    """A wake word detection event."""
    wake_word: str
    confidence: float
    timestamp: float
    consecutive_count: int


@dataclass
class WakeWordConfig:
    """Configuration for a wake word."""
    phrase: str
    model_path: Optional[str] = None
    threshold: float = 0.5
    min_consecutive: int = 2
    cooldown_seconds: float = 2.0


class EnhancedWakeWordDetector:
    """
    Enhanced wake word detection with anti-false-positive measures.
    
    Features:
    - Configurable confidence thresholds
    - Consecutive detection requirement
    - Multiple wake word support
    - Custom model loading
    - Cooldown period after detection
    """
    
    # Pre-trained models available in openWakeWord
    PRETRAINED_MODELS = [
        "hey_jarvis",
        "alexa",
        "hey_mycroft",
        "ok_google",
        "hey_siri",
    ]
    
    def __init__(
        self,
        wake_words: Optional[List[WakeWordConfig]] = None,
        sample_rate: int = 16000,
        chunk_size: int = 1280,
        input_device: Optional[int] = None,
    ):
        """
        Initialize the enhanced wake word detector.
        
        Args:
            wake_words: List of wake word configurations.
            sample_rate: Audio sample rate (must be 16000 for openWakeWord).
            chunk_size: Audio chunk size in samples.
            input_device: Input device index.
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.input_device = input_device
        
        # Default wake word if none provided
        if wake_words is None:
            wake_words = [WakeWordConfig(
                phrase="hey jarvis",
                threshold=0.5,
                min_consecutive=2,
            )]
        
        self.wake_words = {ww.phrase.lower(): ww for ww in wake_words}
        
        # Detection state
        self._consecutive_counts: Dict[str, int] = {ww: 0 for ww in self.wake_words}
        self._last_detection_time: Dict[str, float] = {ww: 0 for ww in self.wake_words}
        self._detection_history: List[WakeWordDetection] = []
        
        # Model
        self._model: Optional[OWWModel] = None
        
        # Threading
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable[[WakeWordDetection], None]] = None
        self._audio_queue: queue.Queue = queue.Queue()
    
    @property
    def is_available(self) -> bool:
        return OPENWAKEWORD_AVAILABLE and SOUNDDEVICE_AVAILABLE
    
    def _load_model(self) -> bool:
        """Load the wake word model."""
        if not OPENWAKEWORD_AVAILABLE:
            return False
        
        if self._model is not None:
            return True
        
        try:
            # Download default models if needed
            openwakeword.utils.download_models()
            
            # Collect model paths
            model_paths = []
            for ww_config in self.wake_words.values():
                if ww_config.model_path:
                    model_paths.append(ww_config.model_path)
            
            # Load model
            if model_paths:
                self._model = OWWModel(
                    wakeword_models=model_paths,
                    inference_framework="onnx",
                )
            else:
                # Use default models
                self._model = OWWModel(inference_framework="onnx")
            
            logger.info(f"Wake word model loaded with {len(self._model.models)} models")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load wake word model: {e}")
            return False
    
    def _process_audio(self, audio_chunk: np.ndarray) -> Optional[WakeWordDetection]:
        """
        Process an audio chunk and check for wake words.
        
        Args:
            audio_chunk: Audio data (16kHz, mono, int16 or float32).
            
        Returns:
            WakeWordDetection if detected, None otherwise.
        """
        if self._model is None:
            return None
        
        try:
            # Ensure correct format
            if audio_chunk.dtype == np.float32:
                audio_chunk = (audio_chunk * 32767).astype(np.int16)
            
            # Get predictions
            predictions = self._model.predict(audio_chunk)
            
            current_time = time.time()
            
            # Check each wake word
            for model_name, confidence in predictions.items():
                # Find matching wake word config
                ww_config = None
                for phrase, config in self.wake_words.items():
                    # Match by model name or phrase
                    if model_name.lower().replace("_", " ") in phrase or phrase in model_name.lower().replace("_", " "):
                        ww_config = config
                        phrase_key = phrase
                        break
                
                if ww_config is None:
                    # Use first config as default
                    phrase_key = list(self.wake_words.keys())[0]
                    ww_config = self.wake_words[phrase_key]
                
                # Check if above threshold
                if confidence >= ww_config.threshold:
                    self._consecutive_counts[phrase_key] += 1
                    
                    # Check consecutive requirement
                    if self._consecutive_counts[phrase_key] >= ww_config.min_consecutive:
                        # Check cooldown
                        time_since_last = current_time - self._last_detection_time[phrase_key]
                        if time_since_last >= ww_config.cooldown_seconds:
                            detection = WakeWordDetection(
                                wake_word=phrase_key,
                                confidence=confidence,
                                timestamp=current_time,
                                consecutive_count=self._consecutive_counts[phrase_key],
                            )
                            
                            # Reset state
                            self._consecutive_counts[phrase_key] = 0
                            self._last_detection_time[phrase_key] = current_time
                            self._detection_history.append(detection)
                            
                            return detection
                else:
                    # Reset consecutive count if below threshold
                    self._consecutive_counts[phrase_key] = max(0, self._consecutive_counts[phrase_key] - 1)
            
            return None
        
        except Exception as e:
            logger.error(f"Wake word processing error: {e}")
            return None
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream."""
        if status:
            logger.warning(f"Audio status: {status}")
        
        self._audio_queue.put(indata.copy())
    
    def _detection_loop(self) -> None:
        """Main detection loop."""
        if not self._load_model():
            logger.error("Failed to load wake word model")
            return
        
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.int16,
                blocksize=self.chunk_size,
                device=self.input_device,
                callback=self._audio_callback,
            ):
                logger.info("Wake word detection started")
                
                while self._running:
                    try:
                        audio_chunk = self._audio_queue.get(timeout=0.1)
                        audio_chunk = audio_chunk.flatten()
                        
                        detection = self._process_audio(audio_chunk)
                        
                        if detection and self._callback:
                            logger.info(f"Wake word detected: {detection.wake_word} (confidence: {detection.confidence:.2f})")
                            self._callback(detection)
                    
                    except queue.Empty:
                        continue
        
        except Exception as e:
            logger.error(f"Wake word detection error: {e}")
    
    def start(self, callback: Callable[[WakeWordDetection], None]) -> bool:
        """
        Start wake word detection.
        
        Args:
            callback: Function called when wake word is detected.
            
        Returns:
            True if started successfully.
        """
        if not self.is_available:
            logger.error("Wake word detection not available")
            return False
        
        if self._running:
            return True
        
        self._callback = callback
        self._running = True
        self._thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._thread.start()
        
        return True
    
    def stop(self) -> None:
        """Stop wake word detection."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        
        # Clear queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
    
    def update_threshold(self, wake_word: str, threshold: float) -> bool:
        """Update threshold for a wake word."""
        wake_word = wake_word.lower()
        if wake_word in self.wake_words:
            self.wake_words[wake_word].threshold = max(0.0, min(1.0, threshold))
            return True
        return False
    
    def get_detection_history(self, limit: int = 10) -> List[WakeWordDetection]:
        """Get recent detection history."""
        return self._detection_history[-limit:]
    
    def reset_state(self) -> None:
        """Reset detection state."""
        for ww in self._consecutive_counts:
            self._consecutive_counts[ww] = 0
            self._last_detection_time[ww] = 0


class WakeWordTrainer:
    """
    Helper for training custom wake words.
    
    Provides guidance and utilities for collecting training data
    and training custom wake word models.
    """
    
    TRAINING_INSTRUCTIONS = """
# Custom Wake Word Training Guide

## Overview
Training a custom wake word requires collecting audio samples and using
openWakeWord's training pipeline.

## Step 1: Collect Positive Samples
Record yourself saying the wake word phrase multiple times:
- Record at least 50-100 samples
- Vary your tone, speed, and distance from microphone
- Include samples from different times of day
- Use different microphones if possible

## Step 2: Collect Negative Samples
Collect audio that does NOT contain the wake word:
- General speech
- Background noise
- Similar-sounding phrases
- Music and TV audio

## Step 3: Prepare Training Data
Organize your data:
```
training_data/
├── positive/
│   ├── sample_001.wav
│   ├── sample_002.wav
│   └── ...
└── negative/
    ├── noise_001.wav
    ├── speech_001.wav
    └── ...
```

## Step 4: Train the Model
Use openWakeWord's training script:
```python
from openwakeword.train import train_model

train_model(
    positive_dir="training_data/positive",
    negative_dir="training_data/negative",
    output_path="models/my_wake_word.onnx",
    epochs=100,
)
```

## Step 5: Test and Tune
- Test with various speakers
- Adjust threshold based on false positive/negative rate
- Collect more samples if needed

## Tips
- Use 16kHz sample rate for all recordings
- Keep samples 1-3 seconds long
- Include background noise in some positive samples
- Test in your actual usage environment
"""
    
    def __init__(self, data_dir: Path):
        """
        Initialize the trainer.
        
        Args:
            data_dir: Directory for training data.
        """
        self.data_dir = Path(data_dir)
        self.positive_dir = self.data_dir / "positive"
        self.negative_dir = self.data_dir / "negative"
    
    def setup_directories(self) -> None:
        """Create training data directories."""
        self.positive_dir.mkdir(parents=True, exist_ok=True)
        self.negative_dir.mkdir(parents=True, exist_ok=True)
        
        # Save instructions
        instructions_path = self.data_dir / "TRAINING_INSTRUCTIONS.md"
        instructions_path.write_text(self.TRAINING_INSTRUCTIONS)
        
        logger.info(f"Training directories created at {self.data_dir}")
    
    def record_sample(
        self,
        output_path: Path,
        duration: float = 2.0,
        sample_rate: int = 16000,
        countdown: int = 3,
    ) -> bool:
        """
        Record a training sample.
        
        Args:
            output_path: Path to save the recording.
            duration: Recording duration in seconds.
            sample_rate: Sample rate.
            countdown: Countdown before recording.
            
        Returns:
            True if successful.
        """
        if not SOUNDDEVICE_AVAILABLE:
            logger.error("sounddevice not available")
            return False
        
        try:
            import soundfile as sf
            
            # Countdown
            for i in range(countdown, 0, -1):
                print(f"Recording in {i}...")
                time.sleep(1)
            
            print("Recording...")
            
            # Record
            audio = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype=np.float32,
            )
            sd.wait()
            
            print("Done!")
            
            # Save
            sf.write(str(output_path), audio.flatten(), sample_rate)
            logger.info(f"Saved sample to {output_path}")
            
            return True
        
        except Exception as e:
            logger.error(f"Recording failed: {e}")
            return False
    
    def collect_positive_samples(
        self,
        num_samples: int = 10,
        duration: float = 2.0,
    ) -> int:
        """
        Interactively collect positive samples.
        
        Args:
            num_samples: Number of samples to collect.
            duration: Duration of each sample.
            
        Returns:
            Number of samples collected.
        """
        self.setup_directories()
        
        print(f"\n{'='*50}")
        print("Positive Sample Collection")
        print(f"{'='*50}")
        print(f"Say your wake word phrase {num_samples} times.")
        print("Press Enter to start each recording, or 'q' to quit.\n")
        
        collected = 0
        existing = len(list(self.positive_dir.glob("*.wav")))
        
        for i in range(num_samples):
            user_input = input(f"Sample {i+1}/{num_samples} - Press Enter to record (q to quit): ")
            
            if user_input.lower() == 'q':
                break
            
            output_path = self.positive_dir / f"sample_{existing + i + 1:04d}.wav"
            if self.record_sample(output_path, duration):
                collected += 1
        
        print(f"\nCollected {collected} positive samples.")
        return collected
    
    def get_sample_counts(self) -> Dict[str, int]:
        """Get counts of collected samples."""
        return {
            "positive": len(list(self.positive_dir.glob("*.wav"))) if self.positive_dir.exists() else 0,
            "negative": len(list(self.negative_dir.glob("*.wav"))) if self.negative_dir.exists() else 0,
        }
    
    def get_training_status(self) -> str:
        """Get training readiness status."""
        counts = self.get_sample_counts()
        
        status = []
        status.append(f"Positive samples: {counts['positive']} (recommended: 50+)")
        status.append(f"Negative samples: {counts['negative']} (recommended: 100+)")
        
        if counts['positive'] >= 50 and counts['negative'] >= 100:
            status.append("\n✓ Ready for training!")
        else:
            status.append("\n⚠ Need more samples before training.")
        
        return "\n".join(status)
