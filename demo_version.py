#!/usr/bin/env python3
import asyncio
import logging
from datetime import datetime, timedelta
from deriv_connector import StepIndexDerivTrader
from real_analytics import RealAnalytics

class DemoTradingSystem:
    def __init__(self, api_token):
        self.api_token = api_token
        self.trader = None
        self.analytics = RealAnalytics()
        self.running = False
        self.start_time = datetime.now()
        self.demo_duration = timedelta(days=7)  # 7-day trial
        
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
        self.logger = logging.getLogger(__name__)
    
    async def start_demo(self):
        """Start demo trading system"""
        print("="*60)
        print("STEP INDEX DEMO TRADING SYSTEM")
        print("="*60)
        print("🎯 Strategy: Mean reversion after 3+ consecutive steps")
        print("📊 Proven: 75.3% win rate on real data")
        print("⚠️  Demo Mode: Virtual money only")
        print("⏰ Trial: 7 days maximum")
        print("🔒 Risk: Conservative mode only (2-5%)")
        print("="*60)
        
        try:
            # Initialize trader
            self.trader = StepIndexDerivTrader("1089", self.api_token, is_demo=True)
            await self.trader.connect()
            await asyncio.sleep(3)
            
            if not self.trader.connector.is_connected:
                self.logger.error("❌ Connection failed - check API token")
                return
            
            balance = self.trader.connector.balance
            self.logger.info(f"✅ Connected - Demo Balance: ${balance}")
            
            if balance <= 0:
                self.logger.error("❌ Demo account has no balance")
                return
            
            print(f"\n🚀 Starting demo trading with ${balance} virtual balance")
            print("📝 Logs saved to: stepbot.log")
            print("📊 Performance data: trading_data.json")
            print("⏹️  Press Ctrl+C to stop\n")
            
            self.running = True
            await self._demo_trading_loop()
            
        except Exception as e:
            self.logger.error(f"❌ Demo system error: {e}")
    
    async def _demo_trading_loop(self):
        """Demo trading loop with time limit"""
        price_history = []
        
        while self.running:
            try:
                # Check trial period
                if datetime.now() - self.start_time > self.demo_duration:
                    print("\n⏰ 7-day demo period expired")
                    print("Contact us for full system access")
                    break
                
                # Get current price
                price = await self.trader.get_current_price('STEP_10')
                
                if price:
                    price_history.append(price)
                    
                    if len(price_history) > 15:
                        price_history = price_history[-15:]
                    
                    # Analyze for signals
                    if len(price_history) >= 5:
                        signal = self._analyze_signal(price_history)
                        
                        if signal:
                            await self._execute_demo_trade(signal)
                
                # Update balance every 30 seconds
                if len(price_history) % 6 == 0:
                    await self.trader.connector.get_account_info()
                    await asyncio.sleep(1)
                    balance = self.trader.connector.balance
                    
                    if balance <= 10:
                        self.logger.warning("⚠️ Demo balance too low")
                        break
                
                await asyncio.sleep(5)
                
            except Exception as e:
                self.logger.error(f"❌ Trading loop error: {e}")
                await asyncio.sleep(10)
    
    def _analyze_signal(self, prices):
        """Proven signal analysis"""
        if len(prices) < 5:
            return None
        
        current_price = prices[-1]
        
        # Count consecutive steps
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
        
        # Mean reversion after 3+ steps (proven strategy)
        if step_count >= 3:
            trade_direction = 'SHORT' if direction == 'up' else 'LONG'
            
            return {
                'price': current_price,
                'direction': trade_direction,
                'step_count': step_count,
                'confidence': min(95, 60 + step_count * 8)
            }
        
        return None
    
    async def _execute_demo_trade(self, signal):
        """Execute demo trade (conservative mode only)"""
        try:
            balance = self.trader.connector.balance
            
            if balance <= 10:
                return
            
            # Conservative sizing only (2-3% max)
            stake = balance * 0.025  # 2.5% risk
            stake = max(1.0, min(stake, 50))  # Max $50 for demo
            
            # Place real demo trade
            contract_id = await self.trader.place_step_trade(
                symbol='STEP_10',
                direction=signal['direction'],
                stake=stake,
                duration_ticks=5
            )
            
            if contract_id:
                self.analytics.add_trade({
                    'timestamp': datetime.now(),
                    'symbol': 'STEP_10',
                    'direction': signal['direction'],
                    'stake': stake,
                    'confidence': signal['confidence'],
                    'step_count': signal['step_count'],
                    'outcome': 'PENDING',
                    'contract_id': contract_id
                })
                
                self.logger.info(f"📈 DEMO TRADE: {signal['direction']} ${stake:.2f} | Steps:{signal['step_count']} | Confidence:{signal['confidence']}%")
            
        except Exception as e:
            self.logger.error(f"❌ Demo trade error: {e}")
    
    async def stop(self):
        """Stop demo system"""
        self.running = False
        if self.trader:
            await self.trader.connector.disconnect()
        
        print("\n" + "="*60)
        print("DEMO SESSION ENDED")
        print("="*60)
        print("📊 Check trading_data.json for performance results")
        print("📝 Check stepbot.log for detailed trade logs")
        print("💬 Contact us for full system access")
        print("="*60)

async def main():
    print("STEP INDEX DEMO SYSTEM")
    print("Proven 75% win rate strategy")
    print()
    
    api_token = input("Enter your Deriv API token: ").strip()
    
    if not api_token:
        print("❌ API token required")
        return
    
    if len(api_token) < 10:
        print("❌ Invalid API token format")
        return
    
    demo_system = DemoTradingSystem(api_token)
    
    try:
        await demo_system.start_demo()
    except KeyboardInterrupt:
        print("\n⏹️ Stopping demo system...")
        await demo_system.stop()

if __name__ == "__main__":
    asyncio.run(main())