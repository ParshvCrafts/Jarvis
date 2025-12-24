"""
Health Tracker for JARVIS Health & Wellness Module.

SQLite-based tracking for workouts, sleep, nutrition, and mood.
"""

import sqlite3
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .models import (
    Workout, WorkoutType, Intensity,
    SleepLog, Meal, MealType,
    MoodLog, WaterIntake, HealthGoals,
    DailyHealthSummary, WeeklyHealthSummary
)


class HealthTracker:
    """
    SQLite-based health tracking.
    
    Features:
    - Workout logging and history
    - Sleep tracking
    - Meal/nutrition logging
    - Mood and stress tracking
    - Water intake
    - Daily and weekly summaries
    """
    
    def __init__(self, db_path: str = "data/health.db"):
        self.db_path = db_path
        self._init_db()
        logger.info(f"Health tracker initialized: {db_path}")
    
    def _init_db(self):
        """Initialize the database schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS workouts (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                workout_type TEXT NOT NULL,
                duration_minutes INTEGER,
                intensity TEXT,
                distance_miles REAL,
                calories_burned INTEGER,
                heart_rate_avg INTEGER,
                exercises TEXT,
                notes TEXT,
                start_time TEXT,
                end_time TEXT,
                created_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS sleep_logs (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL UNIQUE,
                bedtime TEXT,
                wake_time TEXT,
                duration_hours REAL,
                quality INTEGER,
                deep_sleep_hours REAL,
                rem_sleep_hours REAL,
                awakenings INTEGER,
                notes TEXT,
                created_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS meals (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                meal_type TEXT NOT NULL,
                time TEXT,
                description TEXT,
                calories INTEGER,
                protein_g REAL,
                carbs_g REAL,
                fat_g REAL,
                fiber_g REAL,
                location TEXT,
                created_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS mood_logs (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                time TEXT,
                mood INTEGER,
                energy INTEGER,
                stress INTEGER,
                notes TEXT,
                triggers TEXT,
                created_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS water_intake (
                date TEXT PRIMARY KEY,
                glasses INTEGER DEFAULT 0,
                updated_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS health_goals (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                sleep_hours REAL DEFAULT 7,
                water_glasses INTEGER DEFAULT 8,
                workout_days INTEGER DEFAULT 4,
                daily_steps INTEGER DEFAULT 10000,
                daily_calories INTEGER,
                updated_at TEXT
            );
            
            INSERT OR IGNORE INTO health_goals (id) VALUES (1);
            
            CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts(date);
            CREATE INDEX IF NOT EXISTS idx_meals_date ON meals(date);
            CREATE INDEX IF NOT EXISTS idx_mood_date ON mood_logs(date);
        """)
        
        conn.commit()
        conn.close()
    
    # =========================================================================
    # Workouts
    # =========================================================================
    
    def log_workout(self, workout: Workout) -> bool:
        """Log a workout."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO workouts 
                (id, date, workout_type, duration_minutes, intensity, distance_miles,
                 calories_burned, heart_rate_avg, exercises, notes, start_time, end_time, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                workout.id,
                workout.date.isoformat(),
                workout.workout_type.value,
                workout.duration_minutes,
                workout.intensity.value,
                workout.distance_miles,
                workout.calories_burned,
                workout.heart_rate_avg,
                ",".join(workout.exercises),
                workout.notes,
                workout.start_time.isoformat() if workout.start_time else None,
                workout.end_time.isoformat() if workout.end_time else None,
                datetime.now().isoformat(),
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Logged workout: {workout.workout_type.value} for {workout.duration_minutes} min")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log workout: {e}")
            return False
    
    def get_workouts(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10,
    ) -> List[Workout]:
        """Get workout history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM workouts"
        params = []
        
        if start_date and end_date:
            query += " WHERE date BETWEEN ? AND ?"
            params = [start_date.isoformat(), end_date.isoformat()]
        elif start_date:
            query += " WHERE date >= ?"
            params = [start_date.isoformat()]
        
        query += " ORDER BY date DESC, start_time DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        workouts = []
        for row in rows:
            workout = Workout(
                id=row[0],
                date=date.fromisoformat(row[1]),
                workout_type=WorkoutType(row[2]),
                duration_minutes=row[3] or 0,
                intensity=Intensity(row[4]) if row[4] else Intensity.MEDIUM,
                distance_miles=row[5],
                calories_burned=row[6],
                heart_rate_avg=row[7],
                exercises=row[8].split(",") if row[8] else [],
                notes=row[9] or "",
            )
            workouts.append(workout)
        
        return workouts
    
    def get_workout_streak(self) -> int:
        """Get current workout streak (consecutive days with workouts)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT date FROM workouts 
            ORDER BY date DESC
        """)
        
        dates = [date.fromisoformat(row[0]) for row in cursor.fetchall()]
        conn.close()
        
        if not dates:
            return 0
        
        streak = 0
        expected_date = date.today()
        
        for workout_date in dates:
            if workout_date == expected_date:
                streak += 1
                expected_date -= timedelta(days=1)
            elif workout_date < expected_date:
                break
        
        return streak
    
    # =========================================================================
    # Sleep
    # =========================================================================
    
    def log_sleep(self, sleep_log: SleepLog) -> bool:
        """Log sleep for a night."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO sleep_logs
                (id, date, bedtime, wake_time, duration_hours, quality,
                 deep_sleep_hours, rem_sleep_hours, awakenings, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sleep_log.id,
                sleep_log.date.isoformat(),
                sleep_log.bedtime.isoformat() if sleep_log.bedtime else None,
                sleep_log.wake_time.isoformat() if sleep_log.wake_time else None,
                sleep_log.duration_hours,
                sleep_log.quality,
                sleep_log.deep_sleep_hours,
                sleep_log.rem_sleep_hours,
                sleep_log.awakenings,
                sleep_log.notes,
                datetime.now().isoformat(),
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Logged sleep: {sleep_log.duration_hours} hours")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log sleep: {e}")
            return False
    
    def get_sleep_logs(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 7,
    ) -> List[SleepLog]:
        """Get sleep history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM sleep_logs"
        params = []
        
        if start_date and end_date:
            query += " WHERE date BETWEEN ? AND ?"
            params = [start_date.isoformat(), end_date.isoformat()]
        
        query += " ORDER BY date DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        logs = []
        for row in rows:
            log = SleepLog(
                id=row[0],
                date=date.fromisoformat(row[1]),
                bedtime=time.fromisoformat(row[2]) if row[2] else None,
                wake_time=time.fromisoformat(row[3]) if row[3] else None,
                duration_hours=row[4] or 0,
                quality=row[5] or 5,
                deep_sleep_hours=row[6],
                rem_sleep_hours=row[7],
                awakenings=row[8] or 0,
                notes=row[9] or "",
            )
            logs.append(log)
        
        return logs
    
    def get_avg_sleep(self, days: int = 7) -> float:
        """Get average sleep hours over past N days."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start = (date.today() - timedelta(days=days)).isoformat()
        cursor.execute("""
            SELECT AVG(duration_hours) FROM sleep_logs
            WHERE date >= ?
        """, (start,))
        
        result = cursor.fetchone()[0]
        conn.close()
        
        return result or 0.0
    
    # =========================================================================
    # Meals
    # =========================================================================
    
    def log_meal(self, meal: Meal) -> bool:
        """Log a meal."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO meals
                (id, date, meal_type, time, description, calories, protein_g,
                 carbs_g, fat_g, fiber_g, location, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                meal.id,
                meal.date.isoformat(),
                meal.meal_type.value,
                meal.time.isoformat() if meal.time else None,
                meal.description,
                meal.calories,
                meal.protein_g,
                meal.carbs_g,
                meal.fat_g,
                meal.fiber_g,
                meal.location,
                datetime.now().isoformat(),
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Logged meal: {meal.description}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log meal: {e}")
            return False
    
    def get_meals(
        self,
        target_date: Optional[date] = None,
        limit: int = 10,
    ) -> List[Meal]:
        """Get meals for a date or recent meals."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if target_date:
            cursor.execute(
                "SELECT * FROM meals WHERE date = ? ORDER BY time",
                (target_date.isoformat(),)
            )
        else:
            cursor.execute(
                "SELECT * FROM meals ORDER BY date DESC, time DESC LIMIT ?",
                (limit,)
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        meals = []
        for row in rows:
            meal = Meal(
                id=row[0],
                date=date.fromisoformat(row[1]),
                meal_type=MealType(row[2]),
                time=time.fromisoformat(row[3]) if row[3] else None,
                description=row[4] or "",
                calories=row[5],
                protein_g=row[6],
                carbs_g=row[7],
                fat_g=row[8],
                fiber_g=row[9],
                location=row[10] or "",
            )
            meals.append(meal)
        
        return meals
    
    def get_daily_calories(self, target_date: Optional[date] = None) -> int:
        """Get total calories for a day."""
        target = target_date or date.today()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT SUM(calories) FROM meals WHERE date = ?
        """, (target.isoformat(),))
        
        result = cursor.fetchone()[0]
        conn.close()
        
        return result or 0
    
    # =========================================================================
    # Mood
    # =========================================================================
    
    def log_mood(self, mood_log: MoodLog) -> bool:
        """Log mood/stress."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO mood_logs
                (id, date, time, mood, energy, stress, notes, triggers, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mood_log.id,
                mood_log.date.isoformat(),
                mood_log.time.isoformat() if mood_log.time else None,
                mood_log.mood,
                mood_log.energy,
                mood_log.stress,
                mood_log.notes,
                ",".join(mood_log.triggers),
                datetime.now().isoformat(),
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Logged mood: {mood_log.mood}/10, stress: {mood_log.stress}/10")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log mood: {e}")
            return False
    
    def get_mood_logs(self, days: int = 7) -> List[MoodLog]:
        """Get recent mood logs."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start = (date.today() - timedelta(days=days)).isoformat()
        cursor.execute("""
            SELECT * FROM mood_logs WHERE date >= ? ORDER BY date DESC, time DESC
        """, (start,))
        
        rows = cursor.fetchall()
        conn.close()
        
        logs = []
        for row in rows:
            log = MoodLog(
                id=row[0],
                date=date.fromisoformat(row[1]),
                time=time.fromisoformat(row[2]) if row[2] else None,
                mood=row[3] or 5,
                energy=row[4] or 5,
                stress=row[5] or 5,
                notes=row[6] or "",
                triggers=row[7].split(",") if row[7] else [],
            )
            logs.append(log)
        
        return logs
    
    # =========================================================================
    # Water
    # =========================================================================
    
    def log_water(self, glasses: int = 1, target_date: Optional[date] = None) -> int:
        """Add water intake. Returns new total."""
        target = target_date or date.today()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current
        cursor.execute("SELECT glasses FROM water_intake WHERE date = ?", (target.isoformat(),))
        row = cursor.fetchone()
        current = row[0] if row else 0
        
        new_total = current + glasses
        
        cursor.execute("""
            INSERT OR REPLACE INTO water_intake (date, glasses, updated_at)
            VALUES (?, ?, ?)
        """, (target.isoformat(), new_total, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Water intake: {new_total} glasses today")
        return new_total
    
    def get_water_intake(self, target_date: Optional[date] = None) -> int:
        """Get water intake for a day."""
        target = target_date or date.today()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT glasses FROM water_intake WHERE date = ?", (target.isoformat(),))
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else 0
    
    # =========================================================================
    # Goals
    # =========================================================================
    
    def get_goals(self) -> HealthGoals:
        """Get health goals."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM health_goals WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return HealthGoals(
                sleep_hours=row[1] or 7,
                water_glasses=row[2] or 8,
                workout_days_per_week=row[3] or 4,
                daily_steps=row[4] or 10000,
                daily_calories=row[5],
            )
        
        return HealthGoals()
    
    def update_goals(self, goals: HealthGoals) -> bool:
        """Update health goals."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE health_goals SET
                    sleep_hours = ?,
                    water_glasses = ?,
                    workout_days = ?,
                    daily_steps = ?,
                    daily_calories = ?,
                    updated_at = ?
                WHERE id = 1
            """, (
                goals.sleep_hours,
                goals.water_glasses,
                goals.workout_days_per_week,
                goals.daily_steps,
                goals.daily_calories,
                datetime.now().isoformat(),
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update goals: {e}")
            return False
    
    # =========================================================================
    # Summaries
    # =========================================================================
    
    def get_daily_summary(self, target_date: Optional[date] = None) -> DailyHealthSummary:
        """Get health summary for a day."""
        target = target_date or date.today()
        goals = self.get_goals()
        
        summary = DailyHealthSummary(date=target)
        
        # Sleep
        sleep_logs = self.get_sleep_logs(start_date=target, end_date=target, limit=1)
        if sleep_logs:
            summary.sleep_hours = sleep_logs[0].duration_hours
            summary.sleep_quality = sleep_logs[0].quality
            summary.sleep_goal_met = summary.sleep_hours >= goals.sleep_hours
        
        # Workouts
        summary.workouts = self.get_workouts(start_date=target, end_date=target, limit=10)
        summary.total_workout_minutes = sum(w.duration_minutes for w in summary.workouts)
        summary.calories_burned = sum(w.calories_burned or 0 for w in summary.workouts)
        summary.workout_done = len(summary.workouts) > 0
        
        # Meals
        summary.meals = self.get_meals(target_date=target)
        summary.total_calories = sum(m.calories or 0 for m in summary.meals)
        summary.total_protein = sum(m.protein_g or 0 for m in summary.meals)
        
        # Water
        summary.water_glasses = self.get_water_intake(target)
        summary.water_goal_met = summary.water_glasses >= goals.water_glasses
        
        # Mood
        mood_logs = [m for m in self.get_mood_logs(days=1) if m.date == target]
        if mood_logs:
            summary.avg_mood = sum(m.mood for m in mood_logs) / len(mood_logs)
            summary.avg_stress = sum(m.stress for m in mood_logs) / len(mood_logs)
        
        return summary
    
    def get_weekly_summary(self) -> WeeklyHealthSummary:
        """Get health summary for the past week."""
        today = date.today()
        week_start = today - timedelta(days=6)
        
        summary = WeeklyHealthSummary(week_start=week_start)
        
        # Sleep averages
        sleep_logs = self.get_sleep_logs(start_date=week_start, end_date=today, limit=7)
        if sleep_logs:
            summary.avg_sleep_hours = sum(s.duration_hours for s in sleep_logs) / len(sleep_logs)
            summary.avg_sleep_quality = sum(s.quality for s in sleep_logs) / len(sleep_logs)
        
        # Workout totals
        workouts = self.get_workouts(start_date=week_start, end_date=today, limit=50)
        summary.total_workouts = len(workouts)
        summary.total_workout_minutes = sum(w.duration_minutes for w in workouts)
        summary.total_calories_burned = sum(w.calories_burned or 0 for w in workouts)
        
        # Streaks
        summary.workout_streak = self.get_workout_streak()
        
        return summary
