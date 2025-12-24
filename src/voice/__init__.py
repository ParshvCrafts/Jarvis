"""Voice pipeline modules for JARVIS."""

from loguru import logger

# Enhanced modules (canonical) - with graceful fallback
try:
    from .pipeline_enhanced import (
        EnhancedVoicePipeline,
        PipelineState,
        VoiceCommand,
        ConversationState,
    )
except ImportError as e:
    logger.warning(f"Enhanced pipeline not available: {e}")
    EnhancedVoicePipeline = None
    from .pipeline import PipelineState, VoiceCommand
    ConversationState = None

try:
    from .stt_enhanced import (
        EnhancedSpeechToText,
        EnhancedSileroVAD,
        AudioPreprocessor,
        TranscriptionResult,
        STTProvider,
    )
except ImportError as e:
    logger.warning(f"Enhanced STT not available: {e}")
    EnhancedSpeechToText = None
    EnhancedSileroVAD = None
    AudioPreprocessor = None
    STTProvider = None
    from .stt import TranscriptionResult

try:
    from .wake_word_enhanced import (
        EnhancedWakeWordDetector,
        WakeWordConfig,
        WakeWordDetection,
    )
except ImportError as e:
    logger.warning(f"Enhanced wake word not available: {e}")
    EnhancedWakeWordDetector = None
    WakeWordConfig = None
    WakeWordDetection = None

from .tts import TextToSpeech, InterruptibleTTS

# Audio cues
try:
    from .audio_cues import (
        AudioCuePlayer,
        AudioCueGenerator,
        AudioCueType,
        get_audio_cue_player,
        play_cue,
    )
except ImportError as e:
    logger.warning(f"Audio cues not available: {e}")
    AudioCuePlayer = None
    AudioCueGenerator = None
    AudioCueType = None
    get_audio_cue_player = None
    play_cue = None

# Multilingual support
try:
    from .multilingual import (
        SupportedLanguage,
        LanguageDetectionResult,
        VoiceConfig,
        MultilingualVoiceManager,
        AmbientNoiseCalibrator,
        get_language_name,
        detect_script,
        infer_language_from_text,
    )
    MULTILINGUAL_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Multilingual support not available: {e}")
    MULTILINGUAL_AVAILABLE = False
    SupportedLanguage = None
    LanguageDetectionResult = None
    VoiceConfig = None
    MultilingualVoiceManager = None
    AmbientNoiseCalibrator = None
    get_language_name = None
    detect_script = None
    infer_language_from_text = None

# Calibration tools
try:
    from .calibration import (
        CalibrationManager,
        MicrophoneCalibrator,
        WakeWordCalibrator,
        SpeakerCalibrator,
        AudioCalibration,
        CalibrationResult,
        run_calibration,
        run_wake_word_calibration,
        get_calibration,
    )
except ImportError as e:
    logger.warning(f"Calibration tools not available: {e}")
    CalibrationManager = None
    MicrophoneCalibrator = None
    WakeWordCalibrator = None
    SpeakerCalibrator = None
    AudioCalibration = None
    CalibrationResult = None
    run_calibration = None
    run_wake_word_calibration = None
    get_calibration = None

# Testing tools
try:
    from .testing import (
        VoiceTestRunner,
        STTAccuracyTester,
        TestCase,
        TestResult,
        TestSuiteResult,
        run_voice_tests,
        run_stt_accuracy_test,
    )
except ImportError as e:
    logger.warning(f"Testing tools not available: {e}")
    VoiceTestRunner = None
    STTAccuracyTester = None
    TestCase = None
    TestResult = None
    TestSuiteResult = None
    run_voice_tests = None
    run_stt_accuracy_test = None

# Legacy aliases for backwards compatibility
from .pipeline import VoicePipeline as LegacyVoicePipeline
from .stt import SpeechToText as LegacySpeechToText
from .wake_word import WakeWordDetector as LegacyWakeWordDetector

__all__ = [
    # Enhanced (use these)
    "EnhancedVoicePipeline",
    "EnhancedSpeechToText",
    "EnhancedWakeWordDetector",
    "EnhancedSileroVAD",
    "AudioPreprocessor",
    "PipelineState",
    "VoiceCommand",
    "ConversationState",
    "TranscriptionResult",
    "STTProvider",
    "WakeWordConfig",
    "WakeWordDetection",
    "TextToSpeech",
    "InterruptibleTTS",
    # Audio cues
    "AudioCuePlayer",
    "AudioCueGenerator",
    "AudioCueType",
    "get_audio_cue_player",
    "play_cue",
    # Calibration
    "CalibrationManager",
    "MicrophoneCalibrator",
    "WakeWordCalibrator",
    "SpeakerCalibrator",
    "AudioCalibration",
    "CalibrationResult",
    "run_calibration",
    "run_wake_word_calibration",
    "get_calibration",
    # Testing
    "VoiceTestRunner",
    "STTAccuracyTester",
    "TestCase",
    "TestResult",
    "TestSuiteResult",
    "run_voice_tests",
    "run_stt_accuracy_test",
    # Multilingual
    "MULTILINGUAL_AVAILABLE",
    "SupportedLanguage",
    "LanguageDetectionResult",
    "VoiceConfig",
    "MultilingualVoiceManager",
    "AmbientNoiseCalibrator",
    "get_language_name",
    "detect_script",
    "infer_language_from_text",
    # Legacy (deprecated)
    "LegacyVoicePipeline",
    "LegacySpeechToText",
    "LegacyWakeWordDetector",
]
