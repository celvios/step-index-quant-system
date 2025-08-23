#!/usr/bin/env python3
import asyncio
from datetime import datetime, timedelta
from deriv_connector import DerivConnector

class ExecutionOptimizedStrategy:
    def __init__(self, api_token, initial_balance=10000):
        self.api_token = api_token
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.connector = DerivConnector("1089", api_token, is_demo=True)
        self.trades = []
        
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
    
    def analyze_signal_with_execution_buffer(self, prices, current_index):
        """Add execution buffer for real trading"""
        if len(prices) < 6:
            return None
        
        current_price = prices[current_index]
        window = prices[max(0, current_index-5):current_index+1]
        
        # Count steps
        step_count = 0
        direction = None
        
        for i in range(len(window) - 1):
            diff = window[i+1] - window[i]
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
        
        # Require 4+ steps (stronger signal for execution delays)
        if step_count >= 4:
            trade_direction = 'SHORT' if direction == 'up' else 'LONG'
            
            # Check if signal is still valid after execution delay
            if current_index + 2 < len(prices):
                delayed_price = prices[current_index + 2]  # 2-tick execution delay
                
                return {
                    'signal_price': current_price,
                    'execution_price': delayed_price,
                    'direction': trade_direction,
                    'step_count': step_count,
                    'entry_index': current_index + 2
                }
        
        return None
    
    def simulate_real_execution(self, signal, prices):
        """Simulate real execution with spreads, slippage, delays"""
        entry_index = signal['entry_index']
        execution_price = signal['execution_price']
        direction = signal['direction']
        
        # Position sizing: 5% (moderate for execution risk)
        stake = self.current_balance * 0.05
        stake = max(5.0, min(stake, 200))
        
        # Real execution costs
        spread = 0.02  # 0.02 spread cost
        slippage = 0.01  # 0.01 slippage
        
        # Adjust entry price for execution costs
        if direction == 'LONG':
            actual_entry = execution_price + spread + slippage
        else:
            actual_entry = execution_price - spread - slippage
        
        # Exit after 3 ticks (faster exit for execution risk)
        exit_index = min(entry_index + 3, len(prices) - 1)
        exit_price = prices[exit_index]
        
        # Add exit costs
        if direction == 'LONG':
            actual_exit = exit_price - spread - slippage
            price_change = actual_exit - actual_entry
        else:
            actual_exit = exit_price + spread + slippage
            price_change = actual_entry - actual_exit
        
        # Determine outcome
        if price_change > 0:
            # Reduced payout for execution costs
            profit = stake * 0.70  # 70% payout (vs 80% in backtest)
            outcome = 'WIN'
        else:
            profit = -stake
            outcome = 'LOSS'
        
        self.current_balance += profit
        
        trade = {
            'signal_price': signal['signal_price'],
            'execution_price': actual_entry,
            'exit_price': actual_exit,
            'direction': direction,
            'stake': stake,
            'price_change': price_change,
            'outcome': outcome,
            'profit': profit,
            'balance': self.current_balance,
            'execution_cost': spread + slippage
        }
        
        self.trades.append(trade)
        return trade
    
    async def run_execution_test(self):
        """Test strategy with real execution conditions"""
        print("EXECUTION-OPTIMIZED STRATEGY")
        print("Accounting for spreads, slippage, delays")
        
        success = await self.fetch_data(days=7)
        if not success:
            return None
        
        print(f"Testing with execution costs on {len(self.historical_data)} points")
        
        for i in range(10, len(self.historical_data) - 5):
            if self.current_balance <= 10:
                break
            
            signal = self.analyze_signal_with_execution_buffer(self.historical_data, i)
            
            if signal:
                trade = self.simulate_real_execution(signal, self.historical_data)
                
                return_pct = (self.current_balance - self.initial_balance) / self.initial_balance * 100
                print(f"Trade {len(self.trades)}: {trade['direction']} ${trade['stake']:.0f} -> {trade['outcome']} ${trade['profit']:+.0f} ({return_pct:+.1f}%)")
                
                # Skip ahead
                i += 10
        
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
            'avg_execution_cost': sum(t['execution_cost'] for t in self.trades) / len(self.trades),
            'total_execution_costs': sum(t['execution_cost'] for t in self.trades) * len(self.trades)
        }
    
    def print_results(self, results):
        print("\n" + "="*50)
        print("EXECUTION-OPTIMIZED RESULTS")
        print("="*50)
        print("Includes: Spreads, slippage, delays")
        print("Signal: 4+ steps (stronger)")
        print("Exit: 3 ticks (faster)")
        print("Payout: 70% (vs 80% ideal)")
        print()
        print(f"Final Balance: ${results['final_balance']:,.2f}")
        print(f"Return: {results['return_pct']:+.1f}%")
        print(f"Trades: {results['total_trades']}")
        print(f"Win Rate: {results['win_rate']:.1f}%")
        print(f"Avg Execution Cost: {results['avg_execution_cost']:.3f}")
        print()
        
        # Compare to ideal backtest
        ideal_return = 30.2  # From previous backtest
        execution_impact = ideal_return - results['return_pct']
        
        print(f"Ideal Backtest: +30.2%")
        print(f"With Execution: {results['return_pct']:+.1f}%")
        print(f"Execution Impact: {execution_impact:.1f}% loss")
        print("="*50)

async def main():
    strategy = ExecutionOptimizedStrategy("HVPPcwqc75HMSHg", initial_balance=10000)
    results = await strategy.run_execution_test()
    
    if results:
        strategy.print_results(results)

if __name__ == "__main__":
    asyncio.run(main())