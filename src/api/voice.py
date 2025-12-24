"""
Voice Endpoints for Mobile API.

Provides speech-to-text and text-to-speech functionality for mobile apps.
"""

from __future__ import annotations

import base64
import io
import time
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query, status
from fastapi.responses import StreamingResponse
from loguru import logger

from .auth import get_auth_manager
from .routes import get_current_user
from .models import TranscribeResponse, SpeakRequest


voice_router = APIRouter(prefix="/voice", tags=["Voice"])


# Reference to JARVIS instance
_jarvis_instance = None


def set_voice_jarvis(jarvis):
    """Set JARVIS instance for voice processing."""
    global _jarvis_instance
    _jarvis_instance = jarvis


@voice_router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Query(None, description="Language code (e.g., 'en', 'es')"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Transcribe audio file to text.
    
    Accepts audio files in common formats (wav, mp3, webm, ogg, m4a).
    
    - **file**: Audio file to transcribe
    - **language**: Optional language hint
    """
    start_time = time.time()
    
    # Validate file type
    allowed_types = {
        "audio/wav", "audio/wave", "audio/x-wav",
        "audio/mp3", "audio/mpeg",
        "audio/webm",
        "audio/ogg",
        "audio/m4a", "audio/mp4",
        "application/octet-stream",  # Allow binary uploads
    }
    
    content_type = file.content_type or "application/octet-stream"
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format: {content_type}",
        )
    
    # Read audio data
    audio_data = await file.read()
    
    if len(audio_data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio file",
        )
    
    # Limit file size (10MB)
    if len(audio_data) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file too large (max 10MB)",
        )
    
    # Transcribe using JARVIS voice pipeline
    text = ""
    confidence = 0.0
    detected_language = language
    
    if _jarvis_instance:
        try:
            # Try using voice pipeline
            if hasattr(_jarvis_instance, '_voice_pipeline') and _jarvis_instance._voice_pipeline:
                voice = _jarvis_instance._voice_pipeline
                
                # Save to temp file if needed
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp.write(audio_data)
                    tmp_path = tmp.name
                
                try:
                    if hasattr(voice, 'transcribe_file'):
                        result = voice.transcribe_file(tmp_path, language=language)
                        if isinstance(result, dict):
                            text = result.get("text", "")
                            confidence = result.get("confidence", 0.9)
                            detected_language = result.get("language", language)
                        else:
                            text = str(result)
                            confidence = 0.9
                    elif hasattr(voice, '_stt') and voice._stt:
                        text = voice._stt.transcribe(tmp_path)
                        confidence = 0.9
                finally:
                    # Clean up temp file
                    Path(tmp_path).unlink(missing_ok=True)
            
            # Fallback to LLM-based transcription if available
            if not text and hasattr(_jarvis_instance, '_llm_router'):
                # Use Groq's Whisper API if available
                llm = _jarvis_instance._llm_router
                if hasattr(llm, 'transcribe'):
                    text = llm.transcribe(audio_data)
                    confidence = 0.85
        
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transcription failed: {str(e)}",
            )
    
    if not text:
        # Return empty result if no transcription available
        text = ""
        confidence = 0.0
    
    processing_time = (time.time() - start_time) * 1000
    
    return TranscribeResponse(
        text=text,
        confidence=confidence,
        language=detected_language,
        processing_time_ms=processing_time,
    )


@voice_router.post("/transcribe/base64", response_model=TranscribeResponse)
async def transcribe_audio_base64(
    audio_base64: str,
    format: str = Query("wav", description="Audio format (wav, mp3, webm)"),
    language: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Transcribe base64-encoded audio to text.
    
    Alternative to file upload for mobile apps that prefer base64.
    
    - **audio_base64**: Base64-encoded audio data
    - **format**: Audio format
    - **language**: Optional language hint
    """
    start_time = time.time()
    
    try:
        audio_data = base64.b64decode(audio_base64)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 encoding",
        )
    
    if len(audio_data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio data",
        )
    
    if len(audio_data) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio data too large (max 10MB)",
        )
    
    # Process same as file upload
    text = ""
    confidence = 0.0
    
    if _jarvis_instance:
        try:
            if hasattr(_jarvis_instance, '_voice_pipeline') and _jarvis_instance._voice_pipeline:
                voice = _jarvis_instance._voice_pipeline
                
                with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as tmp:
                    tmp.write(audio_data)
                    tmp_path = tmp.name
                
                try:
                    if hasattr(voice, 'transcribe_file'):
                        result = voice.transcribe_file(tmp_path, language=language)
                        text = result.get("text", "") if isinstance(result, dict) else str(result)
                        confidence = 0.9
                    elif hasattr(voice, '_stt') and voice._stt:
                        text = voice._stt.transcribe(tmp_path)
                        confidence = 0.9
                finally:
                    Path(tmp_path).unlink(missing_ok=True)
        except Exception as e:
            logger.error(f"Transcription error: {e}")
    
    processing_time = (time.time() - start_time) * 1000
    
    return TranscribeResponse(
        text=text,
        confidence=confidence,
        language=language,
        processing_time_ms=processing_time,
    )


