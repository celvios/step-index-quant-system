import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

@dataclass
class Trade:
    entry_price: float
    entry_time: datetime
    direction: str  # 'long' or 'short'
    position_size: float
    stop_loss: float
    take_profit: float
    confluence_score: int
    status: str = 'open'
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None

class StepIndexQuantSystem:
    def __init__(self, initial_capital: float = 100000):
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.positions = []
        self.trades_history = []
        self.daily_pnl = []
        self.peak_capital = initial_capital
        self.daily_drawdown_limit = 0.08
        self.max_drawdown_limit = 0.15
        self.trading_enabled = True
        
    def calculate_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(closes) < period + 1:
            return 0.0
        
        tr_values = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_values.append(tr)
        
        return sum(tr_values[-period:]) / period if len(tr_values) >= period else 0.0
    
    def detect_liquidity_sweep(self, prices: List[float], structure_level: float) -> bool:
        """Detect valid liquidity sweep"""
        if len(prices) < 4:
            return False
            
        # Check for break of prior structure by ≥ 0.3 steps
        break_distance = abs(prices[-1] - structure_level)
        if break_distance < 0.3:
            return False
            
        # Check for immediate rejection (close within 0.1 steps)
        rejection_distance = abs(prices[-1] - structure_level)
        return rejection_distance <= 0.1
    
    def detect_bos(self, prices: List[float], direction: str) -> bool:
        """Detect Break of Structure"""
        if len(prices) < 3:
            return False
            
        consecutive_steps = 0
        for i in range(len(prices) - 2, len(prices)):
            if direction == 'bullish':
                if prices[i] > prices[i-1]:
                    consecutive_steps += 1
                else:
                    consecutive_steps = 0
            else:  # bearish
                if prices[i] < prices[i-1]:
                    consecutive_steps += 1
                else:
                    consecutive_steps = 0
                    
        return consecutive_steps >= 3
    
    def calculate_fibonacci_levels(self, swing_low: float, swing_high: float, atr: float) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels with volatility adjustment"""
        range_size = swing_high - swing_low
        
        # Volatility-based POI adjustment
        if atr > 2.0:  # High volatility
            fib_levels = {
                '0.55': swing_high - 0.55 * range_size,
                '0.618': swing_high - 0.618 * range_size,
                '0.786': swing_high - 0.786 * range_size,
                '0.82': swing_high - 0.82 * range_size
            }
        elif atr < 0.5:  # Low volatility
            fib_levels = {
                '0.65': swing_high - 0.65 * range_size,
                '0.618': swing_high - 0.618 * range_size,
                '0.75': swing_high - 0.75 * range_size
            }
        else:  # Normal volatility
            fib_levels = {
                '0.60': swing_high - 0.60 * range_size,
                '0.618': swing_high - 0.618 * range_size,
                '0.786': swing_high - 0.786 * range_size,
                '0.80': swing_high - 0.80 * range_size
            }
            
        return fib_levels
    
    def step_velocity(self, prices: List[float], threshold: int = 3) -> bool:
        """Check for step velocity confirmation"""
        if len(prices) < threshold + 1:
            return False
            
        count = 0
        for i in range(1, len(prices)):
            if abs(prices[i] - prices[i-1]) >= 0.1:  # Step movement
                count += 1
            else:
                count = 0
            if count >= threshold:
                return True
        return False
    
    def cluster_density(self, price: float, lookback: int = 5) -> float:
        """Calculate cluster density at price level"""
        rounded_price = round(price, 1)
        density_count = 0
        
        for i in range(-lookback, lookback + 1):
            test_price = rounded_price + (i * 0.1)
            if abs(price - test_price) < 0.01:
                density_count += 1
                
        return density_count / (2 * lookback + 1)
    
    def calculate_confluence_score(self, price: float, fib_level: float, cluster_density: float, 
                                 step_velocity: bool, psychological_level: bool) -> int:
        """Calculate confluence score for entry validation"""
        score = 0
        
        # Fib Alignment (40%)
        fib_distance = abs(price - fib_level)
        if fib_distance <= 0.05:
            score += 40
        elif fib_distance <= 0.1:
            score += 30
        elif fib_distance <= 0.2:
            score += 20
            
        # Cluster Density (30%)
        if cluster_density > 0.6:
            score += 30
        elif cluster_density > 0.4:
            score += 20
        elif cluster_density > 0.2:
            score += 10
            
        # Step Velocity (20%)
        if step_velocity:
            score += 20
            
        # Psychological Level (10%)
        if psychological_level:
            score += 10
            
        return score
    
    def is_psychological_level(self, price: float) -> bool:
        """Check if price is at psychological level"""
        # Whole numbers
        if price == round(price):
            return True
        # Half-steps
        if abs(price - (round(price * 2) / 2)) < 0.01:
            return True
        # Quarter-steps
        if abs(price - (round(price * 4) / 4)) < 0.01:
            return True
        return False
    
    def calculate_position_size(self, confluence_score: int) -> float:
        """Calculate position size based on confluence score"""
        if confluence_score >= 90:
            return 0.10 * self.capital
        elif confluence_score >= 80:
            return 0.07 * self.capital
        elif confluence_score >= 75:
            return 0.05 * self.capital
        else:
            return 0.02 * self.capital
    
    def calculate_rr_target(self, confluence_score: int) -> Tuple[float, float]:
        """Calculate RR target and TP multiplier"""
        if confluence_score >= 90:
            return 4.0, 1.0
        elif confluence_score >= 80:
            return 5.0, 1.2
        else:
            return 6.0, 1.5
    
    def calculate_dynamic_tp(self, entry: float, sl: float, rr_target: float, volatility: float, direction: str) -> float:
        """Calculate dynamic take profit with volatility adjustment"""
        base_distance = abs(entry - sl)
        
        # Volatility multiplier
        if volatility < 0.5:
            mult = 0.8
        elif volatility > 1.5:
            mult = 1.5
        else:
            mult = 1.0
            
        tp_distance = base_distance * rr_target * mult
        
        if direction == 'long':
            return entry + tp_distance
        else:
            return entry - tp_distance
    
    def check_circuit_breakers(self) -> bool:
        """Check if circuit breakers are triggered"""
        # Daily drawdown check
        daily_dd = (self.peak_capital - self.capital) / self.peak_capital
        if daily_dd >= self.daily_drawdown_limit:
            self.trading_enabled = False
            return False
            
        # Peak-to-trough drawdown
        max_dd = (self.peak_capital - self.capital) / self.peak_capital
        if max_dd >= self.max_drawdown_limit:
            self.trading_enabled = False
            return False
            
        return True
    
    def enter_trade(self, price: float, direction: str, confluence_score: int, 
                   fib_level: str, atr: float) -> Optional[Trade]:
        """Enter a new trade"""
        if not self.trading_enabled or not self.check_circuit_breakers():
            return None
            
        if confluence_score < 75:
            return None
            
        position_size = self.calculate_position_size(confluence_score)
        rr_target, tp_mult = self.calculate_rr_target(confluence_score)
        
        # Calculate stop loss based on entry type
        if fib_level == '0.618':
            sl_distance = 0.168 * abs(price)  # Distance to 0.786 level
        elif fib_level == '0.786':
            sl_distance = 0.064 * abs(price)  # Distance to 0.85 level
        else:  # 0.50 fib
            sl_distance = 0.1  # Beyond rejection candle
            
        if direction == 'long':
            stop_loss = price - sl_distance
            take_profit = self.calculate_dynamic_tp(price, stop_loss, rr_target, atr, direction)
        else:
            stop_loss = price + sl_distance
            take_profit = self.calculate_dynamic_tp(price, stop_loss, rr_target, atr, direction)
            
        trade = Trade(
            entry_price=price,
            entry_time=datetime.now(),
            direction=direction,
            position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confluence_score=confluence_score
        )
        
        self.positions.append(trade)
        return trade
    
    def scale_position(self, trade: Trade, current_price: float, atr: float) -> bool:
        """Scale position based on momentum"""
        if trade.status != 'open':
            return False
            
        # Check if price reached 50% of TP
        tp_progress = abs(current_price - trade.entry_price) / abs(trade.take_profit - trade.entry_price)
        
        if tp_progress >= 0.5 and self.step_velocity([trade.entry_price, current_price]):
            # Scale in with 50% additional size
            trade.position_size *= 1.5
            
            # Extend TP by 40%
            tp_extension = 0.4 * abs(trade.take_profit - trade.entry_price)
            if trade.direction == 'long':
                trade.take_profit += tp_extension
            else:
                trade.take_profit -= tp_extension
                
            return True
        return False
    
    def update_trailing_stop(self, trade: Trade, current_price: float) -> None:
        """Update trailing stop loss"""
        if trade.status != 'open':
            return
            
        # Move to breakeven after 0.5% profit
        profit_pct = abs(current_price - trade.entry_price) / trade.entry_price
        if profit_pct >= 0.005:
            trade.stop_loss = trade.entry_price
            
        # Trail by 0.1 steps for each new extreme
        if trade.direction == 'long' and current_price > trade.entry_price:
            new_sl = current_price - 0.1
            trade.stop_loss = max(trade.stop_loss, new_sl)
        elif trade.direction == 'short' and current_price < trade.entry_price:
            new_sl = current_price + 0.1
            trade.stop_loss = min(trade.stop_loss, new_sl)
    
    def check_exit_conditions(self, trade: Trade, current_price: float) -> bool:
        """Check if trade should be exited"""
        if trade.status != 'open':
            return False
            
        # Stop loss hit
        if trade.direction == 'long' and current_price <= trade.stop_loss:
            return True
        elif trade.direction == 'short' and current_price >= trade.stop_loss:
            return True
            
        # Take profit hit
        if trade.direction == 'long' and current_price >= trade.take_profit:
            return True
        elif trade.direction == 'short' and current_price <= trade.take_profit:
            return True
            
        return False
    
    def close_trade(self, trade: Trade, exit_price: float) -> float:
        """Close a trade and calculate PnL"""
        trade.status = 'closed'
        trade.exit_price = exit_price
        trade.exit_time = datetime.now()
        
        if trade.direction == 'long':
            pnl = (exit_price - trade.entry_price) * trade.position_size
        else:
            pnl = (trade.entry_price - exit_price) * trade.position_size
            
        self.capital += pnl
        self.peak_capital = max(self.peak_capital, self.capital)
        self.trades_history.append(trade)
        
        if trade in self.positions:
            self.positions.remove(trade)
            
        return pnl
    
    def get_performance_metrics(self) -> Dict:
        """Calculate performance metrics"""
        if not self.trades_history:
            return {}
            
        total_trades = len(self.trades_history)
        winning_trades = sum(1 for t in self.trades_history 
                           if (t.direction == 'long' and t.exit_price > t.entry_price) or
                              (t.direction == 'short' and t.exit_price < t.entry_price))
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        total_return = (self.capital - self.initial_capital) / self.initial_capital
        max_drawdown = (self.peak_capital - min(self.capital, self.initial_capital)) / self.peak_capital
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'current_capital': self.capital,
            'peak_capital': self.peak_capital
        }

# Usage Example
if __name__ == "__main__":
    system = StepIndexQuantSystem(initial_capital=100000)
    
    # Example trade execution
    confluence_score = system.calculate_confluence_score(
        price=8525.0,
        fib_level=8520.0,
        cluster_density=0.7,
        step_velocity=True,
        psychological_level=True
    )
    
    if confluence_score >= 75:
        trade = system.enter_trade(
            price=8525.0,
            direction='long',
            confluence_score=confluence_score,
            fib_level='0.618',
            atr=1.2
        )
        
        if trade:
            print(f"Trade entered: {trade}")
            print(f"Performance: {system.get_performance_metrics()}")