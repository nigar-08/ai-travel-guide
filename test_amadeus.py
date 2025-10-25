# test_amadeus.py - UPDATED VERSION
import os
import json
from utils.amadeus_auth import create_amadeus_client
from dotenv import load_dotenv

load_dotenv()

def test_amadeus():
    print("🧪 TESTING AMADEUS API...")
    print("=" * 50)
    
    # Check credentials
    client_id = os.getenv("AMADEUS_CLIENT_ID")
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    
    print(f"1. Checking credentials...")
    print(f"   🔑 Client ID: {'✅ Set' if client_id else '❌ Missing'}")
    print(f"   🔑 Client Secret: {'✅ Set' if client_secret else '❌ Missing'}")
    
    if not client_id or not client_secret:
        print("❌ Please set AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET in .env file")
        return
    
    try:
        print("2. Creating Amadeus client...")
        client = create_amadeus_client()
        print("   ✅ Client created successfully")
        
        print("3. Testing token generation...")
        token = client.get_token()
        print(f"   ✅ Token obtained: {token[:20]}...")
        
        print("4. Testing flight search...")
        print("   🔍 Searching: BOM → DEL on 2025-11-25")
        
        flights = client.search_flights(
            origin="BOM",      # Mumbai
            destination="DEL", # Delhi  
            departure_date="2025-11-25",
            adults=1,
            max_price=10000
        )
        
        if flights:
            print(f"   ✅ SUCCESS! Found {len(flights)} real flights!")
            print("\n   📋 FLIGHT RESULTS:")
            for i, flight in enumerate(flights[:3], 1):
                print(f"      {i}. {flight['airline']} {flight['flight_number']}")
                print(f"         💰 ₹{flight['price']:,.0f} per person")
                print(f"         🕒 {flight['departure_time']} → {flight['arrival_time']}")
                print(f"         ⏱️ {flight['duration']} | 🛑 {flight['stops']} stops")
        else:
            print("   ❌ No flights found.")
            print("   💡 Possible reasons:")
            print("      - Amadeus test environment limitations")
            print("      - No flights available for this route/date")
            print("      - API quota exceeded")
            
    except Exception as e:
        print(f"   ❌ TEST FAILED: {e}")

if __name__ == "__main__":
    test_amadeus()