"""
Trip Planner for JARVIS Travel Module.

Generates complete trip itineraries with flights, hotels, and activities.
"""

import os
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .models import (
    Trip, TripPurpose, TripStatus, BudgetLevel,
    Location, Flight, Hotel, Activity,
    Itinerary, ItineraryItem, PackingList, PackingItem,
    TripBudget, TripSearchCriteria, WeatherForecast
)
from .apis import (
    AmadeusAPI, GooglePlacesAPI, OpenTripMapAPI, WeatherAPI,
    get_airport_code
)


# Budget estimates per day by level
DAILY_BUDGETS = {
    BudgetLevel.BUDGET: {"food": 30, "activities": 20, "transport": 15},
    BudgetLevel.MODERATE: {"food": 60, "activities": 40, "transport": 30},
    BudgetLevel.LUXURY: {"food": 120, "activities": 100, "transport": 60},
}

# Packing templates by weather/purpose
PACKING_TEMPLATES = {
    "winter": [
        PackingItem("Warm jacket", "clothes", essential=True),
        PackingItem("Warm layers (sweaters)", "clothes", essential=True),
        PackingItem("Warm socks", "clothes"),
        PackingItem("Gloves", "clothes"),
        PackingItem("Beanie/hat", "clothes"),
        PackingItem("Scarf", "clothes"),
    ],
    "rainy": [
        PackingItem("Rain jacket", "clothes", essential=True),
        PackingItem("Umbrella", "accessories", essential=True),
        PackingItem("Waterproof shoes", "clothes"),
    ],
    "summer": [
        PackingItem("T-shirts", "clothes", essential=True),
        PackingItem("Shorts", "clothes"),
        PackingItem("Sunglasses", "accessories", essential=True),
        PackingItem("Sunscreen", "toiletries", essential=True),
        PackingItem("Hat/cap", "accessories"),
    ],
    "interview": [
        PackingItem("Business casual outfit", "clothes", essential=True),
        PackingItem("Dress shoes", "clothes", essential=True),
        PackingItem("Resume copies (printed)", "documents", essential=True),
        PackingItem("Portfolio/laptop", "tech", essential=True),
        PackingItem("Notebook and pen", "documents"),
    ],
    "base": [
        PackingItem("Phone charger", "tech", essential=True),
        PackingItem("ID/Driver's license", "documents", essential=True),
        PackingItem("Booking confirmations", "documents", essential=True),
        PackingItem("Comfortable walking shoes", "clothes", essential=True),
        PackingItem("Toiletries bag", "toiletries", essential=True),
        PackingItem("Medications (if any)", "toiletries"),
        PackingItem("Headphones", "tech"),
        PackingItem("Laptop", "tech"),
        PackingItem("Laptop charger", "tech"),
    ],
}

# City tips
CITY_TIPS = {
    "seattle": [
        "Rain is usually light drizzle - umbrella works better than raincoat",
        "Coffee shops on every corner - try local roasters",
        "Pike Place Market is a must-visit",
        "Public transit is good - get an ORCA card",
    ],
    "new york": [
        "Walk or take subway - don't drive",
        "Get a MetroCard for unlimited rides",
        "Book restaurants in advance for popular spots",
        "Times Square is touristy - explore other neighborhoods",
    ],
    "los angeles": [
        "You'll need a car or Uber - public transit is limited",
        "Traffic is bad 7-10am and 4-7pm",
        "Beach cities are cooler than inland",
        "Parking can be expensive downtown",
    ],
    "san francisco": [
        "Layers are essential - weather changes quickly",
        "BART and Muni are good for getting around",
        "Fog is common in summer mornings",
        "Cable cars are fun but touristy",
    ],
    "mountain view": [
        "Caltrain connects to SF and San Jose",
        "Rent a bike - the area is very bike-friendly",
        "Google campus has great cafeterias",
        "Downtown has good restaurants on Castro Street",
    ],
}


