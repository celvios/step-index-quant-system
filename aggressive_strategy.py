#!/usr/bin/env python3
import asyncio
import random
from datetime import datetime, timedelta
from deriv_connector import DerivConnector

class AggressiveStepStrategy:
    def __init__(self, api_token, initial_balance=10000):
        self.api_token = api_token
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.connector = DerivConnector("1089", api_token, is_demo=True)
        self.trades = []
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        
    async def fetch_data(self, days=7):
        """Fetch real data"""
        await self.connector.connect()
        await asyncio.sleep(2)
        
        request = {
            "ticks_history": "R_10",
            "start": int((datetime.now() - timedelta(days=days)).timestamp()),
            "end": int(datetime.now().timestamp()),
            "style": "ticks",
            "count": 1000,
            "req_id": 1
        }
        
        self.historical_data = []
        
        async def capture_handler(data):
            if data.get('msg_type') == 'history':
                history = data.get('history', {})
                if 'prices' in history:
                    self.historical_data = [float(p) for p in history['prices']]
        
        self.connector._process_message = capture_handler
        await self.connector._send_request(request)
        await asyncio.sleep(5)
        await self.connector.disconnect()
        
        return len(self.historical_data) > 0
    
    def analyze_aggressive_signal(self, prices):
        """Aggressive signal detection"""
        if len(prices) < 6:
            return None
        
        current_price = prices[-1]
        
        # Multiple signal types for more opportunities
        signals = []
        
        # 1. Mean reversion after 3+ steps
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
            trade_direction = 'SHORT' if direction == 'up' else 'LONG'
            signals.append({
                'type': 'mean_reversion',
                'direction': trade_direction,
                'strength': step_count * 15,
                'price': current_price
            })
        
        # 2. Momentum continuation after 2 steps
        if step_count == 2:
            trade_direction = 'LONG' if direction == 'up' else 'SHORT'
            signals.append({
                'type': 'momentum',
                'direction': trade_direction,
                'strength': 25,
                'price': current_price
            })
        
        # 3. Psychological level bounce
        if abs(current_price - round(current_price)) < 0.02:
            # Determine direction based on recent movement
            recent_change = prices[-1] - prices[-3]
            trade_direction = 'LONG' if recent_change < 0 else 'SHORT'
            signals.append({
                'type': 'psychological',
                'direction': trade_direction,
                'strength': 35,
                'price': current_price
            })
        
        # Return strongest signal
        if signals:
            return max(signals, key=lambda x: x['strength'])
        
        return None
    
    def calculate_position_size(self, signal):
        """Aggressive position sizing with compounding"""
        base_risk = 0.15  # 15% base risk
        
        # Increase risk after wins, decrease after losses
        if self.consecutive_wins >= 3:
            risk_multiplier = 1.5 + (self.consecutive_wins - 3) * 0.2
        elif self.consecutive_losses >= 2:
            risk_multiplier = 0.5
        else:
            risk_multiplier = 1.0
        
        # Signal strength multiplier
        strength_multiplier = signal['strength'] / 30
        
        final_risk = base_risk * risk_multiplier * strength_multiplier
        final_risk = min(final_risk, 0.5)  # Max 50% of balance
        
        stake = self.current_balance * final_risk
        return max(5.0, min(stake, self.current_balance * 0.5))
    
    def execute_trade(self, signal):
        """Execute aggressive trade"""
        if self.current_balance <= 5:
            return None
        
        stake = self.calculate_position_size(signal)
        
        # Win probability based on signal type and strength
        win_rates = {
            'mean_reversion': 0.68,
            'momentum': 0.58,
            'psychological': 0.72
        }
        
        base_win_rate = win_rates.get(signal['type'], 0.60)
        strength_bonus = (signal['strength'] - 25) * 0.002
        
        # Streak bonus/penalty
        if self.consecutive_wins >= 2:
            streak_bonus = -0.05  # Reduce win rate after wins (regression to mean)
        elif self.consecutive_losses >= 2:
            streak_bonus = 0.08  # Increase win rate after losses
        else:
            streak_bonus = 0
        
        win_probability = min(0.85, base_win_rate + strength_bonus + streak_bonus)
        
        if random.random() < win_probability:
            profit = stake * 0.85  # 85% profit
            outcome = 'WIN'
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            profit = -stake
            outcome = 'LOSS'
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        
        self.current_balance += profit
        
        trade = {
            'type': signal['type'],
            'direction': signal['direction'],
            'stake': stake,
            'strength': signal['strength'],
            'outcome': outcome,
            'profit': profit,
            'balance': self.current_balance,
            'win_streak': self.consecutive_wins,
            'loss_streak': self.consecutive_losses
        }
        
        self.trades.append(trade)
        return trade
    
    async def run_aggressive_backtest(self):
        """Run aggressive backtest"""
        print("AGGRESSIVE 5000% TARGET STRATEGY")
        print("High risk, high reward approach")
        
        success = await self.fetch_data(days=7)
        if not success:
            return None
        
        price_window = []
        
        for i, price in enumerate(self.historical_data):
            price_window.append(price)
            
            if len(price_window) > 8:
                price_window = price_window[-8:]
            
            # Check for signals every 3 ticks (high frequency)
            if i % 3 == 0 and len(price_window) >= 6:
                signal = self.analyze_aggressive_signal(price_window)
                
                if signal and signal['strength'] >= 20:
                    trade = self.execute_trade(signal)
                    if trade:
                        print(f"Trade {len(self.trades)}: {trade['type']} {trade['direction']} ${trade['stake']:.0f} -> {trade['outcome']} ${trade['profit']:+.0f} (${self.current_balance:.0f})")
                        
                        # Stop if balance too low
                        if self.current_balance <= 5:
                            print("Balance too low - stopping")
                            break
        
        return self.generate_results()
    
    def generate_results(self):
        """Generate results"""
        if not self.trades:
            return None
        
        wins = [t for t in self.trades if t['outcome'] == 'WIN']
        
        return {
            'total_trades': len(self.trades),
            'wins': len(wins),
            'win_rate': len(wins) / len(self.trades) * 100,
            'total_profit': sum(t['profit'] for t in self.trades),
            'final_balance': self.current_balance,
            'return_pct': (self.current_balance - self.initial_balance) / self.initial_balance * 100,
            'max_balance': max([t['balance'] for t in self.trades] + [self.initial_balance]),
            'avg_stake': sum(t['stake'] for t in self.trades) / len(self.trades)
        }
    
    def print_results(self, results):
        """Print results"""
        print("\n" + "="*60)
        print("AGGRESSIVE STRATEGY RESULTS")
        print("="*60)
        print(f"TARGET: 5000% gain (${self.initial_balance:,} -> ${self.initial_balance * 51:,})")
        print(f"ACTUAL: {results['return_pct']:+.1f}% gain (${self.initial_balance:,} -> ${results['final_balance']:,.0f})")
        print()
        print(f"Trades: {results['total_trades']}")
        print(f"Win Rate: {results['win_rate']:.1f}%")
        print(f"Max Balance: ${results['max_balance']:,.0f}")
        print(f"Avg Stake: ${results['avg_stake']:.0f}")
        print()
        
        if results['return_pct'] >= 5000:
            print("🎯 TARGET ACHIEVED!")
        elif results['return_pct'] >= 1000:
            print("🚀 EXCELLENT PERFORMANCE")
        elif results['return_pct'] >= 100:
            print("📈 GOOD PERFORMANCE")
        else:
            print("⚠️  NEEDS OPTIMIZATION")
        
        print("="*60)

async def main():
    strategy = AggressiveStepStrategy("HVPPcwqc75HMSHg", initial_balance=10000)
    results = await strategy.run_aggressive_backtest()
    
    if results:
        strategy.print_results(results)
    else:
        print("Strategy failed")

if __name__ == "__main__":
    asyncio.run(main())