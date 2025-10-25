# check_dead_letters.py
import redis
import json

def check_dead_letters():
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    print("💀 CHECKING DEAD LETTERS")
    print("="*50)
    
    # Get dead letter messages
    dead_messages = r.xrevrange("tacp:stream:dead_letter", count=10)
    
    if not dead_messages:
        print("✅ No dead letters found!")
        return
    
    print(f"Found {len(dead_messages)} failed messages:")
    
    for i, (msg_id, data) in enumerate(dead_messages, 1):
        print(f"\n{i}. DEAD LETTER:")
        try:
            payload = json.loads(data['payload'])
            print(f"   Error: {payload.get('error', 'Unknown error')}")
            print(f"   Failed Agent: {payload.get('failed_by_agent', 'Unknown')}")
            print(f"   Original Sender: {payload.get('original_sender', 'Unknown')}")
            print(f"   Context: {payload.get('context_id', 'Unknown')}")
            
            # Show original message if available
            if 'original_message' in payload:
                print(f"   Original Message: {json.dumps(payload['original_message'], indent=2)}")
                
        except Exception as e:
            print(f"   Could not parse: {e}")
            print(f"   Raw data: {data['payload'][:200]}...")

if __name__ == "__main__":
    check_dead_letters()