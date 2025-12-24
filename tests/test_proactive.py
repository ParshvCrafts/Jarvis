"""
Tests for proactive intelligence module.
"""

import pytest
import tempfile
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestLocation:
    """Tests for Location class."""
    
    def test_distance_calculation(self):
        """Test distance calculation between locations."""
        from src.proactive.intelligence import Location
        
        # New York City
        nyc = Location(latitude=40.7128, longitude=-74.0060)
        
        # Los Angeles
        la = Location(latitude=34.0522, longitude=-118.2437)
        
        distance = nyc.distance_to(la)
        
        # Should be approximately 3940 km
        assert 3900000 < distance < 4000000  # meters


class TestGeoZone:
    """Tests for GeoZone class."""
    
    def test_zone_contains(self):
        """Test zone containment check."""
        from src.proactive.intelligence import Location, GeoZone
        
        # Create a zone at origin with 1000m radius
        center = Location(latitude=0.0, longitude=0.0)
        zone = GeoZone(
            zone_id="test",
            name="Test Zone",
            center=center,
            radius=1000,
        )
        
        # Point inside zone
        inside = Location(latitude=0.001, longitude=0.001)
        assert zone.contains(inside)
        
        # Point outside zone
        outside = Location(latitude=1.0, longitude=1.0)
        assert not zone.contains(outside)


class TestGeofenceManager:
    """Tests for GeofenceManager."""
    
    def test_add_zone(self):
        """Test adding a zone."""
        from src.proactive.intelligence import GeofenceManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GeofenceManager(Path(tmpdir) / "geo.db")
            
            zone = manager.add_zone(
                zone_id="home",
                name="Home",
                latitude=40.7128,
                longitude=-74.0060,
                radius=100,
            )
            
            assert zone.zone_id == "home"
            assert zone.name == "Home"
            assert zone.radius == 100
    
    def test_zone_transitions(self):
        """Test zone entry/exit detection."""
        from src.proactive.intelligence import GeofenceManager, Location, ZoneEvent
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GeofenceManager(Path(tmpdir) / "geo.db")
            
            # Add home zone
            manager.add_zone(
                zone_id="home",
                name="Home",
                latitude=0.0,
                longitude=0.0,
                radius=1000,
            )
            
            # Enter zone
            location = Location(latitude=0.001, longitude=0.001)
            transitions = manager.update_location(location)
            
            assert len(transitions) == 1
            assert transitions[0].event == ZoneEvent.ENTER
            assert transitions[0].zone.zone_id == "home"
            
            # Exit zone
            location = Location(latitude=1.0, longitude=1.0)
            transitions = manager.update_location(location)
            
            assert len(transitions) == 1
            assert transitions[0].event == ZoneEvent.EXIT


class TestRoutineLearner:
    """Tests for RoutineLearner."""
    
    def test_log_command(self):
        """Test logging commands."""
        from src.proactive.intelligence import RoutineLearner
        
        with tempfile.TemporaryDirectory() as tmpdir:
            learner = RoutineLearner(Path(tmpdir) / "routines.db")
            
            # Log some commands
            learner.log_command("turn on the lights")
            learner.log_command("what's the weather")
            
            # Should not error
            patterns = learner.get_patterns(min_count=1)
            assert isinstance(patterns, list)
    
    def test_pattern_detection(self):
        """Test pattern detection."""
        from src.proactive.intelligence import RoutineLearner
        
        with tempfile.TemporaryDirectory() as tmpdir:
            learner = RoutineLearner(Path(tmpdir) / "routines.db")
            
            # Log same command multiple times
            for _ in range(5):
                learner.log_command("turn on the lights")
            
            patterns = learner.get_patterns(min_count=3)
            
            # Should detect the pattern
            assert len(patterns) >= 1


class TestContextAwareness:
    """Tests for ContextAwareness."""
    
    def test_greeting(self):
        """Test time-appropriate greeting."""
        from src.proactive.intelligence import ContextAwareness
        
        context = ContextAwareness()
        greeting = context.get_greeting()
        
        # Should return a valid greeting
        assert greeting in ["Good morning", "Good afternoon", "Good evening", "Hello"]
    
    def test_context_info(self):
        """Test context information."""
        from src.proactive.intelligence import ContextAwareness
        
        context = ContextAwareness()
        info = context.get_context()
        
        assert "time_of_day" in info
        assert "day_of_week" in info
        assert "is_weekend" in info
        assert "greeting" in info
    
    def test_response_style(self):
        """Test response style adjustment."""
        from src.proactive.intelligence import ContextAwareness
        
        context = ContextAwareness()
        
        # Test with coding app
        context.update_active_app("Visual Studio Code")
        style = context.get_response_style()
        
        assert style["technical"] == True
        assert style["verbosity"] == "concise"


class TestProactiveIntelligence:
    """Tests for main ProactiveIntelligence class."""
    
    def test_initialization(self):
        """Test initialization."""
        from src.proactive.intelligence import ProactiveIntelligence
        
        with tempfile.TemporaryDirectory() as tmpdir:
            pi = ProactiveIntelligence(Path(tmpdir))
            
            assert pi.geofence is not None
            assert pi.routines is not None
            assert pi.context is not None
    
    def test_welcome_message(self):
        """Test welcome message generation."""
        from src.proactive.intelligence import ProactiveIntelligence
        
        with tempfile.TemporaryDirectory() as tmpdir:
            pi = ProactiveIntelligence(Path(tmpdir))
            
            message = pi.get_welcome_message()
            assert isinstance(message, str)
            assert len(message) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
