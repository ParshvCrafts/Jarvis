"""
JARVIS Travel Module.

AI-powered trip planning with flights, hotels, activities, and weather.
"""

from loguru import logger

TRAVEL_AVAILABLE = False

try:
    from .models import (
        Trip,
        TripPurpose,
        TripStatus,
        BudgetLevel,
        Location,
        Flight,
        Hotel,
        Activity,
        Itinerary,
        ItineraryItem,
        PackingList,
        PackingItem,
        TripBudget,
        TripSearchCriteria,
        WeatherForecast,
    )
    
    from .apis import (
        AmadeusAPI,
        GooglePlacesAPI,
        OpenTripMapAPI,
        WeatherAPI,
        get_airport_code,
    )
    
    from .planner import (
        TripPlanner,
        format_trip_summary,
        format_packing_list,
    )
    
    from .manager import (
        TravelManager,
        TravelConfig,
    )
    
    TRAVEL_AVAILABLE = True
    logger.info("Travel module loaded successfully")
    
except ImportError as e:
    logger.warning(f"Travel module not fully available: {e}")

__all__ = [
    "TRAVEL_AVAILABLE",
    # Models
    "Trip",
    "TripPurpose",
    "TripStatus",
    "BudgetLevel",
    "Location",
    "Flight",
    "Hotel",
    "Activity",
    "Itinerary",
    "ItineraryItem",
    "PackingList",
    "PackingItem",
    "TripBudget",
    "TripSearchCriteria",
    "WeatherForecast",
    # APIs
    "AmadeusAPI",
    "GooglePlacesAPI",
    "OpenTripMapAPI",
    "WeatherAPI",
    "get_airport_code",
    # Planner
    "TripPlanner",
    "format_trip_summary",
    "format_packing_list",
    # Manager
    "TravelManager",
    "TravelConfig",
]
