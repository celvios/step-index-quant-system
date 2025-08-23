#!/usr/bin/env python3
"""
Step Index Institutional Quant System
Main orchestration system that integrates all components
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

from step_index_quant_system import StepIndexQuantSystem
from data_manager import StepIndexDataManager
from risk_manager import InstitutionalRiskManager
from execution_engine import StepIndexExecutionEngine, Order
from backtester import StepIndexBacktester

class StepIndexInstitutionalSystem:
    def __init__(self, config: Dict):
        self.config = config
        self.running = False
        
        # Initialize components
        self.quant_system = StepIndexQuantSystem(config.get('initial_capital', 100000))
        self.data_manager = StepIndexDataManager()
        self.risk_manager = InstitutionalRiskManager(
            max_portfolio_risk=config.get('max_portfolio_risk', 0.02),
            max_single_trade_risk=config.get('max_single_trade_risk', 0.005)
        )
        self.execution_engine = StepIndexExecutionEngine(
            api_key=config.get('api_key'),
            secret_key=config.get('secret_key'),
            sandbox=config.get('sandbox', True)
        )
        
        # Performance tracking
        self.performance_history = []
        self.daily_pnl = []
        self.trade_log = []
        
        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def setup_logging(self):
        """Setup comprehensive logging"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # File handler
        file_handler = logging.FileHandler(f'step_index_system_{datetime.now().strftime("%Y%m%d")}.log')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(log_format))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(log_format))
        
        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    async def start(self):
        """Start the institutional system"""
        self.logger.info("Starting Step Index Institutional Quant System")
        
        try:
            # Start execution engine
            self.execution_engine.start()
            
            # Register fill callback
            self.execution_engine.add_fill_callback(self._on_order_fill)
            
            # Start main trading loop
            self.running = True
            await self._main_trading_loop()
            
        except Exception as e:
            self.logger.error(f"System startup error: {e}")
            raise
    
    async def stop(self):
        """Stop the system gracefully"""
        self.logger.info("Stopping Step Index Institutional System")
        
        self.running = False
        
        # Close all positions
        await self._close_all_positions()
        
        # Stop execution engine
        self.execution_engine.stop()
        
        # Generate final report
        self._generate_final_report()
        
        self.logger.info("System stopped successfully")
    
    async def _main_trading_loop(self):
        """Main trading loop"""
        last_analysis_time = datetime.now()
        analysis_interval = timedelta(minutes=self.config.get('analysis_interval_minutes', 5))
        
        while self.running:
            try:
                current_time = datetime.now()
                
                # Periodic analysis and signal generation
                if current_time - last_analysis_time >= analysis_interval:
                    await self._run_analysis_cycle()
                    last_analysis_time = current_time
                
                # Update positions and risk monitoring
                await self._update_positions()
                await self._monitor_risk()
                
                # Sleep before next iteration
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(5)  # Wait before retry
    
    async def _run_analysis_cycle(self):
        """Run complete analysis cycle"""
        self.logger.info("Running analysis cycle")
        
        try:
            # Get latest market data
            market_data = self._get_latest_market_data()
            
            if market_data.empty:
                self.logger.warning("No market data available")
                return
            
            # Analyze market structure
            structure = self.data_manager.detect_market_structure(market_data)
            
            # Generate signals
            signals = self._generate_trading_signals(market_data, structure)
            
            # Process signals
            for signal in signals:
                await self._process_signal(signal, market_data)
                
        except Exception as e:
            self.logger.error(f"Analysis cycle error: {e}")
    
    def _get_latest_market_data(self) -> pd.DataFrame:
        """Get latest market data for analysis"""
        try:
            # In production, this would fetch real-time data
            # For now, generate synthetic data
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            
            # Try to load from database first
            df = self.data_manager.load_data(start_time, end_time)
            
            if df.empty:
                # Generate synthetic data if no historical data
                df = self.data_manager.generate_step_index_data(periods=100)
                df['timestamp'] = pd.date_range(end=end_time, periods=len(df), freq='5T')
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting market data: {e}")
            return pd.DataFrame()
    
    def _generate_trading_signals(self, market_data: pd.DataFrame, structure: Dict) -> List[Dict]:
        """Generate trading signals based on strategy"""
        signals = []
        
        if len(market_data) < 50:
            return signals
        
        try:
            current_price = market_data.iloc[-1]['close']
            recent_prices = market_data['close'].tail(10).tolist()
            atr = market_data['atr'].iloc[-1] if 'atr' in market_data.columns else 1.0
            
            # Check for swing points
            if not structure['swing_points']['highs'] or not structure['swing_points']['lows']:
                return signals
            
            recent_high = structure['swing_points']['highs'][-1]['price']
            recent_low = structure['swing_points']['lows'][-1]['price']
            
            # Calculate Fibonacci levels
            fib_levels = self.quant_system.calculate_fibonacci_levels(recent_low, recent_high, atr)
            
            # Check each Fibonacci level for entry opportunities
            for fib_name, fib_price in fib_levels.items():
                distance = abs(current_price - fib_price)
                
                if distance <= 0.1:  # Within entry zone
                    # Calculate confluence
                    cluster_density = self.quant_system.cluster_density(current_price)
                    step_velocity = self.quant_system.step_velocity(recent_prices)
                    psychological_level = self.quant_system.is_psychological_level(current_price)
                    
                    confluence_score = self.quant_system.calculate_confluence_score(
                        current_price, fib_price, cluster_density, step_velocity, psychological_level
                    )
                    
                    if confluence_score >= 75:
                        # Determine direction
                        direction = 'long' if current_price < (recent_high + recent_low) / 2 else 'short'
                        
                        signals.append({
                            'symbol': 'STEP_INDEX_10',
                            'direction': direction,
                            'entry_price': current_price,
                            'confluence_score': confluence_score,
                            'fib_level': fib_name,
                            'atr': atr,
                            'timestamp': datetime.now()
                        })
            
        except Exception as e:
            self.logger.error(f"Signal generation error: {e}")
        
        return signals
    
    async def _process_signal(self, signal: Dict, market_data: pd.DataFrame):
        """Process a trading signal"""
        try:
            # Risk checks
            if not self.quant_system.check_circuit_breakers():
                self.logger.warning("Circuit breakers triggered - skipping signal")
                return
            
            # Position sizing
            position_info = self.risk_manager.calculate_position_size(
                entry_price=signal['entry_price'],
                stop_loss=self._calculate_stop_loss(signal),
                account_balance=self.quant_system.capital,
                confluence_score=signal['confluence_score'],
                volatility=signal['atr']
            )
            
            if position_info['position_size'] <= 0:
                self.logger.info("Position size too small - skipping signal")
                return
            
            # Create and submit order
            order = Order(
                symbol=signal['symbol'],
                side='buy' if signal['direction'] == 'long' else 'sell',
                quantity=position_info['position_size'],
                order_type='market'
            )
            
            order_id = self.execution_engine.submit_order(order)
            
            self.logger.info(f"Signal processed - Order {order_id} submitted for {signal['direction']} {position_info['position_size']} at {signal['entry_price']}")
            
            # Log trade details
            self.trade_log.append({
                'timestamp': signal['timestamp'],
                'signal': signal,
                'position_info': position_info,
                'order_id': order_id
            })
            
        except Exception as e:
            self.logger.error(f"Signal processing error: {e}")
    
    def _calculate_stop_loss(self, signal: Dict) -> float:
        """Calculate stop loss for signal"""
        entry_price = signal['entry_price']
        fib_level = signal['fib_level']
        direction = signal['direction']
        
        # Stop loss based on Fibonacci level
        if fib_level == '0.618':
            sl_distance = 0.168 * entry_price  # Distance to 0.786
        elif fib_level == '0.786':
            sl_distance = 0.064 * entry_price  # Distance to 0.85
        else:
            sl_distance = 0.1  # Default 0.1 steps
        
        if direction == 'long':
            return entry_price - sl_distance
        else:
            return entry_price + sl_distance
    
    async def _update_positions(self):
        """Update all open positions"""
        try:
            current_price = self.execution_engine.get_current_price('STEP_INDEX_10')
            
            if current_price is None:
                return
            
            positions_to_close = []
            
            for trade in self.quant_system.positions:
                # Update trailing stops
                self.quant_system.update_trailing_stop(trade, current_price)
                
                # Check exit conditions
                if self.quant_system.check_exit_conditions(trade, current_price):
                    positions_to_close.append(trade)
            
            # Close positions
            for trade in positions_to_close:
                await self._close_position(trade, current_price)
                
        except Exception as e:
            self.logger.error(f"Position update error: {e}")
    
    async def _close_position(self, trade, exit_price: float):
        """Close a position"""
        try:
            # Create closing order
            order = Order(
                symbol='STEP_INDEX_10',
                side='sell' if trade.direction == 'long' else 'buy',
                quantity=trade.position_size,
                order_type='market'
            )
            
            order_id = self.execution_engine.submit_order(order)
            
            # Update trade in system
            pnl = self.quant_system.close_trade(trade, exit_price)
            
            self.logger.info(f"Position closed - PnL: ${pnl:.2f}")
            
        except Exception as e:
            self.logger.error(f"Position closing error: {e}")
    
    async def _close_all_positions(self):
        """Close all open positions"""
        current_price = self.execution_engine.get_current_price('STEP_INDEX_10') or 8500.0
        
        for trade in self.quant_system.positions.copy():
            await self._close_position(trade, current_price)
    
    async def _monitor_risk(self):
        """Monitor risk metrics and limits"""
        try:
            # Get current positions for risk analysis
            positions = [
                {
                    'position_size': trade.position_size,
                    'entry_price': trade.entry_price,
                    'risk_amount': abs(trade.entry_price - trade.stop_loss) * trade.position_size,
                    'direction': trade.direction
                }
                for trade in self.quant_system.positions
            ]
            
            # Generate risk report
            market_data = self._get_latest_market_data()
            
            if not market_data.empty:
                risk_report = self.risk_manager.generate_risk_report(
                    positions=positions,
                    returns_history=market_data,
                    account_balance=self.quant_system.capital
                )
                
                # Check for violations
                if risk_report['limit_checks']['violations']:
                    self.logger.warning(f"Risk violations: {risk_report['limit_checks']['violations']}")
                    
                    # Take corrective action if needed
                    await self._handle_risk_violations(risk_report)
                
        except Exception as e:
            self.logger.error(f"Risk monitoring error: {e}")
    
    async def _handle_risk_violations(self, risk_report: Dict):
        """Handle risk limit violations"""
        violations = risk_report['limit_checks']['violations']
        
        for violation in violations:
            if 'Portfolio risk' in violation:
                # Reduce position sizes
                self.logger.warning("Reducing position sizes due to portfolio risk violation")
                # Implementation would reduce positions
            
            elif 'Drawdown' in violation:
                # Stop trading temporarily
                self.logger.warning("Stopping trading due to drawdown violation")
                self.quant_system.trading_enabled = False
    
    def _on_order_fill(self, fill):
        """Handle order fill callback"""
        self.logger.info(f"Order filled: {fill.order_id} - {fill.side} {fill.quantity} at {fill.price}")
        
        # Update performance tracking
        self.performance_history.append({
            'timestamp': fill.timestamp,
            'action': 'fill',
            'details': fill
        })
    
    def _generate_final_report(self):
        """Generate final performance report"""
        try:
            metrics = self.quant_system.get_performance_metrics()
            
            report = f"""
=== STEP INDEX INSTITUTIONAL SYSTEM - FINAL REPORT ===
Generated: {datetime.now()}

PERFORMANCE METRICS:
- Initial Capital: ${self.quant_system.initial_capital:,.2f}
- Final Capital: ${metrics.get('current_capital', 0):,.2f}
- Total Return: {metrics.get('total_return', 0):.2%}
- Total Trades: {metrics.get('total_trades', 0)}
- Win Rate: {metrics.get('win_rate', 0):.2%}
- Max Drawdown: {metrics.get('max_drawdown', 0):.2%}

EXECUTION STATISTICS:
{self.execution_engine.get_execution_statistics()}

SYSTEM STATUS:
- Trading Enabled: {self.quant_system.trading_enabled}
- Open Positions: {len(self.quant_system.positions)}
- Total Trades Logged: {len(self.trade_log)}
            """
            
            # Save report to file
            with open(f'final_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt', 'w') as f:
                f.write(report)
            
            self.logger.info("Final report generated")
            print(report)
            
        except Exception as e:
            self.logger.error(f"Report generation error: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        self.logger.info(f"Received signal {signum} - initiating shutdown")
        asyncio.create_task(self.stop())

# Configuration
DEFAULT_CONFIG = {
    'initial_capital': 100000,
    'max_portfolio_risk': 0.02,
    'max_single_trade_risk': 0.005,
    'analysis_interval_minutes': 5,
    'sandbox': True,
    'api_key': None,
    'secret_key': None
}

async def main():
    """Main entry point"""
    print("Step Index Institutional Quant System")
    print("=====================================")
    
    # Initialize system
    system = StepIndexInstitutionalSystem(DEFAULT_CONFIG)
    
    try:
        # Start system
        await system.start()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"System error: {e}")
    finally:
        await system.stop()

if __name__ == "__main__":
    asyncio.run(main())