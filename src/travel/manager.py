"""
Travel Manager for JARVIS Travel Module.

Main orchestrator for trip planning, flight search, and travel management.
"""

import os
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .models import (
    Trip, TripPurpose, TripStatus, BudgetLevel,
    Location, Flight, Hotel, Activity,
    TripSearchCriteria, WeatherForecast
)
from .apis import AmadeusAPI, GooglePlacesAPI, OpenTripMapAPI, WeatherAPI
from .planner import TripPlanner, format_trip_summary, format_packing_list


@dataclass
class TravelConfig:
    """Configuration for travel manager."""
    home_airport: str = "SFO"
    home_city: str = "San Francisco, CA"
    preferred_airlines: List[str] = None
    budget_preference: BudgetLevel = BudgetLevel.MODERATE
    db_path: str = "data/travel.db"
    
    def __post_init__(self):
        if self.preferred_airlines is None:
            self.preferred_airlines = ["Southwest", "United"]


class TravelManager:
    """
    Main manager for travel functionality.
    
    Features:
    - Trip planning with flights, hotels, activities
    - Trip storage and retrieval
    - Weather forecasts
    - Packing lists
    - Interview travel mode
    - Budget tracking
    """
    
    def __init__(
        self,
        config: Optional[TravelConfig] = None,
        llm_router: Optional[Any] = None,
    ):
        self.config = config or TravelConfig()
        self.llm_router = llm_router
        
        # Initialize APIs
        self.amadeus = AmadeusAPI()
        self.places = GooglePlacesAPI()
        self.attractions = OpenTripMapAPI()
        self.weather = WeatherAPI()
        
        # Initialize planner
        self.planner = TripPlanner(
            amadeus_api=self.amadeus,
            places_api=self.places,
            attractions_api=self.attractions,
            weather_api=self.weather,
        )
        
        # Initialize database
        self._init_db()
        
        logger.info("Travel Manager initialized")
    
    def _init_db(self):
        """Initialize SQLite database for trips."""
        db_path = Path(self.config.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS trips (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                destination TEXT,
                origin TEXT,
                start_date TEXT,
                end_date TEXT,
                purpose TEXT,
                status TEXT,
                budget_level TEXT,
                budget_total REAL,
                actual_spent REAL DEFAULT 0,
                notes TEXT,
                data JSON,
                created_at TEXT,
                updated_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS trip_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id TEXT,
                category TEXT,
                amount REAL,
                description TEXT,
                date TEXT,
                FOREIGN KEY (trip_id) REFERENCES trips(id)
            );
            
            CREATE TABLE IF NOT EXISTS saved_places (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                city TEXT,
                country TEXT,
                category TEXT,
                rating REAL,
                notes TEXT,
                visited BOOLEAN DEFAULT 0,
                created_at TEXT
            );
        """)
        
        conn.commit()
        conn.close()
    
    # =========================================================================
    # Trip Planning
    # =========================================================================
    
    async def plan_trip(
        self,
        destination: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        days: int = 3,
        purpose: str = "vacation",
        budget: str = "moderate",
    ) -> Trip:
        """
        Plan a complete trip.
        
        Args:
            destination: Destination city
            start_date: Start date (default: 1 week from now)
            end_date: End date (default: start + days)
            days: Number of days if end_date not specified
            purpose: Trip purpose (vacation, interview, family, business)
            budget: Budget level (budget, moderate, luxury)
        """
        # Default dates
        if not start_date:
            start_date = date.today() + timedelta(days=7)
        if not end_date:
            end_date = start_date + timedelta(days=days - 1)
        
        # Parse purpose
        purpose_map = {
            "vacation": TripPurpose.VACATION,
            "interview": TripPurpose.INTERVIEW,
            "family": TripPurpose.FAMILY,
            "business": TripPurpose.BUSINESS,
            "conference": TripPurpose.CONFERENCE,
        }
        trip_purpose = purpose_map.get(purpose.lower(), TripPurpose.VACATION)
        
        # Parse budget
        budget_map = {
            "budget": BudgetLevel.BUDGET,
            "cheap": BudgetLevel.BUDGET,
            "moderate": BudgetLevel.MODERATE,
            "luxury": BudgetLevel.LUXURY,
            "expensive": BudgetLevel.LUXURY,
        }
        budget_level = budget_map.get(budget.lower(), self.config.budget_preference)
        
        # Create search criteria
        criteria = TripSearchCriteria(
            destination=destination,
            origin=self.config.home_city,
            start_date=start_date,
            end_date=end_date,
            purpose=trip_purpose,
            budget_level=budget_level,
            preferred_airlines=self.config.preferred_airlines,
        )
        
        # Plan trip
        trip = await self.planner.plan_trip(criteria)
        
        # Save to database
        self._save_trip(trip)
        
        return trip
    
    async def plan_interview_trip(
        self,
        company: str,
        location: str,
        interview_date: date,
    ) -> Trip:
        """Plan a trip for an interview."""
        trip = await self.planner.plan_interview_trip(company, location, interview_date)
        self._save_trip(trip)
        return trip
    
    async def plan_budget_trip(
        self,
        destination: str,
        days: int = 3,
    ) -> Trip:
        """Plan a budget-friendly trip."""
        trip = await self.planner.plan_budget_trip(destination, days)
        self._save_trip(trip)
        return trip
    
    # =========================================================================
    # Flight Search
    # =========================================================================
    
    async def search_flights(
        self,
        destination: str,
        departure_date: Optional[date] = None,
        return_date: Optional[date] = None,
        origin: Optional[str] = None,
    ) -> List[Flight]:
        """
        Search for flights.
        
        Args:
            destination: Destination city or airport code
            departure_date: Departure date (default: next weekend)
            return_date: Return date (optional for one-way)
            origin: Origin city (default: home airport)
        """
        if not departure_date:
            # Default to next weekend
            today = date.today()
            days_until_saturday = (5 - today.weekday()) % 7
            if days_until_saturday == 0:
                days_until_saturday = 7
            departure_date = today + timedelta(days=days_until_saturday)
        
        criteria = TripSearchCriteria(
            destination=destination,
            origin=origin or self.config.home_city,
            start_date=departure_date,
            end_date=return_date,
        )
        
        return await self.planner.search_flights(criteria)
    
    # =========================================================================
    # Hotel Search
    # =========================================================================
    
    async def search_hotels(
        self,
        location: str,
        check_in: Optional[date] = None,
        check_out: Optional[date] = None,
        max_price: Optional[float] = None,
        near: Optional[str] = None,
    ) -> List[Hotel]:
        """
        Search for hotels.
        
        Args:
            location: City or area
            check_in: Check-in date
            check_out: Check-out date
            max_price: Maximum price per night
            near: Search near a specific location (e.g., "Google campus")
        """
        query = f"hotels in {location}"
        if near:
            query = f"hotels near {near} {location}"
        
        activities = await self.places.search_places(
            query=query,
            place_type="lodging",
            max_results=10,
        )
        
        hotels = []
        for activity in activities:
            hotel = Hotel(
                name=activity.name,
                address=activity.location.address if activity.location else "",
                city=location,
                rating=activity.rating,
                reviews_count=activity.reviews_count,
                price_per_night=self._estimate_price(activity.price_level),
                source="google_places",
            )
            
            # Filter by max price
            if max_price and hotel.price_per_night > max_price:
                continue
            
            hotels.append(hotel)
        
        return sorted(hotels, key=lambda h: h.rating, reverse=True)
    
    def _estimate_price(self, price_level: int) -> float:
        """Estimate price from Google's price level."""
        prices = {0: 50, 1: 80, 2: 120, 3: 180, 4: 300}
        return prices.get(price_level, 100)
    
    # =========================================================================
    # Activities & Restaurants
    # =========================================================================
    
    async def search_restaurants(
        self,
        location: str,
        cuisine: Optional[str] = None,
        budget: Optional[str] = None,
    ) -> List[Activity]:
        """Search for restaurants."""
        query = f"restaurants in {location}"
        if cuisine:
            query = f"{cuisine} restaurants in {location}"
        if budget == "cheap" or budget == "budget":
            query = f"cheap {query}"
        elif budget == "fancy" or budget == "luxury":
            query = f"fine dining {query}"
        
        return await self.places.search_places(
            query=query,
            place_type="restaurant",
            max_results=10,
        )
    
    async def search_activities(
        self,
        location: str,
        activity_type: Optional[str] = None,
    ) -> List[Activity]:
        """Search for activities and attractions."""
        query = f"things to do in {location}"
        if activity_type:
            query = f"{activity_type} in {location}"
        
        return await self.places.search_places(
            query=query,
            max_results=10,
        )
    
    # =========================================================================
    # Weather
    # =========================================================================
    
    async def get_weather(
        self,
        location: str,
        days: int = 7,
    ) -> List[WeatherForecast]:
        """Get weather forecast for a location."""
        return await self.weather.get_forecast(location, days)
    
    async def get_current_weather(self, location: str) -> Optional[WeatherForecast]:
        """Get current weather for a location."""
        return await self.weather.get_current(location)
    
    # =========================================================================
    # Trip Storage
    # =========================================================================
    
    def _save_trip(self, trip: Trip):
        """Save trip to database."""
        import json
        
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO trips 
            (id, name, destination, origin, start_date, end_date, purpose, status,
             budget_level, budget_total, actual_spent, notes, data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trip.id,
            trip.name,
            str(trip.destination) if trip.destination else None,
            str(trip.origin) if trip.origin else None,
            trip.start_date.isoformat() if trip.start_date else None,
            trip.end_date.isoformat() if trip.end_date else None,
            trip.purpose.value,
            trip.status.value,
            trip.budget_level.value,
            trip.budget.total() if trip.budget else 0,
            trip.actual_spent,
            trip.notes,
            json.dumps(trip.to_dict()),
            trip.created_at.isoformat(),
            datetime.now().isoformat(),
        ))
        
        conn.commit()
        conn.close()
    
    def get_trips(self, status: Optional[str] = None) -> List[Dict]:
        """Get all trips, optionally filtered by status."""
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute(
                "SELECT * FROM trips WHERE status = ? ORDER BY start_date DESC",
                (status,)
            )
        else:
            cursor.execute("SELECT * FROM trips ORDER BY start_date DESC")
        
        columns = [desc[0] for desc in cursor.description]
        trips = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return trips
    
    def get_upcoming_trips(self) -> List[Dict]:
        """Get upcoming trips."""
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        cursor.execute(
            "SELECT * FROM trips WHERE start_date >= ? ORDER BY start_date ASC",
            (today,)
        )
        
        columns = [desc[0] for desc in cursor.description]
        trips = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return trips
    
    # =========================================================================
    # Voice Command Handler
    # =========================================================================
    
    async def handle_command(self, command: str) -> str:
        """Handle voice commands for travel."""
        import re
        command_lower = command.lower()
        
        # Plan trip
        if "plan" in command_lower and "trip" in command_lower:
            # Extract destination
            dest_match = re.search(r'to\s+([a-zA-Z\s]+?)(?:\s+for|\s+in|\s*$)', command_lower)
            if dest_match:
                destination = dest_match.group(1).strip().title()
                
                # Extract days
                days_match = re.search(r'(\d+)\s*days?', command_lower)
                days = int(days_match.group(1)) if days_match else 3
                
                # Check for interview
                if "interview" in command_lower:
                    company_match = re.search(r'(?:at|for)\s+(\w+)', command_lower)
                    company = company_match.group(1).title() if company_match else "Company"
                    trip = await self.plan_interview_trip(
                        company, destination, date.today() + timedelta(days=7)
                    )
                elif "budget" in command_lower or "cheap" in command_lower:
                    trip = await self.plan_budget_trip(destination, days)
                else:
                    trip = await self.plan_trip(destination, days=days)
                
                return format_trip_summary(trip)
            
            return "Please specify a destination: 'Plan trip to Seattle for 3 days'"
        
        # Find flights
        if "flight" in command_lower or "fly" in command_lower:
            dest_match = re.search(r'to\s+([a-zA-Z\s]+?)(?:\s+on|\s+next|\s*$)', command_lower)
            if dest_match:
                destination = dest_match.group(1).strip().title()
                flights = await self.search_flights(destination)
                
                if flights:
                    lines = [f"✈️ **Flights to {destination}:**", ""]
                    for flight in flights[:5]:
                        stops = f" ({flight.stops} stop)" if flight.stops else " (nonstop)"
                        lines.append(f"  - {flight.airline}: ${flight.price:.0f}{stops}")
                    return "\n".join(lines)
                
                return f"No flights found to {destination}"
            
            return "Please specify a destination: 'Find flights to New York'"
        
        # Hotels
        if "hotel" in command_lower:
            # Extract location
            loc_match = re.search(r'(?:in|near)\s+([a-zA-Z\s]+?)(?:\s+under|\s*$)', command_lower)
            if loc_match:
                location = loc_match.group(1).strip().title()
                
                # Extract max price
                price_match = re.search(r'under\s*\$?(\d+)', command_lower)
                max_price = float(price_match.group(1)) if price_match else None
                
                # Check for "near" location
                near_match = re.search(r'near\s+([a-zA-Z\s]+?)(?:\s+in|\s*$)', command_lower)
                near = near_match.group(1).strip() if near_match else None
                
                hotels = await self.search_hotels(location, max_price=max_price, near=near)
                
                if hotels:
                    lines = [f"🏨 **Hotels in {location}:**", ""]
                    for hotel in hotels[:5]:
                        rating = f"⭐{hotel.rating:.1f}" if hotel.rating else ""
                        lines.append(f"  - {hotel.name}: ${hotel.price_per_night:.0f}/night {rating}")
                    return "\n".join(lines)
                
                return f"No hotels found in {location}"
            
            return "Please specify a location: 'Hotels in Seattle under $150'"
        
        # Restaurants
        if "restaurant" in command_lower or "food" in command_lower or "eat" in command_lower:
            loc_match = re.search(r'in\s+([a-zA-Z\s]+)', command_lower)
            if loc_match:
                location = loc_match.group(1).strip().title()
                restaurants = await self.search_restaurants(location)
                
                if restaurants:
                    lines = [f"🍽️ **Restaurants in {location}:**", ""]
                    for r in restaurants[:5]:
                        rating = f"⭐{r.rating:.1f}" if r.rating else ""
                        price = "$" * (r.price_level + 1) if r.price_level else ""
                        lines.append(f"  - {r.name} {rating} {price}")
                    return "\n".join(lines)
                
                return f"No restaurants found in {location}"
            
            return "Please specify a location: 'Restaurants in San Francisco'"
        
        # Weather
        if "weather" in command_lower:
            loc_match = re.search(r'in\s+([a-zA-Z\s]+)', command_lower)
            if loc_match:
                location = loc_match.group(1).strip().title()
                weather = await self.get_current_weather(location)
                
                if weather:
                    return (
                        f"🌤️ **Weather in {location}:**\n"
                        f"  {weather.condition}\n"
                        f"  Temperature: {weather.temp_high:.0f}°F\n"
                        f"  Humidity: {weather.humidity}%\n"
                        f"  Wind: {weather.wind_speed:.0f} mph"
                    )
                
                return f"Could not get weather for {location}"
            
            return "Please specify a location: 'Weather in Seattle'"
        
        # Packing list
        if "pack" in command_lower:
            dest_match = re.search(r'for\s+([a-zA-Z\s]+)', command_lower)
            if dest_match:
                destination = dest_match.group(1).strip().title()
                
                # Get weather and generate packing list
                weather = await self.get_weather(destination)
                
                # Create a dummy trip for packing list
                trip = Trip(
                    destination=Location(name=destination, city=destination),
                    purpose=TripPurpose.VACATION,
                )
                
                packing_list = self.planner.generate_packing_list(trip, weather)
                return format_packing_list(packing_list)
            
            return "Please specify a destination: 'Pack list for Seattle'"
        
        # My trips
        if "my trip" in command_lower or "upcoming trip" in command_lower:
            trips = self.get_upcoming_trips()
            
            if trips:
                lines = ["📅 **Your Upcoming Trips:**", ""]
                for trip in trips[:5]:
                    lines.append(f"  - {trip['name']} ({trip['start_date']})")
                return "\n".join(lines)
            
            return "No upcoming trips. Say 'Plan trip to Seattle' to create one!"
        
        return (
            "Travel commands:\n"
            "  - 'Plan trip to Seattle for 3 days'\n"
            "  - 'Find flights to New York'\n"
            "  - 'Hotels near Google campus'\n"
            "  - 'Restaurants in San Francisco'\n"
            "  - 'Weather in Seattle'\n"
            "  - 'Pack list for Seattle winter'"
        )
    
    # =========================================================================
    # Status
    # =========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get travel module status."""
        upcoming = self.get_upcoming_trips()
        
        return {
            "amadeus_configured": self.amadeus.is_configured,
            "places_configured": self.places.is_configured,
            "weather_configured": self.weather.is_configured,
            "upcoming_trips": len(upcoming),
            "next_trip": upcoming[0] if upcoming else None,
        }
    
    def get_status_summary(self) -> str:
        """Get formatted status summary."""
        status = self.get_status()
        
        lines = [
            "🗺️ **Travel Module Status**",
            "",
            "**APIs:**",
            f"  {'✅' if status['amadeus_configured'] else '⚠️'} Amadeus (Flights/Hotels)",
            f"  {'✅' if status['places_configured'] else '⚠️'} Google Places",
            f"  {'✅' if status['weather_configured'] else '⚠️'} Weather API",
            "",
            f"**Upcoming Trips:** {status['upcoming_trips']}",
        ]
        
        if status['next_trip']:
            trip = status['next_trip']
            lines.append(f"**Next Trip:** {trip['name']} ({trip['start_date']})")
        
        return "\n".join(lines)
