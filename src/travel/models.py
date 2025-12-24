"""
Data models for JARVIS Travel Module.

Defines structures for trips, flights, hotels, and activities.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import Enum
from typing import Any, Dict, List, Optional


class TripPurpose(Enum):
    """Purpose of the trip."""
    VACATION = "vacation"
    INTERVIEW = "interview"
    FAMILY = "family"
    BUSINESS = "business"
    CONFERENCE = "conference"
    OTHER = "other"


class TripStatus(Enum):
    """Status of the trip."""
    PLANNING = "planning"
    BOOKED = "booked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BookingType(Enum):
    """Type of booking."""
    FLIGHT = "flight"
    HOTEL = "hotel"
    CAR = "car"
    ACTIVITY = "activity"
    RESTAURANT = "restaurant"
    OTHER = "other"


class BudgetLevel(Enum):
    """Budget preference level."""
    BUDGET = "budget"
    MODERATE = "moderate"
    LUXURY = "luxury"


@dataclass
class Location:
    """A geographic location."""
    name: str
    city: str
    country: str = "USA"
    state: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    place_id: Optional[str] = None  # Google Places ID
    
    def __str__(self) -> str:
        if self.state:
            return f"{self.city}, {self.state}"
        return f"{self.city}, {self.country}"


@dataclass
class Flight:
    """Flight information."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    airline: str = ""
    flight_number: str = ""
    
    departure_airport: str = ""
    arrival_airport: str = ""
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    
    duration_minutes: int = 0
    stops: int = 0
    
    price: float = 0.0
    currency: str = "USD"
    cabin_class: str = "economy"
    
    booking_url: Optional[str] = None
    source: str = ""  # API source
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "airline": self.airline,
            "flight_number": self.flight_number,
            "departure_airport": self.departure_airport,
            "arrival_airport": self.arrival_airport,
            "departure_time": self.departure_time.isoformat() if self.departure_time else None,
            "arrival_time": self.arrival_time.isoformat() if self.arrival_time else None,
            "duration_minutes": self.duration_minutes,
            "stops": self.stops,
            "price": self.price,
            "currency": self.currency,
            "cabin_class": self.cabin_class,
            "booking_url": self.booking_url,
        }


@dataclass
class Hotel:
    """Hotel information."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    address: str = ""
    city: str = ""
    
    rating: float = 0.0
    stars: int = 0
    reviews_count: int = 0
    
    price_per_night: float = 0.0
    currency: str = "USD"
    
    amenities: List[str] = field(default_factory=list)
    photos: List[str] = field(default_factory=list)
    
    distance_to_center: Optional[float] = None  # km
    distance_to_target: Optional[float] = None  # km to specific location
    
    booking_url: Optional[str] = None
    source: str = ""
    
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "city": self.city,
            "rating": self.rating,
            "stars": self.stars,
            "price_per_night": self.price_per_night,
            "currency": self.currency,
            "amenities": self.amenities,
            "booking_url": self.booking_url,
        }


@dataclass
class Activity:
    """Activity or attraction."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    category: str = ""  # restaurant, attraction, museum, etc.
    
    location: Optional[Location] = None
    
    rating: float = 0.0
    reviews_count: int = 0
    price_level: int = 0  # 0-4 (free to expensive)
    
    opening_hours: Optional[str] = None
    duration_hours: float = 1.0
    
    is_free: bool = False
    student_discount: bool = False
    
    photos: List[str] = field(default_factory=list)
    website: Optional[str] = None
    phone: Optional[str] = None
    
    source: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "rating": self.rating,
            "price_level": self.price_level,
            "is_free": self.is_free,
            "student_discount": self.student_discount,
        }


