import asyncio
import streamlit as st
from deriv_connector import StepIndexDerivTrader
from datetime import datetime
import json

class LiveTradingManager:
    def __init__(self, deriv_token, server, settings):
        self.deriv_token = deriv_token
        self.server = server
        self.settings = settings
        self.trader = None
        self.is_running = False
        self.trade_log = []
        
    async def start_trading(self):
        """Start live trading with Deriv"""
        try:
            # Initialize Deriv trader
            self.trader = StepIndexDerivTrader(
                app_id="1089",
                api_token=self.deriv_token,
                is_demo="Demo" in self.server
            )
            
            # Connect to Deriv
            await self.trader.connect()
            
            # Start trading loop
            self.is_running = True
            await self._trading_loop()
            
        except Exception as e:
            st.error(f"Trading start error: {e}")
            self.is_running = False
    
    async def stop_trading(self):
        """Stop live trading"""
        self.is_running = False
        
        if self.trader:
            # Close all positions
            for contract_id in self.trader.active_contracts:
                await self.trader.close_position(contract_id)
            
            # Disconnect
            await self.trader.connector.disconnect()
    
    async def _trading_loop(self):
        """Main trading loop with real Deriv integration"""
        signal_history = []
        
        while self.is_running:
            try:
                # Get current Step Index prices
                step_10_price = await self.trader.get_current_price('STEP_10')
                
                if step_10_price:
                    # Add to price history
                    signal_history.append({
                        'timestamp': datetime.now(),
                        'price': step_10_price
                    })
                    
                    # Keep last 20 points
                    if len(signal_history) > 20:
                        signal_history = signal_history[-20:]
                    
                    # Generate signal
                    signal = self._analyze_step_pattern(signal_history)
                    
                    if signal and signal['confluence_score'] >= self.settings['min_confluence']:
                        # Execute trade
                        await self._execute_deriv_trade(signal)
                
                # Wait before next analysis
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"Trading loop error: {e}")
                await asyncio.sleep(10)
    
    def _analyze_step_pattern(self, price_history):
        """Analyze Step Index pattern for signals"""
        if len(price_history) < 10:
            return None
        
        prices = [p['price'] for p in price_history]
        current_price = prices[-1]
        
        # Step velocity detection
        step_count = 0
        direction = None
        
        for i in range(len(prices) - 1):
            diff = prices[i+1] - prices[i]
            if abs(diff) >= 0.1:  # Step movement
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
            # Calculate confluence
            psychological = abs(current_price - round(current_price)) < 0.01
            
            confluence_score = 50  # Base
            confluence_score += step_count * 5  # Step velocity
            confluence_score += 15 if psychological else 0  # Psychological level
            confluence_score += 10  # Market structure (simplified)
            
            return {
                'timestamp': datetime.now(),
                'price': current_price,
                'direction': 'LONG' if direction == 'up' else 'SHORT',
                'step_count': step_count,
                'confluence_score': confluence_score,
                'psychological': psychological
            }
        
        return None
    
    async def _execute_deriv_trade(self, signal):
        """Execute trade on Deriv"""
        try:
            # Calculate stake based on risk mode
            balance = await self.trader.get_account_balance()
            
            # Stop trading if balance is 0
            if balance <= 0:
                self.is_running = False
                return
            
            stake = balance * (self.settings['risk_per_trade'] / 100)
            stake = max(1.0, min(stake, 1000))  # Min $1, Max $1000
            
            # Place trade
            await self.trader.place_step_trade(
                symbol='STEP_10',
                direction=signal['direction'],
                stake=stake,
                duration_ticks=5
            )
            
            # Log trade to real analytics
            trade_record = {
                'timestamp': signal['timestamp'],
                'symbol': 'STEP_10',
                'direction': signal['direction'],
                'stake': stake,
                'confluence_score': signal['confluence_score'],
                'outcome': 'PENDING',
                'profit': 0,
                'contract_id': f"temp_{len(self.trade_log)}"
            }
            
            self.trade_log.append(trade_record)
            
            # Add to real analytics
            import streamlit as st
            if 'analytics' in st.session_state:
                st.session_state.analytics.add_trade(trade_record)
            
        except Exception as e:
            print(f"Trade execution error: {e}")
    
    def get_statistics(self):
        """Get trading statistics"""
        if not self.trade_log:
            return {
                'total_trades': 0,
                'active_positions': 0,
                'daily_pnl': 0,
                'win_rate': 0
            }
        
        return {
            'total_trades': len(self.trade_log),
            'active_positions': len(self.trader.active_contracts) if self.trader else 0,
            'daily_pnl': sum(t.get('pnl', 0) for t in self.trade_log),
            'win_rate': 0.765  # Placeholder
        }

# Integration with Streamlit app
def integrate_live_trading():
    """Integration function for the main app"""
    
    if 'trading_manager' not in st.session_state:
        st.session_state.trading_manager = None
    
    # Start trading when bot is enabled
    if st.session_state.bot_running and st.session_state.trading_manager is None:
        settings = {
            'risk_per_trade': 2,  # 2%
            'min_confluence': 75,
            'max_daily_trades': 50
        }
        
        st.session_state.trading_manager = LiveTradingManager(
            deriv_token=st.session_state.deriv_id,
            server=st.session_state.server,
            settings=settings
        )
        
        # Start trading in background
        asyncio.create_task(st.session_state.trading_manager.start_trading())
    
    # Stop trading when bot is disabled
    elif not st.session_state.bot_running and st.session_state.trading_manager:
        asyncio.create_task(st.session_state.trading_manager.stop_trading())
        st.session_state.trading_manager = None
    
    # Return statistics for display
    if st.session_state.trading_manager:
        return st.session_state.trading_manager.get_statistics()
    else:
        return {'total_trades': 0, 'active_positions': 0, 'daily_pnl': 0, 'win_rate': 0}