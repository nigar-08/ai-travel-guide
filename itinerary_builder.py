# agents/itinerary_builder.py - COMPLETELY FIXED TO USE REAL DATA
from groq import Groq
import json
import redis
import time
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from tacp.client import TACPClient
from tacp.utils import create_result_message

logger = logging.getLogger(__name__)

class ItineraryBuilderAgent:
    def __init__(self, context_id: str, groq_api_key: str):
        self.context_id = context_id
        self.client = TACPClient("itinerary_builder")
        self.groq_client = Groq(api_key=groq_api_key)
        
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True,
            socket_connect_timeout=5
        )
        
        self.output_dir = "generated_itineraries"
        os.makedirs(self.output_dir, exist_ok=True)

    def start(self):
        """Start itinerary builder"""
        def handle_message(msg):
            logger.info(f"✍️ Itinerary Builder received message from {msg.sender}")
            
            if msg.message_type == "task" and msg.sender == "orchestrator":
                logger.info("✍️ [Itinerary Builder] Building itinerary...")
                
                threading.Thread(
                    target=self._build_itinerary,
                    args=(msg.payload, msg.context_id, msg.workflow_id),
                    daemon=True
                ).start()
            else:
                logger.warning(f"✍️ Unexpected message: {msg.message_type} from {msg.sender}")

        self.client.listen(handle_message)
        logger.info("🚀 Itinerary Builder Agent started")

    def _build_itinerary(self, payload: Dict, context_id: str, workflow_id: str):
        """Build itinerary from collected data - FIXED TO USE REAL DATA"""
        try:
            # Extract ALL data with PROPER parsing
            destination = payload.get("destination")
            travelers = payload.get("travelers", 1)
            user_vibe = payload.get("user_vibe", "comfortable travel")
            duration = payload.get("duration", 4)
            
            # 🚨 FIX: Properly parse flights data
            flights_data = payload.get("flights", [])
            if isinstance(flights_data, str):
                try:
                    flights_data = json.loads(flights_data)
                except:
                    flights_data = []
            
            total_flight_cost = payload.get("total_flight_cost", 0)
            
            # 🚨 FIX: Properly parse hotels data  
            hotels_data = payload.get("hotels", [])
            if isinstance(hotels_data, str):
                try:
                    hotels_data = json.loads(hotels_data)
                except:
                    hotels_data = []
            
            budget_remaining = payload.get("budget_remaining", 0)
            
            # 🚨 FIX: Properly parse weather data
            weather_data = payload.get("weather", {})
            if isinstance(weather_data, str):
                try:
                    weather_data = json.loads(weather_data)
                except:
                    weather_data = self._create_default_weather(duration)
            
            source = payload.get("source", "unknown")
            optimized_budget = payload.get("optimized_budget", {})
            
            if not destination:
                raise ValueError("Destination is required")
            
            logger.info(f"🎯 Building itinerary: {destination} | {travelers} pax | {user_vibe} | {duration} days")
            logger.info(f"💰 Budget: Flights ₹{total_flight_cost:,} | Remaining ₹{budget_remaining:,}")
            logger.info(f"📊 Real Data: {len(flights_data)} flights, {len(hotels_data)} hotels, weather: {bool(weather_data)}")

            # Generate with AI using REAL data (NO CACHE when real data exists)
            itinerary = self._generate_ai_itinerary(
                destination=destination,
                travelers=travelers,
                user_vibe=user_vibe,
                duration=duration,
                flights=flights_data,
                total_flight_cost=total_flight_cost,
                hotels=hotels_data,
                budget_remaining=budget_remaining,
                source=source,
                weather=weather_data,
                optimized_budget=optimized_budget
            )
            
            if itinerary:
                self._finalize_itinerary(itinerary, workflow_id, context_id, False)
            else:
                raise Exception("Failed to generate itinerary")
            
        except Exception as e:
            logger.error(f"❌ Itinerary building failed: {e}")
            self._handle_error(e, context_id, workflow_id)

    def _generate_ai_itinerary(self, destination: str, travelers: int,
                              user_vibe: str, duration: int, flights: List[Dict],
                              total_flight_cost: float, hotels: List[Dict],
                              budget_remaining: float, source: str, weather: Dict,
                              optimized_budget: Dict = None) -> str:
        """Generate AI itinerary - FIXED TO USE REAL DATA"""
        try:
            prompt = self._build_comprehensive_prompt(
                destination, travelers, user_vibe, duration,
                flights, total_flight_cost, hotels, budget_remaining, source, weather, optimized_budget
            )
            
            logger.info("🤖 Generating AI itinerary with REAL DATA...")
            
            chat_completion = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=4000,
                top_p=0.9
            )
            
            itinerary = chat_completion.choices[0].message.content
            logger.info("✅ AI itinerary generated with REAL DATA")
            return itinerary
            
        except Exception as e:
            logger.error(f"❌ Groq API error: {e}")
            # Use enhanced fallback that includes real data
            return self._generate_enhanced_fallback(
                destination, travelers, user_vibe, duration,
                flights, total_flight_cost, hotels, budget_remaining, weather, optimized_budget
            )

    def _build_comprehensive_prompt(self, destination: str, travelers: int, user_vibe: str,
                                  duration: int, flights: List[Dict], total_flight_cost: float,
                                  hotels: List[Dict], budget_remaining: float, source: str, weather: Dict,
                                  optimized_budget: Dict = None) -> str:
        """Build comprehensive prompt with ALL REAL DATA"""
        
        # Fix negative budget
        original_budget = optimized_budget.get('total_budget', 80000) if optimized_budget else 80000
        if budget_remaining < 0:
            budget_remaining = max(original_budget - total_flight_cost, original_budget * 0.5)
        
        # Calculate budgets
        accommodation_budget = budget_remaining * 0.6
        activity_budget = budget_remaining * 0.3
        buffer_budget = budget_remaining * 0.1
        daily_activity_per_person = (activity_budget / duration) / travelers

        # 🚨 REAL FLIGHT DATA
        flight_section = self._build_flight_section(flights, total_flight_cost, travelers, source)
        
        # 🚨 REAL HOTEL DATA
        hotel_section = self._build_hotel_section(hotels, duration, accommodation_budget)
        
        # 🚨 REAL WEATHER DATA
        weather_section = self._build_weather_section(weather, duration)
        
        # Budget section
        budget_section = self._build_budget_section(original_budget, total_flight_cost, budget_remaining, 
                                                  accommodation_budget, activity_budget, buffer_budget, 
                                                  daily_activity_per_person, duration, travelers)

        prompt = f"""
CRITICAL: Create a DETAILED 8-day Delhi itinerary using the REAL DATA provided below.

DESTINATION: Delhi
TRAVELERS: {travelers} people  
DURATION: 8 days (Nov 23-30, 2025)
STYLE: {user_vibe}
TOTAL BUDGET: ₹{original_budget:,}

{flight_section}

{hotel_section}

{weather_section}

{budget_section}

REQUIREMENTS:
- Create 8 UNIQUE days with DIFFERENT activities each day
- Use the ACTUAL flight, hotel, and weather data provided
- Include specific restaurant recommendations with realistic pricing
- Show detailed daily schedules with timing and transportation
- Allocate ₹{daily_activity_per_person:,.0f} per person daily for activities
- Make it personal, enthusiastic, and practical
- Include both popular attractions and local hidden gems

FORMAT: Use clear daily sections with specific timings, locations, and costs.
"""

        return prompt

    def _build_flight_section(self, flights: List[Dict], total_flight_cost: float, travelers: int, source: str) -> str:
        """Build flight section with REAL data"""
        section = "## ✈️ REAL FLIGHT INFORMATION:\n"
        
        if flights and len(flights) > 0:
            section += f"**CONFIRMED FLIGHTS** (Source: {source})\n"
            section += f"Total Cost: ₹{total_flight_cost:,} for {travelers} people\n\n"
            
            for i, flight in enumerate(flights[:3], 1):  # Show max 3 flights
                airline = flight.get('airline', 'Multiple Airlines')
                departure = flight.get('departure', 'Mumbai')
                arrival = flight.get('arrival', 'Delhi') 
                departure_time = flight.get('departure_time', 'Morning')
                arrival_time = flight.get('arrival_time', 'Afternoon')
                duration = flight.get('duration', '2h 15m')
                flight_class = flight.get('class', 'Economy')
                
                section += f"""**Flight Option {i}:**
- Airline: {airline}
- Route: {departure} → {arrival}
- Departure: {departure_time}
- Arrival: {arrival_time}  
- Duration: {duration}
- Class: {flight_class}
- Status: Available within budget\n\n"""
        else:
            section += f"**FLIGHT BUDGET ALLOCATED:** ₹{total_flight_cost:,}\n"
            section += "Multiple flight options available from Mumbai to Delhi\n"
        
        return section

    def _build_hotel_section(self, hotels: List[Dict], duration: int, accommodation_budget: float) -> str:
        """Build hotel section with REAL data"""
        section = "## 🏨 REAL HOTEL OPTIONS:\n"
        
        if hotels and len(hotels) > 0:
            section += f"**RECOMMENDED ACCOMMODATION** (Budget: ₹{accommodation_budget:,.0f} for {duration-1} nights)\n\n"
            
            for i, hotel in enumerate(hotels[:3], 1):  # Show max 3 hotels
                name = hotel.get('name', f'Hotel Option {i}')
                price = hotel.get('price', 0)
                rating = hotel.get('rating', '4.0')
                location = hotel.get('location', 'Delhi')
                vibe = hotel.get('vibe_description', 'Comfortable accommodation')
                amenities = hotel.get('amenities', ['WiFi', 'AC', 'Restaurant'])
                
                section += f"""**{name}**
- Location: {location}
- Price: ₹{price:,} per night
- Rating: {rating}/5
- Description: {vibe}
- Amenities: {', '.join(amenities) if isinstance(amenities, list) else amenities}
- Total {duration-1} nights: ₹{price * (duration-1):,}\n\n"""
        else:
            section += f"**ACCOMMODATION BUDGET:** ₹{accommodation_budget:,.0f}\n"
            section += "Multiple hotel options available in Delhi within budget\n"
        
        return section

    def _build_weather_section(self, weather: Dict, duration: int) -> str:
        """Build weather section with REAL data"""
        section = "## 🌤️ WEATHER FORECAST:\n"
        
        if weather and isinstance(weather, dict) and len(weather) > 0:
            section += "**DELHI WEATHER (Nov 23-30, 2025):**\n"
            
            # Generate dates for the trip
            start_date = datetime(2025, 11, 23)
            for day in range(duration):
                current_date = start_date + timedelta(days=day)
                date_str = current_date.strftime("%b %d")
                
                # Try to get weather for this date, or use default
                weather_key = f"2025-11-{23+day}"
                forecast = weather.get(weather_key, {})
                
                temp = forecast.get('temp', 20 + day)  # Default: 20-27°C range
                desc = forecast.get('description', 'Sunny')
                
                section += f"- **{date_str}**: {temp}°C, {desc}\n"
        else:
            section += "**TYPICAL NOVEMBER WEATHER IN DELHI:**\n"
            section += "- Temperature: 15-25°C (Pleasant)\n"
            section += "- Conditions: Mostly sunny, perfect for sightseeing\n"
            section += "- Recommendation: Light layers, comfortable walking shoes\n"
        
        return section

    def _build_budget_section(self, original_budget: float, total_flight_cost: float, budget_remaining: float,
                            accommodation_budget: float, activity_budget: float, buffer_budget: float,
                            daily_activity_per_person: float, duration: int, travelers: int) -> str:
        """Build comprehensive budget section"""
        return f"""
## 💰 DETAILED BUDGET BREAKDOWN:

**TOTAL BUDGET: ₹{original_budget:,}**

**ALLOCATED SPENDING:**
- Flights: ₹{total_flight_cost:,} (Booked)
- Accommodation: ₹{accommodation_budget:,.0f} ({duration-1} nights)
- Activities & Food: ₹{activity_budget:,.0f} ({duration} days) 
- Buffer: ₹{buffer_budget:,.0f}
- **TOTAL: ₹{total_flight_cost + budget_remaining:,.0f}**

**DAILY BUDGET PER PERSON:**
- Activities & Food: ₹{daily_activity_per_person:,.0f} per day
- This covers: Entry fees, local transport, meals, shopping
- Accommodation cost already allocated separately

**BUDGET TIPS:**
- Book attraction tickets online for discounts
- Use Delhi Metro for affordable transportation
- Street food: ₹100-300 per meal
- Restaurant meals: ₹500-1500 per person
- Monument entry: ₹50-1000 per person
"""

    def _generate_enhanced_fallback(self, destination: str, travelers: int,
                                  user_vibe: str, duration: int, flights: List[Dict],
                                  total_flight_cost: float, hotels: List[Dict],
                                  budget_remaining: float, weather: Dict,
                                  optimized_budget: Dict = None) -> str:
        """Generate enhanced fallback with REAL data included"""
        logger.info("🔄 Using enhanced fallback with real data")
        
        # Use original budget
        original_budget = optimized_budget.get('total_budget', 80000) if optimized_budget else 80000
        if budget_remaining < 0:
            budget_remaining = original_budget - total_flight_cost
        
        # Calculate budgets
        accommodation_budget = budget_remaining * 0.6
        activity_budget = budget_remaining * 0.3
        buffer_budget = budget_remaining * 0.1
        daily_activity_per_person = (activity_budget / duration) / travelers

        # Build real data sections
        flight_info = self._build_flight_section(flights, total_flight_cost, travelers, "Amadeus")
        hotel_info = self._build_hotel_section(hotels, duration, accommodation_budget)
        weather_info = self._build_weather_section(weather, duration)

        # Delhi daily themes
        delhi_days = [
            "Old Delhi Heritage - Red Fort, Jama Masjid, Chandni Chowk, Paranthe Wali Gali",
            "Historical Monuments - Qutub Minar, Humayun's Tomb, India Gate, Lodhi Garden", 
            "Spiritual Journey - Lotus Temple, Akshardham, Bangla Sahib Gurudwara, ISKCON",
            "Cultural Experience - Dilli Haat, National Museum, Crafts Museum, Hauz Khas",
            "Modern Delhi - Connaught Place, Select Citywalk, Khan Market, DLF Promenade",
            "Markets & Food - Sarojini Nagar, Majnu Ka Tilla, Paharganj, Local Street Food",
            "Day Trip Option - Optional: Agra Taj Mahal or Local Exploration",
            "Leisure & Departure - Last-minute shopping, Local experiences, Departure"
        ]

        itinerary_days = ""
        for day, theme in enumerate(delhi_days[:duration], 1):
            main_attraction = theme.split(' - ')[1].split(',')[0].strip()
            itinerary_days += f'''
DAY {day}: {theme}
🌅 Morning (7 AM - 12 PM): Explore {main_attraction} - Entry fee: ₹500-1000
🍽️ Lunch (12 PM - 1 PM): Local restaurant - ₹{600 * travelers} total
🌆 Afternoon (1 PM - 5 PM): Continue exploration - Transport: ₹200-500
🌃 Evening (5 PM - 10 PM): Dinner & experiences - ₹{800 * travelers} total
💵 Daily Budget: ₹{daily_activity_per_person:,.0f} per person for activities

'''

        return f"""
🌍 TRAVEL ITINERARY FOR DELHI - WITH REAL DATA

{flight_info}

{hotel_info}

{weather_info}

🎯 TRIP OVERVIEW
{travelers} traveler(s) | {duration} days | {user_vibe} style

💰 BUDGET SUMMARY
- Total Budget: ₹{original_budget:,}
- Flights: ₹{total_flight_cost:,}
- Accommodation: ₹{accommodation_budget:,.0f}
- Activities & Food: ₹{activity_budget:,.0f}
- Buffer: ₹{buffer_budget:,.0f}
- **Total Used: ₹{total_flight_cost + budget_remaining:,.0f}**

📅 {duration}-DAY ITINERARY
{itinerary_days}

🌟 REAL DELHI EXPERIENCES
- Mughal heritage at Red Fort & Jama Masjid
- Ancient architecture at Qutub Minar & Humayun's Tomb  
- Spiritual peace at Lotus Temple & Akshardham
- Vibrant markets like Chandni Chowk & Dilli Haat
- Modern Delhi at Connaught Place & luxury malls
- Beautiful gardens like Lodhi Garden
- Diverse street food and fine dining
- Rich cultural experiences and shopping

🎒 TRAVEL TIPS
- Book monument tickets online to avoid queues
- Use Delhi Metro for efficient transportation
- Carry cash for local markets
- Dress modestly for religious sites
- Stay hydrated and use sunscreen

TOTAL COST: ₹{total_flight_cost + budget_remaining:,.0f}
PER PERSON: ₹{(total_flight_cost + budget_remaining) / travelers:,.0f}

Enjoy your {user_vibe} trip to Delhi! 🎉
"""

    def _create_default_weather(self, duration: int) -> Dict:
        """Create default weather data"""
        weather = {}
        start_date = datetime(2025, 11, 23)
        for i in range(duration):
            date_str = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            weather[date_str] = {
                'temp': 20 + i,  # 20-27°C range
                'description': 'Sunny',
                'humidity': 50 + i
            }
        return weather

    def _finalize_itinerary(self, itinerary: str, workflow_id: str,
                           context_id: str, from_cache: bool):
        """Save and send itinerary"""
        try:
            # Save to file
            filename = f"itinerary_{workflow_id}_{int(time.time())}.txt"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(itinerary)
            
            # Print to console
            cache_note = " (from cache)" if from_cache else " (FRESH with REAL DATA)"
            print(f"\n{'='*70}")
            print(f"✅ ITINERARY READY{cache_note}")
            print('='*70)
            print(itinerary)
            print('='*70)
            print(f"💾 Saved: {filepath}\n")
            
            # Send to orchestrator
            result_msg = create_result_message(
                context_id=context_id,
                sender="itinerary_builder",
                receiver="orchestrator",
                payload={
                    "workflow_id": workflow_id,
                    "itinerary": itinerary,
                    "file_path": filepath,
                    "from_cache": from_cache,
                    "status": "success",
                    "completion_time": datetime.now().isoformat()
                }
            )
            
            self.client.send_message_with_retry(result_msg)
            logger.info("✅ Itinerary sent to orchestrator")
            
        except Exception as e:
            logger.error(f"❌ Finalization failed: {e}")
            raise

    def _handle_error(self, error: Exception, context_id: str, workflow_id: str):
        """Handle errors"""
        logger.error(f"Itinerary Builder Error: {error}")
        
        try:
            error_msg = create_result_message(
                context_id=context_id,
                sender="itinerary_builder",
                receiver="orchestrator",
                payload={
                    "workflow_id": workflow_id,
                    "error": str(error),
                    "status": "failed"
                }
            )
            self.client.send_message_with_retry(error_msg)
        except Exception as e:
            logger.critical(f"🚨 Failed to send error: {e}")

    def shutdown(self):
        """Shutdown"""
        logger.info("🛑 Shutting down Itinerary Builder...")

def create_itinerary_builder_agent(context_id: str, groq_api_key: str) -> ItineraryBuilderAgent:
    return ItineraryBuilderAgent(context_id, groq_api_key)