@voice_router.get("/speak")
async def text_to_speech(
    text: str = Query(..., min_length=1, max_length=5000),
    voice: Optional[str] = Query(None, description="Voice name"),
    speed: float = Query(1.0, ge=0.5, le=2.0),
    format: str = Query("mp3", description="Output format (mp3, wav)"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Convert text to speech audio.
    
    Returns audio file stream.
    
    - **text**: Text to convert to speech
    - **voice**: Voice name (default: en-US-GuyNeural)
    - **speed**: Speech speed (0.5-2.0)
    - **format**: Output format (mp3, wav)
    """
    audio_data = None
    
    if _jarvis_instance:
        try:
            if hasattr(_jarvis_instance, '_voice_pipeline') and _jarvis_instance._voice_pipeline:
                voice_pipeline = _jarvis_instance._voice_pipeline
                
                if hasattr(voice_pipeline, '_tts') and voice_pipeline._tts:
                    tts = voice_pipeline._tts
                    
                    # Generate speech
                    if hasattr(tts, 'synthesize_to_bytes'):
                        audio_data = tts.synthesize_to_bytes(
                            text,
                            voice=voice,
                            speed=speed,
                        )
                    elif hasattr(tts, 'synthesize'):
                        # Save to temp file and read
                        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as tmp:
                            tmp_path = tmp.name
                        
                        try:
                            tts.synthesize(text, tmp_path, voice=voice)
                            with open(tmp_path, "rb") as f:
                                audio_data = f.read()
                        finally:
                            Path(tmp_path).unlink(missing_ok=True)
        
        except Exception as e:
            logger.error(f"TTS error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Text-to-speech failed: {str(e)}",
            )
    
    if not audio_data:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Text-to-speech service not available",
        )
    
    # Determine content type
    content_type = "audio/mpeg" if format == "mp3" else "audio/wav"
    
    return StreamingResponse(
        io.BytesIO(audio_data),
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename=speech.{format}",
            "Content-Length": str(len(audio_data)),
        },
    )


@voice_router.post("/speak", response_model=Dict[str, Any])
async def text_to_speech_post(
    request: SpeakRequest,
    format: str = Query("mp3"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Convert text to speech and return base64-encoded audio.
    
    Alternative to GET endpoint for longer text.
    
    - **text**: Text to convert
    - **voice**: Voice name
    - **speed**: Speech speed
    - **format**: Output format
    """
    audio_data = None
    
    if _jarvis_instance:
        try:
            if hasattr(_jarvis_instance, '_voice_pipeline') and _jarvis_instance._voice_pipeline:
                voice_pipeline = _jarvis_instance._voice_pipeline
                
                if hasattr(voice_pipeline, '_tts') and voice_pipeline._tts:
                    tts = voice_pipeline._tts
                    
                    if hasattr(tts, 'synthesize_to_bytes'):
                        audio_data = tts.synthesize_to_bytes(
                            request.text,
                            voice=request.voice,
                            speed=request.speed,
                        )
                    elif hasattr(tts, 'synthesize'):
                        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as tmp:
                            tmp_path = tmp.name
                        
                        try:
                            tts.synthesize(request.text, tmp_path, voice=request.voice)
                            with open(tmp_path, "rb") as f:
                                audio_data = f.read()
                        finally:
                            Path(tmp_path).unlink(missing_ok=True)
        
        except Exception as e:
            logger.error(f"TTS error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Text-to-speech failed: {str(e)}",
            )
    
    if not audio_data:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Text-to-speech service not available",
        )
    
    # Return base64-encoded audio
    audio_base64 = base64.b64encode(audio_data).decode("utf-8")
    
    return {
        "audio_base64": audio_base64,
        "format": format,
        "size_bytes": len(audio_data),
        "text_length": len(request.text),
    }


@voice_router.get("/voices")
async def list_voices(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    List available TTS voices.
    """
    voices = []
    
    # Default voices (Edge TTS)
    default_voices = [
        {"id": "en-US-GuyNeural", "name": "Guy (US)", "language": "en-US", "gender": "male"},
        {"id": "en-US-JennyNeural", "name": "Jenny (US)", "language": "en-US", "gender": "female"},
        {"id": "en-US-AriaNeural", "name": "Aria (US)", "language": "en-US", "gender": "female"},
        {"id": "en-GB-RyanNeural", "name": "Ryan (UK)", "language": "en-GB", "gender": "male"},
        {"id": "en-GB-SoniaNeural", "name": "Sonia (UK)", "language": "en-GB", "gender": "female"},
        {"id": "en-AU-WilliamNeural", "name": "William (AU)", "language": "en-AU", "gender": "male"},
        {"id": "en-IN-NeerjaNeural", "name": "Neerja (IN)", "language": "en-IN", "gender": "female"},
    ]
    
    if _jarvis_instance:
        try:
            if hasattr(_jarvis_instance, '_voice_pipeline') and _jarvis_instance._voice_pipeline:
                voice_pipeline = _jarvis_instance._voice_pipeline
                
                if hasattr(voice_pipeline, '_tts') and voice_pipeline._tts:
                    tts = voice_pipeline._tts
                    
                    if hasattr(tts, 'list_voices'):
                        voices = tts.list_voices()
        except Exception as e:
            logger.error(f"Error listing voices: {e}")
    
    if not voices:
        voices = default_voices
    
    return {"voices": voices}


@voice_router.get("/status")
async def voice_status(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get voice service status.
    """
    status = {
        "stt_available": False,
        "tts_available": False,
        "stt_provider": None,
        "tts_provider": None,
    }
    
    if _jarvis_instance:
        if hasattr(_jarvis_instance, '_voice_pipeline') and _jarvis_instance._voice_pipeline:
            voice = _jarvis_instance._voice_pipeline
            
            if hasattr(voice, '_stt') and voice._stt:
                status["stt_available"] = True
                status["stt_provider"] = type(voice._stt).__name__
            
            if hasattr(voice, '_tts') and voice._tts:
                status["tts_available"] = True
                status["tts_provider"] = type(voice._tts).__name__
    
    return status
