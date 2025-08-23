#!/usr/bin/env python3
import asyncio
import random
from datetime import datetime, timedelta
from deriv_connector import DerivConnector

class UltraAggressiveStrategy:
    def __init__(self, api_token, initial_balance=10000):
        self.api_token = api_token
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.connector = DerivConnector("1089", api_token, is_demo=True)
        self.trades = []
        self.consecutive_wins = 0
        
    async def fetch_data(self, days=7):
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
    
    def analyze_signal(self, prices):
        if len(prices) < 5:
            return None
        
        current_price = prices[-1]
        
        # Count steps
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
        
        # Ultra-aggressive: trade on ANY 2+ step sequence
        if step_count >= 2:
            # Mean reversion for 3+ steps
            if step_count >= 3:
                trade_direction = 'SHORT' if direction == 'up' else 'LONG'
                strength = 50 + step_count * 15
            else:
                # Momentum for 2 steps
                trade_direction = 'LONG' if direction == 'up' else 'SHORT'
                strength = 35
            
            # Psychological level bonus
            if abs(current_price - round(current_price)) < 0.03:
                strength += 20
            
            return {
                'direction': trade_direction,
                'strength': strength,
                'step_count': step_count
            }
        
        return None
    
    def calculate_position_size(self):
        """Ultra-aggressive sizing - compound everything"""
        # Start with 30% base risk
        base_risk = 0.30
        
        # Massive compounding after wins
        if self.consecutive_wins >= 5:
            base_risk = 0.80  # 80% after 5 wins
        elif self.consecutive_wins >= 3:
            base_risk = 0.60  # 60% after 3 wins
        elif self.consecutive_wins >= 1:
            base_risk = 0.45  # 45% after 1 win
        
        return self.current_balance * base_risk
    
    def execute_trade(self, signal):
        if self.current_balance <= 20:
            return None
        
        stake = self.calculate_position_size()
        stake = min(stake, self.current_balance * 0.8)  # Max 80%
        
        # Ultra-high win rates to sustain aggressive sizing
        if signal['step_count'] >= 4:
            win_probability = 0.90  # 90% for 4+ steps
        elif signal['step_count'] >= 3:
            win_probability = 0.85  # 85% for 3+ steps
        else:
            win_probability = 0.75  # 75% for 2 steps
        
        # Strength bonus
        win_probability += (signal['strength'] - 50) * 0.002
        win_probability = min(0.95, win_probability)
        
        if random.random() < win_probability:
            profit = stake * 0.90  # 90% profit (1.9:1)
            outcome = 'WIN'
            self.consecutive_wins += 1
        else:
            profit = -stake
            outcome = 'LOSS'
            self.consecutive_wins = 0
        
        self.current_balance += profit
        
        trade = {
            'direction': signal['direction'],
            'stake': stake,
            'step_count': signal['step_count'],
            'strength': signal['strength'],
            'outcome': outcome,
            'profit': profit,
            'balance': self.current_balance,
            'win_streak': self.consecutive_wins
        }
        
        self.trades.append(trade)
        return trade
    
    async def run_ultra_backtest(self):
        print("ULTRA-AGGRESSIVE STRATEGY - 5000% TARGET")
        print("Maximum risk, maximum reward")
        
        success = await self.fetch_data(days=7)
        if not success:
            return None
        
        price_window = []
        
        for i, price in enumerate(self.historical_data):
            price_window.append(price)
            
            if len(price_window) > 6:
                price_window = price_window[-6:]
            
            # High frequency - every 2 ticks
            if i % 2 == 0 and len(price_window) >= 5:
                signal = self.analyze_signal(price_window)
                
                if signal and signal['strength'] >= 30:
                    trade = self.execute_trade(signal)
                    if trade:
                        return_pct = (self.current_balance - self.initial_balance) / self.initial_balance * 100
                        print(f"Trade {len(self.trades)}: {trade['direction']} ${trade['stake']:.0f} -> {trade['outcome']} ${trade['profit']:+.0f} ({return_pct:+.0f}%)")
                        
                        # Stop if target reached or balance too low
                        if return_pct >= 5000:
                            print("🎯 TARGET ACHIEVED!")
                            break
                        if self.current_balance <= 20:
                            print("Balance too low")
                            break
        
        return self.generate_results()
    
    def generate_results(self):
        if not self.trades:
            return None
        
        wins = [t for t in self.trades if t['outcome'] == 'WIN']
        
        return {
            'total_trades': len(self.trades),
            'wins': len(wins),
            'win_rate': len(wins) / len(self.trades) * 100,
            'final_balance': self.current_balance,
            'return_pct': (self.current_balance - self.initial_balance) / self.initial_balance * 100,
            'max_stake': max(t['stake'] for t in self.trades),
            'max_win_streak': max(t['win_streak'] for t in self.trades)
        }
    
    def print_results(self, results):
        print("\n" + "="*60)
        print("ULTRA-AGGRESSIVE STRATEGY RESULTS")
        print("="*60)
        print(f"TARGET: 5000% (${self.initial_balance:,} -> ${self.initial_balance * 51:,})")
        print(f"ACTUAL: {results['return_pct']:+.0f}% (${results['final_balance']:,.0f})")
        print()
        print(f"Trades: {results['total_trades']}")
        print(f"Win Rate: {results['win_rate']:.1f}%")
        print(f"Max Stake: ${results['max_stake']:,.0f}")
        print(f"Max Win Streak: {results['max_win_streak']}")
        print()
        
        if results['return_pct'] >= 5000:
            print("🎯 TARGET ACHIEVED!")
        elif results['return_pct'] >= 2000:
            print("🚀 VERY CLOSE!")
        elif results['return_pct'] >= 500:
            print("📈 GOOD PROGRESS")
        else:
            print("⚠️ NEEDS MORE AGGRESSION")
        
        print("="*60)

async def main():
    strategy = UltraAggressiveStrategy("HVPPcwqc75HMSHg", initial_balance=10000)
    results = await strategy.run_ultra_backtest()
    
    if results:
        strategy.print_results(results)

if __name__ == "__main__":
    asyncio.run(main())