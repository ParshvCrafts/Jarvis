"""
Face Authentication Module for JARVIS.

Provides face recognition capabilities using the face_recognition library
with support for multiple face encodings per user.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import List, Optional, Tuple

from loguru import logger

# Optional cv2 import
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    logger.warning("opencv-python not installed. Face authentication disabled.")

# Optional numpy import
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

# Optional face_recognition import
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    logger.warning("face_recognition not available. Face authentication disabled.")


class FaceAuthenticator:
    """
    Face authentication using face_recognition library.
    
    Supports:
    - Face detection and encoding
    - Multiple face encodings per user for robustness
    - Configurable tolerance for matching
    - Caching of encodings for performance
    """
    
    def __init__(
        self,
        encodings_dir: Path | str,
        tolerance: float = 0.5,
        model: str = "hog",
        num_jitters: int = 1,
    ):
        """
        Initialize the face authenticator.
        
        Args:
            encodings_dir: Directory to store face encodings.
            tolerance: How much distance between faces to consider a match (lower = stricter).
            model: Face detection model - "hog" (faster, CPU) or "cnn" (more accurate, GPU).
            num_jitters: Number of times to re-sample face when calculating encoding.
        """
        self.encodings_dir = Path(encodings_dir)
        self.encodings_dir.mkdir(parents=True, exist_ok=True)
        
        self.tolerance = tolerance
        self.model = model
        self.num_jitters = num_jitters
        
        # Cache for loaded encodings
        self._encodings_cache: Optional[List[np.ndarray]] = None
        self._cache_valid = False
        
        if not FACE_RECOGNITION_AVAILABLE:
            logger.error("Face recognition library not installed!")
    
    @property
    def is_available(self) -> bool:
        """Check if face recognition is available."""
        return FACE_RECOGNITION_AVAILABLE
    
    @property
    def encodings_file(self) -> Path:
        """Path to the encodings file."""
        return self.encodings_dir / "user_encodings.pkl"
    
    def _load_encodings(self) -> List[np.ndarray]:
        """Load cached face encodings from disk."""
        if self._cache_valid and self._encodings_cache is not None:
            return self._encodings_cache
        
        if not self.encodings_file.exists():
            self._encodings_cache = []
            self._cache_valid = True
            return []
        
        try:
            with open(self.encodings_file, "rb") as f:
                self._encodings_cache = pickle.load(f)
            self._cache_valid = True
            logger.debug(f"Loaded {len(self._encodings_cache)} face encodings")
            return self._encodings_cache
        except Exception as e:
            logger.error(f"Failed to load face encodings: {e}")
            self._encodings_cache = []
            self._cache_valid = True
            return []
    
    def _save_encodings(self, encodings: List[np.ndarray]) -> bool:
        """Save face encodings to disk."""
        try:
            with open(self.encodings_file, "wb") as f:
                pickle.dump(encodings, f)
            self._encodings_cache = encodings
            self._cache_valid = True
            logger.info(f"Saved {len(encodings)} face encodings")
            return True
        except Exception as e:
            logger.error(f"Failed to save face encodings: {e}")
            return False
    
    def has_enrolled_faces(self) -> bool:
        """Check if any faces are enrolled."""
        return len(self._load_encodings()) > 0
    
    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in a frame.
        
        Args:
            frame: BGR image from OpenCV.
            
        Returns:
            List of face locations as (top, right, bottom, left) tuples.
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return []
        
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_frame, model=self.model)
        
        return face_locations
    
    def get_face_encoding(self, frame: np.ndarray, face_location: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        """
        Get face encoding from a frame.
        
        Args:
            frame: BGR image from OpenCV.
            face_location: Optional specific face location. If None, uses first detected face.
            
        Returns:
            Face encoding as numpy array, or None if no face found.
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return None
        
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Get face locations if not provided
        if face_location is None:
            face_locations = face_recognition.face_locations(rgb_frame, model=self.model)
            if not face_locations:
                return None
            face_location = face_locations[0]
        
        # Get encoding
        encodings = face_recognition.face_encodings(
            rgb_frame,
            known_face_locations=[face_location],
            num_jitters=self.num_jitters,
        )
        
        if not encodings:
            return None
        
        return encodings[0]
    
    def enroll_face(self, frame: np.ndarray) -> bool:
        """
        Enroll a new face encoding.
        
        Args:
            frame: BGR image containing the face to enroll.
            
        Returns:
            True if enrollment successful, False otherwise.
        """
        if not FACE_RECOGNITION_AVAILABLE:
            logger.error("Face recognition not available")
            return False
        
        encoding = self.get_face_encoding(frame)
        if encoding is None:
            logger.warning("No face detected in frame for enrollment")
            return False
        
        # Load existing encodings and add new one
        encodings = self._load_encodings()
        encodings.append(encoding)
        
        return self._save_encodings(encodings)
    
    def enroll_multiple_faces(self, frames: List[np.ndarray]) -> int:
        """
        Enroll multiple face encodings from different frames.
        
        Args:
            frames: List of BGR images containing faces to enroll.
            
        Returns:
            Number of faces successfully enrolled.
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return 0
        
        encodings = self._load_encodings()
        enrolled_count = 0
        
        for frame in frames:
            encoding = self.get_face_encoding(frame)
            if encoding is not None:
                encodings.append(encoding)
                enrolled_count += 1
        
        if enrolled_count > 0:
            self._save_encodings(encodings)
        
        logger.info(f"Enrolled {enrolled_count} faces from {len(frames)} frames")
        return enrolled_count
    
    def verify_face(self, frame: np.ndarray) -> Tuple[bool, float]:
        """
        Verify if a face matches enrolled faces.
        
        Args:
            frame: BGR image containing the face to verify.
            
        Returns:
            Tuple of (is_match, confidence).
            confidence is 1.0 - distance, so higher is better.
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return False, 0.0
        
        known_encodings = self._load_encodings()
        if not known_encodings:
            logger.warning("No enrolled faces to verify against")
            return False, 0.0
        
        # Get encoding from frame
        encoding = self.get_face_encoding(frame)
        if encoding is None:
            logger.debug("No face detected in verification frame")
            return False, 0.0
        
        # Compare with all known encodings
        distances = face_recognition.face_distance(known_encodings, encoding)
        
        if len(distances) == 0:
            return False, 0.0
        
        # Get best match (lowest distance)
        min_distance = float(np.min(distances))
        confidence = 1.0 - min_distance
        
        # Check if within tolerance
        is_match = min_distance <= self.tolerance
        
        logger.debug(f"Face verification: match={is_match}, confidence={confidence:.3f}, distance={min_distance:.3f}")
        
        return is_match, confidence
    
    def clear_enrollments(self) -> bool:
        """Clear all enrolled face encodings."""
        try:
            if self.encodings_file.exists():
                self.encodings_file.unlink()
            self._encodings_cache = []
            self._cache_valid = True
            logger.info("Cleared all face enrollments")
            return True
        except Exception as e:
            logger.error(f"Failed to clear enrollments: {e}")
            return False
    
    def get_enrollment_count(self) -> int:
        """Get the number of enrolled face encodings."""
        return len(self._load_encodings())


def capture_enrollment_frames(
    num_frames: int = 5,
    delay_seconds: float = 0.5,
    camera_index: int = 0,
) -> List[np.ndarray]:
    """
    Capture multiple frames for face enrollment.
    
    Args:
        num_frames: Number of frames to capture.
        delay_seconds: Delay between captures.
        camera_index: Camera device index.
        
    Returns:
        List of captured frames.
    """
    import time
    
    frames = []
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        logger.error("Failed to open camera")
        return frames
    
    try:
        logger.info(f"Capturing {num_frames} frames for enrollment...")
        
        for i in range(num_frames):
            ret, frame = cap.read()
            if ret:
                frames.append(frame)
                logger.debug(f"Captured frame {i + 1}/{num_frames}")
            time.sleep(delay_seconds)
    finally:
        cap.release()
    
    return frames
