# agents/orchestrator.py - COMPLETELY FIXED BUDGET FLOW
import threading
import time
import json
import redis
from datetime import datetime, timedelta
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class OrchestratorAgent:
    def __init__(self, context_id: str):
        self.context_id = context_id
        self.redis_client = redis.Redis(
            host='localhost', port=6379, db=0, decode_responses=True
        )
        self.running = True
        self.active_workflows = {}
        self.last_processed_id = "$"

    def start(self):
        """Start orchestrator with single unified stream listener"""
        logger.info("🚀 Orchestrator Agent Started")
        
        # Clear streams
        self._clear_streams()
        
        # ONE unified listener for orchestrator stream
        threading.Thread(target=self._listen_orchestrator_stream, daemon=True).start()
        logger.info("✅ Orchestrator listening on orchestrator stream")

    def _clear_streams(self):
        """Clear all streams to start fresh"""
        try:
            streams = [
                "tacp:stream:orchestrator",
                "tacp:stream:budget_optimizer", 
                "tacp:stream:flight_booker",
                "tacp:stream:hotel_scout",
                "tacp:stream:itinerary_builder",
                "tacp:stream:weather_agent",
                "tacp:stream:user"
            ]
            for stream in streams:
                try:
                    self.redis_client.delete(stream)
                except:
                    pass
            logger.info("🧹 Cleared all Redis streams")
        except Exception as e:
            logger.warning(f"⚠️ Stream cleanup failed: {e}")

    def _listen_orchestrator_stream(self):
        """Listen to orchestrator stream for both user requests AND agent results"""
        while self.running:
            try:
                messages = self.redis_client.xread(
                    {"tacp:stream:orchestrator": self.last_processed_id},
                    count=10,
                    block=5000
                )
                
                if messages:
                    for stream_name, message_list in messages:
                        for message_id, message_data in message_list:
                            self.last_processed_id = message_id
                            
                            try:
                                message = json.loads(message_data["payload"])
                                sender = message.get("sender")
                                receiver = message.get("receiver")
                                
                                # Route based on sender
                                if sender == "user" and receiver == "orchestrator":
                                    logger.info(f"👤 Received user request: {message.get('context_id')}")
                                    self._process_user_request(message)
                                    
                                elif receiver == "orchestrator" and sender != "user":
                                    logger.info(f"📨 Processing message from {sender}")
                                    self._route_agent_result(message)
                                    
                                else:
                                    logger.debug(f"⏭️ Skipping message from {sender} to {receiver}")
                                
                            except Exception as e:
                                logger.error(f"❌ Failed to parse message: {e}")
                                
            except Exception as e:
                logger.error(f"❌ Stream listen error: {e}")
                time.sleep(1)

    def _process_user_request(self, message: Dict):
        """Process incoming user travel request"""
        try:
            payload = message.get("payload", {})
            context_id = message.get("context_id")
            destination = payload.get("destination")
            budget = payload.get("budget")
            travelers = payload.get("travelers")
            
            if not all([destination, budget, travelers]):
                self._send_error_to_user(context_id, "Missing destination, budget, or travelers")
                return
                
            logger.info(f"🎯 NEW TRIP: {destination} | {travelers} pax | ₹{budget:,}")
            
            workflow_id = f"wf_{context_id}_{int(time.time())}"
            self.active_workflows[workflow_id] = {
                "user_data": payload,
                "context_id": context_id,
                "start_time": time.time(),
                "current_step": "budget_optimization",
                "collected_data": {}
            }
            
            self._start_budget_optimization(workflow_id, payload, context_id)
            self._monitor_workflow(workflow_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to process user request: {e}")

    def _start_budget_optimization(self, workflow_id: str, user_data: Dict, context_id: str):
        """Start budget optimization"""
        try:
            budget_request = {
                "message_type": "task",
                "sender": "orchestrator",
                "receiver": "budget_optimizer",
                "context_id": context_id,
                "workflow_id": workflow_id,
                "payload": {
                    "budget": user_data["budget"],
                    "vibe": user_data.get("vibe", "comfortable travel"),
                    "destination": user_data["destination"],
                    "travelers": user_data["travelers"],
                    "duration": user_data.get("duration", 4),
                    "origin": user_data.get("origin", "Mumbai")
                }
            }
            self.redis_client.xadd("tacp:stream:budget_optimizer", {"payload": json.dumps(budget_request)})
            logger.info("💰 Sent budget optimization request")
        except Exception as e:
            logger.error(f"❌ Budget request failed: {e}")
            self._start_flight_search(workflow_id, user_data, context_id, user_data["budget"] * 0.4)

    def _route_agent_result(self, message: Dict):
        """Route results from agents to next step"""
        try:
            sender = message.get("sender")
            payload = message.get("payload", {})
            workflow_id = payload.get("workflow_id")
            
            logger.info(f"🔄 Routing from {sender} for workflow {workflow_id}")
            
            if not workflow_id:
                logger.warning(f"⚠️ No workflow ID from {sender}")
                return
                
            if workflow_id not in self.active_workflows:
                logger.warning(f"⚠️ Unknown workflow: {workflow_id}")
                return
                
            if sender == "budget_optimizer":
                logger.info("💰 Processing budget result")
                self._handle_budget_result(workflow_id, payload)
            elif sender == "flight_booker":
                logger.info("✈️ Processing flight result") 
                self._handle_flight_result(workflow_id, payload)
            elif sender == "hotel_scout":
                logger.info("🏨 Processing hotel result")
                self._handle_hotel_result(workflow_id, payload)
            elif sender == "weather_agent":
                logger.info("🌤️ Processing weather result")
                self._handle_weather_result(workflow_id, payload)
            elif sender == "itinerary_builder":
                logger.info("✏️ Processing itinerary result")
                self._handle_itinerary_result(workflow_id, payload)
            else:
                logger.warning(f"⚠️ Unknown sender: {sender}")
                
        except Exception as e:
            logger.error(f"❌ Routing error: {e}")

    def _handle_budget_result(self, workflow_id: str, budget_data: Dict):
        """Handle budget result"""
        try:
            workflow = self.active_workflows[workflow_id]
            workflow["collected_data"]["budget"] = budget_data
            workflow["current_step"] = "flight_search"
            
            if budget_data.get("optimized_budget"):
                optimized_budget = budget_data["optimized_budget"]
                flight_budget = optimized_budget["category_allocations"].get("flights", 0)
                logger.info(f"💰 Budget done. Flight budget: ₹{flight_budget:,}")
                
                self._start_flight_search(
                    workflow_id, 
                    workflow["user_data"], 
                    workflow["context_id"], 
                    flight_budget,
                    optimized_budget
                )
            else:
                total_budget = workflow["user_data"]["budget"]
                logger.info("🔄 Using fallback flight budget")
                self._start_flight_search(workflow_id, workflow["user_data"], workflow["context_id"], total_budget * 0.4)
                
        except Exception as e:
            logger.error(f"❌ Budget handling error: {e}")
            workflow = self.active_workflows[workflow_id]
            total_budget = workflow["user_data"]["budget"]
            self._start_flight_search(workflow_id, workflow["user_data"], workflow["context_id"], total_budget * 0.4)

    def _start_flight_search(self, workflow_id: str, user_data: Dict, context_id: str, flight_budget: float, optimized_budget: Dict = None):
        """Start flight search"""
        try:
            travel_dates = user_data.get("travel_dates", {})
            departure_date = travel_dates.get("start_date") or (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            return_date = travel_dates.get("end_date") or (datetime.now() + timedelta(days=30 + user_data.get("duration", 4))).strftime("%Y-%m-%d")
            
            flight_request = {
                "message_type": "task",
                "sender": "orchestrator",
                "receiver": "flight_booker",
                "context_id": context_id,
                "workflow_id": workflow_id,
                "payload": {
                    "origin": user_data.get("origin", "Mumbai"),
                    "destination": user_data["destination"],
                    "budget": flight_budget,
                    "travelers": user_data["travelers"],
                    "vibe": user_data.get("vibe", "comfortable travel"),
                    "duration": user_data.get("duration", 4),
                    "departure_date": departure_date,
                    "return_date": return_date,
                    "optimized_budget": optimized_budget,
                    "total_budget": user_data["budget"]
                }
            }
            self.redis_client.xadd("tacp:stream:flight_booker", {"payload": json.dumps(flight_request)})
            logger.info(f"✈️ Sent flight search: {user_data.get('origin')} → {user_data['destination']}")
        except Exception as e:
            logger.error(f"❌ Flight request failed: {e}")
            self._send_error_to_user(context_id, f"Flight search failed: {e}")

    def _handle_flight_result(self, workflow_id: str, flight_data: Dict):
        """Handle flight result - FIXED BUDGET CALCULATION"""
        try:
            workflow = self.active_workflows[workflow_id]
            if flight_data.get("success"):
                workflow["collected_data"]["flights"] = flight_data
                workflow["current_step"] = "hotel_search"
                
                # 🚨 CRITICAL FIX: Calculate PROPER remaining budget
                total_budget = workflow["user_data"]["budget"]
                total_flight_cost = flight_data.get("total_flight_cost", 0)
                budget_remaining = total_budget - total_flight_cost
                
                logger.info(f"✅ Flights found: ₹{total_flight_cost:,}. Remaining: ₹{budget_remaining:,}")
                self._start_hotel_search(workflow_id, workflow["user_data"], flight_data, budget_remaining)
            else:
                error = flight_data.get("error", "No flights available")
                logger.error(f"❌ Flight search failed: {error}")
                self._send_error_to_user(workflow["context_id"], error)
                del self.active_workflows[workflow_id]
        except Exception as e:
            logger.error(f"❌ Flight handling error: {e}")

    def _start_hotel_search(self, workflow_id: str, user_data: Dict, flight_data: Dict, budget_remaining: float):
        """Start hotel search - FIXED BUDGET PASSING"""
        try:
            travel_dates = user_data.get("travel_dates", {})
            departure_date = travel_dates.get("start_date", "2025-11-23")
            return_date = travel_dates.get("end_date", "2025-11-30")
            
            # 🚨 CRITICAL FIX: Pass PROPER budget to hotel scout
            total_budget = user_data.get("budget", 0)
            total_flight_cost = flight_data.get("total_flight_cost", 0)
            
            # Ensure budget is realistic
            if budget_remaining <= 0:
                logger.warning(f"🚨 Budget overrun: Flights ₹{total_flight_cost} > Total ₹{total_budget}")
                budget_remaining = total_budget * 0.6  # Use 60% as fallback
            
            hotel_request = {
                "message_type": "task",
                "sender": "orchestrator",
                "receiver": "hotel_scout",
                "context_id": self.active_workflows[workflow_id]["context_id"],
                "workflow_id": workflow_id,
                "payload": {
                    "destination": user_data["destination"],
                    "budget_remaining": budget_remaining,  # ✅ FIXED: Pass actual remaining budget
                    "travelers": user_data["travelers"],
                    "vibe": user_data.get("vibe", "comfortable travel"),
                    "duration": user_data.get("duration", 4),
                    "departure_date": departure_date,
                    "return_date": return_date,
                    "total_flight_cost": total_flight_cost,
                    "total_budget": total_budget
                }
            }
            self.redis_client.xadd("tacp:stream:hotel_scout", {"payload": json.dumps(hotel_request)})
            logger.info(f"🏨 Sent hotel search request with ₹{budget_remaining:,} budget")
        except Exception as e:
            logger.error(f"❌ Hotel request failed: {e}")

    def _handle_hotel_result(self, workflow_id: str, hotel_data: Dict):
        """Handle hotel result + START WEATHER"""
        try:
            workflow = self.active_workflows[workflow_id]
            workflow["collected_data"]["hotels"] = hotel_data
            workflow["current_step"] = "weather_fetch"
            logger.info(f"✅ Hotels found. Fetching weather")
            self._start_weather_fetch(workflow_id, workflow["user_data"])
        except Exception as e:
            logger.error(f"❌ Hotel handling error: {e}")

    def _start_weather_fetch(self, workflow_id: str, user_data: Dict):
        """Fetch weather for trip dates"""
        try:
            travel_dates = user_data.get("travel_dates", {})
            start_date = travel_dates.get("start_date", "2025-11-23")
            end_date = travel_dates.get("end_date", "2025-11-30")
            
            weather_request = {
                "message_type": "task",
                "sender": "orchestrator",
                "receiver": "weather_agent",
                "context_id": self.active_workflows[workflow_id]["context_id"],
                "workflow_id": workflow_id,
                "payload": {
                    "destination": user_data["destination"],
                    "start_date": start_date,
                    "end_date": end_date,
                    "departure_date": start_date,
                    "return_date": end_date
                }
            }
            self.redis_client.xadd("tacp:stream:weather_agent", {"payload": json.dumps(weather_request)})
            logger.info("🌤️ Sent weather fetch request")
        except Exception as e:
            logger.error(f"❌ Weather request failed: {e}")
            self._start_itinerary_building(workflow_id, user_data, self.active_workflows[workflow_id]["collected_data"].get("hotels", {}))

    def _handle_weather_result(self, workflow_id: str, weather_data: Dict):
        """Handle weather result + START ITINERARY"""
        try:
            workflow = self.active_workflows[workflow_id]
            workflow["collected_data"]["weather"] = weather_data
            logger.info("✅ Weather received. Starting itinerary")
            self._start_itinerary_building(workflow_id, workflow["user_data"], workflow["collected_data"].get("hotels", {}))
        except Exception as e:
            logger.error(f"❌ Weather handling error: {e}")
            self._start_itinerary_building(workflow_id, workflow["user_data"], workflow["collected_data"].get("hotels", {}))

    def _start_itinerary_building(self, workflow_id: str, user_data: Dict, hotel_data: Dict):
        """Start itinerary building - FIXED DATA PASSING"""
        try:
            workflow = self.active_workflows[workflow_id]
            flight_data = workflow["collected_data"].get("flights", {})
            budget_data = workflow["collected_data"].get("budget", {})
            weather_data = workflow["collected_data"].get("weather", {})
            
            # 🚨 CRITICAL FIX: Calculate proper remaining budget for itinerary
            total_budget = user_data.get("budget", 0)
            total_flight_cost = flight_data.get("total_flight_cost", 0)
            budget_remaining = total_budget - total_flight_cost
            
            itinerary_request = {
                "message_type": "task",
                "sender": "orchestrator",
                "receiver": "itinerary_builder",
                "context_id": workflow["context_id"],
                "workflow_id": workflow_id,
                "payload": {
                    "destination": user_data["destination"],
                    "travelers": user_data["travelers"],
                    "user_vibe": user_data.get("vibe", "comfortable travel"),
                    "duration": user_data.get("duration", 4),
                    "flights": flight_data.get("flights", []),
                    "total_flight_cost": total_flight_cost,
                    "hotels": hotel_data.get("hotels", []),
                    "budget_remaining": budget_remaining,  # ✅ FIXED: Pass correct budget
                    "optimized_budget": budget_data.get("optimized_budget"),
                    "weather": weather_data,
                    "source": flight_data.get("source", "estimated")
                }
            }
            self.redis_client.xadd("tacp:stream:itinerary_builder", {"payload": json.dumps(itinerary_request)})
            logger.info(f"✏️ Sent itinerary build request with ₹{budget_remaining:,} remaining budget")
        except Exception as e:
            logger.error(f"❌ Itinerary request failed: {e}")

    def _handle_itinerary_result(self, workflow_id: str, itinerary_data: Dict):
        """Handle final itinerary and send to user"""
        try:
            workflow = self.active_workflows[workflow_id]
            if itinerary_data.get("itinerary"):
                user_response = {
                    "message_type": "result",
                    "sender": "orchestrator",
                    "receiver": "user",
                    "context_id": workflow["context_id"],
                    "payload": {
                        "status": "completed",
                        "itinerary": itinerary_data["itinerary"],
                        "workflow_id": workflow_id,
                        "processing_time": time.time() - workflow["start_time"]
                    }
                }
                self.redis_client.xadd("tacp:stream:user", {"payload": json.dumps(user_response)})
                del self.active_workflows[workflow_id]
                logger.info(f"✅ Workflow {workflow_id} completed successfully")
            else:
                error = itinerary_data.get("error", "Itinerary generation failed")
                self._send_error_to_user(workflow["context_id"], error)
                del self.active_workflows[workflow_id]
        except Exception as e:
            logger.error(f"❌ Itinerary handling error: {e}")

    def _send_error_to_user(self, context_id: str, error: str):
        """Send error to user"""
        try:
            error_msg = {
                "message_type": "result",
                "sender": "orchestrator",
                "receiver": "user",
                "context_id": context_id,
                "payload": {"status": "failed", "error": error}
            }
            self.redis_client.xadd("tacp:stream:user", {"payload": json.dumps(error_msg)})
            logger.error(f"❌ Sent error to user: {error}")
        except Exception as e:
            logger.error(f"❌ Failed to send error: {e}")

    def _monitor_workflow(self, workflow_id: str):
        """Monitor workflow for timeouts"""
        def monitor():
            start = time.time()
            while time.time() - start < 120:
                if workflow_id not in self.active_workflows:
                    return
                time.sleep(5)
            if workflow_id in self.active_workflows:
                workflow = self.active_workflows[workflow_id]
                self._send_error_to_user(workflow["context_id"], "Planning timed out after 2 minutes")
                del self.active_workflows[workflow_id]
                logger.warning(f"⏰ Workflow {workflow_id} timed out")
        threading.Thread(target=monitor, daemon=True).start()

    def shutdown(self):
        """Shutdown"""
        self.running = False
        logger.info("🛑 Orchestrator shutdown")

def create_orchestrator_agent(context_id: str) -> OrchestratorAgent:
    return OrchestratorAgent(context_id)