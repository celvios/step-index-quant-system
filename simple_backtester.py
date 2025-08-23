#!/usr/bin/env python3
import asyncio
import json
import logging
from datetime import datetime, timedelta
from deriv_connector import DerivConnector

class SimpleBacktester:
    def __init__(self, api_token):
        self.api_token = api_token
        self.connector = DerivConnector("1089", api_token, is_demo=True)
        self.historical_data = []
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    async def fetch_data(self):
        """Fetch historical data"""
        try:
            await self.connector.connect()
            
            # Wait for connection
            await asyncio.sleep(2)
            
            if not self.connector.is_connected:
                self.logger.error("Failed to connect")
                return False
            
            # Request historical data
            end_time = int(datetime.now().timestamp())
            start_time = int((datetime.now() - timedelta(days=7)).timestamp())  # 7 days
            
            request = {
                "ticks_history": "R_10",
                "start": start_time,
                "end": end_time,
                "style": "ticks",
                "count": 500,
                "req_id": 1
            }
            
            # Override message handler to capture data
            original_handler = self.connector._process_message
            
            async def capture_handler(data):
                if data.get('msg_type') == 'history':
                    history = data.get('history', {})
                    if 'prices' in history:
                        self.logger.info(f"Received {len(history['prices'])} price points")
                        # Store raw data for inspection
                        self.historical_data = history['prices']
                        self.logger.info(f"Sample data: {history['prices'][:3]}")
                
                await original_handler(data)
            
            self.connector._process_message = capture_handler
            
            await self.connector._send_request(request)
            
            # Wait for response
            await asyncio.sleep(5)
            
            await self.connector.disconnect()
            
            return len(self.historical_data) > 0
            
        except Exception as e:
            self.logger.error(f"Error fetching data: {e}")
            return False
    
    async def run_simple_backtest(self):
        """Run simple backtest"""
        success = await self.fetch_data()
        
        if not success:
            print("Failed to fetch historical data")
            return
        
        print(f"\nFetched {len(self.historical_data)} data points")
        print(f"Sample data: {self.historical_data[:5]}")
        
        # Simple analysis
        if len(self.historical_data) > 10:
            # Convert to prices if needed
            prices = []
            for item in self.historical_data:
                if isinstance(item, list) and len(item) >= 2:
                    prices.append(item[1])  # price is second element
                elif isinstance(item, (int, float)):
                    prices.append(item)
            
            if prices:
                print(f"\nPrice Analysis:")
                print(f"First price: {prices[0]}")
                print(f"Last price: {prices[-1]}")
                print(f"Min price: {min(prices)}")
                print(f"Max price: {max(prices)}")
                print(f"Price range: {max(prices) - min(prices)}")
                
                # Count step movements
                steps = 0
                for i in range(1, len(prices)):
                    if abs(prices[i] - prices[i-1]) >= 0.1:
                        steps += 1
                
                print(f"Step movements detected: {steps}")
                print(f"Step frequency: {steps/len(prices)*100:.1f}%")

async def main():
    api_token = "HVPPcwqc75HMSHg"
    
    backtester = SimpleBacktester(api_token)
    await backtester.run_simple_backtest()

if __name__ == "__main__":
    asyncio.run(main())