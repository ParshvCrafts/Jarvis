"""
Multilingual Support for JARVIS Voice Pipeline

Provides:
- Language detection from speech
- Language-aware TTS voice selection
- Language switching commands
- Ambient noise calibration
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


class SupportedLanguage(Enum):
    """Supported languages for JARVIS."""
    ENGLISH = "en"
    HINDI = "hi"
    GUJARATI = "gu"
    
    @classmethod
    def from_code(cls, code: str) -> Optional["SupportedLanguage"]:
        """Get language from code."""
        code = code.lower().split("-")[0]  # Handle en-US, hi-IN, etc.
        for lang in cls:
            if lang.value == code:
                return lang
        return None
    
    @property
    def display_name(self) -> str:
        """Get display name for language."""
        names = {
            "en": "English",
            "hi": "हिंदी (Hindi)",
            "gu": "ગુજરાતી (Gujarati)",
        }
        return names.get(self.value, self.value)
    
    @property
    def native_name(self) -> str:
        """Get native name for language."""
        names = {
            "en": "English",
            "hi": "हिंदी",
            "gu": "ગુજરાતી",
        }
        return names.get(self.value, self.value)


@dataclass
class LanguageDetectionResult:
    """Result of language detection."""
    language: SupportedLanguage
    confidence: float
    raw_code: str
    
    @property
    def is_confident(self) -> bool:
        """Check if detection is confident enough."""
        return self.confidence >= 0.7


@dataclass
class VoiceConfig:
    """Voice configuration for a language."""
    language: SupportedLanguage
    male_voice: str
    female_voice: str
    
    def get_voice(self, gender: str = "male") -> str:
        """Get voice for specified gender."""
        if gender.lower() == "female":
            return self.female_voice
        return self.male_voice


class MultilingualVoiceManager:
    """
    Manages multilingual voice settings.
    
    Handles:
    - Voice selection by language
    - Language detection from Whisper
    - Language preference storage
    """
    
    # Default voice configurations
    DEFAULT_VOICES = {
        SupportedLanguage.ENGLISH: VoiceConfig(
            language=SupportedLanguage.ENGLISH,
            male_voice="en-IN-PrabhatNeural",
            female_voice="en-IN-NeerjaNeural",
        ),
        SupportedLanguage.HINDI: VoiceConfig(
            language=SupportedLanguage.HINDI,
            male_voice="hi-IN-MadhurNeural",
            female_voice="hi-IN-SwaraNeural",
        ),
        SupportedLanguage.GUJARATI: VoiceConfig(
            language=SupportedLanguage.GUJARATI,
            male_voice="gu-IN-NiranjanNeural",
            female_voice="gu-IN-DhwaniNeural",
        ),
    }
    
    # Language switching commands
    LANGUAGE_COMMANDS = {
        # English commands
        "switch to hindi": SupportedLanguage.HINDI,
        "speak in hindi": SupportedLanguage.HINDI,
        "hindi mode": SupportedLanguage.HINDI,
        "switch to gujarati": SupportedLanguage.GUJARATI,
        "speak in gujarati": SupportedLanguage.GUJARATI,
        "gujarati mode": SupportedLanguage.GUJARATI,
        "switch to english": SupportedLanguage.ENGLISH,
        "speak in english": SupportedLanguage.ENGLISH,
        "english mode": SupportedLanguage.ENGLISH,
        # Hindi commands
        "हिंदी में बात करो": SupportedLanguage.HINDI,
        "हिंदी में बोलो": SupportedLanguage.HINDI,
        "अंग्रेजी में बात करो": SupportedLanguage.ENGLISH,
        "अंग्रेजी में बोलो": SupportedLanguage.ENGLISH,
        "गुजराती में बात करो": SupportedLanguage.GUJARATI,
        # Gujarati commands
        "ગુજરાતીમાં બોલો": SupportedLanguage.GUJARATI,
        "અંગ્રેજીમાં બોલો": SupportedLanguage.ENGLISH,
        "હિન્દીમાં બોલો": SupportedLanguage.HINDI,
    }
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        preferred_gender: str = "male",
    ):
        """
        Initialize multilingual voice manager.
        
        Args:
            config: Voice configuration from settings
            preferred_gender: Preferred voice gender
        """
        self.preferred_gender = preferred_gender
        self.current_language = SupportedLanguage.ENGLISH
        self.auto_detect = True
        
        # Load voice configs from settings
        self.voice_configs = self.DEFAULT_VOICES.copy()
        if config:
            self._load_config(config)
    
    def _load_config(self, config: Dict[str, Any]):
        """Load configuration from settings."""
        multilingual = config.get("multilingual", {})
        
        if not multilingual.get("enabled", True):
            self.auto_detect = False
            return
        
        self.preferred_gender = multilingual.get("preferred_gender", "male")
        
        # Load custom voice mappings
        voices = multilingual.get("voices", {})
        for lang_code, voice_map in voices.items():
            lang = SupportedLanguage.from_code(lang_code)
            if lang:
                self.voice_configs[lang] = VoiceConfig(
                    language=lang,
                    male_voice=voice_map.get("male", self.DEFAULT_VOICES[lang].male_voice),
                    female_voice=voice_map.get("female", self.DEFAULT_VOICES[lang].female_voice),
                )
    
    def get_voice_for_language(
        self,
        language: Optional[SupportedLanguage] = None,
        gender: Optional[str] = None,
    ) -> str:
        """
        Get TTS voice for a language.
        
        Args:
            language: Target language (uses current if None)
            gender: Voice gender (uses preferred if None)
            
        Returns:
            Voice name for Edge TTS
        """
        lang = language or self.current_language
        gen = gender or self.preferred_gender
        
        config = self.voice_configs.get(lang, self.DEFAULT_VOICES[SupportedLanguage.ENGLISH])
        return config.get_voice(gen)
    
    def detect_language_from_whisper(
        self,
        whisper_result: Dict[str, Any],
    ) -> LanguageDetectionResult:
        """
        Extract language from Whisper transcription result.
        
        Args:
            whisper_result: Result from Whisper transcription
            
        Returns:
            LanguageDetectionResult
        """
        # Whisper returns language code and probability
        raw_code = whisper_result.get("language", "en")
        probability = whisper_result.get("language_probability", 0.0)
        
        # Map to supported language
        lang = SupportedLanguage.from_code(raw_code)
        if lang is None:
            lang = SupportedLanguage.ENGLISH
            probability = 0.5  # Lower confidence for fallback
        
        return LanguageDetectionResult(
            language=lang,
            confidence=probability,
            raw_code=raw_code,
        )
    
    def check_language_command(self, text: str) -> Optional[SupportedLanguage]:
        """
        Check if text is a language switching command.
        
        Args:
            text: Transcribed text
            
        Returns:
            Target language if command detected, None otherwise
        """
        text_lower = text.lower().strip()
        
        for command, language in self.LANGUAGE_COMMANDS.items():
            if command in text_lower:
                return language
        
        return None
    
    def set_language(self, language: SupportedLanguage) -> str:
        """
        Set current language.
        
        Args:
            language: New language
            
        Returns:
            Confirmation message in the new language
        """
        self.current_language = language
        
        confirmations = {
            SupportedLanguage.ENGLISH: "Switched to English. I'll now respond in English.",
            SupportedLanguage.HINDI: "हिंदी में बदल गया। अब मैं हिंदी में जवाब दूंगा।",
            SupportedLanguage.GUJARATI: "ગુજરાતીમાં બદલાયું. હવે હું ગુજરાતીમાં જવાબ આપીશ.",
        }
        
        return confirmations.get(language, f"Switched to {language.display_name}")
    
    def get_llm_language_instruction(self, language: SupportedLanguage) -> str:
        """
        Get instruction for LLM to respond in specific language.
        
        Args:
            language: Target response language
            
        Returns:
            System prompt addition for language
        """
        instructions = {
            SupportedLanguage.ENGLISH: (
                "The user is speaking in English. "
                "Respond in English."
            ),
            SupportedLanguage.HINDI: (
                "The user is speaking in Hindi (हिंदी). "
                "Respond in Hindi using Devanagari script. "
                "Use natural Hindi, not transliteration."
            ),
            SupportedLanguage.GUJARATI: (
                "The user is speaking in Gujarati (ગુજરાતી). "
                "Respond in Gujarati using Gujarati script. "
                "Use natural Gujarati, not transliteration."
            ),
        }
        
        return instructions.get(language, "Respond in the same language as the user.")


class AmbientNoiseCalibrator:
    """
    Calibrates microphone for ambient noise.
    
    Samples background noise and adjusts recognition threshold.
    """
    
    def __init__(
        self,
        calibration_duration: float = 1.0,
        energy_threshold_multiplier: float = 1.5,
    ):
        """
        Initialize calibrator.
        
        Args:
            calibration_duration: Seconds to sample ambient noise
            energy_threshold_multiplier: Multiplier for threshold
        """
        self.calibration_duration = calibration_duration
        self.threshold_multiplier = energy_threshold_multiplier
        self.ambient_energy = 0.0
        self.is_calibrated = False
    
    def calibrate(self, audio_samples: Optional[List[float]] = None) -> float:
        """
        Calibrate based on ambient noise.
        
        Args:
            audio_samples: Audio samples to analyze (or will record if None)
            
        Returns:
            Calculated energy threshold
        """
        if audio_samples:
            # Calculate RMS energy
            import math
            rms = math.sqrt(sum(s * s for s in audio_samples) / len(audio_samples))
            self.ambient_energy = rms
        else:
            # Would need to record - for now use default
            self.ambient_energy = 0.01
        
        self.is_calibrated = True
        threshold = self.ambient_energy * self.threshold_multiplier
        
        logger.info(f"Ambient noise calibrated: energy={self.ambient_energy:.4f}, threshold={threshold:.4f}")
        return threshold
    
    def get_adjusted_threshold(self, base_threshold: float) -> float:
        """
        Get threshold adjusted for ambient noise.
        
        Args:
            base_threshold: Base VAD threshold
            
        Returns:
            Adjusted threshold
        """
        if not self.is_calibrated:
            return base_threshold
        
        # Increase threshold in noisy environments
        noise_factor = min(2.0, 1.0 + self.ambient_energy * 10)
        return base_threshold * noise_factor


# Language name mappings for display
LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "gu": "Gujarati",
    "en-IN": "English (India)",
    "hi-IN": "Hindi (India)",
    "gu-IN": "Gujarati (India)",
}


def get_language_name(code: str) -> str:
    """Get display name for language code."""
    return LANGUAGE_NAMES.get(code, code)


def detect_script(text: str) -> str:
    """
    Detect the script used in text.
    
    Returns:
        Script name: "devanagari", "gujarati", "latin", or "mixed"
    """
    devanagari_count = 0
    gujarati_count = 0
    latin_count = 0
    
    for char in text:
        code = ord(char)
        if 0x0900 <= code <= 0x097F:  # Devanagari
            devanagari_count += 1
        elif 0x0A80 <= code <= 0x0AFF:  # Gujarati
            gujarati_count += 1
        elif (0x0041 <= code <= 0x007A) or (0x00C0 <= code <= 0x00FF):  # Latin
            latin_count += 1
    
    total = devanagari_count + gujarati_count + latin_count
    if total == 0:
        return "unknown"
    
    if devanagari_count / total > 0.5:
        return "devanagari"
    elif gujarati_count / total > 0.5:
        return "gujarati"
    elif latin_count / total > 0.5:
        return "latin"
    else:
        return "mixed"


def infer_language_from_text(text: str) -> SupportedLanguage:
    """
    Infer language from text content.
    
    Args:
        text: Text to analyze
        
    Returns:
        Inferred language
    """
    script = detect_script(text)
    
    if script == "devanagari":
        return SupportedLanguage.HINDI
    elif script == "gujarati":
        return SupportedLanguage.GUJARATI
    else:
        return SupportedLanguage.ENGLISH
