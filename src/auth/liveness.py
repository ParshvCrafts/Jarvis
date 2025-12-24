"""
Liveness Detection Module for JARVIS.

Implements anti-spoofing measures using:
- Eye blink detection (Eye Aspect Ratio)
- Head pose estimation
- Optional challenge-response (random actions)

Uses MediaPipe for facial landmark detection.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from loguru import logger

# Optional cv2 import
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None

# Optional numpy import
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    mp = None
    logger.warning("MediaPipe not available. Liveness detection limited.")


class LivenessChallenge(Enum):
    """Types of liveness challenges."""
    BLINK = "blink"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    NOD = "nod"


@dataclass
class LivenessResult:
    """Result of a liveness check."""
    is_live: bool
    confidence: float
    blinks_detected: int
    head_movement_detected: bool
    challenges_passed: List[LivenessChallenge]
    message: str


class LivenessDetector:
    """
    Liveness detection using facial landmarks.
    
    Detects:
    - Eye blinks using Eye Aspect Ratio (EAR)
    - Head pose changes (yaw, pitch)
    - Challenge-response verification
    """
    
    # MediaPipe face mesh landmark indices
    # Left eye landmarks
    LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
    # Right eye landmarks  
    RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
    # Nose tip for head pose
    NOSE_TIP_INDEX = 1
    # Face oval for head pose reference
    FACE_OVAL_INDICES = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 
                         397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
                         172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
    
    def __init__(
        self,
        ear_threshold: float = 0.25,
        consec_frames: int = 3,
        head_movement_enabled: bool = True,
        head_movement_threshold: float = 15.0,
        timeout: float = 10.0,
    ):
        """
        Initialize the liveness detector.
        
        Args:
            ear_threshold: Eye Aspect Ratio threshold for blink detection.
            consec_frames: Consecutive frames below threshold to count as blink.
            head_movement_enabled: Whether to check for head movement.
            head_movement_threshold: Degrees of head movement required.
            timeout: Maximum time for liveness check in seconds.
        """
        self.ear_threshold = ear_threshold
        self.consec_frames = consec_frames
        self.head_movement_enabled = head_movement_enabled
        self.head_movement_threshold = head_movement_threshold
        self.timeout = timeout
        
        # State tracking
        self._blink_counter = 0
        self._total_blinks = 0
        self._initial_head_pose: Optional[Tuple[float, float, float]] = None
        self._max_head_deviation = 0.0
        
        # Initialize MediaPipe
        self._face_mesh = None
        if MEDIAPIPE_AVAILABLE:
            self._mp_face_mesh = mp.solutions.face_mesh
            self._face_mesh = self._mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
    
    @property
    def is_available(self) -> bool:
        """Check if liveness detection is available."""
        return MEDIAPIPE_AVAILABLE and self._face_mesh is not None
    
    def _calculate_ear(self, eye_landmarks: List[Tuple[float, float]]) -> float:
        """
        Calculate Eye Aspect Ratio (EAR).
        
        EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        
        Args:
            eye_landmarks: List of 6 eye landmark coordinates.
            
        Returns:
            Eye Aspect Ratio value.
        """
        if len(eye_landmarks) != 6:
            return 1.0
        
        # Vertical distances
        v1 = np.linalg.norm(np.array(eye_landmarks[1]) - np.array(eye_landmarks[5]))
        v2 = np.linalg.norm(np.array(eye_landmarks[2]) - np.array(eye_landmarks[4]))
        
        # Horizontal distance
        h = np.linalg.norm(np.array(eye_landmarks[0]) - np.array(eye_landmarks[3]))
        
        if h == 0:
            return 1.0
        
        ear = (v1 + v2) / (2.0 * h)
        return ear
    
    def _get_eye_landmarks(
        self,
        landmarks,
        indices: List[int],
        frame_width: int,
        frame_height: int,
    ) -> List[Tuple[float, float]]:
        """Extract eye landmark coordinates."""
        coords = []
        for idx in indices:
            lm = landmarks[idx]
            coords.append((lm.x * frame_width, lm.y * frame_height))
        return coords
    
    def _estimate_head_pose(
        self,
        landmarks,
        frame_width: int,
        frame_height: int,
    ) -> Tuple[float, float, float]:
        """
        Estimate head pose (yaw, pitch, roll) from landmarks.
        
        Returns:
            Tuple of (yaw, pitch, roll) in degrees.
        """
        # Get key facial points
        nose_tip = landmarks[self.NOSE_TIP_INDEX]
        
        # Get face bounding points for reference
        left_point = landmarks[234]  # Left cheek
        right_point = landmarks[454]  # Right cheek
        top_point = landmarks[10]  # Forehead
        bottom_point = landmarks[152]  # Chin
        
        # Calculate yaw (left-right rotation)
        nose_x = nose_tip.x
        face_center_x = (left_point.x + right_point.x) / 2
        face_width = abs(right_point.x - left_point.x)
        
        if face_width > 0:
            yaw = (nose_x - face_center_x) / face_width * 90
        else:
            yaw = 0
        
        # Calculate pitch (up-down rotation)
        nose_y = nose_tip.y
        face_center_y = (top_point.y + bottom_point.y) / 2
        face_height = abs(bottom_point.y - top_point.y)
        
        if face_height > 0:
            pitch = (nose_y - face_center_y) / face_height * 90
        else:
            pitch = 0
        
        # Roll is more complex, simplified here
        roll = 0
        
        return (yaw, pitch, roll)
    
    def process_frame(self, frame: np.ndarray) -> Tuple[bool, dict]:
        """
        Process a single frame for liveness detection.
        
        Args:
            frame: BGR image from OpenCV.
            
        Returns:
            Tuple of (face_detected, metrics_dict).
        """
        if not self.is_available:
            return False, {}
        
        # Convert to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame.shape[:2]
        
        # Process with MediaPipe
        results = self._face_mesh.process(rgb_frame)
        
        if not results.multi_face_landmarks:
            return False, {}
        
        landmarks = results.multi_face_landmarks[0].landmark
        
        # Calculate EAR for both eyes
        left_eye = self._get_eye_landmarks(landmarks, self.LEFT_EYE_INDICES, w, h)
        right_eye = self._get_eye_landmarks(landmarks, self.RIGHT_EYE_INDICES, w, h)
        
        left_ear = self._calculate_ear(left_eye)
        right_ear = self._calculate_ear(right_eye)
        avg_ear = (left_ear + right_ear) / 2
        
        # Detect blink
        blink_detected = False
        if avg_ear < self.ear_threshold:
            self._blink_counter += 1
        else:
            if self._blink_counter >= self.consec_frames:
                self._total_blinks += 1
                blink_detected = True
            self._blink_counter = 0
        
        # Estimate head pose
        head_pose = self._estimate_head_pose(landmarks, w, h)
        
        # Track head movement
        if self._initial_head_pose is None:
            self._initial_head_pose = head_pose
        else:
            yaw_diff = abs(head_pose[0] - self._initial_head_pose[0])
            pitch_diff = abs(head_pose[1] - self._initial_head_pose[1])
            deviation = max(yaw_diff, pitch_diff)
            self._max_head_deviation = max(self._max_head_deviation, deviation)
        
        metrics = {
            "ear": avg_ear,
            "blink_detected": blink_detected,
            "total_blinks": self._total_blinks,
            "head_pose": head_pose,
            "head_deviation": self._max_head_deviation,
        }
        
        return True, metrics
    
    def reset(self) -> None:
        """Reset the liveness detector state."""
        self._blink_counter = 0
        self._total_blinks = 0
        self._initial_head_pose = None
        self._max_head_deviation = 0.0
    
    def check_liveness(
        self,
        camera_index: int = 0,
        required_blinks: int = 2,
        show_preview: bool = True,
    ) -> LivenessResult:
        """
        Perform a complete liveness check.
        
        Args:
            camera_index: Camera device index.
            required_blinks: Number of blinks required to pass.
            show_preview: Whether to show camera preview.
            
        Returns:
            LivenessResult with check outcome.
        """
        if not self.is_available:
            return LivenessResult(
                is_live=False,
                confidence=0.0,
                blinks_detected=0,
                head_movement_detected=False,
                challenges_passed=[],
                message="Liveness detection not available",
            )
        
        self.reset()
        
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return LivenessResult(
                is_live=False,
                confidence=0.0,
                blinks_detected=0,
                head_movement_detected=False,
                challenges_passed=[],
                message="Failed to open camera",
            )
        
        start_time = time.time()
        challenges_passed = []
        
        try:
            logger.info("Starting liveness check. Please blink naturally and move your head slightly.")
            
            while time.time() - start_time < self.timeout:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                face_detected, metrics = self.process_frame(frame)
                
                if show_preview:
                    # Draw info on frame
                    if face_detected:
                        cv2.putText(
                            frame,
                            f"Blinks: {metrics['total_blinks']}/{required_blinks}",
                            (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 255, 0),
                            2,
                        )
                        cv2.putText(
                            frame,
                            f"Head movement: {metrics['head_deviation']:.1f}deg",
                            (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 255, 0),
                            2,
                        )
                    else:
                        cv2.putText(
                            frame,
                            "No face detected",
                            (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 0, 255),
                            2,
                        )
                    
                    cv2.imshow("Liveness Check", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                # Check if requirements met
                blinks_ok = self._total_blinks >= required_blinks
                head_ok = (not self.head_movement_enabled or 
                          self._max_head_deviation >= self.head_movement_threshold)
                
                if blinks_ok:
                    challenges_passed.append(LivenessChallenge.BLINK)
                
                if blinks_ok and head_ok:
                    # Success!
                    confidence = min(1.0, (self._total_blinks / required_blinks) * 0.5 +
                                    (self._max_head_deviation / self.head_movement_threshold) * 0.5)
                    
                    return LivenessResult(
                        is_live=True,
                        confidence=confidence,
                        blinks_detected=self._total_blinks,
                        head_movement_detected=head_ok,
                        challenges_passed=list(set(challenges_passed)),
                        message="Liveness verified successfully",
                    )
        
        finally:
            cap.release()
            if show_preview:
                cv2.destroyAllWindows()
        
        # Timeout - check partial success
        confidence = (self._total_blinks / required_blinks) * 0.5
        if self.head_movement_enabled:
            confidence += (min(self._max_head_deviation, self.head_movement_threshold) / 
                          self.head_movement_threshold) * 0.5
        
        return LivenessResult(
            is_live=False,
            confidence=confidence,
            blinks_detected=self._total_blinks,
            head_movement_detected=self._max_head_deviation >= self.head_movement_threshold,
            challenges_passed=challenges_passed,
            message=f"Liveness check timed out. Blinks: {self._total_blinks}/{required_blinks}",
        )
    
    def quick_check(self, frame: np.ndarray) -> Tuple[bool, float]:
        """
        Quick liveness check on a single frame.
        
        This is less reliable than the full check but useful for
        continuous monitoring during a session.
        
        Args:
            frame: BGR image from OpenCV.
            
        Returns:
            Tuple of (likely_live, confidence).
        """
        if not self.is_available:
            return False, 0.0
        
        face_detected, metrics = self.process_frame(frame)
        
        if not face_detected:
            return False, 0.0
        
        # Basic checks for a single frame
        ear = metrics.get("ear", 0)
        
        # EAR should be in a reasonable range for a real face
        # Too low = closed eyes, too high = might be a photo
        if 0.15 < ear < 0.4:
            confidence = 0.7
        else:
            confidence = 0.3
        
        return True, confidence
