#!/usr/bin/env python3
import asyncio
import logging
import signal
import sys
from datetime import datetime
from deriv_connector import StepIndexDerivTrader
from real_analytics import RealAnalytics

class HeadlessStepBot:
    def __init__(self, api_token, risk_mode=2, is_demo=True, min_confluence=75):
        self.api_token = api_token
        self.risk_mode = risk_mode  # 2%, 5%, or 15%
        self.is_demo = is_demo
        self.min_confluence = min_confluence
        self.running = False
        self.trader = None
        self.analytics = RealAnalytics()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('stepbot.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start headless bot"""
        self.logger.info("Starting Step Index Headless Bot")
        
        try:
            # Initialize trader
            self.trader = StepIndexDerivTrader(
                app_id="1089",
                api_token=self.api_token,
                is_demo=self.is_demo
            )
            
            # Connect
            await self.trader.connect()
            
            # Wait for balance to load
            await asyncio.sleep(3)
            
            # Check if connection is still valid
            if not self.trader.connector.is_connected:
                self.logger.error("Connection failed - invalid API token")
                return
            
            balance = self.trader.connector.balance
            self.logger.info(f"Connected - Balance: ${balance}")
            
            if balance <= 0:
                self.logger.error("Balance is 0 - check your Deriv account")
                return
            
            # Start trading
            self.running = True
            await self._trading_loop()
            
        except Exception as e:
            self.logger.error(f"Bot error: {e}")
    
    async def _trading_loop(self):
        """Main trading loop"""
        price_history = []
        
        while self.running:
            try:
                # Get current price
                price = await self.trader.get_current_price('STEP_10')
                
                if price:
                    price_history.append({
                        'timestamp': datetime.now(),
                        'price': price
                    })
                    
                    # Keep last 20 prices
                    if len(price_history) > 20:
                        price_history = price_history[-20:]
                    
                    # Check for signals
                    signal = self._analyze_signal(price_history)
                    
                    if signal and signal['confluence_score'] >= self.min_confluence:
                        await self._execute_trade(signal)
                
                # Check balance and update from API every 10 cycles
                if len(price_history) % 10 == 0:
                    await self.trader.connector.get_account_info()
                    await asyncio.sleep(1)  # Wait for balance update
                    balance = self.trader.connector.balance
                    if balance <= 0:
                        self.logger.warning("Balance depleted - stopping bot")
                        self.running = False
                    else:
                        self.logger.info(f"Current balance: ${balance}")
                        self.analytics.update_balance(balance)
                
                await asyncio.sleep(2)  # 2-second cycle
                
            except Exception as e:
                self.logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(5)
    
    def _analyze_signal(self, price_history):
        """Analyze for Step Index signals"""
        if len(price_history) < 10:
            return None
        
        prices = [p['price'] for p in price_history]
        current_price = prices[-1]
        
        # Step velocity detection
        step_count = 0
        direction = None
        
        for i in range(len(prices) - 1):
            diff = prices[i+1] - prices[i]
            if abs(diff) >= 0.1:
                if diff > 0:
                    if direction == 'up':
                        step_count += 1
                    else:
                        direction = 'up'
                        step_count = 1
                else:
                    if direction == 'down':
                        step_count += 1
                    else:
                        direction = 'down'
                        step_count = 1
        
        if step_count >= 3:
            psychological = abs(current_price - round(current_price)) < 0.01
            
            confluence_score = 50 + step_count * 5
            if psychological:
                confluence_score += 15
            
            return {
                'timestamp': datetime.now(),
                'price': current_price,
                'direction': 'LONG' if direction == 'up' else 'SHORT',
                'confluence_score': confluence_score
            }
        
        return None
    
    async def _execute_trade(self, signal):
        """Execute real trade"""
        try:
            balance = self.trader.connector.balance
            
            # Skip if balance is 0
            if balance <= 0:
                self.logger.warning("Skipping trade - balance is 0")
                return
            
            stake = balance * (self.risk_mode / 100)
            stake = max(1.0, min(stake, 100))
            
            # Place real trade
            contract_id = await self.trader.place_step_trade(
                symbol='STEP_10',
                direction=signal['direction'],
                stake=stake,
                duration_ticks=5
            )
            
            if contract_id:
                # Log pending trade
                self.analytics.add_trade({
                    'timestamp': signal['timestamp'],
                    'symbol': 'STEP_10',
                    'direction': signal['direction'],
                    'stake': stake,
                    'confluence_score': signal['confluence_score'],
                    'outcome': 'PENDING',
                    'profit': 0,
                    'contract_id': contract_id
                })
                
                self.logger.info(f"Real Trade Placed: {signal['direction']} ${stake} Score:{signal['confluence_score']} Contract:{contract_id}")
            
        except Exception as e:
            self.logger.error(f"Trade execution error: {e}")
    
    async def stop(self):
        """Stop bot gracefully"""
        self.logger.info("Stopping bot...")
        self.running = False
        
        if self.trader:
            await self.trader.connector.disconnect()

# Signal handlers
bot_instance = None

def signal_handler(signum, frame):
    if bot_instance:
        asyncio.create_task(bot_instance.stop())
    sys.exit(0)

async def main():
    global bot_instance
    
    print("Use start_bot.py for interactive setup")
    print("Or run directly with: python3 headless_bot.py")
    
    # Quick start with defaults
    API_TOKEN = input("Enter Deriv API Token: ").strip()
    if not API_TOKEN:
        return
    
    bot_instance = HeadlessStepBot(API_TOKEN, risk_mode=2, is_demo=True)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await bot_instance.start()
    except KeyboardInterrupt:
        await bot_instance.stop()

if __name__ == "__main__":
    asyncio.run(main())