@dataclass
class ItineraryItem:
    """A single item in the itinerary."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    day: int = 1
    time_slot: str = "morning"  # morning, afternoon, evening
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    
    activity_type: str = ""  # flight, hotel_checkin, restaurant, attraction, etc.
    title: str = ""
    description: str = ""
    location: Optional[str] = None
    
    estimated_cost: float = 0.0
    notes: str = ""
    
    booking_required: bool = False
    booking_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "day": self.day,
            "time_slot": self.time_slot,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "activity_type": self.activity_type,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "estimated_cost": self.estimated_cost,
        }


@dataclass
class Itinerary:
    """Complete trip itinerary."""
    items: List[ItineraryItem] = field(default_factory=list)
    
    def get_day(self, day: int) -> List[ItineraryItem]:
        """Get items for a specific day."""
        return [item for item in self.items if item.day == day]
    
    def total_cost(self) -> float:
        """Calculate total estimated cost."""
        return sum(item.estimated_cost for item in self.items)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "total_cost": self.total_cost(),
        }


@dataclass
class PackingItem:
    """An item in the packing list."""
    name: str
    category: str  # clothes, tech, documents, toiletries, etc.
    packed: bool = False
    essential: bool = False
    notes: str = ""


@dataclass
class PackingList:
    """Complete packing list for a trip."""
    items: List[PackingItem] = field(default_factory=list)
    weather_notes: str = ""
    destination_tips: List[str] = field(default_factory=list)
    
    def get_by_category(self, category: str) -> List[PackingItem]:
        """Get items by category."""
        return [item for item in self.items if item.category == category]
    
    def categories(self) -> List[str]:
        """Get all unique categories."""
        return list(set(item.category for item in self.items))


@dataclass
class TripBudget:
    """Budget breakdown for a trip."""
    flights: float = 0.0
    hotels: float = 0.0
    food: float = 0.0
    activities: float = 0.0
    transport: float = 0.0
    other: float = 0.0
    
    def total(self) -> float:
        return self.flights + self.hotels + self.food + self.activities + self.transport + self.other
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "flights": self.flights,
            "hotels": self.hotels,
            "food": self.food,
            "activities": self.activities,
            "transport": self.transport,
            "other": self.other,
            "total": self.total(),
        }


@dataclass
class Trip:
    """Complete trip information."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    
    destination: Optional[Location] = None
    origin: Optional[Location] = None
    
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    purpose: TripPurpose = TripPurpose.VACATION
    status: TripStatus = TripStatus.PLANNING
    budget_level: BudgetLevel = BudgetLevel.MODERATE
    
    # Components
    flights: List[Flight] = field(default_factory=list)
    hotels: List[Hotel] = field(default_factory=list)
    activities: List[Activity] = field(default_factory=list)
    itinerary: Optional[Itinerary] = None
    packing_list: Optional[PackingList] = None
    
    # Budget
    budget: Optional[TripBudget] = None
    actual_spent: float = 0.0
    
    # Metadata
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def duration_days(self) -> int:
        """Calculate trip duration in days."""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "destination": str(self.destination) if self.destination else None,
            "origin": str(self.origin) if self.origin else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "duration_days": self.duration_days,
            "purpose": self.purpose.value,
            "status": self.status.value,
            "budget_level": self.budget_level.value,
            "budget": self.budget.to_dict() if self.budget else None,
            "actual_spent": self.actual_spent,
        }


@dataclass
class WeatherForecast:
    """Weather forecast for a location."""
    date: date
    location: str
    
    temp_high: float
    temp_low: float
    temp_unit: str = "F"
    
    condition: str = ""  # sunny, cloudy, rainy, etc.
    precipitation_chance: int = 0
    humidity: int = 0
    wind_speed: float = 0.0
    
    icon: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "location": self.location,
            "temp_high": self.temp_high,
            "temp_low": self.temp_low,
            "condition": self.condition,
            "precipitation_chance": self.precipitation_chance,
        }


@dataclass
class TripSearchCriteria:
    """Search criteria for trip planning."""
    destination: str
    origin: str = "San Francisco, CA"
    
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    flexible_dates: bool = False
    
    travelers: int = 1
    budget_level: BudgetLevel = BudgetLevel.MODERATE
    max_budget: Optional[float] = None
    
    purpose: TripPurpose = TripPurpose.VACATION
    
    # Preferences
    preferred_airlines: List[str] = field(default_factory=list)
    hotel_min_rating: float = 3.0
    include_activities: bool = True
    
    # Special modes
    interview_mode: bool = False
    interview_company: Optional[str] = None
    budget_backpacker: bool = False
