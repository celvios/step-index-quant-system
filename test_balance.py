import asyncio
import websockets
import json

async def test_balance(api_token):
    """Test balance retrieval from Deriv"""
    
    print(f"Testing balance with token: {api_token[:10]}...")
    
    try:
        url = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
        
        async with websockets.connect(url) as ws:
            # Authorize
            auth_msg = {
                "authorize": api_token,
                "req_id": 1
            }
            
            await ws.send(json.dumps(auth_msg))
            response = await ws.recv()
            data = json.loads(response)
            
            print(f"Auth response: {data}")
            
            if "authorize" in data:
                balance = data["authorize"].get("balance", 0)
                currency = data["authorize"].get("currency", "USD")
                loginid = data["authorize"].get("loginid", "N/A")
                
                print(f"✅ Balance: {balance} {currency}")
                print(f"✅ Account: {loginid}")
                
                # Also try balance request
                balance_msg = {
                    "balance": 1,
                    "req_id": 2
                }
                
                await ws.send(json.dumps(balance_msg))
                balance_response = await ws.recv()
                balance_data = json.loads(balance_response)
                
                print(f"Balance response: {balance_data}")
                
                return True
            else:
                print(f"❌ Auth failed: {data}")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    token = input("Enter your Deriv API token: ").strip()
    
    if token:
        await test_balance(token)
    else:
        print("No token provided")

if __name__ == "__main__":
    asyncio.run(main())