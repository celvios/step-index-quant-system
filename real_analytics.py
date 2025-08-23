import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os

class RealAnalytics:
    def __init__(self):
        self.data_file = "trading_data.json"
        self.load_data()
    
    def load_data(self):
        """Load real trading data from file"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.trades = data.get('trades', [])
                self.balance_history = data.get('balance_history', [])
                self.daily_stats = data.get('daily_stats', [])
        else:
            self.trades = []
            self.balance_history = []
            self.daily_stats = []
    
    def save_data(self):
        """Save trading data to file"""
        data = {
            'trades': self.trades,
            'balance_history': self.balance_history,
            'daily_stats': self.daily_stats
        }
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_trade(self, trade_data):
        """Add new trade to analytics"""
        trade_record = {
            'timestamp': trade_data['timestamp'].isoformat() if isinstance(trade_data['timestamp'], datetime) else trade_data['timestamp'],
            'symbol': trade_data['symbol'],
            'direction': trade_data['direction'],
            'stake': trade_data['stake'],
            'payout': trade_data.get('payout', 0),
            'profit': trade_data.get('profit', 0),
            'confluence_score': trade_data['confluence_score'],
            'outcome': trade_data.get('outcome', 'PENDING'),
            'contract_id': trade_data.get('contract_id', ''),
            'hour': datetime.now().hour
        }
        
        self.trades.append(trade_record)
        self.save_data()
    
    def update_balance(self, new_balance):
        """Update balance history"""
        balance_record = {
            'timestamp': datetime.now().isoformat(),
            'balance': new_balance
        }
        
        self.balance_history.append(balance_record)
        
        # Keep only last 100 records
        if len(self.balance_history) > 100:
            self.balance_history = self.balance_history[-100:]
        
        self.save_data()
    
    def get_performance_metrics(self):
        """Calculate real performance metrics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'profit_factor': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0
            }
        
        # Basic metrics
        total_trades = len(self.trades)
        completed_trades = [t for t in self.trades if t['outcome'] in ['WIN', 'LOSS']]
        
        if not completed_trades:
            return {'total_trades': total_trades, 'win_rate': 0, 'total_return': 0, 'profit_factor': 0, 'avg_win': 0, 'avg_loss': 0, 'max_drawdown': 0, 'sharpe_ratio': 0}
        
        wins = [t for t in completed_trades if t['outcome'] == 'WIN']
        losses = [t for t in completed_trades if t['outcome'] == 'LOSS']
        
        win_rate = len(wins) / len(completed_trades) if completed_trades else 0
        
        # P&L calculations
        total_profit = sum(t['profit'] for t in completed_trades)
        total_wins = sum(t['profit'] for t in wins) if wins else 0
        total_losses = abs(sum(t['profit'] for t in losses)) if losses else 1
        
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        avg_win = np.mean([t['profit'] for t in wins]) if wins else 0
        avg_loss = np.mean([abs(t['profit']) for t in losses]) if losses else 0
        
        # Calculate return based on balance history
        if len(self.balance_history) >= 2:
            initial_balance = self.balance_history[0]['balance']
            current_balance = self.balance_history[-1]['balance']
            total_return = (current_balance - initial_balance) / initial_balance
        else:
            total_return = 0
        
        # Max drawdown
        max_drawdown = self.calculate_max_drawdown()
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_return': total_return,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': self.calculate_sharpe_ratio()
        }
    
    def calculate_max_drawdown(self):
        """Calculate maximum drawdown from balance history"""
        if len(self.balance_history) < 2:
            return 0
        
        balances = [b['balance'] for b in self.balance_history]
        peak = balances[0]
        max_dd = 0
        
        for balance in balances:
            if balance > peak:
                peak = balance
            
            drawdown = (peak - balance) / peak
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd
    
    def calculate_sharpe_ratio(self):
        """Calculate Sharpe ratio from daily returns"""
        if len(self.balance_history) < 7:
            return 0
        
        # Calculate daily returns
        daily_returns = []
        balances = [b['balance'] for b in self.balance_history]
        
        for i in range(1, len(balances)):
            daily_return = (balances[i] - balances[i-1]) / balances[i-1]
            daily_returns.append(daily_return)
        
        if len(daily_returns) < 2:
            return 0
        
        mean_return = np.mean(daily_returns)
        std_return = np.std(daily_returns)
        
        if std_return == 0:
            return 0
        
        # Annualized Sharpe ratio
        sharpe = (mean_return / std_return) * np.sqrt(252)
        return sharpe
    
    def get_hourly_performance(self):
        """Get performance by hour"""
        if not self.trades:
            return {}
        
        hourly_stats = {}
        
        for trade in self.trades:
            if trade['outcome'] not in ['WIN', 'LOSS']:
                continue
                
            hour = trade['hour']
            
            if hour not in hourly_stats:
                hourly_stats[hour] = {'trades': 0, 'wins': 0, 'profit': 0}
            
            hourly_stats[hour]['trades'] += 1
            if trade['outcome'] == 'WIN':
                hourly_stats[hour]['wins'] += 1
            hourly_stats[hour]['profit'] += trade['profit']
        
        # Calculate win rates
        for hour in hourly_stats:
            stats = hourly_stats[hour]
            stats['win_rate'] = stats['wins'] / stats['trades'] if stats['trades'] > 0 else 0
        
        return hourly_stats
    
    def get_confluence_performance(self):
        """Get performance by confluence score ranges"""
        if not self.trades:
            return {}
        
        ranges = {
            '75-80': [],
            '80-85': [],
            '85-90': [],
            '90+': []
        }
        
        for trade in self.trades:
            if trade['outcome'] not in ['WIN', 'LOSS']:
                continue
                
            score = trade['confluence_score']
            
            if 75 <= score < 80:
                ranges['75-80'].append(trade)
            elif 80 <= score < 85:
                ranges['80-85'].append(trade)
            elif 85 <= score < 90:
                ranges['85-90'].append(trade)
            else:
                ranges['90+'].append(trade)
        
        # Calculate metrics for each range
        result = {}
        for range_name, trades in ranges.items():
            if trades:
                wins = [t for t in trades if t['outcome'] == 'WIN']
                result[range_name] = {
                    'trades': len(trades),
                    'win_rate': len(wins) / len(trades),
                    'avg_profit': np.mean([t['profit'] for t in trades])
                }
            else:
                result[range_name] = {'trades': 0, 'win_rate': 0, 'avg_profit': 0}
        
        return result
    
    def get_daily_pnl(self):
        """Calculate today's P&L"""
        today = datetime.now().date()
        
        today_trades = [
            t for t in self.trades 
            if datetime.fromisoformat(t['timestamp']).date() == today
            and t['outcome'] in ['WIN', 'LOSS']
        ]
        
        return sum(t['profit'] for t in today_trades)
    
    def get_balance_history_chart_data(self):
        """Get balance history for charting"""
        if not self.balance_history:
            # Return dummy data if no history
            dates = pd.date_range(start=datetime.now() - timedelta(days=7), end=datetime.now(), freq='D')
            return dates.tolist(), [1000] * len(dates)
        
        timestamps = [datetime.fromisoformat(b['timestamp']) for b in self.balance_history]
        balances = [b['balance'] for b in self.balance_history]
        
        return timestamps, balances
    
    def get_recent_trades(self, limit=10):
        """Get recent trades for display"""
        recent = self.trades[-limit:] if self.trades else []
        
        # Format for display
        formatted_trades = []
        for trade in recent:
            formatted_trades.append({
                'Time': datetime.fromisoformat(trade['timestamp']).strftime('%H:%M:%S'),
                'Symbol': trade['symbol'],
                'Direction': trade['direction'],
                'Stake': f"${trade['stake']:.2f}",
                'P&L': f"${trade['profit']:.2f}" if trade['profit'] != 0 else 'Pending',
                'Score': trade['confluence_score'],
                'Status': trade['outcome']
            })
        
        return formatted_trades