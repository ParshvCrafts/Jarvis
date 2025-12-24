"""
Weather Service for JARVIS - Open-Meteo Integration

Provides real-time weather data using Open-Meteo API (FREE, no API key required).

Features:
- Current weather conditions
- Hourly forecast (next 24 hours)
- Daily forecast (next 7 days)
- Location geocoding by city name
- Weather condition descriptions
- Caching support (30 minutes default)

API Documentation: https://open-meteo.com/en/docs
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import httpx
from loguru import logger


class WeatherCondition(Enum):
    """Weather condition codes from Open-Meteo WMO codes."""
    CLEAR = 0
    MAINLY_CLEAR = 1
    PARTLY_CLOUDY = 2
    OVERCAST = 3
    FOG = 45
    DEPOSITING_RIME_FOG = 48
    DRIZZLE_LIGHT = 51
    DRIZZLE_MODERATE = 53
    DRIZZLE_DENSE = 55
    FREEZING_DRIZZLE_LIGHT = 56
    FREEZING_DRIZZLE_DENSE = 57
    RAIN_SLIGHT = 61
    RAIN_MODERATE = 63
    RAIN_HEAVY = 65
    FREEZING_RAIN_LIGHT = 66
    FREEZING_RAIN_HEAVY = 67
    SNOW_SLIGHT = 71
    SNOW_MODERATE = 73
    SNOW_HEAVY = 75
    SNOW_GRAINS = 77
    RAIN_SHOWERS_SLIGHT = 80
    RAIN_SHOWERS_MODERATE = 81
    RAIN_SHOWERS_VIOLENT = 82
    SNOW_SHOWERS_SLIGHT = 85
    SNOW_SHOWERS_HEAVY = 86
    THUNDERSTORM = 95
    THUNDERSTORM_HAIL_SLIGHT = 96
    THUNDERSTORM_HAIL_HEAVY = 99


# Weather code to description mapping
WEATHER_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

# Weather code to emoji mapping
WEATHER_EMOJIS = {
    0: "☀️",
    1: "🌤️",
    2: "⛅",
    3: "☁️",
    45: "🌫️",
    48: "🌫️",
    51: "🌧️",
    53: "🌧️",
    55: "🌧️",
    56: "🌧️❄️",
    57: "🌧️❄️",
    61: "🌧️",
    63: "🌧️",
    65: "🌧️",
    66: "🌧️❄️",
    67: "🌧️❄️",
    71: "🌨️",
    73: "🌨️",
    75: "❄️",
    77: "🌨️",
    80: "🌦️",
    81: "🌦️",
    82: "⛈️",
    85: "🌨️",
    86: "❄️",
    95: "⛈️",
    96: "⛈️",
    99: "⛈️",
}


@dataclass
class GeoLocation:
    """Geographic location data."""
    name: str
    latitude: float
    longitude: float
    country: str
    admin1: Optional[str] = None  # State/Province
    timezone: str = "auto"
    
    @property
    def display_name(self) -> str:
        """Get formatted display name."""
        parts = [self.name]
        if self.admin1:
            parts.append(self.admin1)
        parts.append(self.country)
        return ", ".join(parts)


@dataclass
class CurrentWeather:
    """Current weather conditions."""
    temperature: float
    feels_like: float
    humidity: int
    wind_speed: float
    wind_direction: int
    weather_code: int
    is_day: bool
    precipitation: float = 0.0
    cloud_cover: int = 0
    pressure: float = 0.0
    visibility: float = 0.0
    uv_index: float = 0.0
    
    @property
    def condition(self) -> str:
        """Get weather condition description."""
        return WEATHER_DESCRIPTIONS.get(self.weather_code, "Unknown")
    
    @property
    def emoji(self) -> str:
        """Get weather emoji."""
        return WEATHER_EMOJIS.get(self.weather_code, "🌡️")
    
    @property
    def wind_direction_text(self) -> str:
        """Convert wind direction degrees to compass direction."""
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                      "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        idx = round(self.wind_direction / 22.5) % 16
        return directions[idx]


@dataclass
class HourlyForecast:
    """Hourly weather forecast."""
    time: datetime
    temperature: float
    precipitation_probability: int
    precipitation: float
    weather_code: int
    wind_speed: float
    humidity: int
    feels_like: float
    
    @property
    def condition(self) -> str:
        return WEATHER_DESCRIPTIONS.get(self.weather_code, "Unknown")
    
    @property
    def emoji(self) -> str:
        return WEATHER_EMOJIS.get(self.weather_code, "🌡️")


@dataclass
class DailyForecast:
    """Daily weather forecast."""
    date: datetime
    temperature_max: float
    temperature_min: float
    precipitation_sum: float
    precipitation_probability_max: int
    weather_code: int
    sunrise: datetime
    sunset: datetime
    wind_speed_max: float
    uv_index_max: float
    
    @property
    def condition(self) -> str:
        return WEATHER_DESCRIPTIONS.get(self.weather_code, "Unknown")
    
    @property
    def emoji(self) -> str:
        return WEATHER_EMOJIS.get(self.weather_code, "🌡️")


@dataclass
class WeatherData:
    """Complete weather data for a location."""
    location: GeoLocation
    current: CurrentWeather
    hourly: List[HourlyForecast] = field(default_factory=list)
    daily: List[DailyForecast] = field(default_factory=list)
    fetched_at: datetime = field(default_factory=datetime.now)
    
    def get_summary(self, include_forecast: bool = True) -> str:
        """Generate a natural language weather summary."""
        lines = []
        
        # Current conditions
        lines.append(f"{self.current.emoji} **Current Weather in {self.location.display_name}**")
        lines.append(f"Temperature: {self.current.temperature:.1f}°F (feels like {self.current.feels_like:.1f}°F)")
        lines.append(f"Conditions: {self.current.condition}")
        lines.append(f"Humidity: {self.current.humidity}%")
        lines.append(f"Wind: {self.current.wind_speed:.1f} mph {self.current.wind_direction_text}")
        
        if self.current.precipitation > 0:
            lines.append(f"Precipitation: {self.current.precipitation:.2f} inches")
        
        if include_forecast and self.daily:
            lines.append("")
            lines.append("**Forecast:**")
            for day in self.daily[:3]:  # Next 3 days
                day_name = day.date.strftime("%A")
                lines.append(
                    f"- {day_name}: {day.emoji} {day.temperature_max:.0f}°F / {day.temperature_min:.0f}°F - {day.condition}"
                )
                if day.precipitation_probability_max > 30:
                    lines.append(f"  ({day.precipitation_probability_max}% chance of precipitation)")
        
        return "\n".join(lines)
    
    def get_hourly_summary(self, hours: int = 12) -> str:
        """Generate hourly forecast summary."""
        lines = [f"**Hourly Forecast for {self.location.display_name}**"]
        
        for hour in self.hourly[:hours]:
            time_str = hour.time.strftime("%I %p")
            lines.append(
                f"- {time_str}: {hour.emoji} {hour.temperature:.0f}°F - {hour.condition}"
            )
            if hour.precipitation_probability > 30:
                lines.append(f"  ({hour.precipitation_probability}% chance of rain)")
        
        return "\n".join(lines)


class WeatherCache:
    """Simple in-memory cache for weather data."""
    
    def __init__(self, ttl_seconds: int = 1800):  # 30 minutes default
        self.ttl = ttl_seconds
        self._cache: Dict[str, Tuple[WeatherData, float]] = {}
    
    def _make_key(self, lat: float, lon: float) -> str:
        """Create cache key from coordinates."""
        return f"{lat:.2f},{lon:.2f}"
    
    def get(self, lat: float, lon: float) -> Optional[WeatherData]:
        """Get cached weather data if not expired."""
        key = self._make_key(lat, lon)
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl:
                logger.debug(f"Weather cache hit for {key}")
                return data
            else:
                del self._cache[key]
        return None
    
    def set(self, lat: float, lon: float, data: WeatherData) -> None:
        """Cache weather data."""
        key = self._make_key(lat, lon)
        self._cache[key] = (data, time.time())
        logger.debug(f"Weather cached for {key}")
    
    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()


class WeatherService:
    """
    Weather service using Open-Meteo API.
    
    Open-Meteo is completely FREE with no API key required.
    - Geocoding API: Convert city names to coordinates
    - Weather API: Get current and forecast weather data
    """
    
    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
    WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
    
    def __init__(
        self,
        cache_ttl: int = 1800,
        timeout: int = 30,
        temperature_unit: str = "fahrenheit",
        wind_speed_unit: str = "mph",
        precipitation_unit: str = "inch",
    ):
        """
        Initialize weather service.
        
        Args:
            cache_ttl: Cache time-to-live in seconds (default 30 minutes)
            timeout: HTTP request timeout in seconds
            temperature_unit: "fahrenheit" or "celsius"
            wind_speed_unit: "mph", "kmh", "ms", or "kn"
            precipitation_unit: "inch" or "mm"
        """
        self.cache = WeatherCache(ttl_seconds=cache_ttl)
        self.timeout = timeout
        self.temperature_unit = temperature_unit
        self.wind_speed_unit = wind_speed_unit
        self.precipitation_unit = precipitation_unit
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def geocode(self, city: str, count: int = 1) -> List[GeoLocation]:
        """
        Convert city name to geographic coordinates.
        
        Args:
            city: City name to search for
            count: Maximum number of results
            
        Returns:
            List of matching locations
        """
        client = await self._get_client()
        
        try:
            response = await client.get(
                self.GEOCODING_URL,
                params={
                    "name": city,
                    "count": count,
                    "language": "en",
                    "format": "json",
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if "results" not in data:
                logger.warning(f"No geocoding results for '{city}'")
                return []
            
            locations = []
            for result in data["results"]:
                locations.append(GeoLocation(
                    name=result.get("name", city),
                    latitude=result["latitude"],
                    longitude=result["longitude"],
                    country=result.get("country", "Unknown"),
                    admin1=result.get("admin1"),
                    timezone=result.get("timezone", "auto"),
                ))
            
            return locations
            
        except httpx.HTTPError as e:
            logger.error(f"Geocoding error for '{city}': {e}")
            raise WeatherError(f"Failed to find location '{city}': {e}")
    
    async def get_weather(
        self,
        latitude: float,
        longitude: float,
        location_name: Optional[str] = None,
        include_hourly: bool = True,
        include_daily: bool = True,
        hourly_hours: int = 24,
        daily_days: int = 7,
    ) -> WeatherData:
        """
        Get weather data for coordinates.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            location_name: Optional display name for location
            include_hourly: Include hourly forecast
            include_daily: Include daily forecast
            hourly_hours: Number of hours for hourly forecast
            daily_days: Number of days for daily forecast
            
        Returns:
            WeatherData with current conditions and forecasts
        """
        # Check cache first
        cached = self.cache.get(latitude, longitude)
        if cached:
            return cached
        
        client = await self._get_client()
        
        # Build parameters
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "is_day",
                "precipitation",
                "weather_code",
                "cloud_cover",
                "pressure_msl",
                "wind_speed_10m",
                "wind_direction_10m",
            ],
            "temperature_unit": self.temperature_unit,
            "wind_speed_unit": self.wind_speed_unit,
            "precipitation_unit": self.precipitation_unit,
            "timezone": "auto",
        }
        
        if include_hourly:
            params["hourly"] = [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "precipitation_probability",
                "precipitation",
                "weather_code",
                "wind_speed_10m",
            ]
            params["forecast_hours"] = hourly_hours
        
        if include_daily:
            params["daily"] = [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "weather_code",
                "sunrise",
                "sunset",
                "wind_speed_10m_max",
                "uv_index_max",
            ]
            params["forecast_days"] = daily_days
        
        try:
            response = await client.get(self.WEATHER_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Parse current weather
            current_data = data.get("current", {})
            current = CurrentWeather(
                temperature=current_data.get("temperature_2m", 0),
                feels_like=current_data.get("apparent_temperature", 0),
                humidity=current_data.get("relative_humidity_2m", 0),
                wind_speed=current_data.get("wind_speed_10m", 0),
                wind_direction=current_data.get("wind_direction_10m", 0),
                weather_code=current_data.get("weather_code", 0),
                is_day=current_data.get("is_day", 1) == 1,
                precipitation=current_data.get("precipitation", 0),
                cloud_cover=current_data.get("cloud_cover", 0),
                pressure=current_data.get("pressure_msl", 0),
            )
            
            # Parse hourly forecast
            hourly_forecasts = []
            if include_hourly and "hourly" in data:
                hourly_data = data["hourly"]
                times = hourly_data.get("time", [])
                for i, time_str in enumerate(times[:hourly_hours]):
                    hourly_forecasts.append(HourlyForecast(
                        time=datetime.fromisoformat(time_str),
                        temperature=hourly_data.get("temperature_2m", [0] * len(times))[i],
                        precipitation_probability=hourly_data.get("precipitation_probability", [0] * len(times))[i] or 0,
                        precipitation=hourly_data.get("precipitation", [0] * len(times))[i] or 0,
                        weather_code=hourly_data.get("weather_code", [0] * len(times))[i] or 0,
                        wind_speed=hourly_data.get("wind_speed_10m", [0] * len(times))[i] or 0,
                        humidity=hourly_data.get("relative_humidity_2m", [0] * len(times))[i] or 0,
                        feels_like=hourly_data.get("apparent_temperature", [0] * len(times))[i] or 0,
                    ))
            
            # Parse daily forecast
            daily_forecasts = []
            if include_daily and "daily" in data:
                daily_data = data["daily"]
                times = daily_data.get("time", [])
                for i, date_str in enumerate(times[:daily_days]):
                    sunrise_str = daily_data.get("sunrise", [""] * len(times))[i]
                    sunset_str = daily_data.get("sunset", [""] * len(times))[i]
                    daily_forecasts.append(DailyForecast(
                        date=datetime.fromisoformat(date_str),
                        temperature_max=daily_data.get("temperature_2m_max", [0] * len(times))[i] or 0,
                        temperature_min=daily_data.get("temperature_2m_min", [0] * len(times))[i] or 0,
                        precipitation_sum=daily_data.get("precipitation_sum", [0] * len(times))[i] or 0,
                        precipitation_probability_max=daily_data.get("precipitation_probability_max", [0] * len(times))[i] or 0,
                        weather_code=daily_data.get("weather_code", [0] * len(times))[i] or 0,
                        sunrise=datetime.fromisoformat(sunrise_str) if sunrise_str else datetime.now(),
                        sunset=datetime.fromisoformat(sunset_str) if sunset_str else datetime.now(),
                        wind_speed_max=daily_data.get("wind_speed_10m_max", [0] * len(times))[i] or 0,
                        uv_index_max=daily_data.get("uv_index_max", [0] * len(times))[i] or 0,
                    ))
            
            # Create location
            location = GeoLocation(
                name=location_name or f"{latitude:.2f}, {longitude:.2f}",
                latitude=latitude,
                longitude=longitude,
                country="",
                timezone=data.get("timezone", "auto"),
            )
            
            # Build weather data
            weather_data = WeatherData(
                location=location,
                current=current,
                hourly=hourly_forecasts,
                daily=daily_forecasts,
            )
            
            # Cache the result
            self.cache.set(latitude, longitude, weather_data)
            
            return weather_data
            
        except httpx.HTTPError as e:
            logger.error(f"Weather API error: {e}")
            raise WeatherError(f"Failed to get weather data: {e}")
    
    async def get_weather_by_city(
        self,
        city: str,
        include_hourly: bool = True,
        include_daily: bool = True,
    ) -> WeatherData:
        """
        Get weather data for a city name.
        
        Args:
            city: City name (e.g., "Chicago", "New York, NY", "London, UK")
            include_hourly: Include hourly forecast
            include_daily: Include daily forecast
            
        Returns:
            WeatherData with current conditions and forecasts
        """
        # Geocode the city
        locations = await self.geocode(city)
        if not locations:
            raise WeatherError(f"Could not find location: {city}")
        
        location = locations[0]
        logger.info(f"Found location: {location.display_name} ({location.latitude}, {location.longitude})")
        
        # Get weather for the location
        weather = await self.get_weather(
            latitude=location.latitude,
            longitude=location.longitude,
            location_name=location.display_name,
            include_hourly=include_hourly,
            include_daily=include_daily,
        )
        
        # Update location with full details
        weather.location = location
        
        return weather
    
    async def will_it_rain(self, city: str, hours: int = 24) -> str:
        """
        Check if it will rain in the next N hours.
        
        Args:
            city: City name
            hours: Number of hours to check
            
        Returns:
            Natural language response about rain probability
        """
        weather = await self.get_weather_by_city(city, include_hourly=True, include_daily=False)
        
        rain_hours = []
        for hour in weather.hourly[:hours]:
            if hour.precipitation_probability > 30 or hour.precipitation > 0:
                rain_hours.append(hour)
        
        if not rain_hours:
            return f"No rain expected in {weather.location.display_name} for the next {hours} hours."
        
        # Find the first rain period
        first_rain = rain_hours[0]
        time_until = first_rain.time - datetime.now()
        hours_until = int(time_until.total_seconds() / 3600)
        
        if hours_until <= 1:
            return f"Rain is expected soon in {weather.location.display_name}! {first_rain.precipitation_probability}% chance of {first_rain.condition.lower()}."
        else:
            return f"Rain expected in about {hours_until} hours in {weather.location.display_name}. {first_rain.precipitation_probability}% chance of {first_rain.condition.lower()} around {first_rain.time.strftime('%I %p')}."


class WeatherError(Exception):
    """Weather service error."""
    pass


# Singleton instance
_weather_service: Optional[WeatherService] = None


def get_weather_service(
    cache_ttl: int = 1800,
    temperature_unit: str = "fahrenheit",
) -> WeatherService:
    """
    Get or create the weather service singleton.
    
    Args:
        cache_ttl: Cache time-to-live in seconds
        temperature_unit: "fahrenheit" or "celsius"
        
    Returns:
        WeatherService instance
    """
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService(
            cache_ttl=cache_ttl,
            temperature_unit=temperature_unit,
        )
    return _weather_service


# Tool functions for agent integration
async def get_current_weather(city: str) -> str:
    """
    Get current weather for a city.
    
    Args:
        city: City name (e.g., "Chicago", "New York")
        
    Returns:
        Weather summary string
    """
    try:
        service = get_weather_service()
        weather = await service.get_weather_by_city(city, include_hourly=False, include_daily=True)
        return weather.get_summary(include_forecast=True)
    except WeatherError as e:
        return f"Sorry, I couldn't get the weather for {city}: {e}"
    except Exception as e:
        logger.error(f"Weather error: {e}")
        return f"Sorry, there was an error getting the weather: {e}"


async def get_weather_forecast(city: str, days: int = 7) -> str:
    """
    Get weather forecast for a city.
    
    Args:
        city: City name
        days: Number of days (1-7)
        
    Returns:
        Forecast summary string
    """
    try:
        service = get_weather_service()
        weather = await service.get_weather_by_city(city, include_hourly=False, include_daily=True)
        
        lines = [f"**{days}-Day Forecast for {weather.location.display_name}**"]
        for day in weather.daily[:days]:
            day_name = day.date.strftime("%A, %b %d")
            lines.append(
                f"- {day_name}: {day.emoji} High {day.temperature_max:.0f}°F / Low {day.temperature_min:.0f}°F"
            )
            lines.append(f"  {day.condition}")
            if day.precipitation_probability_max > 20:
                lines.append(f"  {day.precipitation_probability_max}% chance of precipitation")
        
        return "\n".join(lines)
    except WeatherError as e:
        return f"Sorry, I couldn't get the forecast for {city}: {e}"
    except Exception as e:
        logger.error(f"Forecast error: {e}")
        return f"Sorry, there was an error getting the forecast: {e}"


async def check_rain(city: str, hours: int = 24) -> str:
    """
    Check if it will rain in a city.
    
    Args:
        city: City name
        hours: Hours to check ahead
        
    Returns:
        Rain prediction string
    """
    try:
        service = get_weather_service()
        return await service.will_it_rain(city, hours)
    except WeatherError as e:
        return f"Sorry, I couldn't check rain for {city}: {e}"
    except Exception as e:
        logger.error(f"Rain check error: {e}")
        return f"Sorry, there was an error checking for rain: {e}"


# Weather tool definition for agent system
WEATHER_TOOLS = [
    {
        "name": "get_current_weather",
        "description": "Get current weather conditions and short forecast for a city. Use this when the user asks about current weather, temperature, or conditions.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The city name, e.g., 'Chicago', 'New York', 'London, UK'"
                }
            },
            "required": ["city"]
        },
        "function": get_current_weather,
    },
    {
        "name": "get_weather_forecast",
        "description": "Get extended weather forecast for a city (up to 7 days). Use this when the user asks about future weather or weekly forecast.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The city name"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to forecast (1-7)",
                    "default": 7
                }
            },
            "required": ["city"]
        },
        "function": get_weather_forecast,
    },
    {
        "name": "check_rain",
        "description": "Check if it will rain in a city within the next 24 hours. Use this when the user asks about rain or precipitation.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The city name"
                },
                "hours": {
                    "type": "integer",
                    "description": "Hours to check ahead (default 24)",
                    "default": 24
                }
            },
            "required": ["city"]
        },
        "function": check_rain,
    },
]
