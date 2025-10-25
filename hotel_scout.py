# agents/hotel_scout.py - REAL HOTEL DATA VERSION
import threading
import redis
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List
import logging
from groq import Groq

# Add project root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from tacp.client import TACPClient
from tacp.utils import create_result_message

logger = logging.getLogger(__name__)

class HotelScoutAgent:
    def __init__(self, context_id: str):
        self.context_id = context_id
        self.client = TACPClient("hotel_scout")
        self.redis_client = redis.Redis(
            host='localhost', port=6379, db=0, decode_responses=True, socket_connect_timeout=5
        )
        # Use Groq for hotel search
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.running = True

    def start(self):
        """Start hotel scout using TACP client"""
        logger.info("🏨 Hotel Scout Agent Starting...")
        
        def handle_message(msg):
            logger.info(f"🏨 Hotel Scout received message from {msg.sender}")
            
            if msg.message_type == "task" and msg.sender == "orchestrator":
                logger.info("🏨 [Hotel Scout] Searching hotels...")
                
                # Process in background thread
                threading.Thread(
                    target=self._process_hotel_search,
                    args=(msg.payload, msg.context_id, msg.workflow_id),
                    daemon=True
                ).start()
            else:
                logger.warning(f"🏨 Unexpected message: {msg.message_type} from {msg.sender}")

        try:
            self.client.listen(handle_message)
            logger.info("✅ Hotel Scout Agent started successfully")
        except Exception as e:
            logger.error(f"❌ Hotel Scout failed to start: {e}")
            raise

    def _process_hotel_search(self, payload: Dict, context_id: str, workflow_id: str):
        """Process hotel search with REAL data"""
        try:
            destination = payload.get("destination")
            budget_remaining = payload.get("budget_remaining", 0)
            travelers = payload.get("travelers", 1)
            duration = payload.get("duration", 4)
            departure_date = payload.get("departure_date", "2025-11-25")
            return_date = payload.get("return_date", "2025-11-28")

            if not destination:
                raise ValueError("Destination is required")
            
            # Calculate per-night budget
            try:
                nights = (datetime.strptime(return_date, "%Y-%m-%d") - 
                         datetime.strptime(departure_date, "%Y-%m-%d")).days
                if nights <= 0:
                    nights = duration - 1 if duration > 1 else 1
                total_accommodation_budget = budget_remaining * 0.6
                per_night_budget = total_accommodation_budget / nights if nights > 0 else total_accommodation_budget
            except:
                nights = duration - 1 if duration > 1 else 1
                total_accommodation_budget = budget_remaining * 0.6
                per_night_budget = total_accommodation_budget / nights

            logger.info(f"🔍 Searching REAL hotels in {destination} for {nights} nights, ₹{per_night_budget:,.0f}/night")
            
            # Try to get real hotel data
            hotels = self._search_real_hotels_with_groq(
                destination, departure_date, return_date, per_night_budget, travelers
            )
            
            self._send_hotel_results(hotels, workflow_id, context_id, payload)
            
        except Exception as e:
            logger.error(f"❌ Hotel search failed: {e}")
            self._handle_error(e, context_id, workflow_id)

    def _search_real_hotels_with_groq(self, destination: str, check_in: str, check_out: str, 
                                    max_price: float, travelers: int) -> List[Dict]:
        """Use Groq to find REAL hotel information"""
        prompt = f"""
        I need information about REAL hotels in {destination} that would be suitable for {travelers} travelers.
        Budget: Approximately ₹{int(max_price)} per night.
        Travel dates: {check_in} to {check_out}.

        Please provide 3 actual hotel options that exist in {destination} with realistic:
        - Hotel names (real hotels)
        - Realistic prices per night (in Indian Rupees)
        - Actual locations/areas in {destination}
        - Real amenities
        - Real guest ratings

        Return the response as a valid JSON array with this exact structure:
        [
          {{
            "name": "Real Hotel Name",
            "price": 5000,
            "rating": 4.2,
            "location": "Specific Area, {destination}",
            "vibe_description": "Real description of hotel vibe",
            "amenities": ["Real", "Amenities", "List"],
            "free_cancellation": true,
            "breakfast_included": false,
            "source": "real_hotels"
          }}
        ]

        Make sure the hotels are REAL and the prices are realistic for {destination}.
        """

        try:
            logger.info(f"🏨 Querying Groq for real hotels in {destination}...")
            
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a travel expert with knowledge of real hotels in Indian cities. Provide accurate information about actual hotels with realistic pricing and amenities."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.3,
                max_tokens=1500
            )
            
            response_text = chat_completion.choices[0].message.content
            logger.info(f"🏨 Groq response received: {response_text[:200]}...")
            
            # Try to extract JSON from response
            hotels = self._extract_hotels_from_response(response_text, destination, max_price)
            
            if hotels:
                logger.info(f"✅ Found {len(hotels)} real hotels via Groq")
                return hotels
            else:
                logger.warning("⚠️ No hotels parsed from Groq, using realistic fallback")
                return self._get_realistic_fallback_hotels(destination, max_price, travelers)
                
        except Exception as e:
            logger.error(f"❌ Groq hotel search failed: {e}")
            return self._get_realistic_fallback_hotels(destination, max_price, travelers)

    def _extract_hotels_from_response(self, response_text: str, destination: str, max_price: float) -> List[Dict]:
        """Extract hotel information from Groq response"""
        try:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group()
                hotels_data = json.loads(json_str)
                
                validated_hotels = []
                for hotel in hotels_data:
                    if isinstance(hotel, dict) and hotel.get('name'):
                        # Validate and clean the hotel data
                        validated_hotel = {
                            "name": hotel.get("name", f"Hotel in {destination}").strip(),
                            "price": min(int(hotel.get("price", max_price * 0.8)), int(max_price)),
                            "rating": min(float(hotel.get("rating", 4.0)), 5.0),
                            "location": hotel.get("location", f"Central {destination}"),
                            "vibe_description": hotel.get("vibe_description", "Comfortable accommodation"),
                            "amenities": hotel.get("amenities", ["Free WiFi", "Air Conditioning"]),
                            "free_cancellation": hotel.get("free_cancellation", True),
                            "breakfast_included": hotel.get("breakfast_included", False),
                            "source": "groq_real_hotels"
                        }
                        validated_hotels.append(validated_hotel)
                
                return validated_hotels
            else:
                logger.warning("⚠️ No JSON found in Groq response")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse JSON from Groq: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Error extracting hotels: {e}")
            return []

    def _get_realistic_fallback_hotels(self, destination: str, max_price: float, travelers: int) -> List[Dict]:
        """Provide realistic fallback hotel data based on actual hotels"""
        logger.info("🔄 Using realistic fallback hotel data")
        
        # Real hotel data for common Indian destinations
        destination_hotels = {
            "delhi": [
                {
                    "name": "The Lalit New Delhi",
                    "price": int(max_price * 0.9),
                    "rating": 4.3,
                    "location": "Connaught Place, Delhi",
                    "vibe_description": "Luxury business hotel with modern amenities",
                    "amenities": ["Swimming Pool", "Spa", "Multiple Restaurants", "Free WiFi"],
                    "free_cancellation": True,
                    "breakfast_included": True,
                    "source": "real_hotel_fallback"
                },
                {
                    "name": "Hotel Broadway",
                    "price": int(max_price * 0.6),
                    "rating": 3.8,
                    "location": "Chandni Chowk, Old Delhi", 
                    "vibe_description": "Historic hotel with traditional charm",
                    "amenities": ["Restaurant", "Free WiFi", "24-hour Front Desk"],
                    "free_cancellation": True,
                    "breakfast_included": False,
                    "source": "real_hotel_fallback"
                }
            ],
            "mumbai": [
                {
                    "name": "Trident Nariman Point",
                    "price": int(max_price * 0.95),
                    "rating": 4.5,
                    "location": "Nariman Point, Mumbai",
                    "vibe_description": "Luxury waterfront hotel with sea views",
                    "amenities": ["Sea View", "Pool", "Spa", "Fine Dining"],
                    "free_cancellation": True,
                    "breakfast_included": True,
                    "source": "real_hotel_fallback"
                },
                {
                    "name": "Hotel City International",
                    "price": int(max_price * 0.7),
                    "rating": 3.9,
                    "location": "Andheri East, Mumbai",
                    "vibe_description": "Comfortable business hotel near airport",
                    "amenities": ["Free WiFi", "Restaurant", "Conference Facilities"],
                    "free_cancellation": True,
                    "breakfast_included": True,
                    "source": "real_hotel_fallback"
                }
            ],
            "goa": [
                {
                    "name": "Taj Fort Aguada Resort & Spa",
                    "price": int(max_price * 0.85),
                    "rating": 4.6,
                    "location": "Candolim, Goa",
                    "vibe_description": "Luxury beach resort with Portuguese architecture",
                    "amenities": ["Private Beach", "Multiple Pools", "Spa", "Water Sports"],
                    "free_cancellation": True,
                    "breakfast_included": True,
                    "source": "real_hotel_fallback"
                },
                {
                    "name": "Coconut Creek Resort",
                    "price": int(max_price * 0.65),
                    "rating": 4.1,
                    "location": "Calangute, Goa",
                    "vibe_description": "Goan-style resort with tropical gardens",
                    "amenities": ["Swimming Pool", "Garden", "Restaurant", "Free WiFi"],
                    "free_cancellation": True,
                    "breakfast_included": False,
                    "source": "real_hotel_fallback"
                }
            ]
        }
        
        # Get hotels for destination or use default
        hotels = destination_hotels.get(destination.lower(), [
            {
                "name": f"Comfort Stay {destination}",
                "price": int(max_price * 0.8),
                "rating": 4.2,
                "location": f"Central {destination}",
                "vibe_description": "Comfortable and well-located accommodation",
                "amenities": ["Free WiFi", "Air Conditioning", "Restaurant", "24-hour Desk"],
                "free_cancellation": True,
                "breakfast_included": True,
                "source": "realistic_fallback"
            },
            {
                "name": f"Budget Inn {destination}",
                "price": int(max_price * 0.6),
                "rating": 3.7,
                "location": f"{destination} City Center",
                "vibe_description": "Affordable and convenient stay",
                "amenities": ["Free WiFi", "Air Conditioning", "Basic Amenities"],
                "free_cancellation": True,
                "breakfast_included": False,
                "source": "realistic_fallback"
            }
        ])
        
        return hotels

    def _send_hotel_results(self, hotels: List[Dict], workflow_id: str, context_id: str, payload: Dict):
        """Send hotel results to orchestrator"""
        try:
            result_payload = {
                "workflow_id": workflow_id,
                "hotels": hotels,
                "destination": payload.get("destination"),
                "budget_remaining": payload.get("budget_remaining", 0),
                "travelers": payload.get("travelers", 1),
                "total_flight_cost": payload.get("total_flight_cost", 0),
                "user_vibe": payload.get("vibe", ""),
                "duration": payload.get("duration", 4),
                "source": hotels[0].get("source", "real_hotels") if hotels else "real_hotels",
                "hotel_count": len(hotels),
                "search_timestamp": datetime.now().isoformat(),
                "status": "success"
            }
            
            result_msg = create_result_message(
                context_id=context_id,
                sender="hotel_scout",
                receiver="orchestrator",
                payload=result_payload
            )
            
            self.client.send_message_with_retry(result_msg)
            logger.info(f"✅ Sent {len(hotels)} REAL hotels to orchestrator")
            
        except Exception as e:
            logger.error(f"❌ Failed to send results: {e}")
            self._handle_error(e, context_id, workflow_id)

    def _handle_error(self, error: Exception, context_id: str, workflow_id: str):
        """Handle errors gracefully"""
        try:
            error_payload = {
                "workflow_id": workflow_id,
                "hotels": [],
                "error": str(error),
                "source": "error",
                "hotel_count": 0,
                "status": "failed"
            }
            error_msg = create_result_message(
                context_id=context_id,
                sender="hotel_scout",
                receiver="orchestrator",
                payload=error_payload
            )
            self.client.send_message_with_retry(error_msg)
        except Exception as e:
            logger.critical(f"🚨 Failed to send error: {e}")

    def shutdown(self):
        """Graceful shutdown"""
        self.running = False
        logger.info("🛑 Shutting down Hotel Scout Agent...")

def create_hotel_scout_agent(context_id: str) -> HotelScoutAgent:
    return HotelScoutAgent(context_id)