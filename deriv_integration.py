import asyncio
from datetime import datetime
from typing import Dict, Optional
from deriv_connector import StepIndexDerivTrader
from step_index_quant_system import StepIndexQuantSystem
from risk_manager import InstitutionalRiskManager
import logging

class DerivStepIndexSystem:
    def __init__(self, deriv_app_id: str, deriv_api_token: str, 
                 initial_capital: float = 1000, is_demo: bool = True):
        
        # Deriv connection
        self.deriv_trader = StepIndexDerivTrader(deriv_app_id, deriv_api_token, is_demo)
        
        # Trading system
        self.quant_system = StepIndexQuantSystem(initial_capital)
        self.risk_manager = InstitutionalRiskManager(
            max_portfolio_risk=0.05,  # 5% for Deriv
            max_single_trade_risk=0.02  # 2% per trade
        )
        
        # State tracking
        self.running = False
        self.active_signals = {}
        self.price_history = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the Deriv integrated system"""
        self.logger.info("Starting Deriv Step Index System")
        
        try:
            # Connect to Deriv
            await self.deriv_trader.connect()
            
            # Wait for initial data
            await asyncio.sleep(3)
            
            # Start trading loop
            self.running = True
            await self._trading_loop()
            
        except Exception as e:
            self.logger.error(f"System start error: {e}")
            raise
    
    async def stop(self):
        """Stop the system"""
        self.logger.info("Stopping system")
        self.running = False
        
        # Close all positions
        await self._close_all_positions()
        
        # Disconnect
        await self.deriv_trader.connector.disconnect()
    
    async def _trading_loop(self):
        """Main trading loop"""
        while self.running:
            try:
                # Get current market data
                await self._update_market_data()
                
                # Generate signals
                signals = await self._generate_signals()
                
                # Process signals
                for signal in signals:
                    await self._process_signal(signal)
                
                # Monitor positions
                await self._monitor_positions()
                
                # Wait before next cycle
                await asyncio.sleep(5)  # 5-second cycle
                
            except Exception as e:
                self.logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(10)
    
    async def _update_market_data(self):
        """Update market data from Deriv"""
        try:
            # Get current prices
            step_10_price = await self.deriv_trader.get_current_price('STEP_10')
            
            if step_10_price:
                # Add to price history
                price_data = {
                    'timestamp': datetime.now(),
                    'close': step_10_price,
                    'high': step_10_price,  # Simplified
                    'low': step_10_price,
                    'open': step_10_price
                }
                
                self.price_history.append(price_data)
                
                # Keep only last 100 points
                if len(self.price_history) > 100:
                    self.price_history = self.price_history[-100:]
                    
        except Exception as e:
            self.logger.error(f"Market data update error: {e}")
    
    async def _generate_signals(self) -> list:
        """Generate trading signals based on Step Index strategy"""
        signals = []
        
        if len(self.price_history) < 20:
            return signals
        
        try:
            # Get recent prices
            recent_prices = [p['close'] for p in self.price_history[-10:]]
            current_price = recent_prices[-1]
            
            # Simple Step Index strategy implementation
            # Look for step velocity (3+ consecutive 0.1 moves)
            step_count = 0
            direction = None
            
            for i in range(len(recent_prices) - 1):
                price_diff = recent_prices[i+1] - recent_prices[i]
                
                if abs(price_diff) >= 0.1:  # Step movement
                    if price_diff > 0:
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
                else:
                    step_count = 0
                    direction = None
            
            # Generate signal if we have 3+ consecutive steps
            if step_count >= 3 and direction:
                # Check if we're at a psychological level
                is_psychological = self._is_psychological_level(current_price)
                
                # Calculate confluence score
                confluence_score = 60  # Base score
                if step_count >= 3:
                    confluence_score += 20
                if is_psychological:
                    confluence_score += 15
                
                if confluence_score >= 75:
                    signals.append({
                        'symbol': 'STEP_10',
                        'direction': 'LONG' if direction == 'up' else 'SHORT',
                        'entry_price': current_price,
                        'confluence_score': confluence_score,
                        'timestamp': datetime.now()
                    })
                    
        except Exception as e:
            self.logger.error(f"Signal generation error: {e}")
        
        return signals
    
    def _is_psychological_level(self, price: float) -> bool:
        """Check if price is at psychological level"""
        # Whole numbers
        if abs(price - round(price)) < 0.01:
            return True
        # Half levels (x.5)
        if abs(price - (round(price * 2) / 2)) < 0.01:
            return True
        return False
    
    async def _process_signal(self, signal: Dict):
        """Process a trading signal"""
        try:
            # Check if we already have a signal for this direction
            signal_key = f"{signal['symbol']}_{signal['direction']}"
            
            if signal_key in self.active_signals:
                return  # Skip duplicate signals
            
            # Get account balance
            balance = await self.deriv_trader.get_account_balance()
            
            if balance <= 0:
                self.logger.warning("Insufficient balance")
                return
            
            # Calculate position size (risk management)
            risk_per_trade = min(balance * 0.02, 50)  # 2% or $50 max
            stake_amount = max(risk_per_trade, 1.0)  # Minimum $1
            
            # Place trade
            await self.deriv_trader.place_step_trade(
                symbol=signal['symbol'],
                direction=signal['direction'],
                stake=stake_amount,
                duration_ticks=5  # 5 ticks duration
            )
            
            # Track signal
            self.active_signals[signal_key] = {
                'signal': signal,
                'stake': stake_amount,
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"Trade placed: {signal['direction']} {signal['symbol']} - Stake: ${stake_amount}")
            
        except Exception as e:
            self.logger.error(f"Signal processing error: {e}")
    
    async def _monitor_positions(self):
        """Monitor active positions"""
        try:
            # Get portfolio from Deriv
            await self.deriv_trader.connector.get_portfolio()
            
            # Clean up old signals (older than 5 minutes)
            current_time = datetime.now()
            expired_signals = []
            
            for key, signal_data in self.active_signals.items():
                age = (current_time - signal_data['timestamp']).total_seconds()
                if age > 300:  # 5 minutes
                    expired_signals.append(key)
            
            for key in expired_signals:
                del self.active_signals[key]
                
        except Exception as e:
            self.logger.error(f"Position monitoring error: {e}")
    
    async def _close_all_positions(self):
        """Close all open positions"""
        try:
            # Get current portfolio
            await self.deriv_trader.connector.get_portfolio()
            
            # Close each active contract
            for contract_id in self.deriv_trader.active_contracts:
                await self.deriv_trader.close_position(contract_id)
                
            self.logger.info("All positions closed")
            
        except Exception as e:
            self.logger.error(f"Error closing positions: {e}")

# Configuration and startup
class DerivConfig:
    def __init__(self):
        # Deriv API credentials (replace with your actual credentials)
        self.APP_ID = "1089"  # Default app ID, get your own from Deriv
        self.API_TOKEN = ""   # Your API token from Deriv account
        self.IS_DEMO = True   # Set to False for real account
        self.INITIAL_CAPITAL = 1000  # Starting balance

async def main():
    """Main entry point"""
    config = DerivConfig()
    
    # Check if API token is provided
    if not config.API_TOKEN:
        print("Please set your Deriv API token in DerivConfig")
        print("Get your token from: https://app.deriv.com/account/api-token")
        return
    
    # Initialize system
    system = DerivStepIndexSystem(
        deriv_app_id=config.APP_ID,
        deriv_api_token=config.API_TOKEN,
        initial_capital=config.INITIAL_CAPITAL,
        is_demo=config.IS_DEMO
    )
    
    try:
        print("Starting Deriv Step Index Trading System...")
        print("Press Ctrl+C to stop")
        
        await system.start()
        
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        print(f"System error: {e}")
    finally:
        await system.stop()
        print("System stopped")

if __name__ == "__main__":
    asyncio.run(main())