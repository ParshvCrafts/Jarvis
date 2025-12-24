"""
Voice Pipeline Calibration Tools for JARVIS.

Provides tools for:
- Wake word sensitivity calibration
- Microphone input calibration
- VAD threshold tuning
- Audio output testing
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


@dataclass
class CalibrationResult:
    """Result of a calibration test."""
    success: bool
    metric_name: str
    measured_value: float
    recommended_value: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AudioCalibration:
    """Stored audio calibration settings."""
    input_device: Optional[int] = None
    output_device: Optional[int] = None
    input_volume: float = 1.0
    output_volume: float = 1.0
    noise_gate_threshold: float = 0.02
    vad_threshold: float = 0.5
    wake_word_sensitivity: float = 0.5
    sample_rate: int = 16000
    calibrated_at: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_device": self.input_device,
            "output_device": self.output_device,
            "input_volume": self.input_volume,
            "output_volume": self.output_volume,
            "noise_gate_threshold": self.noise_gate_threshold,
            "vad_threshold": self.vad_threshold,
            "wake_word_sensitivity": self.wake_word_sensitivity,
            "sample_rate": self.sample_rate,
            "calibrated_at": self.calibrated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioCalibration":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class MicrophoneCalibrator:
    """
    Calibrates microphone input settings.
    
    Tests:
    - Input level detection
    - Ambient noise measurement
    - Noise gate threshold recommendation
    - VAD sensitivity tuning
    """
    
    def __init__(self, sample_rate: int = 16000, device: Optional[int] = None):
        self.sample_rate = sample_rate
        self.device = device
    
    def list_input_devices(self) -> List[Dict[str, Any]]:
        """List available input devices."""
        if not SOUNDDEVICE_AVAILABLE:
            return []
        
        devices = []
        for i, dev in enumerate(sd.query_devices()):
            if dev["max_input_channels"] > 0:
                devices.append({
                    "index": i,
                    "name": dev["name"],
                    "channels": dev["max_input_channels"],
                    "sample_rate": dev["default_samplerate"],
                    "is_default": i == sd.default.device[0],
                })
        return devices
    
    def measure_ambient_noise(self, duration: float = 3.0) -> CalibrationResult:
        """
        Measure ambient noise level.
        
        Args:
            duration: Measurement duration in seconds.
            
        Returns:
            CalibrationResult with noise level.
        """
        if not SOUNDDEVICE_AVAILABLE or not NUMPY_AVAILABLE:
            return CalibrationResult(
                success=False,
                metric_name="ambient_noise",
                measured_value=0,
                recommended_value=0,
                message="Audio libraries not available",
            )
        
        print(f"Measuring ambient noise for {duration} seconds...")
        print("Please remain quiet...")
        
        try:
            # Record ambient noise
            recording = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.float32,
                device=self.device,
            )
            sd.wait()
            
            # Calculate RMS level
            rms = np.sqrt(np.mean(recording ** 2))
            peak = np.max(np.abs(recording))
            
            # Recommend noise gate slightly above ambient
            recommended_gate = rms * 1.5
            
            return CalibrationResult(
                success=True,
                metric_name="ambient_noise",
                measured_value=float(rms),
                recommended_value=float(recommended_gate),
                message=f"Ambient noise RMS: {rms:.4f}, Peak: {peak:.4f}",
                details={
                    "rms": float(rms),
                    "peak": float(peak),
                    "duration": duration,
                    "recommended_noise_gate": float(recommended_gate),
                },
            )
            
        except Exception as e:
            return CalibrationResult(
                success=False,
                metric_name="ambient_noise",
                measured_value=0,
                recommended_value=0.02,
                message=f"Measurement failed: {e}",
            )
    
    def measure_speech_level(self, duration: float = 5.0) -> CalibrationResult:
        """
        Measure speech input level.
        
        Args:
            duration: Recording duration in seconds.
            
        Returns:
            CalibrationResult with speech level.
        """
        if not SOUNDDEVICE_AVAILABLE or not NUMPY_AVAILABLE:
            return CalibrationResult(
                success=False,
                metric_name="speech_level",
                measured_value=0,
                recommended_value=0,
                message="Audio libraries not available",
            )
        
        print(f"Recording speech for {duration} seconds...")
        print("Please speak normally (e.g., count from 1 to 10)...")
        
        try:
            recording = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.float32,
                device=self.device,
            )
            sd.wait()
            
            # Calculate levels
            rms = np.sqrt(np.mean(recording ** 2))
            peak = np.max(np.abs(recording))
            
            # Check if level is good
            if rms < 0.01:
                message = "Speech level too low - move closer to microphone or increase gain"
                recommended = 0.05
            elif rms > 0.5:
                message = "Speech level too high - move away from microphone or decrease gain"
                recommended = 0.2
            else:
                message = f"Speech level good: RMS {rms:.4f}"
                recommended = rms
            
            return CalibrationResult(
                success=True,
                metric_name="speech_level",
                measured_value=float(rms),
                recommended_value=float(recommended),
                message=message,
                details={
                    "rms": float(rms),
                    "peak": float(peak),
                    "duration": duration,
                },
            )
            
        except Exception as e:
            return CalibrationResult(
                success=False,
                metric_name="speech_level",
                measured_value=0,
                recommended_value=0,
                message=f"Measurement failed: {e}",
            )
    
    def test_vad_sensitivity(
        self,
        thresholds: List[float] = [0.3, 0.4, 0.5, 0.6, 0.7],
        duration: float = 10.0,
    ) -> CalibrationResult:
        """
        Test VAD at different sensitivity levels.
        
        Args:
            thresholds: List of thresholds to test.
            duration: Test duration in seconds.
            
        Returns:
            CalibrationResult with recommended threshold.
        """
        if not SOUNDDEVICE_AVAILABLE or not NUMPY_AVAILABLE:
            return CalibrationResult(
                success=False,
                metric_name="vad_threshold",
                measured_value=0.5,
                recommended_value=0.5,
                message="Audio libraries not available",
            )
        
        try:
            from .stt_enhanced import EnhancedSileroVAD
        except ImportError:
            return CalibrationResult(
                success=False,
                metric_name="vad_threshold",
                measured_value=0.5,
                recommended_value=0.5,
                message="VAD not available",
            )
        
        print(f"Testing VAD sensitivity for {duration} seconds...")
        print("Alternate between speaking and silence...")
        
        try:
            # Record test audio
            recording = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.float32,
                device=self.device,
            )
            sd.wait()
            
            # Test each threshold
            results = {}
            chunk_size = int(0.1 * self.sample_rate)  # 100ms chunks
            
            for threshold in thresholds:
                vad = EnhancedSileroVAD(threshold=threshold)
                
                speech_chunks = 0
                silence_chunks = 0
                
                for i in range(0, len(recording) - chunk_size, chunk_size):
                    chunk = recording[i:i + chunk_size].flatten()
                    is_speech, _ = vad.is_speech(chunk, return_probability=True)
                    
                    if is_speech:
                        speech_chunks += 1
                    else:
                        silence_chunks += 1
                
                total = speech_chunks + silence_chunks
                speech_ratio = speech_chunks / total if total > 0 else 0
                
                results[threshold] = {
                    "speech_chunks": speech_chunks,
                    "silence_chunks": silence_chunks,
                    "speech_ratio": speech_ratio,
                }
            
            # Find best threshold (aim for ~30-50% speech ratio for mixed audio)
            best_threshold = 0.5
            best_diff = float("inf")
            target_ratio = 0.4
            
            for threshold, data in results.items():
                diff = abs(data["speech_ratio"] - target_ratio)
                if diff < best_diff:
                    best_diff = diff
                    best_threshold = threshold
            
            return CalibrationResult(
                success=True,
                metric_name="vad_threshold",
                measured_value=best_threshold,
                recommended_value=best_threshold,
                message=f"Recommended VAD threshold: {best_threshold}",
                details={"threshold_results": results},
            )
            
        except Exception as e:
            return CalibrationResult(
                success=False,
                metric_name="vad_threshold",
                measured_value=0.5,
                recommended_value=0.5,
                message=f"VAD test failed: {e}",
            )


class WakeWordCalibrator:
    """
    Calibrates wake word detection sensitivity.
    
    Tests detection at various sensitivity levels and recommends
    optimal settings based on false positive/negative rates.
    """
    
    def __init__(self, wake_phrase: str = "hey jarvis"):
        self.wake_phrase = wake_phrase
    
    def test_sensitivity(
        self,
        sensitivity: float,
        duration: float = 60.0,
        say_wake_word_count: int = 5,
    ) -> CalibrationResult:
        """
        Test wake word detection at a specific sensitivity.
        
        Args:
            sensitivity: Sensitivity level (0.0 to 1.0).
            duration: Test duration in seconds.
            say_wake_word_count: How many times user should say wake word.
            
        Returns:
            CalibrationResult with detection metrics.
        """
        if not SOUNDDEVICE_AVAILABLE or not NUMPY_AVAILABLE:
            return CalibrationResult(
                success=False,
                metric_name="wake_word_sensitivity",
                measured_value=sensitivity,
                recommended_value=0.5,
                message="Audio libraries not available",
            )
        
        try:
            from .wake_word_enhanced import EnhancedWakeWordDetector, WakeWordConfig
        except ImportError:
            return CalibrationResult(
                success=False,
                metric_name="wake_word_sensitivity",
                measured_value=sensitivity,
                recommended_value=0.5,
                message="Wake word detector not available",
            )
        
        print(f"\nTesting wake word sensitivity: {sensitivity}")
        print(f"Duration: {duration} seconds")
        print(f"\nInstructions:")
        print(f"1. Say '{self.wake_phrase}' {say_wake_word_count} times during the test")
        print(f"2. Space them out evenly")
        print(f"3. Also include some normal speech that is NOT the wake word")
        print("\nStarting in 3 seconds...")
        time.sleep(3)
        
        detections = []
        
        def on_detection(detection):
            detections.append({
                "time": time.time(),
                "confidence": detection.confidence,
            })
            print(f"  [DETECTED] Confidence: {detection.confidence:.2f}")
        
        try:
            detector = EnhancedWakeWordDetector(
                wake_words=[WakeWordConfig(
                    phrase=self.wake_phrase,
                    threshold=sensitivity,
                )],
            )
            
            detector.start(on_detection)
            
            start_time = time.time()
            while time.time() - start_time < duration:
                remaining = int(duration - (time.time() - start_time))
                print(f"\r  Time remaining: {remaining}s   ", end="", flush=True)
                time.sleep(1)
            
            detector.stop()
            print("\n")
            
            # Analyze results
            detection_count = len(detections)
            
            # Calculate metrics
            if detection_count == 0:
                message = "No detections - sensitivity may be too low"
            elif detection_count < say_wake_word_count:
                message = f"Detected {detection_count}/{say_wake_word_count} - sensitivity may be too low"
            elif detection_count > say_wake_word_count * 2:
                message = f"Detected {detection_count} times - too many false positives, increase threshold"
            else:
                message = f"Detected {detection_count} times - good sensitivity"
            
            return CalibrationResult(
                success=True,
                metric_name="wake_word_sensitivity",
                measured_value=sensitivity,
                recommended_value=sensitivity,
                message=message,
                details={
                    "detection_count": detection_count,
                    "expected_count": say_wake_word_count,
                    "detections": detections,
                    "duration": duration,
                },
            )
            
        except Exception as e:
            return CalibrationResult(
                success=False,
                metric_name="wake_word_sensitivity",
                measured_value=sensitivity,
                recommended_value=0.5,
                message=f"Test failed: {e}",
            )
    
    def find_optimal_sensitivity(
        self,
        sensitivities: List[float] = [0.3, 0.4, 0.5, 0.6, 0.7],
        test_duration: float = 30.0,
        wake_word_count: int = 3,
    ) -> CalibrationResult:
        """
        Find optimal wake word sensitivity by testing multiple levels.
        
        Args:
            sensitivities: List of sensitivity levels to test.
            test_duration: Duration for each test.
            wake_word_count: Wake words to say per test.
            
        Returns:
            CalibrationResult with optimal sensitivity.
        """
        print("\n" + "=" * 50)
        print("WAKE WORD SENSITIVITY CALIBRATION")
        print("=" * 50)
        print(f"\nThis will test {len(sensitivities)} sensitivity levels.")
        print(f"Each test lasts {test_duration} seconds.")
        print(f"Say '{self.wake_phrase}' {wake_word_count} times per test.")
        print("\nPress Enter to begin...")
        input()
        
        results = {}
        
        for sensitivity in sensitivities:
            result = self.test_sensitivity(
                sensitivity=sensitivity,
                duration=test_duration,
                say_wake_word_count=wake_word_count,
            )
            results[sensitivity] = result.details
            
            print(f"Result: {result.message}")
            print("-" * 30)
        
        # Find best sensitivity
        best_sensitivity = 0.5
        best_score = -1
        
        for sensitivity, data in results.items():
            detected = data.get("detection_count", 0)
            expected = data.get("expected_count", wake_word_count)
            
            # Score: penalize both false negatives and false positives
            if detected == 0:
                score = 0
            else:
                accuracy = min(detected, expected) / expected
                false_positive_penalty = max(0, detected - expected) / expected
                score = accuracy - (false_positive_penalty * 0.5)
            
            if score > best_score:
                best_score = score
                best_sensitivity = sensitivity
        
        return CalibrationResult(
            success=True,
            metric_name="wake_word_sensitivity",
            measured_value=best_sensitivity,
            recommended_value=best_sensitivity,
            message=f"Recommended sensitivity: {best_sensitivity}",
            details={"all_results": results, "best_score": best_score},
        )


class SpeakerCalibrator:
    """Calibrates audio output settings."""
    
    def __init__(self, device: Optional[int] = None):
        self.device = device
    
    def list_output_devices(self) -> List[Dict[str, Any]]:
        """List available output devices."""
        if not SOUNDDEVICE_AVAILABLE:
            return []
        
        devices = []
        for i, dev in enumerate(sd.query_devices()):
            if dev["max_output_channels"] > 0:
                devices.append({
                    "index": i,
                    "name": dev["name"],
                    "channels": dev["max_output_channels"],
                    "sample_rate": dev["default_samplerate"],
                    "is_default": i == sd.default.device[1],
                })
        return devices
    
    def test_output(self, frequency: float = 440.0, duration: float = 1.0) -> bool:
        """
        Play a test tone.
        
        Args:
            frequency: Tone frequency in Hz.
            duration: Duration in seconds.
            
        Returns:
            True if playback succeeded.
        """
        if not SOUNDDEVICE_AVAILABLE or not NUMPY_AVAILABLE:
            return False
        
        try:
            sample_rate = 44100
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            tone = np.sin(2 * np.pi * frequency * t) * 0.3
            
            # Fade in/out
            fade_samples = int(0.05 * sample_rate)
            tone[:fade_samples] *= np.linspace(0, 1, fade_samples)
            tone[-fade_samples:] *= np.linspace(1, 0, fade_samples)
            
            sd.play(tone.astype(np.float32), sample_rate, device=self.device)
            sd.wait()
            
            return True
        except Exception as e:
            logger.error(f"Audio output test failed: {e}")
            return False
    
    def test_tts(self) -> bool:
        """Test TTS output."""
        try:
            from .tts import TextToSpeech
            
            tts = TextToSpeech()
            tts.speak("Audio output test successful.", blocking=True)
            return True
        except Exception as e:
            logger.error(f"TTS test failed: {e}")
            return False


class CalibrationManager:
    """
    Manages all calibration settings.
    
    Provides a unified interface for running calibrations
    and persisting results.
    """
    
    CALIBRATION_FILE = "audio_calibration.json"
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data")
        self.calibration = AudioCalibration()
        
        self.mic_calibrator = MicrophoneCalibrator()
        self.wake_word_calibrator = WakeWordCalibrator()
        self.speaker_calibrator = SpeakerCalibrator()
        
        self._load_calibration()
    
    def _load_calibration(self) -> None:
        """Load saved calibration."""
        path = self.data_dir / self.CALIBRATION_FILE
        
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                self.calibration = AudioCalibration.from_dict(data)
                logger.info("Loaded audio calibration")
            except Exception as e:
                logger.warning(f"Failed to load calibration: {e}")
    
    def save_calibration(self) -> None:
        """Save calibration to file."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        path = self.data_dir / self.CALIBRATION_FILE
        
        try:
            self.calibration.calibrated_at = time.time()
            with open(path, "w") as f:
                json.dump(self.calibration.to_dict(), f, indent=2)
            logger.info("Saved audio calibration")
        except Exception as e:
            logger.error(f"Failed to save calibration: {e}")
    
    def run_full_calibration(self) -> Dict[str, CalibrationResult]:
        """
        Run full audio calibration.
        
        Returns:
            Dict of calibration results.
        """
        results = {}
        
        print("\n" + "=" * 50)
        print("JARVIS AUDIO CALIBRATION")
        print("=" * 50)
        
        # 1. Ambient noise
        print("\n[1/4] Measuring ambient noise...")
        result = self.mic_calibrator.measure_ambient_noise()
        results["ambient_noise"] = result
        if result.success:
            self.calibration.noise_gate_threshold = result.recommended_value
        print(f"  {result.message}")
        
        # 2. Speech level
        print("\n[2/4] Measuring speech level...")
        result = self.mic_calibrator.measure_speech_level()
        results["speech_level"] = result
        print(f"  {result.message}")
        
        # 3. VAD threshold
        print("\n[3/4] Testing VAD sensitivity...")
        result = self.mic_calibrator.test_vad_sensitivity()
        results["vad_threshold"] = result
        if result.success:
            self.calibration.vad_threshold = result.recommended_value
        print(f"  {result.message}")
        
        # 4. Speaker test
        print("\n[4/4] Testing audio output...")
        if self.speaker_calibrator.test_output():
            results["speaker_test"] = CalibrationResult(
                success=True,
                metric_name="speaker_test",
                measured_value=1.0,
                recommended_value=1.0,
                message="Audio output working",
            )
        else:
            results["speaker_test"] = CalibrationResult(
                success=False,
                metric_name="speaker_test",
                measured_value=0.0,
                recommended_value=1.0,
                message="Audio output failed",
            )
        print(f"  {results['speaker_test'].message}")
        
        # Save results
        self.save_calibration()
        
        print("\n" + "=" * 50)
        print("CALIBRATION COMPLETE")
        print("=" * 50)
        print(f"\nRecommended settings:")
        print(f"  Noise gate threshold: {self.calibration.noise_gate_threshold:.4f}")
        print(f"  VAD threshold: {self.calibration.vad_threshold:.2f}")
        print(f"\nSettings saved to: {self.data_dir / self.CALIBRATION_FILE}")
        
        return results
    
    def run_wake_word_calibration(self) -> CalibrationResult:
        """Run wake word sensitivity calibration."""
        result = self.wake_word_calibrator.find_optimal_sensitivity()
        
        if result.success:
            self.calibration.wake_word_sensitivity = result.recommended_value
            self.save_calibration()
        
        return result
    
    def get_calibration(self) -> AudioCalibration:
        """Get current calibration settings."""
        return self.calibration


# Convenience functions

def run_calibration(data_dir: Optional[Path] = None) -> Dict[str, CalibrationResult]:
    """Run full audio calibration."""
    manager = CalibrationManager(data_dir)
    return manager.run_full_calibration()


def run_wake_word_calibration(data_dir: Optional[Path] = None) -> CalibrationResult:
    """Run wake word calibration."""
    manager = CalibrationManager(data_dir)
    return manager.run_wake_word_calibration()


def get_calibration(data_dir: Optional[Path] = None) -> AudioCalibration:
    """Get saved calibration settings."""
    manager = CalibrationManager(data_dir)
    return manager.get_calibration()
