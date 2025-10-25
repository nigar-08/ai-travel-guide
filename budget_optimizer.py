# agents/budget_optimizer.py - COMPLETELY FIXED VERSION
import json
import redis
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from prometheus_client import Counter, Histogram
import logging

from tacp.client import TACPClient
from tacp.utils import create_result_message

# Metrics
BUDGET_OPTIMIZATION_REQUESTS = Counter('budget_optimization_requests_total', 'Total budget optimization requests', ['status'])
OPTIMIZATION_DURATION = Histogram('budget_optimization_duration_seconds', 'Budget optimization duration')

logger = logging.getLogger(__name__)

class BudgetOptimizerAgent:
    def __init__(self, context_id: str):
        self.context_id = context_id
        self.client = TACPClient("budget_optimizer")
        
        # Redis for caching optimization strategies
        self.redis_client = redis.Redis(
            host='localhost', port=6379, db=0,
            decode_responses=True, socket_connect_timeout=5
        )
        
        # Budget allocation strategies - REALISTIC PERCENTAGES
        self.allocation_strategies = {
            "peaceful beach yoga with some adventure activities": {
                "flights": 0.25,
                "accommodation": 0.35,
                "activities": 0.20,
                "food_transport": 0.15,
                "buffer": 0.05
            },
            "mountain adventure with comfortable stays": {
                "flights": 0.30,
                "accommodation": 0.30,
                "activities": 0.25,
                "food_transport": 0.12,
                "buffer": 0.03
            },
            "luxury premium experience": {
                "flights": 0.20,
                "accommodation": 0.50,
                "activities": 0.20,
                "food_transport": 0.08,
                "buffer": 0.02
            },
            "budget friendly travel": {
                "flights": 0.30,
                "accommodation": 0.30,
                "activities": 0.15,
                "food_transport": 0.20,
                "buffer": 0.05
            },
            "adventure and exploration": {
                "flights": 0.25,
                "accommodation": 0.30,
                "activities": 0.30,
                "food_transport": 0.12,
                "buffer": 0.03
            },
            "romantic couples getaway": {
                "flights": 0.25,
                "accommodation": 0.45,
                "activities": 0.20,
                "food_transport": 0.08,
                "buffer": 0.02
            },
            "family friendly vacation": {
                "flights": 0.25,
                "accommodation": 0.40,
                "activities": 0.20,
                "food_transport": 0.12,
                "buffer": 0.03
            },
            "comfortable travel": {
                "flights": 0.25,  # REALISTIC: 25% for flights
                "accommodation": 0.40,  # 40% for accommodation
                "activities": 0.20,  # 20% for activities
                "food_transport": 0.12,  # 12% for food & transport
                "buffer": 0.03  # 3% buffer
            }
        }

    def start(self):
        """Start the budget optimizer agent - FIXED VERSION"""
        def handle_message(msg):
            logger.info(f"💰 Budget Optimizer received message from {msg.sender}")
            
            if (msg.message_type == "task" and msg.sender == "orchestrator" and
                "budget" in msg.payload and "vibe" in msg.payload):
                
                logger.info("💰 [Budget Optimizer] Optimizing budget allocation...")
                
                try:
                    with OPTIMIZATION_DURATION.time():
                        total_budget = float(msg.payload.get("budget", 15000))
                        user_vibe = msg.payload.get("vibe", "comfortable travel")
                        destination = msg.payload.get("destination", "Goa")
                        travelers = int(msg.payload.get("travelers", 1))
                        duration = int(msg.payload.get("duration", 4))
                        origin = msg.payload.get("origin", "Mumbai")
                        
                        logger.info(f"🎯 Optimizing budget: ₹{total_budget:,} for {travelers} travelers, {user_vibe} to {destination}")
                        
                        # Optimize budget allocation
                        optimized_budget = self.optimize_budget_allocation(
                            total_budget, user_vibe, destination, travelers, duration, origin
                        )
                        
                        result_msg = create_result_message(
                            context_id=msg.context_id,
                            sender="budget_optimizer", 
                            receiver="orchestrator",
                            payload={
                                "workflow_id": msg.workflow_id,
                                "optimized_budget": optimized_budget,
                                "original_budget": total_budget,
                                "vibe": user_vibe,
                                "destination": destination,
                                "travelers": travelers,
                                "duration": duration,
                                "origin": origin,
                                "optimization_timestamp": datetime.now().isoformat(),
                                "strategy_used": optimized_budget.get("strategy", "default")
                            }
                        )
                        
                        self.client.send_message_with_retry(result_msg)
                        BUDGET_OPTIMIZATION_REQUESTS.labels(status='success').inc()
                        logger.info(f"✅ Budget optimized for {user_vibe}: ₹{total_budget:,}")
                        logger.info(f"📤 Sent result with workflow_id: {msg.workflow_id}")

                except Exception as e:
                    logger.error(f"❌ Budget optimization failed: {str(e)}")
                    BUDGET_OPTIMIZATION_REQUESTS.labels(status='error').inc()
                    self._handle_error(e, "budget_optimization", msg.context_id, msg.workflow_id)
            else:
                logger.warning(f"💰 Unexpected message: {msg.message_type} from {msg.sender}")

        self.client.listen(handle_message)
        logger.info("🚀 Budget Optimizer Agent started successfully")

    def optimize_budget_allocation(self, total_budget: float, user_vibe: str, 
                                 destination: str, travelers: int, duration: int, origin: str) -> Dict:
        """Optimize budget allocation based on vibe and destination - FIXED VERSION"""
        cache_key = f"budget:{destination}:{user_vibe}:{total_budget}:{travelers}:{duration}:{origin}"
        cached = self._get_cached_budget(cache_key)
        
        if cached:
            logger.info("✅ Using cached budget optimization")
            return cached

        # Get allocation strategy for vibe
        strategy = self._get_strategy_for_vibe(user_vibe)
        
        # Calculate base category budgets
        category_budgets = {}
        for category, percentage in strategy.items():
            category_budgets[category] = total_budget * percentage

        # Adjust based on destination, travelers, and duration
        adjusted_budgets = self._adjust_budgets_for_context(
            category_budgets, destination, travelers, duration, total_budget, origin
        )

        # Validate budgets are realistic
        validated_budgets = self._validate_budgets(adjusted_budgets, total_budget, duration, travelers)

        # Create optimization suggestions
        suggestions = self._generate_optimization_suggestions(
            validated_budgets, user_vibe, total_budget, travelers, destination, duration
        )

        optimized_budget = {
            "total_budget": total_budget,
            "category_allocations": validated_budgets,
            "vibe_strategy": user_vibe,
            "suggestions": suggestions,
            "daily_breakdown": self._calculate_daily_breakdown(validated_budgets, duration, travelers),
            "travelers": travelers,
            "duration": duration,
            "destination": destination,
            "origin": origin,
            "strategy": user_vibe,
            "remaining_budget_after_flights": total_budget - validated_budgets.get("flights", 0),
            "is_realistic": self._is_budget_realistic(validated_budgets, total_budget, duration, travelers),
            "optimization_timestamp": datetime.now().isoformat()
        }

        # Cache the result for 12 hours
        self._cache_budget(cache_key, optimized_budget, 43200)
        
        logger.info(f"📊 Budget allocation: Flights ₹{validated_budgets.get('flights', 0):.0f}, "
                   f"Hotels ₹{validated_budgets.get('accommodation', 0):.0f}, "
                   f"Activities ₹{validated_budgets.get('activities', 0):.0f}")
        
        return optimized_budget

    def _get_strategy_for_vibe(self, user_vibe: str) -> Dict:
        """Get allocation strategy for user vibe with intelligent fallback"""
        # Exact match
        if user_vibe in self.allocation_strategies:
            logger.info(f"🎯 Using exact strategy match for: {user_vibe}")
            return self.allocation_strategies[user_vibe]
        
        # Partial match fallback
        for vibe_key, strategy in self.allocation_strategies.items():
            if any(word in user_vibe.lower() for word in vibe_key.lower().split()):
                logger.info(f"🔄 Using '{vibe_key}' strategy for '{user_vibe}'")
                return strategy
        
        # Default fallback based on vibe keywords
        user_vibe_lower = user_vibe.lower()
        
        if any(word in user_vibe_lower for word in ['beach', 'yoga', 'peaceful', 'relax']):
            logger.info(f"🏖️ Using beach strategy for: {user_vibe}")
            return self.allocation_strategies["peaceful beach yoga with some adventure activities"]
        elif any(word in user_vibe_lower for word in ['mountain', 'adventure', 'trek', 'hike']):
            logger.info(f"🏔️ Using mountain strategy for: {user_vibe}")
            return self.allocation_strategies["mountain adventure with comfortable stays"]
        elif any(word in user_vibe_lower for word in ['luxury', 'premium', 'luxurious', '5-star']):
            logger.info(f"⭐ Using luxury strategy for: {user_vibe}")
            return self.allocation_strategies["luxury premium experience"]
        elif any(word in user_vibe_lower for word in ['budget', 'cheap', 'economy', 'save']):
            logger.info(f"💰 Using budget strategy for: {user_vibe}")
            return self.allocation_strategies["budget friendly travel"]
        elif any(word in user_vibe_lower for word in ['romantic', 'couple', 'honeymoon']):
            logger.info(f"💖 Using romantic strategy for: {user_vibe}")
            return self.allocation_strategies["romantic couples getaway"]
        elif any(word in user_vibe_lower for word in ['family', 'kids', 'children']):
            logger.info(f"👨‍👩‍👧‍👦 Using family strategy for: {user_vibe}")
            return self.allocation_strategies["family friendly vacation"]
        else:
            logger.info(f"🎯 Using default comfortable travel strategy for: {user_vibe}")
            return self.allocation_strategies["comfortable travel"]

    def _adjust_budgets_for_context(self, category_budgets: Dict, destination: str, 
                              travelers: int, duration: int, total_budget: float, origin: str) -> Dict:
        """Adjust budgets based on destination, travelers, and duration - FIXED"""
        adjusted = category_budgets.copy()
        
        # Destination cost multipliers
        cost_multipliers = {
            "goa": 1.0, "manali": 1.15, "mumbai": 1.3, "delhi": 1.2,
            "bangalore": 1.25, "kerala": 1.1, "shimla": 1.2, "darjeeling": 1.1,
            "jaipur": 1.1, "kolkata": 1.15, "chennai": 1.2, "hyderabad": 1.15
        }
        
        multiplier = cost_multipliers.get(destination.lower(), 1.0)
        
        # Apply destination multiplier to accommodation and activities
        adjusted["accommodation"] = adjusted["accommodation"] * multiplier
        adjusted["activities"] = adjusted["activities"] * multiplier
        
        # Adjust flights based on route
        flight_adjustment = self._calculate_flight_adjustment(origin, destination)
        adjusted["flights"] = adjusted["flights"] * flight_adjustment
        
        # Accommodation proportional to actual nights
        nights_stay = duration - 1 if duration > 1 else 1
        base_nights = 3
        adjusted["accommodation"] = adjusted["accommodation"] * (nights_stay / base_nights)
        
        # Food & transport proportional to duration and travelers
        base_duration = 4
        base_travelers = 2
        adjusted["food_transport"] = adjusted["food_transport"] * (duration / base_duration) * (travelers / base_travelers)
        
        # Fixed buffer
        adjusted["buffer"] = total_budget * 0.03
        
        # Ensure total doesn't exceed budget
        total_allocated = sum(adjusted.values())
        if total_allocated > total_budget * 1.05:
            scale_factor = total_budget / total_allocated
            for category in adjusted:
                if category != "buffer":
                    adjusted[category] *= scale_factor
            logger.info(f"🔄 Scaled budgets to fit total budget")
        
        return adjusted

    def _calculate_flight_adjustment(self, origin: str, destination: str) -> float:
        """Calculate flight cost adjustment based on route distance"""
        route_multipliers = {
            "mumbai-delhi": 1.0, "mumbai-goa": 0.8, "mumbai-bangalore": 0.9,
            "mumbai-chennai": 1.1, "mumbai-kolkata": 1.3, "mumbai-manali": 1.4,
            "delhi-goa": 1.2, "delhi-bangalore": 1.1, "delhi-chennai": 1.3,
            "delhi-kolkata": 1.0, "delhi-manali": 0.9, "bangalore-goa": 0.7,
            "bangalore-chennai": 0.6, "bangalore-kolkata": 1.4
        }
        
        route_key = f"{origin.lower()}-{destination.lower()}"
        return route_multipliers.get(route_key, 1.0)

    def _validate_budgets(self, budgets: Dict, total_budget: float, duration: int, travelers: int) -> Dict:
        """Ensure budgets are realistic and within constraints - FIXED"""
        validated = budgets.copy()
        
        nights_stay = duration - 1 if duration > 1 else 1
        
        # 🚨 CRITICAL: Ensure NO negative budgets
        for category, amount in validated.items():
            if amount < 0:
                logger.error(f"🚨 NEGATIVE BUDGET FIXED: {category} = ₹{amount}")
                # Reset to minimum realistic amount
                if category == "accommodation":
                    validated[category] = 1500 * nights_stay  # ₹1500/night minimum
                elif category == "activities":
                    validated[category] = 500 * travelers * duration  # ₹500/person/day
                elif category == "food_transport":
                    validated[category] = 400 * travelers * duration  # ₹400/person/day
                elif category == "flights":
                    validated[category] = 3000 * travelers  # ₹3000/person minimum
                elif category == "buffer":
                    validated[category] = total_budget * 0.03  # 3% buffer
        
        # Ensure flights are realistic
        min_flight_per_person = 3000
        max_flight_per_person = 15000
        total_min_flights = min_flight_per_person * travelers
        total_max_flights = max_flight_per_person * travelers
        
        if validated["flights"] < total_min_flights:
            logger.info(f"🔄 Adjusting flight budget up to minimum: ₹{total_min_flights:,}")
            validated["flights"] = total_min_flights
        elif validated["flights"] > total_max_flights:
            logger.info(f"🔄 Adjusting flight budget down to maximum: ₹{total_max_flights:,}")
            validated["flights"] = total_max_flights
        
        # Ensure accommodation is realistic
        min_accommodation_per_night = 1500
        max_accommodation_per_night = 8000
        total_min_accommodation = min_accommodation_per_night * nights_stay
        total_max_accommodation = max_accommodation_per_night * nights_stay
        
        if validated["accommodation"] < total_min_accommodation:
            logger.info(f"🔄 Adjusting accommodation budget up to minimum: ₹{total_min_accommodation:,}")
            validated["accommodation"] = total_min_accommodation
        elif validated["accommodation"] > total_max_accommodation:
            logger.info(f"🔄 Adjusting accommodation budget down to maximum: ₹{total_max_accommodation:,}")
            validated["accommodation"] = total_max_accommodation
        
        # Ensure total doesn't exceed budget
        total = sum(validated.values())
        if total > total_budget:
            scale_factor = total_budget / total
            for category in validated:
                if category != "buffer":
                    validated[category] *= scale_factor
            logger.info(f"🔄 Scaled all categories to fit budget")
        
        return validated

    def _generate_optimization_suggestions(self, budgets: Dict, user_vibe: str, 
                                        total_budget: float, travelers: int, 
                                        destination: str, duration: int) -> List[str]:
        """Generate practical budget optimization suggestions"""
        suggestions = []
        
        flight_budget = budgets.get("flights", 0)
        accommodation_budget = budgets.get("accommodation", 0)
        
        # Flight suggestions
        flight_per_person = flight_budget / travelers
        if flight_per_person > 10000:
            suggestions.append("✈️ Consider budget airlines or mid-week flights to save on airfare")
        elif flight_per_person < 4000:
            suggestions.append("✈️ Great flight budget! Book early for best deals")
        
        # Accommodation suggestions
        accommodation_per_night = accommodation_budget / (duration - 1) if duration > 1 else accommodation_budget
        if accommodation_per_night > 5000:
            suggestions.append("🏨 Look for vacation rentals or guesthouses for better value")
        
        return suggestions[:3]

    def _calculate_daily_breakdown(self, budgets: Dict, duration: int, travelers: int) -> Dict:
        """Calculate realistic daily budget breakdown"""
        daily_breakdown = {}
        nights_stay = duration - 1 if duration > 1 else 1
        
        # Accommodation per night
        daily_breakdown["accommodation_per_night"] = budgets.get("accommodation", 0) / nights_stay
        
        # Activities per day
        daily_breakdown["activities_per_day"] = budgets.get("activities", 0) / duration
        
        # Food & transport per day per person
        daily_breakdown["food_transport_per_person_per_day"] = budgets.get("food_transport", 0) / duration / travelers
        
        # Total daily budget per person (excluding flights)
        daily_breakdown["total_daily_per_person"] = (
            daily_breakdown["accommodation_per_night"] / travelers + 
            daily_breakdown["activities_per_day"] / travelers + 
            daily_breakdown["food_transport_per_person_per_day"]
        )
        
        # Flights per person (one-time cost)
        daily_breakdown["flights_per_person"] = budgets.get("flights", 0) / travelers
        
        return daily_breakdown

    def _is_budget_realistic(self, budgets: Dict, total_budget: float, duration: int, travelers: int) -> bool:
        """Check if the budget allocation is realistic"""
        flight_budget = budgets.get("flights", 0)
        accommodation_budget = budgets.get("accommodation", 0)
        activities_budget = budgets.get("activities", 0)
        
        # Basic validation
        if flight_budget > total_budget * 0.5:
            return False
        if accommodation_budget < 1500 * (duration - 1):
            return False
        if activities_budget < 500 * travelers * duration:
            return False
        if sum(budgets.values()) > total_budget * 1.1:
            return False
            
        return True

    def _get_cached_budget(self, cache_key: str) -> Optional[Dict]:
        """Get cached budget optimization"""
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                logger.info(f"📦 Retrieved cached budget: {cache_key}")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"⚠️ Cache read failed: {e}")
        return None

    def _cache_budget(self, cache_key: str, budget_data: Dict, ttl: int = 43200):
        """Cache budget optimization for 12 hours"""
        try:
            self.redis_client.setex(cache_key, ttl, json.dumps(budget_data))
            logger.info(f"💾 Cached budget optimization: {cache_key}")
        except Exception as e:
            logger.warning(f"⚠️ Cache write failed: {e}")

    def _handle_error(self, error: Exception, step: str, context_id: str, workflow_id: str):
        """Handle errors gracefully"""
        error_msg = f"Budget Optimizer Error ({step}): {str(error)}"
        logger.error(error_msg)
        
        try:
            error_message = create_result_message(
                context_id=context_id,
                sender="budget_optimizer",
                receiver="orchestrator",
                payload={
                    "workflow_id": workflow_id,
                    "error": error_msg,
                    "step": step,
                    "timestamp": datetime.now().isoformat()
                }
            )
            self.client.send_message_with_retry(error_message)
        except Exception as e:
            logger.critical(f"🚨 Critical: Failed to send error message: {e}")

    def shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down Budget Optimizer Agent...")

def create_budget_optimizer_agent(context_id: str) -> BudgetOptimizerAgent:
    return BudgetOptimizerAgent(context_id)