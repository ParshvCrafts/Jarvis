"""
Health Manager for JARVIS Health & Wellness Module.

Main orchestrator for health tracking, workouts, and wellness features.
"""

import os
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from .models import (
    Workout, WorkoutType, Intensity,
    SleepLog, Meal, MealType,
    MoodLog, WaterIntake, HealthGoals,
    DailyHealthSummary, WeeklyHealthSummary,
    Exercise, BreathingExercise, BREATHING_EXERCISES,
    RSF_HOURS, CAMPUS_DINING
)
from .tracker import HealthTracker


@dataclass
class HealthConfig:
    """Configuration for health manager."""
    db_path: str = "data/health.db"
    
    # Goals
    sleep_hours: float = 7.0
    water_glasses: int = 8
    workout_days: int = 4
    
    # Reminders
    water_reminder: bool = True
    stretch_reminder: bool = True
    sleep_reminder: bool = True
    
    # Campus
    campus_gym: str = "RSF"


class HealthManager:
    """
    Main manager for health and wellness functionality.
    
    Features:
    - Workout logging and suggestions
    - Sleep tracking
    - Meal/nutrition logging
    - Mood and stress tracking
    - Water intake reminders
    - Breathing exercises
    - Campus gym hours
    - Daily briefing integration
    """
    
    def __init__(
        self,
        config: Optional[HealthConfig] = None,
        llm_router: Optional[Any] = None,
    ):
        self.config = config or HealthConfig()
        self.llm_router = llm_router
        
        # Initialize tracker
        self.tracker = HealthTracker(db_path=self.config.db_path)
        
        logger.info("Health Manager initialized")
    
    # =========================================================================
    # Workout Logging
    # =========================================================================
    
    def log_workout(
        self,
        workout_type: str,
        duration: int,
        intensity: str = "medium",
        distance: Optional[float] = None,
        notes: str = "",
    ) -> str:
        """
        Log a workout.
        
        Args:
            workout_type: Type of workout (running, weights, yoga, etc.)
            duration: Duration in minutes
            intensity: low, medium, or high
            distance: Distance in miles (for cardio)
            notes: Additional notes
        """
        # Parse workout type
        type_map = {
            "run": WorkoutType.RUNNING,
            "running": WorkoutType.RUNNING,
            "ran": WorkoutType.RUNNING,
            "walk": WorkoutType.WALKING,
            "walking": WorkoutType.WALKING,
            "walked": WorkoutType.WALKING,
            "bike": WorkoutType.CYCLING,
            "cycling": WorkoutType.CYCLING,
            "biked": WorkoutType.CYCLING,
            "swim": WorkoutType.SWIMMING,
            "swimming": WorkoutType.SWIMMING,
            "swam": WorkoutType.SWIMMING,
            "weights": WorkoutType.WEIGHTS,
            "lifting": WorkoutType.WEIGHTS,
            "gym": WorkoutType.WEIGHTS,
            "hiit": WorkoutType.HIIT,
            "yoga": WorkoutType.YOGA,
            "stretch": WorkoutType.STRETCHING,
            "stretching": WorkoutType.STRETCHING,
            "cardio": WorkoutType.CARDIO,
            "sports": WorkoutType.SPORTS,
        }
        wtype = type_map.get(workout_type.lower(), WorkoutType.OTHER)
        
        # Parse intensity
        intensity_map = {
            "low": Intensity.LOW,
            "easy": Intensity.LOW,
            "light": Intensity.LOW,
            "medium": Intensity.MEDIUM,
            "moderate": Intensity.MEDIUM,
            "high": Intensity.HIGH,
            "hard": Intensity.HIGH,
            "intense": Intensity.HIGH,
        }
        wintensity = intensity_map.get(intensity.lower(), Intensity.MEDIUM)
        
        # Estimate calories
        calories = self._estimate_calories(wtype, duration, wintensity)
        
        workout = Workout(
            date=date.today(),
            workout_type=wtype,
            duration_minutes=duration,
            intensity=wintensity,
            distance_miles=distance,
            calories_burned=calories,
            notes=notes,
        )
        
        success = self.tracker.log_workout(workout)
        
        if success:
            streak = self.tracker.get_workout_streak()
            return (
                f"✅ Logged: {wtype.value.title()} for {duration} minutes\n"
                f"   Estimated calories: {calories}\n"
                f"   🔥 Workout streak: {streak} days"
            )
        
        return "❌ Failed to log workout"
    
    def _estimate_calories(
        self,
        workout_type: WorkoutType,
        duration: int,
        intensity: Intensity,
    ) -> int:
        """Estimate calories burned."""
        # Calories per minute by workout type (moderate intensity)
        base_rates = {
            WorkoutType.RUNNING: 11,
            WorkoutType.WALKING: 5,
            WorkoutType.CYCLING: 8,
            WorkoutType.SWIMMING: 10,
            WorkoutType.WEIGHTS: 6,
            WorkoutType.HIIT: 12,
            WorkoutType.YOGA: 4,
            WorkoutType.STRETCHING: 3,
            WorkoutType.CARDIO: 9,
            WorkoutType.SPORTS: 8,
            WorkoutType.OTHER: 6,
        }
        
        base = base_rates.get(workout_type, 6)
        
        # Adjust for intensity
        multipliers = {
            Intensity.LOW: 0.7,
            Intensity.MEDIUM: 1.0,
            Intensity.HIGH: 1.3,
        }
        multiplier = multipliers.get(intensity, 1.0)
        
        return int(base * duration * multiplier)
    
    def get_workout_suggestions(self, duration: int = 30) -> str:
        """Get workout suggestions based on history."""
        workouts = self.tracker.get_workouts(limit=10)
        
        # Analyze recent workouts
        recent_types = [w.workout_type for w in workouts]
        
        suggestions = []
        
        # Suggest variety
        if recent_types.count(WorkoutType.RUNNING) >= 3:
            suggestions.append("🏋️ Try weights or yoga for variety")
        elif recent_types.count(WorkoutType.WEIGHTS) >= 3:
            suggestions.append("🏃 Add some cardio for balance")
        
        # Quick workout suggestions
        quick_workouts = [
            f"🏃 {duration}-min jog around campus",
            f"🏋️ {duration}-min bodyweight circuit",
            f"🧘 {duration}-min yoga flow",
            f"🚴 {duration}-min stationary bike at RSF",
        ]
        
        lines = ["💪 **Workout Suggestions:**", ""]
        lines.extend(suggestions if suggestions else quick_workouts[:3])
        
        return "\n".join(lines)
    
    # =========================================================================
    # Sleep Logging
    # =========================================================================
    
    def log_sleep(
        self,
        hours: float,
        quality: Optional[int] = None,
        notes: str = "",
    ) -> str:
        """Log sleep hours."""
        # Auto-calculate quality based on hours
        if quality is None:
            goals = self.tracker.get_goals()
            if hours >= goals.sleep_hours:
                quality = 8
            elif hours >= goals.sleep_hours - 1:
                quality = 6
            else:
                quality = 4
        
        sleep_log = SleepLog(
            date=date.today(),
            duration_hours=hours,
            quality=quality,
            notes=notes,
        )
        
        success = self.tracker.log_sleep(sleep_log)
        
        if success:
            goals = self.tracker.get_goals()
            goal_met = "✅" if hours >= goals.sleep_hours else "⚠️"
            avg = self.tracker.get_avg_sleep(7)
            
            return (
                f"{goal_met} Logged: {hours} hours of sleep\n"
                f"   Quality: {quality}/10\n"
                f"   7-day average: {avg:.1f} hours"
            )
        
        return "❌ Failed to log sleep"
    
    # =========================================================================
    # Meal Logging
    # =========================================================================
    
    def log_meal(
        self,
        description: str,
        meal_type: str = "snack",
        calories: Optional[int] = None,
    ) -> str:
        """Log a meal."""
        # Parse meal type
        type_map = {
            "breakfast": MealType.BREAKFAST,
            "lunch": MealType.LUNCH,
            "dinner": MealType.DINNER,
            "snack": MealType.SNACK,
        }
        mtype = type_map.get(meal_type.lower(), MealType.SNACK)
        
        meal = Meal(
            date=date.today(),
            meal_type=mtype,
            description=description,
            calories=calories,
            time=datetime.now().time(),
        )
        
        success = self.tracker.log_meal(meal)
        
        if success:
            daily_cals = self.tracker.get_daily_calories()
            cal_str = f" (~{calories} cal)" if calories else ""
            
            return (
                f"✅ Logged {mtype.value}: {description}{cal_str}\n"
                f"   Today's total: {daily_cals} calories"
            )
        
        return "❌ Failed to log meal"
    
    # =========================================================================
    # Water Tracking
    # =========================================================================
    
    def log_water(self, glasses: int = 1) -> str:
        """Log water intake."""
        total = self.tracker.log_water(glasses)
        goals = self.tracker.get_goals()
        
        remaining = max(0, goals.water_glasses - total)
        progress = min(100, int((total / goals.water_glasses) * 100))
        
        bar = "█" * (progress // 10) + "░" * (10 - progress // 10)
        
        if remaining == 0:
            return f"💧 Water: {total} glasses [{bar}] 100% ✅ Goal met!"
        
        return f"💧 Water: {total} glasses [{bar}] {progress}% ({remaining} more to goal)"
    
    # =========================================================================
    # Mood & Stress
    # =========================================================================
    
    def log_mood(
        self,
        mood: int,
        stress: int = 5,
        notes: str = "",
    ) -> str:
        """Log mood and stress levels."""
        mood_log = MoodLog(
            date=date.today(),
            time=datetime.now().time(),
            mood=max(1, min(10, mood)),
            stress=max(1, min(10, stress)),
            notes=notes,
        )
        
        success = self.tracker.log_mood(mood_log)
        
        if success:
            mood_emoji = "😊" if mood >= 7 else "😐" if mood >= 4 else "😔"
            stress_emoji = "😌" if stress <= 3 else "😰" if stress >= 7 else "😐"
            
            return (
                f"Logged: Mood {mood}/10 {mood_emoji}, Stress {stress}/10 {stress_emoji}"
            )
        
        return "❌ Failed to log mood"
    
    def get_stress_relief(self) -> str:
        """Get stress relief suggestions."""
        lines = [
            "🧘 **Stress Relief Options:**",
            "",
            "**Quick Options:**",
            "  1. 5-minute breathing exercise (say 'breathing exercise')",
            "  2. Quick walk outside (15 min)",
            "  3. Desk stretches",
            "",
            "**Campus Resources:**",
            "  - CAPS: Free counseling (510-642-9494)",
            "  - RSF: Yoga classes",
            "  - Meditation room: MLK building",
            "",
            "Remember: You've got this! 💪",
        ]
        
        return "\n".join(lines)
    
    def get_breathing_exercise(self, exercise_name: Optional[str] = None) -> str:
        """Get a breathing exercise."""
        if exercise_name:
            exercise = next(
                (e for e in BREATHING_EXERCISES if exercise_name.lower() in e.name.lower()),
                BREATHING_EXERCISES[0]
            )
        else:
            exercise = BREATHING_EXERCISES[0]  # Default to 4-7-8
        
        lines = [
            f"🧘 **{exercise.name}**",
            f"*{exercise.description}*",
            "",
            "**Instructions:**",
        ]
        
        for i, instruction in enumerate(exercise.instructions, 1):
            lines.append(f"  {i}. {instruction}")
        
        lines.extend([
            "",
            f"Duration: {exercise.duration_minutes} minutes",
            f"Pattern: Inhale {exercise.inhale_seconds}s → Hold {exercise.hold_seconds}s → Exhale {exercise.exhale_seconds}s",
        ])
        
        return "\n".join(lines)
    
    # =========================================================================
    # Campus Features
    # =========================================================================
    
    def get_gym_hours(self, day: Optional[str] = None) -> str:
        """Get RSF gym hours."""
        if day is None:
            day = date.today().strftime("%A").lower()
        else:
            day = day.lower()
        
        hours = RSF_HOURS.get(day)
        
        if hours:
            return f"🏋️ **RSF Hours ({day.title()}):** {hours[0]} - {hours[1]}"
        
        # Show all hours
        lines = ["🏋️ **RSF Hours:**", ""]
        for d, h in RSF_HOURS.items():
            lines.append(f"  {d.title()}: {h[0]} - {h[1]}")
        
        return "\n".join(lines)
    
    def get_dining_info(self, hall: Optional[str] = None) -> str:
        """Get campus dining information."""
        if hall:
            hall_key = hall.lower().replace(" ", "")
            info = CAMPUS_DINING.get(hall_key)
            
            if info:
                lines = [
                    f"🍽️ **{info['name']}**",
                    f"📍 {info['location']}",
                    f"🕐 {info['hours']}",
                    "",
                    "**Healthy Options:**",
                ]
                for option in info['healthy_options']:
                    lines.append(f"  - {option}")
                
                return "\n".join(lines)
        
        # Show all dining halls
        lines = ["🍽️ **Campus Dining:**", ""]
        for key, info in CAMPUS_DINING.items():
            lines.append(f"  **{info['name']}** ({info['location']})")
            lines.append(f"    Hours: {info['hours']}")
        
        return "\n".join(lines)
    
    # =========================================================================
    # Summaries
    # =========================================================================
    
    def get_daily_summary(self) -> str:
        """Get today's health summary."""
        summary = self.tracker.get_daily_summary()
        goals = self.tracker.get_goals()
        
        lines = [
            "🏃 **Today's Health Summary:**",
            "",
        ]
        
        # Sleep
        if summary.sleep_hours > 0:
            sleep_icon = "✅" if summary.sleep_goal_met else "⚠️"
            lines.append(f"{sleep_icon} Sleep: {summary.sleep_hours:.1f}h (goal: {goals.sleep_hours}h)")
        else:
            lines.append("😴 Sleep: Not logged")
        
        # Workouts
        if summary.workouts:
            lines.append(f"💪 Workouts: {len(summary.workouts)} ({summary.total_workout_minutes} min)")
        else:
            lines.append("💪 Workouts: None logged")
        
        # Calories
        if summary.total_calories > 0:
            lines.append(f"🍽️ Calories: {summary.total_calories}")
        
        # Water
        water_icon = "✅" if summary.water_goal_met else "💧"
        lines.append(f"{water_icon} Water: {summary.water_glasses}/{goals.water_glasses} glasses")
        
        # Mood
        if summary.avg_mood > 0:
            mood_emoji = "😊" if summary.avg_mood >= 7 else "😐" if summary.avg_mood >= 4 else "😔"
            lines.append(f"{mood_emoji} Mood: {summary.avg_mood:.0f}/10")
        
        return "\n".join(lines)
    
    def get_weekly_summary(self) -> str:
        """Get weekly health summary."""
        summary = self.tracker.get_weekly_summary()
        
        lines = [
            "📊 **This Week's Health Summary:**",
            "",
            f"😴 Avg Sleep: {summary.avg_sleep_hours:.1f} hours",
            f"💪 Workouts: {summary.total_workouts} ({summary.total_workout_minutes} min total)",
            f"🔥 Calories Burned: {summary.total_calories_burned}",
            f"🏆 Workout Streak: {summary.workout_streak} days",
        ]
        
        return "\n".join(lines)
    
    def get_briefing_summary(self) -> str:
        """Get health summary for daily briefing."""
        summary = self.tracker.get_daily_summary(date.today() - timedelta(days=1))
        goals = self.tracker.get_goals()
        streak = self.tracker.get_workout_streak()
        
        lines = []
        
        # Sleep from last night
        if summary.sleep_hours > 0:
            if summary.sleep_hours < goals.sleep_hours - 1:
                lines.append(f"😴 You slept {summary.sleep_hours:.1f}h (target: {goals.sleep_hours}h)")
        
        # Workout reminder
        if streak == 0:
            lines.append("💪 No workout logged yesterday")
        elif streak >= 3:
            lines.append(f"🔥 {streak}-day workout streak!")
        
        # Gym hours
        today = date.today().strftime("%A").lower()
        hours = RSF_HOURS.get(today, ("6:00 AM", "11:00 PM"))
        lines.append(f"🏋️ RSF opens at {hours[0]} today")
        
        return "\n".join(lines) if lines else ""
    
    # =========================================================================
    # Voice Command Handler
    # =========================================================================
    
    async def handle_command(self, command: str) -> str:
        """Handle voice commands for health."""
        command_lower = command.lower()
        
        # Log workout
        if any(kw in command_lower for kw in ["log workout", "logged workout", "worked out", "ran", "walked", "biked"]):
            # Parse workout details
            # "Log workout: ran 2 miles" or "Ran 30 minutes"
            
            # Extract duration
            duration_match = re.search(r'(\d+)\s*(?:min|minutes?|mins?)', command_lower)
            duration = int(duration_match.group(1)) if duration_match else 30
            
            # Extract distance
            distance_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:miles?|mi)', command_lower)
            distance = float(distance_match.group(1)) if distance_match else None
            
            # Determine workout type
            workout_type = "other"
            for wtype in ["ran", "run", "running", "walk", "walked", "bike", "biked", "swim", "swam", "yoga", "weights", "gym", "hiit"]:
                if wtype in command_lower:
                    workout_type = wtype
                    break
            
            # If distance given but no duration, estimate duration
            if distance and not duration_match:
                if "ran" in command_lower or "run" in command_lower:
                    duration = int(distance * 10)  # ~10 min/mile
                elif "walk" in command_lower:
                    duration = int(distance * 18)  # ~18 min/mile
            
            return self.log_workout(workout_type, duration, distance=distance)
        
        # Log sleep
        if "slept" in command_lower or "sleep" in command_lower:
            hours_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)', command_lower)
            if hours_match:
                hours = float(hours_match.group(1))
                return self.log_sleep(hours)
            return "Please specify hours: 'Slept 7 hours'"
        
        # Log meal
        if any(kw in command_lower for kw in ["log breakfast", "log lunch", "log dinner", "log snack", "ate", "had for"]):
            # Determine meal type
            meal_type = "snack"
            for mtype in ["breakfast", "lunch", "dinner", "snack"]:
                if mtype in command_lower:
                    meal_type = mtype
                    break
            
            # Extract description
            desc_match = re.search(r'(?:log\s+\w+[:\s]+|ate\s+|had\s+)(.+)', command_lower)
            description = desc_match.group(1).strip() if desc_match else command_lower
            
            return self.log_meal(description, meal_type)
        
        # Log water
        if "water" in command_lower or "drank" in command_lower:
            glasses_match = re.search(r'(\d+)\s*(?:glasses?|cups?)', command_lower)
            glasses = int(glasses_match.group(1)) if glasses_match else 1
            return self.log_water(glasses)
        
        # Calories today
        if "calories" in command_lower and "today" in command_lower:
            cals = self.tracker.get_daily_calories()
            return f"🍽️ Today's calories: {cals}"
        
        # Workout suggestions
        if "suggest" in command_lower and "workout" in command_lower:
            return self.get_workout_suggestions()
        
        # RSF hours
        if "rsf" in command_lower or ("gym" in command_lower and ("hour" in command_lower or "open" in command_lower)):
            return self.get_gym_hours()
        
        # Stress relief
        if "stress" in command_lower or "relax" in command_lower or "anxious" in command_lower:
            return self.get_stress_relief()
        
        # Breathing exercise
        if "breath" in command_lower:
            return self.get_breathing_exercise()
        
        # Health stats / summary
        if any(kw in command_lower for kw in ["health stats", "health summary", "my health"]):
            if "week" in command_lower:
                return self.get_weekly_summary()
            return self.get_daily_summary()
        
        # Dining
        if "dining" in command_lower or "cafeteria" in command_lower:
            return self.get_dining_info()
        
        return (
            "Health commands:\n"
            "  - 'Log workout: ran 2 miles'\n"
            "  - 'Slept 7 hours'\n"
            "  - 'Log breakfast: oatmeal'\n"
            "  - 'Drank 2 glasses water'\n"
            "  - 'How many calories today?'\n"
            "  - 'When is RSF open?'\n"
            "  - 'I'm stressed, help me relax'\n"
            "  - 'My health stats'"
        )
    
    # =========================================================================
    # Status
    # =========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get health module status."""
        summary = self.tracker.get_daily_summary()
        goals = self.tracker.get_goals()
        
        return {
            "sleep_logged": summary.sleep_hours > 0,
            "workout_logged": len(summary.workouts) > 0,
            "water_progress": f"{summary.water_glasses}/{goals.water_glasses}",
            "streak": self.tracker.get_workout_streak(),
        }
    
    def get_status_summary(self) -> str:
        """Get formatted status summary."""
        status = self.get_status()
        
        lines = [
            "🏃 **Health Module Status**",
            "",
            f"😴 Sleep logged today: {'✅' if status['sleep_logged'] else '❌'}",
            f"💪 Workout logged today: {'✅' if status['workout_logged'] else '❌'}",
            f"💧 Water: {status['water_progress']} glasses",
            f"🔥 Workout streak: {status['streak']} days",
        ]
        
        return "\n".join(lines)
