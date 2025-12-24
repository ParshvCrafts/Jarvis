"""
Data models for JARVIS Health & Wellness Module.

Defines structures for workouts, sleep, nutrition, and mood tracking.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class WorkoutType(Enum):
    """Type of workout."""
    RUNNING = "running"
    WALKING = "walking"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    WEIGHTS = "weights"
    HIIT = "hiit"
    YOGA = "yoga"
    STRETCHING = "stretching"
    SPORTS = "sports"
    CARDIO = "cardio"
    OTHER = "other"


class Intensity(Enum):
    """Workout intensity level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MealType(Enum):
    """Type of meal."""
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


@dataclass
class Workout:
    """A workout session."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: date = field(default_factory=date.today)
    workout_type: WorkoutType = WorkoutType.OTHER
    
    duration_minutes: int = 0
    intensity: Intensity = Intensity.MEDIUM
    
    # Metrics
    distance_miles: Optional[float] = None
    calories_burned: Optional[int] = None
    heart_rate_avg: Optional[int] = None
    
    # Details
    exercises: List[str] = field(default_factory=list)
    notes: str = ""
    
    # Timestamps
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "workout_type": self.workout_type.value,
            "duration_minutes": self.duration_minutes,
            "intensity": self.intensity.value,
            "distance_miles": self.distance_miles,
            "calories_burned": self.calories_burned,
            "notes": self.notes,
        }


@dataclass
class SleepLog:
    """A sleep log entry."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: date = field(default_factory=date.today)
    
    bedtime: Optional[time] = None
    wake_time: Optional[time] = None
    duration_hours: float = 0.0
    
    quality: int = 5  # 1-10 scale
    
    # Sleep factors
    deep_sleep_hours: Optional[float] = None
    rem_sleep_hours: Optional[float] = None
    awakenings: int = 0
    
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "bedtime": self.bedtime.isoformat() if self.bedtime else None,
            "wake_time": self.wake_time.isoformat() if self.wake_time else None,
            "duration_hours": self.duration_hours,
            "quality": self.quality,
            "notes": self.notes,
        }


@dataclass
class Meal:
    """A meal log entry."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: date = field(default_factory=date.today)
    meal_type: MealType = MealType.SNACK
    time: Optional[time] = None
    
    description: str = ""
    
    # Nutrition (optional)
    calories: Optional[int] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    
    # Source
    location: str = ""  # e.g., "Crossroads dining hall"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "meal_type": self.meal_type.value,
            "description": self.description,
            "calories": self.calories,
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fat_g": self.fat_g,
        }


@dataclass
class MoodLog:
    """A mood/mental wellness log."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: date = field(default_factory=date.today)
    time: Optional[time] = None
    
    mood: int = 5  # 1-10 scale
    energy: int = 5  # 1-10 scale
    stress: int = 5  # 1-10 scale (higher = more stressed)
    
    notes: str = ""
    triggers: List[str] = field(default_factory=list)  # What affected mood
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "mood": self.mood,
            "energy": self.energy,
            "stress": self.stress,
            "notes": self.notes,
            "triggers": self.triggers,
        }


@dataclass
class WaterIntake:
    """Daily water intake tracking."""
    date: date = field(default_factory=date.today)
    glasses: int = 0  # 8oz glasses
    
    @property
    def ounces(self) -> int:
        return self.glasses * 8
    
    @property
    def liters(self) -> float:
        return self.ounces * 0.0296
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "glasses": self.glasses,
            "ounces": self.ounces,
        }


@dataclass
class HealthGoals:
    """User's health goals."""
    sleep_hours: float = 7.0
    water_glasses: int = 8
    workout_days_per_week: int = 4
    daily_steps: int = 10000
    daily_calories: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sleep_hours": self.sleep_hours,
            "water_glasses": self.water_glasses,
            "workout_days_per_week": self.workout_days_per_week,
            "daily_steps": self.daily_steps,
            "daily_calories": self.daily_calories,
        }


@dataclass
class DailyHealthSummary:
    """Summary of health metrics for a day."""
    date: date = field(default_factory=date.today)
    
    # Sleep
    sleep_hours: float = 0.0
    sleep_quality: int = 0
    
    # Workouts
    workouts: List[Workout] = field(default_factory=list)
    total_workout_minutes: int = 0
    calories_burned: int = 0
    
    # Nutrition
    meals: List[Meal] = field(default_factory=list)
    total_calories: int = 0
    total_protein: float = 0.0
    
    # Water
    water_glasses: int = 0
    
    # Mood
    avg_mood: float = 0.0
    avg_stress: float = 0.0
    
    # Goals met
    sleep_goal_met: bool = False
    water_goal_met: bool = False
    workout_done: bool = False


