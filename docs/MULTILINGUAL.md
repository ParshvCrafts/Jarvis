# JARVIS Multilingual Support

JARVIS supports English, Hindi, and Gujarati for both speech recognition and text-to-speech.

## Supported Languages

| Language | Code | STT | TTS Male | TTS Female |
|----------|------|-----|----------|------------|
| English (India) | en | ✅ | en-IN-PrabhatNeural | en-IN-NeerjaNeural |
| Hindi | hi | ✅ | hi-IN-MadhurNeural | hi-IN-SwaraNeural |
| Gujarati | gu | ✅ | gu-IN-NiranjanNeural | gu-IN-DhwaniNeural |

## Configuration

### settings.yaml

```yaml
voice:
  speech_to_text:
    model: "base"  # Use multilingual model (not base.en)
    language: "auto"  # Auto-detect language
    multilingual:
      enabled: true
      auto_detect: true
      supported_languages: ["en", "hi", "gu"]

  text_to_speech:
    voice: "en-IN-PrabhatNeural"
    multilingual:
      enabled: true
      default_language: "en"
      preferred_gender: "male"
      voices:
        en:
          male: "en-IN-PrabhatNeural"
          female: "en-IN-NeerjaNeural"
        hi:
          male: "hi-IN-MadhurNeural"
          female: "hi-IN-SwaraNeural"
        gu:
          male: "gu-IN-NiranjanNeural"
          female: "gu-IN-DhwaniNeural"
```

## Usage

### Automatic Language Detection

JARVIS automatically detects the language you speak:

- Speak in English → Response in English
- Speak in Hindi → Response in Hindi  
- Speak in Gujarati → Response in Gujarati

### Language Switching Commands

Switch languages using voice commands:

**English commands:**
- "Switch to Hindi"
- "Speak in Gujarati"
- "English mode"

**Hindi commands:**
- "हिंदी में बात करो"
- "अंग्रेजी में बोलो"

**Gujarati commands:**
- "ગુજરાતીમાં બોલો"
- "અંગ્રેજીમાં બોલો"

## API Usage

```python
from src.voice import MultilingualVoiceManager, SupportedLanguage

# Initialize manager
manager = MultilingualVoiceManager(preferred_gender="male")

# Get voice for language
voice = manager.get_voice_for_language(SupportedLanguage.HINDI)
# Returns: "hi-IN-MadhurNeural"

# Check for language command
lang = manager.check_language_command("Switch to Hindi")
# Returns: SupportedLanguage.HINDI

# Get LLM instruction
instruction = manager.get_llm_language_instruction(SupportedLanguage.HINDI)
# Returns prompt to respond in Hindi
```

## TTS Voice Selection

```python
from src.voice.tts import EdgeTTS

tts = EdgeTTS()

# Set voice for Hindi
tts.set_voice_for_language("hi", gender="female")
# Now uses hi-IN-SwaraNeural

# Synthesize Hindi text
audio = await tts.synthesize("नमस्ते, मैं जार्विस हूं")
```

## STT Language Detection

```python
from src.voice.stt_enhanced import FasterWhisperSTT

stt = FasterWhisperSTT(model_size="base", language="auto")
result = stt.transcribe(audio_data)

print(result.detected_language)  # "hi"
print(result.language_probability)  # 0.95
print(result.is_hindi)  # True
```

## Notes

1. **Model Selection**: Use `base` model (not `base.en`) for multilingual support
2. **Whisper Support**: Whisper has excellent Hindi/Gujarati recognition
3. **Edge TTS**: All voices are neural and natural-sounding
4. **Code-switching**: Mixed language input (Hinglish) is supported
