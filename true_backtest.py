#!/usr/bin/env python3
import asyncio
from datetime import datetime, timedelta
from deriv_connector import DerivConnector

class TrueBacktest:
    def __init__(self, api_token, initial_balance=10000):
        self.api_token = api_token
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.connector = DerivConnector("1089", api_token, is_demo=True)
        self.trades = []
        self.historical_data = []
        
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
    
    def analyze_signal(self, prices, current_index):
        if len(prices) < 5:
            return None
        
        current_price = prices[current_index]
        
        # Look at last 5 prices for pattern
        window = prices[max(0, current_index-4):current_index+1]
        
        # Count consecutive steps
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
        
        # Trade after 3+ consecutive steps (mean reversion)
        if step_count >= 3:
            trade_direction = 'SHORT' if direction == 'up' else 'LONG'
            
            return {
                'entry_price': current_price,
                'direction': trade_direction,
                'step_count': step_count,
                'entry_index': current_index
            }
        
        return None
    
    def execute_historical_trade(self, signal, prices):
        """Execute trade on historical data and get REAL outcome"""
        entry_price = signal['entry_price']
        entry_index = signal['entry_index']
        direction = signal['direction']
        
        # Position size: 2% risk
        stake = self.current_balance * 0.02
        stake = max(1.0, min(stake, 100))
        
        # Look ahead 5 ticks to see actual outcome
        exit_index = min(entry_index + 5, len(prices) - 1)
        exit_price = prices[exit_index]
        
        # Calculate actual profit/loss
        price_change = exit_price - entry_price
        
        if direction == 'LONG':
            # Win if price went up
            if price_change > 0:
                profit = stake * 0.8  # 80% payout
                outcome = 'WIN'
            else:
                profit = -stake
                outcome = 'LOSS'
        else:  # SHORT
            # Win if price went down
            if price_change < 0:
                profit = stake * 0.8
                outcome = 'WIN'
            else:
                profit = -stake
                outcome = 'LOSS'
        
        self.current_balance += profit
        
        trade = {
            'entry_index': entry_index,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'direction': direction,
            'stake': stake,
            'price_change': price_change,
            'outcome': outcome,
            'profit': profit,
            'balance': self.current_balance
        }
        
        self.trades.append(trade)
        return trade
    
    async def run_true_backtest(self):
        """Run backtest on actual historical data"""
        print("TRUE BACKTEST - Real trades on past data")
        
        success = await self.fetch_data(days=7)
        if not success:
            print("Failed to fetch data")
            return None
        
        print(f"Testing on {len(self.historical_data)} real price points")
        print(f"Price range: {min(self.historical_data):.3f} - {max(self.historical_data):.3f}")
        
        # Walk through historical data
        for i in range(10, len(self.historical_data) - 5):  # Leave room for exit
            if self.current_balance <= 1:
                break
            
            # Check for signal at this point in time
            signal = self.analyze_signal(self.historical_data, i)
            
            if signal:
                # Execute trade and get REAL outcome
                trade = self.execute_historical_trade(signal, self.historical_data)
                
                print(f"Trade {len(self.trades)}: {trade['direction']} @ {trade['entry_price']:.3f} -> {trade['exit_price']:.3f} = {trade['outcome']} ${trade['profit']:+.2f}")
                
                # Skip ahead to avoid overlapping trades
                i += 10
        
        return self.generate_results()
    
    def generate_results(self):
        if not self.trades:
            return None
        
        wins = [t for t in self.trades if t['outcome'] == 'WIN']
        losses = [t for t in self.trades if t['outcome'] == 'LOSS']
        
        return {
            'total_trades': len(self.trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(self.trades) * 100,
            'total_profit': sum(t['profit'] for t in self.trades),
            'final_balance': self.current_balance,
            'return_pct': (self.current_balance - self.initial_balance) / self.initial_balance * 100,
            'avg_win': sum(t['profit'] for t in wins) / len(wins) if wins else 0,
            'avg_loss': sum(t['profit'] for t in losses) / len(losses) if losses else 0
        }
    
    def print_results(self, results):
        print("\n" + "="*50)
        print("TRUE BACKTEST RESULTS")
        print("="*50)
        print("Strategy: Mean reversion after 3+ steps")
        print(f"Data: Real Step Index prices")
        print(f"Trades: ACTUAL outcomes on past data")
        print()
        print(f"Initial Balance: ${self.initial_balance:,.2f}")
        print(f"Final Balance: ${results['final_balance']:,.2f}")
        print(f"Return: {results['return_pct']:+.2f}%")
        print(f"Total Profit: ${results['total_profit']:+.2f}")
        print()
        print(f"Total Trades: {results['total_trades']}")
        print(f"Wins: {results['wins']} ({results['win_rate']:.1f}%)")
        print(f"Losses: {results['losses']}")
        print(f"Average Win: ${results['avg_win']:.2f}")
        print(f"Average Loss: ${results['avg_loss']:.2f}")
        print("="*50)
        
        if results['win_rate'] > 60:
            print("✅ GOOD STRATEGY")
        elif results['win_rate'] > 50:
            print("⚠️ MARGINAL STRATEGY")
        else:
            print("❌ POOR STRATEGY")

async def main():
    backtester = TrueBacktest("HVPPcwqc75HMSHg", initial_balance=10000)
    results = await backtester.run_true_backtest()
    
    if results:
        backtester.print_results(results)
    else:
        print("No trades executed")

if __name__ == "__main__":
    asyncio.run(main())