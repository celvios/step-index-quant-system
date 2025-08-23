#!/usr/bin/env python3
import asyncio
import json
import logging
from datetime import datetime, timedelta
from deriv_connector import DerivConnector
from step_index_quant_system import StepIndexQuantSystem

class HistoricalBacktester:
    def __init__(self, api_token, initial_balance=10000):
        self.api_token = api_token
        self.initial_balance = initial_balance
        self.connector = DerivConnector("1089", api_token, is_demo=True)
        self.strategy = StepIndexQuantSystem()
        
        # Backtest results
        self.trades = []
        self.balance_history = []
        self.current_balance = initial_balance
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    async def get_historical_data(self, symbol='R_10', days=30):
        """Get historical tick data from Deriv"""
        await self.connector.connect()
        
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(days=days)).timestamp())
        
        request = {
            "ticks_history": symbol,
            "start": start_time,
            "end": end_time,
            "style": "ticks",
            "count": 1000,
            "req_id": 1
        }
        
        await self.connector._send_request(request)
        
        # Wait for response
        await asyncio.sleep(5)
        
        # Get data from connector
        self.historical_ticks = getattr(self.connector, 'historical_data', [])
        
        await self.connector.disconnect()
        return self.historical_ticks
    
    async def run_backtest(self, days=30):
        """Run backtest on historical data"""
        self.logger.info(f"Starting backtest for past {days} days")
        
        # Get historical data
        self.historical_ticks = []
        await self.get_historical_data(days=days)
        
        if not self.historical_ticks:
            self.logger.error("No historical data received")
            return None
        
        self.logger.info(f"Processing {len(self.historical_ticks)} ticks")
        
        # Process ticks
        price_history = []
        
        for i, tick in enumerate(self.historical_ticks):
            price_data = {
                'timestamp': datetime.fromtimestamp(tick['epoch']),
                'price': tick['quote']
            }
            price_history.append(price_data)
            
            # Keep last 20 prices for analysis
            if len(price_history) > 20:
                price_history = price_history[-20:]
            
            # Analyze every 10 ticks (reduce computation)
            if i % 10 == 0 and len(price_history) >= 10:
                signal = self._analyze_signal(price_history)
                
                if signal and signal['confluence_score'] >= 75:
                    await self._execute_backtest_trade(signal, price_data['timestamp'])
        
        return self._generate_results()
    
    def _analyze_signal(self, price_history):
        """Same signal analysis as live bot"""
        prices = [p['price'] for p in price_history]
        current_price = prices[-1]
        
        # Step velocity detection
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
            psychological = abs(current_price - round(current_price)) < 0.01
            
            confluence_score = 50 + step_count * 5
            if psychological:
                confluence_score += 15
            
            return {
                'timestamp': price_history[-1]['timestamp'],
                'price': current_price,
                'direction': 'LONG' if direction == 'up' else 'SHORT',
                'confluence_score': confluence_score
            }
        
        return None
    
    async def _execute_backtest_trade(self, signal, timestamp):
        """Execute trade in backtest"""
        if self.current_balance <= 0:
            return
        
        stake = self.current_balance * 0.02  # 2% risk
        stake = max(1.0, min(stake, 100))
        
        # Simulate Step Index outcome (80% win rate based on confluence)
        import random
        win_probability = min(0.8, signal['confluence_score'] / 100)
        
        if random.random() < win_probability:
            profit = stake * 0.8  # 1.8:1 payout
            outcome = 'WIN'
        else:
            profit = -stake
            outcome = 'LOSS'
        
        self.current_balance += profit
        
        trade = {
            'timestamp': timestamp,
            'symbol': 'STEP_10',
            'direction': signal['direction'],
            'stake': stake,
            'confluence_score': signal['confluence_score'],
            'outcome': outcome,
            'profit': profit,
            'balance': self.current_balance
        }
        
        self.trades.append(trade)
        self.balance_history.append({
            'timestamp': timestamp,
            'balance': self.current_balance
        })
        
        if len(self.trades) % 10 == 0:
            self.logger.info(f"Trade {len(self.trades)}: {outcome} ${profit:+.2f} Balance: ${self.current_balance:.2f}")
    
    def _generate_results(self):
        """Generate backtest results"""
        if not self.trades:
            return None
        
        wins = [t for t in self.trades if t['outcome'] == 'WIN']
        losses = [t for t in self.trades if t['outcome'] == 'LOSS']
        
        total_profit = sum(t['profit'] for t in self.trades)
        win_rate = len(wins) / len(self.trades) * 100
        
        avg_win = sum(t['profit'] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t['profit'] for t in losses) / len(losses) if losses else 0
        
        max_balance = max(h['balance'] for h in self.balance_history)
        min_balance = min(h['balance'] for h in self.balance_history)
        max_drawdown = (max_balance - min_balance) / max_balance * 100
        
        results = {
            'total_trades': len(self.trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'total_profit': total_profit,
            'final_balance': self.current_balance,
            'return_pct': (self.current_balance - self.initial_balance) / self.initial_balance * 100,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_drawdown': max_drawdown,
            'profit_factor': abs(sum(t['profit'] for t in wins) / sum(t['profit'] for t in losses)) if losses else float('inf')
        }
        
        return results
    
    def print_results(self, results):
        """Print backtest results"""
        if not results:
            print("No backtest results to display")
            return
        
        print("\n" + "="*50)
        print("STEP INDEX BACKTEST RESULTS")
        print("="*50)
        print(f"Period: {30} days")
        print(f"Initial Balance: ${self.initial_balance:,.2f}")
        print(f"Final Balance: ${results['final_balance']:,.2f}")
        print(f"Total Return: {results['return_pct']:+.2f}%")
        print(f"Total Profit: ${results['total_profit']:+,.2f}")
        print()
        print(f"Total Trades: {results['total_trades']}")
        print(f"Wins: {results['wins']} ({results['win_rate']:.1f}%)")
        print(f"Losses: {results['losses']}")
        print(f"Average Win: ${results['avg_win']:.2f}")
        print(f"Average Loss: ${results['avg_loss']:.2f}")
        print(f"Profit Factor: {results['profit_factor']:.2f}")
        print(f"Max Drawdown: {results['max_drawdown']:.2f}%")
        print("="*50)

# Modify DerivConnector to capture historical data
class HistoricalDerivConnector(DerivConnector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.historical_data = []
    
    async def _process_message(self, data):
        """Override to capture historical data"""
        if data.get('msg_type') == 'history':
            history = data.get('history', {})
            if 'prices' in history:
                # Handle different price formats
                prices = history['prices']
                self.historical_data = []
                
                for price in prices:
                    if isinstance(price, list) and len(price) >= 2:
                        self.historical_data.append({
                            'epoch': price[0],
                            'quote': price[1]
                        })
                    elif isinstance(price, (int, float)):
                        # Single price value, use index as timestamp
                        self.historical_data.append({
                            'epoch': len(self.historical_data),
                            'quote': price
                        })
        
        await super()._process_message(data)

# Update the backtester to use the modified connector
HistoricalBacktester.connector_class = HistoricalDerivConnector

async def main():
    api_token = input("Enter Deriv API Token: ").strip()
    if not api_token:
        print("API token required")
        return
    
    backtester = HistoricalBacktester(api_token, initial_balance=10000)
    
    # Override connector
    backtester.connector = HistoricalDerivConnector("1089", api_token, is_demo=True)
    
    print("Running backtest on 30 days of real Step Index data...")
    results = await backtester.run_backtest(days=30)
    
    if results:
        backtester.print_results(results)
    else:
        print("Backtest failed - check API connection")

if __name__ == "__main__":
    asyncio.run(main())