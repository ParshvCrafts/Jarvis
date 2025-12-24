"""
JARVIS Health & Wellness Module.

Workout tracking, sleep logging, nutrition, and mental wellness.
"""

from loguru import logger

HEALTH_AVAILABLE = False

try:
    from .models import (
        Workout,
        WorkoutType,
        Intensity,
        SleepLog,
        Meal,
        MealType,
        MoodLog,
        WaterIntake,
        HealthGoals,
        DailyHealthSummary,
        WeeklyHealthSummary,
        Exercise,
        BreathingExercise,
        BREATHING_EXERCISES,
        RSF_HOURS,
        CAMPUS_DINING,
    )
    
    from .tracker import HealthTracker
    
    from .manager import (
        HealthManager,
        HealthConfig,
    )
    
    HEALTH_AVAILABLE = True
    logger.info("Health module loaded successfully")
    
except ImportError as e:
    logger.warning(f"Health module not fully available: {e}")

__all__ = [
    "HEALTH_AVAILABLE",
    # Models
    "Workout",
    "WorkoutType",
    "Intensity",
    "SleepLog",
    "Meal",
    "MealType",
    "MoodLog",
    "WaterIntake",
    "HealthGoals",
    "DailyHealthSummary",
    "WeeklyHealthSummary",
    "Exercise",
    "BreathingExercise",
    "BREATHING_EXERCISES",
    "RSF_HOURS",
    "CAMPUS_DINING",
    # Tracker
    "HealthTracker",
    # Manager
    "HealthManager",
    "HealthConfig",
]
