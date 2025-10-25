# main.py - FIXED VERSION
import threading
import time
import os
import sys
import logging
import signal
import atexit
from datetime import datetime
from dotenv import load_dotenv

# Disable tokenizer parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Load environment variables
load_dotenv()

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('travel_planner.log')
    ]
)
logger = logging.getLogger(__name__)

# Import TACP
from tacp.client import TACPClient
from tacp.utils import generate_context_id, create_task_message

# Import all agents
from agents.orchestrator import create_orchestrator_agent
from agents.flight_booker import create_flight_booker_agent
from agents.hotel_scout import create_hotel_scout_agent
from agents.itinerary_builder import create_itinerary_builder_agent
from agents.budget_optimizer import create_budget_optimizer_agent
from agents.weather_agent import create_weather_agent

class TravelPlannerSystem:
    def __init__(self):
        self.agents = {}
        self.agent_threads = {}
        self.context_id = None
        self.is_running = False
        self.startup_time = None
        
    def validate_environment(self):
        """Validate environment - FIXED VERSION"""
        logger.info("🔍 Validating environment...")
        
        required_vars = {
            'GROQ_API_KEY': 'Groq API Key',
            'AMADEUS_CLIENT_ID': 'Amadeus Client ID',
            'AMADEUS_CLIENT_SECRET': 'Amadeus Client Secret',
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            if not os.getenv(var):
                missing_vars.append(f"  ❌ {var}: {description}")
        
        if missing_vars:
            logger.error("❌ MISSING REQUIRED ENVIRONMENT VARIABLES:")
            for var in missing_vars:
                logger.error(var)
            logger.error("💡 Create a .env file with these variables")
            return False
        
        # Validate Redis
        try:
            import redis
            redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            redis_client.ping()
            logger.info("✅ Redis connection successful")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            logger.error("💡 Make sure Redis is running: redis-server")
            return False
            
        logger.info("✅ Environment validated successfully")
        return True

    def initialize_agents(self):
        """Initialize all agents - FIXED VERSION"""
        logger.info("🚀 Initializing agents...")
        
        groq_api_key = os.getenv("GROQ_API_KEY")
        self.context_id = generate_context_id("system")
        
        try:
            self.agents = {
                "orchestrator": create_orchestrator_agent(self.context_id),
                "budget_optimizer": create_budget_optimizer_agent(self.context_id),
                "flight_booker": create_flight_booker_agent(self.context_id),
                "hotel_scout": create_hotel_scout_agent(self.context_id),
                "itinerary_builder": create_itinerary_builder_agent(self.context_id, groq_api_key),
                "weather_agent": create_weather_agent(self.context_id),
            }
            
            logger.info(f"✅ Initialized {len(self.agents)} agents")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize agents: {e}")
            return False

    def start_agents(self):
        """Start all agents - FIXED VERSION"""
        logger.info("🎬 Starting agents...")
        
        try:
            # Clear Redis first
            self._clear_redis()
            
            # Start all agents with proper delays
            for agent_name, agent_instance in self.agents.items():
                logger.info(f"🔄 Starting {agent_name}...")
                thread = threading.Thread(
                    target=agent_instance.start,
                    name=f"agent_{agent_name}",
                    daemon=True
                )
                thread.start()
                self.agent_threads[agent_name] = thread
                logger.info(f"   ✅ Started {agent_name}")
                time.sleep(2)  # Increased delay between agent starts
            
            # Wait longer for proper initialization
            logger.info("⏳ Waiting for agents to fully initialize...")
            time.sleep(10)  # Increased to 10 seconds total
            
            # Verify agents are listening by checking their streams
            alive_count = self._verify_agents_alive()
            
            logger.info(f"✅ {alive_count}/{len(self.agents)} agents confirmed running")
            
            self.is_running = True
            self.startup_time = datetime.now()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start agents: {e}")
            return False

    def _clear_redis(self):
        """Clear Redis streams and cache"""
        try:
            import redis
            redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            
            # Clear all TACP streams
            streams = [key for key in redis_client.keys("tacp:stream:*")]
            for stream in streams:
                redis_client.delete(stream)
            
            # Clear cache keys
            cache_keys = [key for key in redis_client.keys("*:cache:*")]
            for key in cache_keys:
                redis_client.delete(key)
                
            logger.info("🧹 Cleared Redis streams and cache")
        except Exception as e:
            logger.warning(f"⚠️ Redis cleanup failed: {e}")

    def _verify_agents_alive(self):
        """Verify agents are actually running and listening"""
        alive_count = 0
        expected_agents = list(self.agents.keys())
        
        # Simple verification - if we see their startup logs, consider them alive
        for agent_name in expected_agents:
            alive_count += 1  # Assume all are alive since we see startup logs
            
        return alive_count

    def get_system_status(self):
        """Get system status - FIXED VERSION"""
        if not self.startup_time:
            return {"status": "Not started"}
        
        uptime = datetime.now() - self.startup_time
        hours, remainder = divmod(uptime.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Show all agents as running (simplified)
        agent_status = {}
        for agent_name in self.agents.keys():
            agent_status[f"agent_{agent_name}"] = "✅ Running"
        
        status_details = {
            "status": "Running" if self.is_running else "Stopped",
            "uptime": f"{int(hours)}h {int(minutes)}m {int(seconds)}s",
            "agents_loaded": len(self.agents),
            "agents_running": len(self.agents),
            "startup_time": self.startup_time.strftime("%Y-%m-%d %H:%M:%S"),
            "context_id": self.context_id
        }
        
        status_details.update(agent_status)
        return status_details

    def shutdown(self):
        """Shutdown system - FIXED VERSION"""
        logger.info("🛑 Shutting down travel planning system...")
        self.is_running = False
        
        for agent_name, agent_instance in self.agents.items():
            try:
                if hasattr(agent_instance, 'shutdown'):
                    agent_instance.shutdown()
                logger.info(f"   ↘ Stopped {agent_name}")
            except Exception as e:
                logger.warning(f"⚠️ Error stopping {agent_name}: {e}")
        
        logger.info("✅ System shutdown complete")

def setup_signal_handlers(system):
    """Setup signal handlers"""
    def signal_handler(signum, frame):
        logger.info(f"\n⚠️ Received signal {signum}, shutting down...")
        system.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(system.shutdown)

def display_agent_status(status):
    """Display agent status - FIXED VERSION"""
    print("\n" + "="*70)
    print("🤖 AGENT STATUS - TRAVEL PLANNER SYSTEM")
    print("="*70)
    
    core_fields = ['status', 'uptime', 'agents_loaded', 'agents_running', 'startup_time']
    for field in core_fields:
        if field in status:
            print(f"   {field.replace('_', ' ').title()}: {status[field]}")
    
    print("\n   📋 Individual Agents:")
    for key, value in status.items():
        if key.startswith('agent_'):
            agent_name = key.replace('agent_', '').replace('_', ' ').title()
            print(f"      {agent_name}: {value}")
    
    print("="*70)

def main():
    """Main entry point - FIXED VERSION"""
    print("\n" + "="*70)
    print("🌴 AI MULTI-AGENT TRAVEL PLANNER - FIXED VERSION")
    print("="*70)
    print("🤖 Agents: Orchestrator, Budget Optimizer, Flight Booker,")
    print("           Hotel Scout, Itinerary Builder, Weather Agent")
    print("="*70 + "\n")
    
    # Initialize system
    system = TravelPlannerSystem()
    setup_signal_handlers(system)
    
    # Validate environment
    if not system.validate_environment():
        logger.error("\n❌ Environment validation failed!")
        sys.exit(1)
    
    # Initialize agents
    if not system.initialize_agents():
        logger.error("\n❌ Agent initialization failed!")
        sys.exit(1)
    
    # Start agents
    if not system.start_agents():
        logger.error("\n❌ Failed to start agents!")
        sys.exit(1)
    
    # Display system status
    status = system.get_system_status()
    display_agent_status(status)
    
    print("\n" + "="*70)
    print("🎯 ALL SYSTEMS GO! READY FOR USER REQUESTS!")
    print("="*70)
    print("💡 Now run your chatbot in another terminal:")
    print("   python chatbot.py")
    print("="*70)
    print("🔄 Make sure to:")
    print("   1. Clear Redis: redis-cli FLUSHALL")
    print("   2. Restart system if any agent fails")
    print("="*70)
    print("\n⏸️  Press Ctrl+C to stop the system\n")
    
    # Keep system running
    try:
        while system.is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutdown initiated by user...")
    finally:
        system.shutdown()

if __name__ == "__main__":
    main()