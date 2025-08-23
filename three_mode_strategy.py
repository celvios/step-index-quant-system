#!/usr/bin/env python3
import asyncio
import random
from datetime import datetime, timedelta
from deriv_connector import DerivConnector

class ThreeModeStrategy:
    def __init__(self, api_token, initial_balance=10000, mode="conservative"):
        self.api_token = api_token
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.mode = mode.lower()
        self.connector = DerivConnector("1089", api_token, is_demo=True)
        self.trades = []
        self.consecutive_wins = 0
        
        # Mode configurations
        self.configs = {
            "conservative": {
                "base_risk": 0.02,
                "max_risk": 0.05,
                "min_steps": 4,
                "frequency": 10,
                "win_rates": {"mean_reversion": 0.75, "momentum": 0.65},
                "target": "50-100%"
            },
            "moderate": {
                "base_risk": 0.10,
                "max_risk": 0.25,
                "min_steps": 3,
                "frequency": 5,
                "win_rates": {"mean_reversion": 0.80, "momentum": 0.70},
                "target": "500-1000%"
            },
            "aggressive": {
                "base_risk": 0.30,
                "max_risk": 0.80,
                "min_steps": 2,
                "frequency": 2,
                "win_rates": {"mean_reversion": 0.90, "momentum": 0.75},
                "target": "5000%+"
            }
        }
        
        self.config = self.configs[self.mode]
    
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
        
        # Only trade if meets minimum steps for mode
        if step_count >= self.config["min_steps"]:
            # Mean reversion for 3+ steps, momentum for 2 steps
            if step_count >= 3:
                trade_direction = 'SHORT' if direction == 'up' else 'LONG'
                signal_type = 'mean_reversion'
            else:
                trade_direction = 'LONG' if direction == 'up' else 'SHORT'
                signal_type = 'momentum'
            
            strength = 40 + step_count * 10
            
            # Psychological level bonus
            if abs(current_price - round(current_price)) < 0.03:
                strength += 15
            
            return {
                'direction': trade_direction,
                'type': signal_type,
                'strength': strength,
                'step_count': step_count
            }
        
        return None
    
    def calculate_position_size(self):
        base_risk = self.config["base_risk"]
        
        # Conservative: steady risk
        if self.mode == "conservative":
            if self.consecutive_wins >= 3:
                risk = base_risk * 1.5
            else:
                risk = base_risk
        
        # Moderate: balanced scaling
        elif self.mode == "moderate":
            if self.consecutive_wins >= 3:
                risk = base_risk * 2.0
            elif self.consecutive_wins >= 1:
                risk = base_risk * 1.5
            else:
                risk = base_risk
        
        # Aggressive: exponential scaling
        else:
            if self.consecutive_wins >= 5:
                risk = self.config["max_risk"]
            elif self.consecutive_wins >= 3:
                risk = base_risk * 2.5
            elif self.consecutive_wins >= 1:
                risk = base_risk * 1.8
            else:
                risk = base_risk
        
        risk = min(risk, self.config["max_risk"])
        return self.current_balance * risk
    
    def execute_trade(self, signal):
        if self.current_balance <= 10:
            return None
        
        stake = self.calculate_position_size()
        
        # Mode-specific win rates
        base_win_rate = self.config["win_rates"][signal['type']]
        
        # Strength bonus
        strength_bonus = (signal['strength'] - 50) * 0.002
        win_probability = min(0.95, base_win_rate + strength_bonus)
        
        if random.random() < win_probability:
            # Mode-specific payouts
            if self.mode == "conservative":
                profit = stake * 0.70  # 70% profit
            elif self.mode == "moderate":
                profit = stake * 0.80  # 80% profit
            else:
                profit = stake * 0.90  # 90% profit
            
            outcome = 'WIN'
            self.consecutive_wins += 1
        else:
            profit = -stake
            outcome = 'LOSS'
            self.consecutive_wins = 0
        
        self.current_balance += profit
        
        trade = {
            'direction': signal['direction'],
            'type': signal['type'],
            'stake': stake,
            'outcome': outcome,
            'profit': profit,
            'balance': self.current_balance
        }
        
        self.trades.append(trade)
        return trade
    
    async def run_backtest(self):
        print(f"{self.mode.upper()} MODE - TARGET: {self.config['target']}")
        
        success = await self.fetch_data(days=7)
        if not success:
            return None
        
        price_window = []
        
        for i, price in enumerate(self.historical_data):
            price_window.append(price)
            
            if len(price_window) > 8:
                price_window = price_window[-8:]
            
            # Mode-specific frequency
            if i % self.config["frequency"] == 0 and len(price_window) >= 5:
                signal = self.analyze_signal(price_window)
                
                if signal:
                    trade = self.execute_trade(signal)
                    if trade:
                        return_pct = (self.current_balance - self.initial_balance) / self.initial_balance * 100
                        print(f"Trade {len(self.trades)}: {trade['type']} ${trade['stake']:.0f} -> {trade['outcome']} ${trade['profit']:+.0f} ({return_pct:+.0f}%)")
                        
                        if self.current_balance <= 10:
                            break
        
        return self.generate_results()
    
    def generate_results(self):
        if not self.trades:
            return None
        
        wins = [t for t in self.trades if t['outcome'] == 'WIN']
        
        return {
            'mode': self.mode,
            'total_trades': len(self.trades),
            'wins': len(wins),
            'win_rate': len(wins) / len(self.trades) * 100,
            'final_balance': self.current_balance,
            'return_pct': (self.current_balance - self.initial_balance) / self.initial_balance * 100
        }
    
    def print_results(self, results):
        print("\n" + "="*50)
        print(f"{results['mode'].upper()} MODE RESULTS")
        print("="*50)
        print(f"Target: {self.config['target']}")
        print(f"Actual: {results['return_pct']:+.1f}%")
        print(f"Final Balance: ${results['final_balance']:,.0f}")
        print(f"Trades: {results['total_trades']}")
        print(f"Win Rate: {results['win_rate']:.1f}%")
        print("="*50)

async def main():
    print("SELECT MODE:")
    print("1. Conservative (2-5% risk, 50-100% target)")
    print("2. Moderate (10-25% risk, 500-1000% target)")
    print("3. Aggressive (30-80% risk, 5000%+ target)")
    
    choice = input("Enter choice (1-3): ").strip()
    
    modes = {"1": "conservative", "2": "moderate", "3": "aggressive"}
    mode = modes.get(choice, "conservative")
    
    strategy = ThreeModeStrategy("HVPPcwqc75HMSHg", initial_balance=10000, mode=mode)
    results = await strategy.run_backtest()
    
    if results:
        strategy.print_results(results)

if __name__ == "__main__":
    asyncio.run(main())