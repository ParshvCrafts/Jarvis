"""
Authentication Manager for JARVIS.

Orchestrates face recognition, voice verification, and liveness detection
into a unified authentication flow.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from loguru import logger

from .face_auth import FaceAuthenticator
from .liveness import LivenessDetector, LivenessResult
from .session import AuthLevel, Session, SessionManager
from .voice_auth import VoiceAuthenticator


@dataclass
class AuthenticationResult:
    """Result of an authentication attempt."""
    success: bool
    session: Optional[Session]
    face_verified: bool
    voice_verified: bool
    liveness_verified: bool
    face_confidence: float
    voice_confidence: float
    message: str


class AuthenticationManager:
    """
    Unified authentication manager for JARVIS.
    
    Coordinates multiple authentication factors:
    - Face recognition
    - Voice verification
    - Liveness detection
    
    Provides both full authentication and quick re-verification.
    """
    
    def __init__(
        self,
        data_dir: Path | str,
        face_config: dict | None = None,
        voice_config: dict | None = None,
        liveness_config: dict | None = None,
        session_config: dict | None = None,
    ):
        """
        Initialize the authentication manager.
        
        Args:
            data_dir: Base directory for authentication data.
            face_config: Face recognition configuration.
            voice_config: Voice verification configuration.
            liveness_config: Liveness detection configuration.
            session_config: Session management configuration.
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Default configurations
        face_config = face_config or {}
        voice_config = voice_config or {}
        liveness_config = liveness_config or {}
        session_config = session_config or {}
        
        # Initialize authenticators
        self.face_auth = FaceAuthenticator(
            encodings_dir=self.data_dir / "face_encodings",
            tolerance=face_config.get("tolerance", 0.5),
            model=face_config.get("model", "hog"),
            num_jitters=face_config.get("num_jitters", 1),
        )
        
        self.voice_auth = VoiceAuthenticator(
            voice_prints_dir=self.data_dir / "voice_prints",
            similarity_threshold=voice_config.get("similarity_threshold", 0.75),
            min_audio_duration=voice_config.get("min_audio_duration", 1.5),
            sample_rate=voice_config.get("sample_rate", 16000),
        )
        
        self.liveness = LivenessDetector(
            ear_threshold=liveness_config.get("ear_threshold", 0.25),
            consec_frames=liveness_config.get("consec_frames", 3),
            head_movement_enabled=liveness_config.get("head_movement_enabled", True),
            timeout=liveness_config.get("timeout", 10),
        )
        
        self.session_manager = SessionManager(
            session_timeout=session_config.get("session_timeout", 1800),
            max_failed_attempts=session_config.get("max_failed_attempts", 3),
            lockout_duration=session_config.get("lockout_duration", 300),
            jwt_secret=session_config.get("jwt_secret"),
        )
        
        # Configure command authorization levels
        auth_levels = session_config.get("authorization_levels", {})
        self.session_manager.configure_command_levels(
            low=auth_levels.get("low", ["query", "search", "weather", "time", "reminder"]),
            medium=auth_levels.get("medium", ["app_control", "file_operations", "browser", "email"]),
            high=auth_levels.get("high", ["door_unlock", "system_settings", "delete_files", "iot_control"]),
        )
    
    @property
    def is_enrolled(self) -> bool:
        """Check if user has enrolled biometrics."""
        return self.face_auth.has_enrolled_faces() or self.voice_auth.has_enrolled_voice()
    
    @property
    def has_active_session(self) -> bool:
        """Check if there's an active session."""
        return self.session_manager.get_active_session() is not None
    
    def get_active_session(self) -> Optional[Session]:
        """Get the current active session."""
        return self.session_manager.get_active_session()
    
    def enroll_face_from_camera(
        self,
        num_samples: int = 5,
        camera_index: int = 0,
    ) -> Tuple[bool, str]:
        """
        Enroll face from camera captures.
        
        Args:
            num_samples: Number of face samples to capture.
            camera_index: Camera device index.
            
        Returns:
            Tuple of (success, message).
        """
        if not self.face_auth.is_available:
            return False, "Face recognition not available"
        
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return False, "Failed to open camera"
        
        enrolled = 0
        
        try:
            logger.info(f"Starting face enrollment. Capturing {num_samples} samples...")
            logger.info("Please look at the camera and move your head slightly between captures.")
            
            for i in range(num_samples):
                # Show preview
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        continue
                    
                    # Detect face
                    faces = self.face_auth.detect_faces(frame)
                    
                    # Draw face rectangle
                    for (top, right, bottom, left) in faces:
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                    
                    cv2.putText(
                        frame,
                        f"Sample {i + 1}/{num_samples} - Press SPACE to capture, Q to quit",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2,
                    )
                    
                    cv2.imshow("Face Enrollment", frame)
                    
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord(' ') and faces:
                        # Capture this frame
                        if self.face_auth.enroll_face(frame):
                            enrolled += 1
                            logger.info(f"Captured sample {enrolled}")
                        break
                    elif key == ord('q'):
                        break
                
                if key == ord('q'):
                    break
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
        
        if enrolled > 0:
            return True, f"Successfully enrolled {enrolled} face samples"
        return False, "No face samples enrolled"
    
    def enroll_voice_from_microphone(
        self,
        num_samples: int = 3,
        duration: float = 3.0,
    ) -> Tuple[bool, str]:
        """
        Enroll voice from microphone recordings.
        
        Args:
            num_samples: Number of voice samples to record.
            duration: Duration of each recording in seconds.
            
        Returns:
            Tuple of (success, message).
        """
        if not self.voice_auth.is_available:
            return False, "Voice authentication not available"
        
        from .voice_auth import record_voice_sample
        
        enrolled = 0
        
        logger.info(f"Starting voice enrollment. Recording {num_samples} samples of {duration}s each.")
        logger.info("Please speak naturally when prompted.")
        
        for i in range(num_samples):
            input(f"\nPress Enter to start recording sample {i + 1}/{num_samples}...")
            
            result = record_voice_sample(duration=duration)
            if result is None:
                logger.warning(f"Failed to record sample {i + 1}")
                continue
            
            audio, sr = result
            if self.voice_auth.enroll_voice(audio, sr):
                enrolled += 1
                logger.info(f"Enrolled sample {enrolled}")
            else:
                logger.warning(f"Failed to enroll sample {i + 1}")
        
        if enrolled > 0:
            return True, f"Successfully enrolled {enrolled} voice samples"
        return False, "No voice samples enrolled"
    
    def authenticate(
        self,
        require_face: bool = True,
        require_voice: bool = False,
        require_liveness: bool = True,
        camera_index: int = 0,
        timeout: float = 30.0,
    ) -> AuthenticationResult:
        """
        Perform full authentication.
        
        Args:
            require_face: Whether face verification is required.
            require_voice: Whether voice verification is required.
            require_liveness: Whether liveness detection is required.
            camera_index: Camera device index.
            timeout: Overall timeout in seconds.
            
        Returns:
            AuthenticationResult with outcome.
        """
        # Check for lockout
        if self.session_manager.is_locked_out():
            remaining = self.session_manager.get_lockout_remaining()
            return AuthenticationResult(
                success=False,
                session=None,
                face_verified=False,
                voice_verified=False,
                liveness_verified=False,
                face_confidence=0.0,
                voice_confidence=0.0,
                message=f"Account locked. Try again in {remaining} seconds.",
            )
        
        face_verified = False
        voice_verified = False
        liveness_verified = False
        face_confidence = 0.0
        voice_confidence = 0.0
        
        # Step 1: Liveness detection (if required)
        if require_liveness and self.liveness.is_available:
            logger.info("Starting liveness detection...")
            liveness_result = self.liveness.check_liveness(
                camera_index=camera_index,
                required_blinks=2,
                show_preview=True,
            )
            liveness_verified = liveness_result.is_live
            
            if not liveness_verified and require_liveness:
                self.session_manager.record_failed_attempt()
                return AuthenticationResult(
                    success=False,
                    session=None,
                    face_verified=False,
                    voice_verified=False,
                    liveness_verified=False,
                    face_confidence=0.0,
                    voice_confidence=0.0,
                    message=f"Liveness check failed: {liveness_result.message}",
                )
        elif not require_liveness:
            liveness_verified = True
        
        # Step 2: Face verification (if required)
        if require_face and self.face_auth.is_available:
            if not self.face_auth.has_enrolled_faces():
                return AuthenticationResult(
                    success=False,
                    session=None,
                    face_verified=False,
                    voice_verified=False,
                    liveness_verified=liveness_verified,
                    face_confidence=0.0,
                    voice_confidence=0.0,
                    message="No face enrolled. Please enroll first.",
                )
            
            logger.info("Starting face verification...")
            cap = cv2.VideoCapture(camera_index)
            
            if cap.isOpened():
                try:
                    # Try multiple frames for better accuracy
                    for _ in range(10):
                        ret, frame = cap.read()
                        if not ret:
                            continue
                        
                        face_verified, face_confidence = self.face_auth.verify_face(frame)
                        if face_verified:
                            break
                finally:
                    cap.release()
            
            if not face_verified and require_face:
                self.session_manager.record_failed_attempt()
                return AuthenticationResult(
                    success=False,
                    session=None,
                    face_verified=False,
                    voice_verified=False,
                    liveness_verified=liveness_verified,
                    face_confidence=face_confidence,
                    voice_confidence=0.0,
                    message=f"Face verification failed. Confidence: {face_confidence:.2f}",
                )
        elif not require_face:
            face_verified = True
        
        # Step 3: Voice verification (if required)
        if require_voice and self.voice_auth.is_available:
            if not self.voice_auth.has_enrolled_voice():
                return AuthenticationResult(
                    success=False,
                    session=None,
                    face_verified=face_verified,
                    voice_verified=False,
                    liveness_verified=liveness_verified,
                    face_confidence=face_confidence,
                    voice_confidence=0.0,
                    message="No voice enrolled. Please enroll first.",
                )
            
            logger.info("Starting voice verification...")
            from .voice_auth import record_voice_sample
            
            print("Please say something for voice verification...")
            result = record_voice_sample(duration=2.0)
            
            if result:
                audio, sr = result
                voice_verified, voice_confidence = self.voice_auth.verify_voice(audio, sr)
            
            if not voice_verified and require_voice:
                self.session_manager.record_failed_attempt()
                return AuthenticationResult(
                    success=False,
                    session=None,
                    face_verified=face_verified,
                    voice_verified=False,
                    liveness_verified=liveness_verified,
                    face_confidence=face_confidence,
                    voice_confidence=voice_confidence,
                    message=f"Voice verification failed. Similarity: {voice_confidence:.2f}",
                )
        elif not require_voice:
            voice_verified = True
        
        # All checks passed - create session
        auth_level = AuthLevel.LOW
        if face_verified and liveness_verified:
            auth_level = AuthLevel.MEDIUM
        if face_verified and voice_verified and liveness_verified:
            auth_level = AuthLevel.HIGH
        
        session = self.session_manager.create_session(
            auth_level=auth_level,
            face_verified=face_verified,
            voice_verified=voice_verified,
            liveness_verified=liveness_verified,
        )
        
        logger.info(f"Authentication successful. Auth level: {auth_level.name}")
        
        return AuthenticationResult(
            success=True,
            session=session,
            face_verified=face_verified,
            voice_verified=voice_verified,
            liveness_verified=liveness_verified,
            face_confidence=face_confidence,
            voice_confidence=voice_confidence,
            message=f"Authentication successful. Level: {auth_level.name}",
        )
    
    def quick_verify(
        self,
        frame: np.ndarray,
        audio: Optional[Tuple[np.ndarray, int]] = None,
    ) -> Tuple[bool, float]:
        """
        Quick verification for continuous monitoring.
        
        Args:
            frame: Camera frame for face verification.
            audio: Optional (audio, sample_rate) for voice verification.
            
        Returns:
            Tuple of (verified, confidence).
        """
        session = self.get_active_session()
        if session is None:
            return False, 0.0
        
        # Quick face check
        face_ok, face_conf = self.face_auth.verify_face(frame)
        
        # Quick liveness check
        live_ok, live_conf = self.liveness.quick_check(frame)
        
        # Combine confidences
        confidence = (face_conf + live_conf) / 2
        
        # Optional voice check
        if audio is not None:
            voice_ok, voice_conf = self.voice_auth.verify_voice(audio[0], audio[1])
            confidence = (face_conf + live_conf + voice_conf) / 3
            verified = face_ok and live_ok and voice_ok
        else:
            verified = face_ok and live_ok
        
        if verified:
            # Refresh session
            self.session_manager.refresh_session(session.session_id)
        
        return verified, confidence
    
    def check_command_authorization(
        self,
        command: str,
    ) -> Tuple[bool, str]:
        """
        Check if current session is authorized for a command.
        
        Args:
            command: Command to check authorization for.
            
        Returns:
            Tuple of (authorized, message).
        """
        session = self.get_active_session()
        if session is None:
            return False, "No active session. Please authenticate first."
        
        return self.session_manager.check_authorization(session.session_id, command)
    
    def logout(self) -> bool:
        """End the current session."""
        session = self.get_active_session()
        if session:
            self.session_manager.invalidate_session(session.session_id)
            logger.info("Session ended")
            return True
        return False
    
    def get_enrollment_status(self) -> dict:
        """Get current enrollment status."""
        return {
            "face_enrolled": self.face_auth.has_enrolled_faces(),
            "face_count": self.face_auth.get_enrollment_count(),
            "voice_enrolled": self.voice_auth.has_enrolled_voice(),
            "voice_count": self.voice_auth.get_enrollment_count(),
            "face_available": self.face_auth.is_available,
            "voice_available": self.voice_auth.is_available,
            "liveness_available": self.liveness.is_available,
        }
    
    def clear_all_enrollments(self) -> bool:
        """Clear all enrolled biometrics."""
        face_cleared = self.face_auth.clear_enrollments()
        voice_cleared = self.voice_auth.clear_enrollments()
        return face_cleared and voice_cleared
