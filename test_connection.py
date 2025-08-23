import asyncio
import websockets
import json

async def test_deriv_connection():
    """Test basic Deriv connection without token"""
    
    print("Testing Deriv WebSocket connection...")
    
    try:
        # Connect without token first
        url = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
        
        async with websockets.connect(url) as ws:
            print("✅ WebSocket connection successful!")
            
            # Test ping
            ping_msg = {"ping": 1, "req_id": 1}
            await ws.send(json.dumps(ping_msg))
            
            response = await ws.recv()
            data = json.loads(response)
            
            if "pong" in data:
                print("✅ Ping/Pong successful!")
                return True
            else:
                print(f"❌ Unexpected response: {data}")
                return False
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

async def test_with_token(api_token):
    """Test connection with API token"""
    
    print(f"\nTesting with API token: {api_token[:10]}...")
    
    try:
        url = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
        
        async with websockets.connect(url) as ws:
            # Authorize
            auth_msg = {
                "authorize": api_token,
                "req_id": 2
            }
            
            await ws.send(json.dumps(auth_msg))
            response = await ws.recv()
            data = json.loads(response)
            
            if "authorize" in data:
                print("✅ Authorization successful!")
                print(f"Account ID: {data['authorize'].get('loginid', 'N/A')}")
                print(f"Currency: {data['authorize'].get('currency', 'N/A')}")
                return True
            elif "error" in data:
                print(f"❌ Authorization failed: {data['error']['message']}")
                return False
            else:
                print(f"❌ Unexpected response: {data}")
                return False
                
    except Exception as e:
        print(f"❌ Connection with token failed: {e}")
        return False

async def main():
    # Test basic connection
    basic_ok = await test_deriv_connection()
    
    if basic_ok:
        print("\n" + "="*50)
        print("Basic connection works!")
        print("Now test with your API token:")
        
        token = input("Enter your Deriv API token: ").strip()
        
        if token:
            await test_with_token(token)
        else:
            print("No token provided - skipping token test")
    
    print("\n" + "="*50)
    print("Connection test complete!")

if __name__ == "__main__":
    asyncio.run(main())