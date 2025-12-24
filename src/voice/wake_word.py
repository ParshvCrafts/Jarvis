"""
Wake Word Detection Module for JARVIS.

Uses openWakeWord for efficient, always-listening wake word detection
with minimal CPU footprint.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable, Optional

from loguru import logger

# Optional numpy import
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    import openwakeword
    from openwakeword.model import Model as WakeWordModel
    OPENWAKEWORD_AVAILABLE = True
except ImportError:
    OPENWAKEWORD_AVAILABLE = False
    logger.warning("openWakeWord not available. Wake word detection disabled.")

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    logger.warning("sounddevice not available.")


class WakeWordDetector:
    """
    Wake word detection using openWakeWord.
    
    Runs in a separate thread with minimal CPU usage,
    continuously listening for the wake word.
    """
    
    def __init__(
        self,
        wake_word: str = "hey jarvis",
        threshold: float = 0.5,
        model_path: Optional[str] = None,
        sample_rate: int = 16000,
        chunk_size: int = 1280,  # 80ms at 16kHz
        input_device: Optional[int] = None,
    ):
        """
        Initialize the wake word detector.
        
        Args:
            wake_word: Wake word phrase to detect.
            threshold: Detection threshold (0.0-1.0).
            model_path: Path to custom wake word model.
            sample_rate: Audio sample rate.
            chunk_size: Audio chunk size for processing.
            input_device: Input device index (None for default).
        """
        self.wake_word = wake_word.lower().replace(" ", "_")
        self.threshold = threshold
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.input_device = input_device
        
        # State
        self._model: Optional[WakeWordModel] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable[[], None]] = None
        self._last_detection_time = 0.0
        self._cooldown = 2.0  # Seconds between detections
        
        # Audio stream
        self._stream = None
    
    @property
    def is_available(self) -> bool:
        """Check if wake word detection is available."""
        return OPENWAKEWORD_AVAILABLE and SOUNDDEVICE_AVAILABLE
    
    def _load_model(self) -> bool:
        """Load the wake word model."""
        if not OPENWAKEWORD_AVAILABLE:
            return False
        
        try:
            # Download default models if needed
            openwakeword.utils.download_models()
            
            if self.model_path:
                self._model = WakeWordModel(
                    wakeword_models=[self.model_path],
                    inference_framework="onnx",
                )
            else:
                # Use default models
                self._model = WakeWordModel(inference_framework="onnx")
            
            logger.info(f"Wake word model loaded. Available models: {list(self._model.models.keys())}")
            return True
        except Exception as e:
            logger.error(f"Failed to load wake word model: {e}")
            return False
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream processing."""
        if status:
            logger.warning(f"Audio stream status: {status}")
        
        if not self._running or self._model is None:
            return
        
        # Convert to int16
        audio_data = (indata[:, 0] * 32767).astype(np.int16)
        
        # Get predictions
        predictions = self._model.predict(audio_data)
        
        # Check for wake word detection
        for model_name, score in predictions.items():
            if score >= self.threshold:
                current_time = time.time()
                if current_time - self._last_detection_time >= self._cooldown:
                    self._last_detection_time = current_time
                    logger.info(f"Wake word detected: {model_name} (score: {score:.3f})")
                    
                    if self._callback:
                        # Run callback in separate thread to not block audio
                        threading.Thread(target=self._callback, daemon=True).start()
    
    def start(self, callback: Callable[[], None]) -> bool:
        """
        Start wake word detection.
        
        Args:
            callback: Function to call when wake word is detected.
            
        Returns:
            True if started successfully.
        """
        if not self.is_available:
            logger.error("Wake word detection not available")
            return False
        
        if self._running:
            logger.warning("Wake word detection already running")
            return True
        
        # Load model
        if self._model is None and not self._load_model():
            return False
        
        self._callback = callback
        self._running = True
        
        try:
            # Start audio stream
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.float32,
                blocksize=self.chunk_size,
                device=self.input_device,
                callback=self._audio_callback,
            )
            self._stream.start()
            
            logger.info("Wake word detection started")
            return True
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
            self._running = False
            return False
    
    def stop(self) -> None:
        """Stop wake word detection."""
        self._running = False
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        logger.info("Wake word detection stopped")
    
    def is_running(self) -> bool:
        """Check if wake word detection is running."""
        return self._running
    
    def set_threshold(self, threshold: float) -> None:
        """Update the detection threshold."""
        self.threshold = max(0.0, min(1.0, threshold))
        logger.debug(f"Wake word threshold set to {self.threshold}")
    
    def set_cooldown(self, seconds: float) -> None:
        """Set cooldown period between detections."""
        self._cooldown = max(0.0, seconds)


class WakeWordTrainer:
    """
    Helper class for training custom wake word models.
    
    Note: Full training requires the openWakeWord training pipeline
    which needs additional setup. This class provides guidance.
    """
    
    @staticmethod
    def get_training_instructions() -> str:
        """Get instructions for training a custom wake word."""
        return """
        Training a Custom Wake Word Model
        ==================================
        
        1. Install training dependencies:
           pip install openwakeword[training]
        
        2. Collect positive samples:
           - Record 50-100 samples of the wake word
           - Use different voices, distances, and environments
           - Save as 16kHz mono WAV files
        
        3. Collect negative samples:
           - Use general speech that doesn't contain the wake word
           - Include background noise samples
           - The more diverse, the better
        
        4. Use the openWakeWord training notebook:
           https://github.com/dscripka/openWakeWord/blob/main/notebooks/
        
        5. Alternatively, use synthetic data generation:
           - Use TTS to generate variations of the wake word
           - Augment with noise and room impulse responses
        
        For "Hey Jarvis", you can also use the pre-trained models
        available in openWakeWord or train using the provided tools.
        """
    
    @staticmethod
    def record_samples(
        output_dir: Path | str,
        num_samples: int = 10,
        duration: float = 2.0,
        sample_rate: int = 16000,
    ) -> int:
        """
        Record wake word samples for training.
        
        Args:
            output_dir: Directory to save samples.
            num_samples: Number of samples to record.
            duration: Duration of each sample in seconds.
            sample_rate: Sample rate.
            
        Returns:
            Number of samples recorded.
        """
        if not SOUNDDEVICE_AVAILABLE:
            logger.error("sounddevice not available for recording")
            return 0
        
        import soundfile as sf
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        recorded = 0
        
        for i in range(num_samples):
            input(f"\nPress Enter to record sample {i + 1}/{num_samples}...")
            print("Recording...")
            
            try:
                audio = sd.rec(
                    int(duration * sample_rate),
                    samplerate=sample_rate,
                    channels=1,
                    dtype=np.float32,
                )
                sd.wait()
                
                # Save sample
                filename = output_dir / f"sample_{i + 1:03d}.wav"
                sf.write(str(filename), audio, sample_rate)
                
                recorded += 1
                print(f"Saved: {filename}")
            except Exception as e:
                logger.error(f"Failed to record sample: {e}")
        
        return recorded