@dataclass
class WeeklyHealthSummary:
    """Summary of health metrics for a week."""
    week_start: date = field(default_factory=date.today)
    
    # Averages
    avg_sleep_hours: float = 0.0
    avg_sleep_quality: float = 0.0
    
    # Totals
    total_workouts: int = 0
    total_workout_minutes: int = 0
    total_calories_burned: int = 0
    
    # Streaks
    workout_streak: int = 0
    water_streak: int = 0
    sleep_streak: int = 0
    
    # Trends
    mood_trend: str = "stable"  # improving, declining, stable
    energy_trend: str = "stable"


@dataclass
class Exercise:
    """An exercise from the exercise database."""
    id: str = ""
    name: str = ""
    body_part: str = ""
    equipment: str = ""
    target_muscle: str = ""
    
    instructions: List[str] = field(default_factory=list)
    gif_url: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "body_part": self.body_part,
            "equipment": self.equipment,
            "target_muscle": self.target_muscle,
            "instructions": self.instructions,
        }


@dataclass
class BreathingExercise:
    """A breathing/relaxation exercise."""
    name: str
    description: str
    duration_minutes: int
    
    inhale_seconds: int = 4
    hold_seconds: int = 4
    exhale_seconds: int = 4
    
    instructions: List[str] = field(default_factory=list)
    
    @property
    def cycle_seconds(self) -> int:
        return self.inhale_seconds + self.hold_seconds + self.exhale_seconds


# Pre-defined breathing exercises
BREATHING_EXERCISES = [
    BreathingExercise(
        name="4-7-8 Breathing",
        description="Calming breath technique for stress relief",
        duration_minutes=5,
        inhale_seconds=4,
        hold_seconds=7,
        exhale_seconds=8,
        instructions=[
            "Sit comfortably with your back straight",
            "Place the tip of your tongue behind your upper front teeth",
            "Exhale completely through your mouth",
            "Inhale quietly through your nose for 4 seconds",
            "Hold your breath for 7 seconds",
            "Exhale completely through your mouth for 8 seconds",
            "Repeat the cycle 4 times",
        ],
    ),
    BreathingExercise(
        name="Box Breathing",
        description="Equal-ratio breathing for focus and calm",
        duration_minutes=4,
        inhale_seconds=4,
        hold_seconds=4,
        exhale_seconds=4,
        instructions=[
            "Sit upright in a comfortable position",
            "Slowly exhale all air from your lungs",
            "Inhale slowly through your nose for 4 seconds",
            "Hold your breath for 4 seconds",
            "Exhale slowly through your mouth for 4 seconds",
            "Hold empty for 4 seconds",
            "Repeat for 4 minutes",
        ],
    ),
    BreathingExercise(
        name="Quick Calm",
        description="Fast stress relief technique",
        duration_minutes=2,
        inhale_seconds=4,
        hold_seconds=2,
        exhale_seconds=6,
        instructions=[
            "Take a deep breath in for 4 seconds",
            "Hold briefly for 2 seconds",
            "Exhale slowly for 6 seconds",
            "Focus on making the exhale longer than inhale",
            "Repeat 5-6 times",
        ],
    ),
]


# RSF (UC Berkeley gym) schedule
RSF_HOURS = {
    "monday": ("6:00 AM", "11:00 PM"),
    "tuesday": ("6:00 AM", "11:00 PM"),
    "wednesday": ("6:00 AM", "11:00 PM"),
    "thursday": ("6:00 AM", "11:00 PM"),
    "friday": ("6:00 AM", "10:00 PM"),
    "saturday": ("9:00 AM", "9:00 PM"),
    "sunday": ("9:00 AM", "11:00 PM"),
}

# Campus dining halls
CAMPUS_DINING = {
    "crossroads": {
        "name": "Crossroads",
        "location": "Lower Sproul",
        "hours": "7:00 AM - 9:00 PM",
        "healthy_options": ["Salad bar", "Grilled proteins", "Fresh fruit"],
    },
    "cafe3": {
        "name": "Café 3",
        "location": "Unit 3",
        "hours": "7:00 AM - 9:00 PM",
        "healthy_options": ["Made-to-order stir fry", "Soup station"],
    },
    "foothill": {
        "name": "Foothill",
        "location": "Foothill",
        "hours": "7:00 AM - 8:00 PM",
        "healthy_options": ["Vegetarian options", "Whole grains"],
    },
}