class TripPlanner:
    """
    AI Trip Planner that generates complete itineraries.
    
    Features:
    - Flight search and comparison
    - Hotel recommendations
    - Activity suggestions
    - Day-by-day itinerary
    - Budget estimation
    - Packing list generation
    - Interview travel mode
    """
    
    def __init__(
        self,
        amadeus_api: Optional[AmadeusAPI] = None,
        places_api: Optional[GooglePlacesAPI] = None,
        attractions_api: Optional[OpenTripMapAPI] = None,
        weather_api: Optional[WeatherAPI] = None,
    ):
        self.amadeus = amadeus_api or AmadeusAPI()
        self.places = places_api or GooglePlacesAPI()
        self.attractions = attractions_api or OpenTripMapAPI()
        self.weather = weather_api or WeatherAPI()
    
    async def plan_trip(self, criteria: TripSearchCriteria) -> Trip:
        """
        Plan a complete trip based on criteria.
        
        Args:
            criteria: Search criteria for the trip
            
        Returns:
            Complete Trip object with all components
        """
        logger.info(f"Planning trip to {criteria.destination}")
        
        # Create trip
        trip = Trip(
            name=f"Trip to {criteria.destination}",
            destination=Location(
                name=criteria.destination,
                city=criteria.destination,
            ),
            origin=Location(
                name=criteria.origin,
                city=criteria.origin,
            ),
            start_date=criteria.start_date,
            end_date=criteria.end_date,
            purpose=criteria.purpose,
            budget_level=criteria.budget_level,
            status=TripStatus.PLANNING,
        )
        
        # Search flights
        if criteria.start_date:
            trip.flights = await self.search_flights(criteria)
        
        # Search hotels
        if criteria.start_date and criteria.end_date:
            trip.hotels = await self.search_hotels(criteria)
        
        # Search activities
        if criteria.include_activities:
            trip.activities = await self.search_activities(criteria)
        
        # Generate itinerary
        trip.itinerary = await self.generate_itinerary(trip, criteria)
        
        # Calculate budget
        trip.budget = self.calculate_budget(trip, criteria)
        
        # Generate packing list
        weather = await self.get_weather(criteria.destination, criteria.start_date)
        trip.packing_list = self.generate_packing_list(trip, weather)
        
        return trip
    
    async def search_flights(self, criteria: TripSearchCriteria) -> List[Flight]:
        """Search for flights."""
        origin_code = get_airport_code(criteria.origin)
        dest_code = get_airport_code(criteria.destination)
        
        flights = await self.amadeus.search_flights(
            origin=origin_code,
            destination=dest_code,
            departure_date=criteria.start_date,
            return_date=criteria.end_date,
            adults=criteria.travelers,
            max_results=10,
        )
        
        # Sort by price
        flights.sort(key=lambda f: f.price)
        
        # Filter by preferred airlines if specified
        if criteria.preferred_airlines:
            preferred = [
                f for f in flights
                if any(airline.lower() in f.airline.lower() for airline in criteria.preferred_airlines)
            ]
            if preferred:
                flights = preferred + [f for f in flights if f not in preferred]
        
        return flights[:5]  # Return top 5
    
    async def search_hotels(self, criteria: TripSearchCriteria) -> List[Hotel]:
        """Search for hotels."""
        # Use Google Places for hotel search
        query = f"hotels in {criteria.destination}"
        
        if criteria.budget_level == BudgetLevel.BUDGET:
            query = f"budget hotels hostels in {criteria.destination}"
        elif criteria.budget_level == BudgetLevel.LUXURY:
            query = f"luxury hotels in {criteria.destination}"
        
        # If interview mode, search near company
        if criteria.interview_mode and criteria.interview_company:
            query = f"hotels near {criteria.interview_company} {criteria.destination}"
        
        activities = await self.places.search_places(
            query=query,
            place_type="lodging",
            max_results=10,
        )
        
        # Convert to Hotel objects
        hotels = []
        for activity in activities:
            hotel = Hotel(
                name=activity.name,
                address=activity.location.address if activity.location else "",
                city=criteria.destination,
                rating=activity.rating,
                reviews_count=activity.reviews_count,
                price_per_night=self._estimate_hotel_price(activity.price_level, criteria.budget_level),
                latitude=activity.location.latitude if activity.location else None,
                longitude=activity.location.longitude if activity.location else None,
                source="google_places",
            )
            hotels.append(hotel)
        
        # Sort by rating
        hotels.sort(key=lambda h: h.rating, reverse=True)
        
        return hotels[:5]
    
    def _estimate_hotel_price(self, price_level: int, budget: BudgetLevel) -> float:
        """Estimate hotel price based on price level."""
        base_prices = {
            0: 50,   # Free/very cheap
            1: 80,   # Budget
            2: 120,  # Moderate
            3: 180,  # Expensive
            4: 300,  # Very expensive
        }
        return base_prices.get(price_level, 100)
    
    async def search_activities(self, criteria: TripSearchCriteria) -> List[Activity]:
        """Search for activities and attractions."""
        activities = []
        
        # Search restaurants
        restaurants = await self.places.search_places(
            query=f"restaurants in {criteria.destination}",
            place_type="restaurant",
            max_results=10,
        )
        activities.extend(restaurants[:5])
        
        # Search attractions
        attractions = await self.places.search_places(
            query=f"attractions things to do in {criteria.destination}",
            place_type="tourist_attraction",
            max_results=10,
        )
        activities.extend(attractions[:5])
        
        # If budget mode, look for free activities
        if criteria.budget_level == BudgetLevel.BUDGET:
            free_activities = await self.places.search_places(
                query=f"free things to do in {criteria.destination}",
                max_results=5,
            )
            activities.extend(free_activities)
        
        return activities
    
    async def generate_itinerary(
        self,
        trip: Trip,
        criteria: TripSearchCriteria,
    ) -> Itinerary:
        """Generate a day-by-day itinerary."""
        itinerary = Itinerary()
        
        if not trip.start_date or not trip.end_date:
            return itinerary
        
        num_days = trip.duration_days
        
        for day in range(1, num_days + 1):
            current_date = trip.start_date + timedelta(days=day - 1)
            
            # Day 1: Arrival
            if day == 1:
                # Flight arrival
                if trip.flights:
                    flight = trip.flights[0]
                    itinerary.items.append(ItineraryItem(
                        day=day,
                        time_slot="morning",
                        activity_type="flight",
                        title=f"Flight to {criteria.destination}",
                        description=f"{flight.airline} - {flight.departure_airport} to {flight.arrival_airport}",
                        estimated_cost=flight.price,
                    ))
                
                # Hotel check-in
                if trip.hotels:
                    hotel = trip.hotels[0]
                    itinerary.items.append(ItineraryItem(
                        day=day,
                        time_slot="afternoon",
                        activity_type="hotel_checkin",
                        title=f"Check in: {hotel.name}",
                        location=hotel.address,
                        estimated_cost=hotel.price_per_night,
                    ))
                
                # Evening: Explore neighborhood
                itinerary.items.append(ItineraryItem(
                    day=day,
                    time_slot="evening",
                    activity_type="explore",
                    title="Explore neighborhood",
                    description="Walk around, find dinner spot",
                    estimated_cost=DAILY_BUDGETS[criteria.budget_level]["food"] / 2,
                ))
            
            # Last day: Departure
            elif day == num_days:
                # Hotel checkout
                itinerary.items.append(ItineraryItem(
                    day=day,
                    time_slot="morning",
                    activity_type="hotel_checkout",
                    title="Hotel checkout",
                    description="Pack and check out",
                ))
                
                # Return flight
                if trip.flights:
                    itinerary.items.append(ItineraryItem(
                        day=day,
                        time_slot="afternoon",
                        activity_type="flight",
                        title=f"Return flight to {criteria.origin}",
                        description="Head to airport",
                    ))
            
            # Middle days: Activities
            else:
                # Morning activity
                if trip.activities:
                    morning_activity = trip.activities[min(day * 2 - 2, len(trip.activities) - 1)]
                    itinerary.items.append(ItineraryItem(
                        day=day,
                        time_slot="morning",
                        activity_type="attraction",
                        title=morning_activity.name,
                        description=morning_activity.description,
                        location=morning_activity.location.address if morning_activity.location else None,
                        estimated_cost=DAILY_BUDGETS[criteria.budget_level]["activities"] / 2,
                    ))
                
                # Lunch
                restaurants = [a for a in trip.activities if a.category == "restaurant"]
                if restaurants:
                    lunch = restaurants[min(day - 1, len(restaurants) - 1)]
                    itinerary.items.append(ItineraryItem(
                        day=day,
                        time_slot="afternoon",
                        start_time=time(12, 0),
                        activity_type="restaurant",
                        title=f"Lunch: {lunch.name}",
                        location=lunch.location.address if lunch.location else None,
                        estimated_cost=DAILY_BUDGETS[criteria.budget_level]["food"] / 3,
                    ))
                
                # Afternoon activity
                if len(trip.activities) > day * 2 - 1:
                    afternoon_activity = trip.activities[day * 2 - 1]
                    itinerary.items.append(ItineraryItem(
                        day=day,
                        time_slot="afternoon",
                        activity_type="attraction",
                        title=afternoon_activity.name,
                        description=afternoon_activity.description,
                        estimated_cost=DAILY_BUDGETS[criteria.budget_level]["activities"] / 2,
                    ))
                
                # Dinner
                itinerary.items.append(ItineraryItem(
                    day=day,
                    time_slot="evening",
                    activity_type="restaurant",
                    title="Dinner",
                    description="Find a local restaurant",
                    estimated_cost=DAILY_BUDGETS[criteria.budget_level]["food"] / 2,
                ))
        
        return itinerary
    
    def calculate_budget(self, trip: Trip, criteria: TripSearchCriteria) -> TripBudget:
        """Calculate estimated budget for the trip."""
        budget = TripBudget()
        
        num_days = trip.duration_days or 1
        daily = DAILY_BUDGETS[criteria.budget_level]
        
        # Flights
        if trip.flights:
            budget.flights = trip.flights[0].price
        
        # Hotels
        if trip.hotels:
            budget.hotels = trip.hotels[0].price_per_night * (num_days - 1)
        
        # Daily expenses
        budget.food = daily["food"] * num_days
        budget.activities = daily["activities"] * num_days
        budget.transport = daily["transport"] * num_days
        
        return budget
    
    async def get_weather(
        self,
        destination: str,
        start_date: Optional[date],
    ) -> List[WeatherForecast]:
        """Get weather forecast for destination."""
        if not start_date:
            return []
        
        # Only get forecast if trip is within 10 days
        days_until = (start_date - date.today()).days
        if days_until > 10 or days_until < 0:
            return []
        
        return await self.weather.get_forecast(destination, days=7)
    
    def generate_packing_list(
        self,
        trip: Trip,
        weather: List[WeatherForecast],
    ) -> PackingList:
        """Generate a packing list based on trip and weather."""
        packing_list = PackingList()
        
        # Add base items
        packing_list.items.extend(PACKING_TEMPLATES["base"])
        
        # Determine weather conditions
        if weather:
            avg_temp = sum(w.temp_high for w in weather) / len(weather)
            avg_precip = sum(w.precipitation_chance for w in weather) / len(weather)
            
            if avg_temp < 50:
                packing_list.items.extend(PACKING_TEMPLATES["winter"])
                packing_list.weather_notes = f"Cold weather expected ({avg_temp:.0f}°F average)"
            elif avg_temp > 75:
                packing_list.items.extend(PACKING_TEMPLATES["summer"])
                packing_list.weather_notes = f"Warm weather expected ({avg_temp:.0f}°F average)"
            
            if avg_precip > 30:
                packing_list.items.extend(PACKING_TEMPLATES["rainy"])
                packing_list.weather_notes += f", {avg_precip:.0f}% chance of rain"
        
        # Add interview items if interview trip
        if trip.purpose == TripPurpose.INTERVIEW:
            packing_list.items.extend(PACKING_TEMPLATES["interview"])
        
        # Add destination tips
        dest_lower = trip.destination.city.lower() if trip.destination else ""
        for city, tips in CITY_TIPS.items():
            if city in dest_lower:
                packing_list.destination_tips = tips
                break
        
        # Remove duplicates
        seen = set()
        unique_items = []
        for item in packing_list.items:
            if item.name not in seen:
                seen.add(item.name)
                unique_items.append(item)
        packing_list.items = unique_items
        
        return packing_list
    
    async def plan_interview_trip(
        self,
        company: str,
        location: str,
        interview_date: date,
    ) -> Trip:
        """
        Plan a trip specifically for an interview.
        
        Arrives day before, leaves day after.
        Focuses on hotels near company.
        """
        # Arrive day before, leave day after
        start_date = interview_date - timedelta(days=1)
        end_date = interview_date + timedelta(days=1)
        
        criteria = TripSearchCriteria(
            destination=location,
            origin="San Francisco, CA",
            start_date=start_date,
            end_date=end_date,
            purpose=TripPurpose.INTERVIEW,
            budget_level=BudgetLevel.MODERATE,
            interview_mode=True,
            interview_company=company,
        )
        
        trip = await self.plan_trip(criteria)
        trip.name = f"{company} Interview Trip"
        
        # Add interview to itinerary
        if trip.itinerary:
            interview_item = ItineraryItem(
                day=2,  # Middle day
                time_slot="morning",
                start_time=time(9, 0),
                activity_type="interview",
                title=f"Interview at {company}",
                description="Arrive 15 minutes early. Bring resume copies.",
                location=f"{company} office, {location}",
                notes="Dress code: Business casual",
            )
            trip.itinerary.items.insert(0, interview_item)
        
        return trip
    
    async def plan_budget_trip(
        self,
        destination: str,
        days: int,
    ) -> Trip:
        """Plan a budget-friendly trip."""
        start_date = date.today() + timedelta(days=7)
        end_date = start_date + timedelta(days=days - 1)
        
        criteria = TripSearchCriteria(
            destination=destination,
            origin="San Francisco, CA",
            start_date=start_date,
            end_date=end_date,
            purpose=TripPurpose.VACATION,
            budget_level=BudgetLevel.BUDGET,
            budget_backpacker=True,
        )
        
        trip = await self.plan_trip(criteria)
        trip.name = f"Budget Trip to {destination}"
        
        return trip


