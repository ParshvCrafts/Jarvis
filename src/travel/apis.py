"""
Travel API integrations for JARVIS Travel Module.

Integrates with Amadeus, Google Places, OpenTripMap, and Weather APIs.
"""

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx
from loguru import logger

from .models import (
    Flight, Hotel, Activity, Location, WeatherForecast,
    BudgetLevel
)


@dataclass
class AmadeusCredentials:
    """Amadeus API credentials."""
    client_id: str
    client_secret: str
    access_token: Optional[str] = None
    token_expires: Optional[datetime] = None


class AmadeusAPI:
    """
    Amadeus API for flights and hotels.
    
    Free tier: 2,000 calls/month
    Docs: https://developers.amadeus.com/
    """
    
    BASE_URL = "https://test.api.amadeus.com"  # Use test for free tier
    
    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id or os.getenv("AMADEUS_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("AMADEUS_CLIENT_SECRET", "")
        self.access_token: Optional[str] = None
        self.token_expires: Optional[datetime] = None
    
    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)
    
    async def _get_token(self) -> Optional[str]:
        """Get or refresh access token."""
        if self.access_token and self.token_expires and datetime.now() < self.token_expires:
            return self.access_token
        
        if not self.is_configured:
            logger.warning("Amadeus API not configured")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/v1/security/oauth2/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data["access_token"]
                    self.token_expires = datetime.now() + timedelta(seconds=data["expires_in"] - 60)
                    return self.access_token
                else:
                    logger.error(f"Amadeus auth failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Amadeus auth error: {e}")
            return None
    
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date] = None,
        adults: int = 1,
        max_results: int = 10,
    ) -> List[Flight]:
        """
        Search for flights.
        
        Args:
            origin: Origin airport code (e.g., "SFO")
            destination: Destination airport code (e.g., "SEA")
            departure_date: Departure date
            return_date: Return date for round trip
            adults: Number of adults
            max_results: Maximum results to return
            
        Returns:
            List of Flight objects
        """
        token = await self._get_token()
        if not token:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                params = {
                    "originLocationCode": origin,
                    "destinationLocationCode": destination,
                    "departureDate": departure_date.isoformat(),
                    "adults": adults,
                    "max": max_results,
                    "currencyCode": "USD",
                }
                
                if return_date:
                    params["returnDate"] = return_date.isoformat()
                
                response = await client.get(
                    f"{self.BASE_URL}/v2/shopping/flight-offers",
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_flights(data.get("data", []))
                else:
                    logger.error(f"Amadeus flight search failed: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Amadeus flight search error: {e}")
            return []
    
    def _parse_flights(self, data: List[Dict]) -> List[Flight]:
        """Parse Amadeus flight response."""
        flights = []
        
        for offer in data:
            try:
                price = float(offer.get("price", {}).get("total", 0))
                
                # Get first itinerary segment
                itineraries = offer.get("itineraries", [])
                if not itineraries:
                    continue
                
                first_itinerary = itineraries[0]
                segments = first_itinerary.get("segments", [])
                if not segments:
                    continue
                
                first_segment = segments[0]
                last_segment = segments[-1]
                
                # Parse times
                dep_time = datetime.fromisoformat(first_segment["departure"]["at"].replace("Z", "+00:00"))
                arr_time = datetime.fromisoformat(last_segment["arrival"]["at"].replace("Z", "+00:00"))
                
                # Calculate duration
                duration_str = first_itinerary.get("duration", "PT0H0M")
                duration_minutes = self._parse_duration(duration_str)
                
                flight = Flight(
                    airline=first_segment.get("carrierCode", ""),
                    flight_number=first_segment.get("number", ""),
                    departure_airport=first_segment["departure"]["iataCode"],
                    arrival_airport=last_segment["arrival"]["iataCode"],
                    departure_time=dep_time,
                    arrival_time=arr_time,
                    duration_minutes=duration_minutes,
                    stops=len(segments) - 1,
                    price=price,
                    currency="USD",
                    source="amadeus",
                )
                flights.append(flight)
                
            except Exception as e:
                logger.debug(f"Error parsing flight: {e}")
                continue
        
        return flights
    
    def _parse_duration(self, duration: str) -> int:
        """Parse ISO 8601 duration to minutes."""
        import re
        hours = 0
        minutes = 0
        
        h_match = re.search(r'(\d+)H', duration)
        m_match = re.search(r'(\d+)M', duration)
        
        if h_match:
            hours = int(h_match.group(1))
        if m_match:
            minutes = int(m_match.group(1))
        
        return hours * 60 + minutes
    
    async def search_hotels(
        self,
        city_code: str,
        check_in: date,
        check_out: date,
        adults: int = 1,
        max_results: int = 10,
    ) -> List[Hotel]:
        """Search for hotels in a city."""
        token = await self._get_token()
        if not token:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # First get hotel list
                response = await client.get(
                    f"{self.BASE_URL}/v1/reference-data/locations/hotels/by-city",
                    params={"cityCode": city_code, "radius": 20, "radiusUnit": "KM"},
                    headers={"Authorization": f"Bearer {token}"},
                )
                
                if response.status_code != 200:
                    return []
                
                hotels_data = response.json().get("data", [])[:max_results]
                
                hotels = []
                for h in hotels_data:
                    hotel = Hotel(
                        name=h.get("name", ""),
                        city=city_code,
                        latitude=h.get("geoCode", {}).get("latitude"),
                        longitude=h.get("geoCode", {}).get("longitude"),
                        source="amadeus",
                    )
                    hotels.append(hotel)
                
                return hotels
                
        except Exception as e:
            logger.error(f"Amadeus hotel search error: {e}")
            return []


class GooglePlacesAPI:
    """
    Google Places API for locations, restaurants, and activities.
    
    Free tier: $200/month credit
    """
    
    BASE_URL = "https://maps.googleapis.com/maps/api/place"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_PLACES_API_KEY", "")
    
    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    async def search_places(
        self,
        query: str,
        location: Optional[Tuple[float, float]] = None,
        radius: int = 5000,
        place_type: Optional[str] = None,
        max_results: int = 10,
    ) -> List[Activity]:
        """
        Search for places.
        
        Args:
            query: Search query
            location: (lat, lng) tuple
            radius: Search radius in meters
            place_type: Type filter (restaurant, lodging, tourist_attraction, etc.)
            max_results: Maximum results
            
        Returns:
            List of Activity objects
        """
        if not self.is_configured:
            logger.warning("Google Places API not configured")
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                params = {
                    "query": query,
                    "key": self.api_key,
                }
                
                if location:
                    params["location"] = f"{location[0]},{location[1]}"
                    params["radius"] = radius
                
                if place_type:
                    params["type"] = place_type
                
                response = await client.get(
                    f"{self.BASE_URL}/textsearch/json",
                    params=params,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "OK":
                        return self._parse_places(data.get("results", []))[:max_results]
                
                return []
                
        except Exception as e:
            logger.error(f"Google Places search error: {e}")
            return []
    
    async def search_nearby(
        self,
        location: Tuple[float, float],
        place_type: str,
        radius: int = 2000,
        keyword: Optional[str] = None,
    ) -> List[Activity]:
        """Search for nearby places of a specific type."""
        if not self.is_configured:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                params = {
                    "location": f"{location[0]},{location[1]}",
                    "radius": radius,
                    "type": place_type,
                    "key": self.api_key,
                }
                
                if keyword:
                    params["keyword"] = keyword
                
                response = await client.get(
                    f"{self.BASE_URL}/nearbysearch/json",
                    params=params,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "OK":
                        return self._parse_places(data.get("results", []))
                
                return []
                
        except Exception as e:
            logger.error(f"Google Places nearby search error: {e}")
            return []
    
    def _parse_places(self, results: List[Dict]) -> List[Activity]:
        """Parse Google Places results."""
        activities = []
        
        for place in results:
            try:
                # Get location
                geometry = place.get("geometry", {})
                loc = geometry.get("location", {})
                
                location = Location(
                    name=place.get("name", ""),
                    city=place.get("vicinity", "").split(",")[-1].strip() if place.get("vicinity") else "",
                    address=place.get("formatted_address", place.get("vicinity", "")),
                    latitude=loc.get("lat"),
                    longitude=loc.get("lng"),
                    place_id=place.get("place_id"),
                )
                
                # Get category from types
                types = place.get("types", [])
                category = types[0] if types else "place"
                
                activity = Activity(
                    name=place.get("name", ""),
                    description="",
                    category=category,
                    location=location,
                    rating=place.get("rating", 0),
                    reviews_count=place.get("user_ratings_total", 0),
                    price_level=place.get("price_level", 0),
                    is_free=place.get("price_level", 1) == 0,
                    source="google_places",
                )
                
                # Check for photos
                if place.get("photos"):
                    activity.photos = [p.get("photo_reference", "") for p in place["photos"][:3]]
                
                activities.append(activity)
                
            except Exception as e:
                logger.debug(f"Error parsing place: {e}")
                continue
        
        return activities
    
    async def get_place_details(self, place_id: str) -> Optional[Activity]:
        """Get detailed information about a place."""
        if not self.is_configured:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.BASE_URL}/details/json",
                    params={
                        "place_id": place_id,
                        "fields": "name,formatted_address,formatted_phone_number,website,opening_hours,rating,reviews,price_level,types",
                        "key": self.api_key,
                    },
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "OK":
                        result = data.get("result", {})
                        
                        activity = Activity(
                            name=result.get("name", ""),
                            description="",
                            category=result.get("types", ["place"])[0],
                            rating=result.get("rating", 0),
                            price_level=result.get("price_level", 0),
                            opening_hours=", ".join(result.get("opening_hours", {}).get("weekday_text", [])),
                            website=result.get("website"),
                            phone=result.get("formatted_phone_number"),
                            source="google_places",
                        )
                        return activity
                
                return None
                
        except Exception as e:
            logger.error(f"Google Places details error: {e}")
            return None


class OpenTripMapAPI:
    """
    OpenTripMap API for attractions and points of interest.
    
    Free tier: Unlimited (basic usage)
    """
    
    BASE_URL = "https://api.opentripmap.com/0.1/en/places"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENTRIPMAP_API_KEY", "")
    
    @property
    def is_configured(self) -> bool:
        # OpenTripMap works without key for basic usage
        return True
    
    async def search_attractions(
        self,
        location: Tuple[float, float],
        radius: int = 5000,
        kinds: str = "interesting_places",
        limit: int = 20,
    ) -> List[Activity]:
        """
        Search for attractions near a location.
        
        Args:
            location: (lat, lng) tuple
            radius: Search radius in meters
            kinds: Types of places (interesting_places, cultural, natural, etc.)
            limit: Maximum results
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                params = {
                    "lat": location[0],
                    "lon": location[1],
                    "radius": radius,
                    "kinds": kinds,
                    "limit": limit,
                    "format": "json",
                }
                
                if self.api_key:
                    params["apikey"] = self.api_key
                
                response = await client.get(
                    f"{self.BASE_URL}/radius",
                    params=params,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_attractions(data)
                
                return []
                
        except Exception as e:
            logger.error(f"OpenTripMap search error: {e}")
            return []
    
    def _parse_attractions(self, data: List[Dict]) -> List[Activity]:
        """Parse OpenTripMap results."""
        activities = []
        
        for place in data:
            try:
                point = place.get("point", {})
                
                location = Location(
                    name=place.get("name", "Unknown"),
                    city="",
                    latitude=point.get("lat"),
                    longitude=point.get("lon"),
                )
                
                activity = Activity(
                    id=place.get("xid", ""),
                    name=place.get("name", "Unknown Attraction"),
                    description="",
                    category=place.get("kinds", "").split(",")[0] if place.get("kinds") else "attraction",
                    location=location,
                    rating=place.get("rate", 0) / 2,  # Convert 0-10 to 0-5
                    is_free=True,  # Most attractions are free to visit
                    source="opentripmap",
                )
                
                if activity.name and activity.name != "Unknown":
                    activities.append(activity)
                    
            except Exception as e:
                logger.debug(f"Error parsing attraction: {e}")
                continue
        
        return activities


class WeatherAPI:
    """
    Weather API for forecasts.
    
    Using weatherapi.com - 1M calls/month free
    """
    
    BASE_URL = "https://api.weatherapi.com/v1"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("WEATHER_API_KEY", "")
    
    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    async def get_forecast(
        self,
        location: str,
        days: int = 7,
    ) -> List[WeatherForecast]:
        """
        Get weather forecast for a location.
        
        Args:
            location: City name or coordinates
            days: Number of days (1-10)
        """
        if not self.is_configured:
            logger.warning("Weather API not configured")
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.BASE_URL}/forecast.json",
                    params={
                        "key": self.api_key,
                        "q": location,
                        "days": min(days, 10),
                        "aqi": "no",
                    },
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_forecast(data, location)
                
                return []
                
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return []
    
    def _parse_forecast(self, data: Dict, location: str) -> List[WeatherForecast]:
        """Parse weather API response."""
        forecasts = []
        
        forecast_days = data.get("forecast", {}).get("forecastday", [])
        
        for day in forecast_days:
            try:
                day_data = day.get("day", {})
                
                forecast = WeatherForecast(
                    date=date.fromisoformat(day.get("date", "")),
                    location=location,
                    temp_high=day_data.get("maxtemp_f", 0),
                    temp_low=day_data.get("mintemp_f", 0),
                    temp_unit="F",
                    condition=day_data.get("condition", {}).get("text", ""),
                    precipitation_chance=day_data.get("daily_chance_of_rain", 0),
                    humidity=day_data.get("avghumidity", 0),
                    wind_speed=day_data.get("maxwind_mph", 0),
                    icon=day_data.get("condition", {}).get("icon", ""),
                )
                forecasts.append(forecast)
                
            except Exception as e:
                logger.debug(f"Error parsing forecast: {e}")
                continue
        
        return forecasts
    
    async def get_current(self, location: str) -> Optional[WeatherForecast]:
        """Get current weather for a location."""
        if not self.is_configured:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.BASE_URL}/current.json",
                    params={
                        "key": self.api_key,
                        "q": location,
                    },
                )
                
                if response.status_code == 200:
                    data = response.json()
                    current = data.get("current", {})
                    
                    return WeatherForecast(
                        date=date.today(),
                        location=location,
                        temp_high=current.get("temp_f", 0),
                        temp_low=current.get("temp_f", 0),
                        temp_unit="F",
                        condition=current.get("condition", {}).get("text", ""),
                        humidity=current.get("humidity", 0),
                        wind_speed=current.get("wind_mph", 0),
                        icon=current.get("condition", {}).get("icon", ""),
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Weather API current error: {e}")
            return None


# Airport codes for common cities
AIRPORT_CODES = {
    "san francisco": "SFO",
    "oakland": "OAK",
    "san jose": "SJC",
    "los angeles": "LAX",
    "new york": "JFK",
    "seattle": "SEA",
    "chicago": "ORD",
    "boston": "BOS",
    "denver": "DEN",
    "austin": "AUS",
    "portland": "PDX",
    "miami": "MIA",
    "atlanta": "ATL",
    "dallas": "DFW",
    "houston": "IAH",
    "phoenix": "PHX",
    "las vegas": "LAS",
    "san diego": "SAN",
    "washington": "DCA",
    "mountain view": "SJC",  # For Google interviews
    "menlo park": "SFO",  # For Meta interviews
    "cupertino": "SJC",  # For Apple interviews
}


def get_airport_code(city: str) -> str:
    """Get airport code for a city."""
    city_lower = city.lower().strip()
    
    # Direct match
    if city_lower in AIRPORT_CODES:
        return AIRPORT_CODES[city_lower]
    
    # Partial match
    for city_name, code in AIRPORT_CODES.items():
        if city_name in city_lower or city_lower in city_name:
            return code
    
    # Return city as-is (might be an airport code already)
    return city.upper()[:3]