def format_trip_summary(trip: Trip) -> str:
    """Format trip as a readable summary."""
    lines = [
        f"🗺️ **{trip.name}**",
        "",
    ]
    
    if trip.destination:
        lines.append(f"📍 **Destination:** {trip.destination}")
    
    if trip.start_date and trip.end_date:
        lines.append(f"📅 **Dates:** {trip.start_date.strftime('%b %d')} - {trip.end_date.strftime('%b %d')} ({trip.duration_days} days)")
    
    lines.append("")
    
    # Flights
    if trip.flights:
        lines.append("✈️ **Flights:**")
        for flight in trip.flights[:3]:
            stops = f" ({flight.stops} stop{'s' if flight.stops > 1 else ''})" if flight.stops > 0 else " (nonstop)"
            lines.append(f"  - {flight.airline}: ${flight.price:.0f}{stops}")
        lines.append("")
    
    # Hotels
    if trip.hotels:
        lines.append("🏨 **Hotels:**")
        for hotel in trip.hotels[:3]:
            rating = f"⭐{hotel.rating:.1f}" if hotel.rating else ""
            lines.append(f"  - {hotel.name}: ${hotel.price_per_night:.0f}/night {rating}")
        lines.append("")
    
    # Budget
    if trip.budget:
        lines.append("💰 **Estimated Budget:**")
        lines.append(f"  - Flights: ${trip.budget.flights:.0f}")
        lines.append(f"  - Hotels: ${trip.budget.hotels:.0f}")
        lines.append(f"  - Food: ${trip.budget.food:.0f}")
        lines.append(f"  - Activities: ${trip.budget.activities:.0f}")
        lines.append(f"  - **Total: ${trip.budget.total():.0f}**")
        lines.append("")
    
    # Packing list preview
    if trip.packing_list:
        lines.append("🎒 **Packing Highlights:**")
        essentials = [item for item in trip.packing_list.items if item.essential][:5]
        for item in essentials:
            lines.append(f"  ☐ {item.name}")
        
        if trip.packing_list.weather_notes:
            lines.append(f"  ℹ️ {trip.packing_list.weather_notes}")
        lines.append("")
    
    # Tips
    if trip.packing_list and trip.packing_list.destination_tips:
        lines.append("💡 **Tips:**")
        for tip in trip.packing_list.destination_tips[:3]:
            lines.append(f"  - {tip}")
    
    return "\n".join(lines)


def format_packing_list(packing_list: PackingList) -> str:
    """Format packing list as a readable checklist."""
    lines = ["🎒 **Packing List**", ""]
    
    if packing_list.weather_notes:
        lines.append(f"🌤️ *{packing_list.weather_notes}*")
        lines.append("")
    
    # Group by category
    for category in packing_list.categories():
        items = packing_list.get_by_category(category)
        lines.append(f"**{category.title()}:**")
        for item in items:
            check = "☐"
            essential = " ⚠️" if item.essential else ""
            lines.append(f"  {check} {item.name}{essential}")
        lines.append("")
    
    # Tips
    if packing_list.destination_tips:
        lines.append("**Destination Tips:**")
        for tip in packing_list.destination_tips:
            lines.append(f"  - {tip}")
    
    return "\n".join(lines)
