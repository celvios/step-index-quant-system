import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from step_index_quant_system import StepIndexQuantSystem, Trade
from data_manager import StepIndexDataManager

class StepIndexBacktester:
    def __init__(self, initial_capital: float = 100000):
        self.system = StepIndexQuantSystem(initial_capital)
        self.data_manager = StepIndexDataManager()
        self.backtest_results = []
        
    def run_backtest(self, start_date: datetime, end_date: datetime, 
                    htf_timeframe: str = '4H', ltf_timeframe: str = '1H') -> Dict:
        """Run comprehensive backtest"""
        
        # Generate or load data
        df = self.data_manager.generate_step_index_data(periods=2000)
        df['timestamp'] = pd.date_range(start=start_date, periods=len(df), freq='1H')
        
        # Resample for HTF analysis
        htf_df = self._resample_data(df, htf_timeframe)
        
        results = {
            'trades': [],
            'equity_curve': [],
            'daily_pnl': [],
            'drawdowns': [],
            'performance_metrics': {}
        }
        
        print(f"Starting backtest from {start_date} to {end_date}")
        print(f"Processing {len(df)} data points...")
        
        for i in range(50, len(df)):  # Start after enough data for indicators
            current_data = df.iloc[:i+1]
            current_price = current_data.iloc[-1]['close']
            current_time = current_data.iloc[-1]['timestamp']
            
            # Update existing positions
            self._update_positions(current_price, current_data)
            
            # Look for new entry signals
            signal = self._generate_signal(current_data, htf_df, i)
            
            if signal and signal['action'] == 'enter':
                trade = self.system.enter_trade(
                    price=current_price,
                    direction=signal['direction'],
                    confluence_score=signal['confluence_score'],
                    fib_level=signal['fib_level'],
                    atr=current_data['atr'].iloc[-1]
                )
                
                if trade:
                    results['trades'].append({
                        'timestamp': current_time,
                        'action': 'enter',
                        'price': current_price,
                        'direction': signal['direction'],
                        'confluence_score': signal['confluence_score'],
                        'position_size': trade.position_size
                    })
            
            # Record equity curve
            results['equity_curve'].append({
                'timestamp': current_time,
                'equity': self.system.capital,
                'drawdown': (self.system.peak_capital - self.system.capital) / self.system.peak_capital
            })
            
            # Progress update
            if i % 200 == 0:
                progress = (i / len(df)) * 100
                print(f"Progress: {progress:.1f}% - Equity: ${self.system.capital:,.2f}")
        
        # Calculate final performance metrics
        results['performance_metrics'] = self._calculate_performance_metrics(results)
        
        print(f"\nBacktest completed!")
        print(f"Final equity: ${self.system.capital:,.2f}")
        print(f"Total return: {results['performance_metrics']['total_return']:.2%}")
        print(f"Win rate: {results['performance_metrics']['win_rate']:.2%}")
        print(f"Max drawdown: {results['performance_metrics']['max_drawdown']:.2%}")
        
        return results
    
    def _resample_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Resample data to higher timeframe"""
        df_copy = df.copy()
        df_copy.set_index('timestamp', inplace=True)
        
        resampled = df_copy.resample(timeframe).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'atr': 'mean'
        }).dropna()
        
        return resampled.reset_index()
    
    def _generate_signal(self, current_data: pd.DataFrame, htf_data: pd.DataFrame, index: int) -> Dict:
        """Generate trading signals based on strategy rules"""
        
        if len(current_data) < 50:
            return None
            
        current_price = current_data.iloc[-1]['close']
        recent_prices = current_data['close'].tail(10).tolist()
        atr = current_data['atr'].iloc[-1]
        
        # Market structure analysis (HTF)
        structure = self.data_manager.detect_market_structure(current_data.tail(100))
        
        if not structure['swing_points']['highs'] or not structure['swing_points']['lows']:
            return None
            
        # Get recent swing points
        recent_high = structure['swing_points']['highs'][-1]['price']
        recent_low = structure['swing_points']['lows'][-1]['price']
        
        # Calculate Fibonacci levels
        fib_levels = self.system.calculate_fibonacci_levels(recent_low, recent_high, atr)
        
        # Check for entry conditions
        for fib_name, fib_price in fib_levels.items():
            price_distance = abs(current_price - fib_price)
            
            if price_distance <= 0.1:  # Within entry zone
                # Calculate confluence factors
                cluster_density = self.system.cluster_density(current_price)
                step_velocity = self.system.step_velocity(recent_prices)
                psychological_level = self.system.is_psychological_level(current_price)
                
                confluence_score = self.system.calculate_confluence_score(
                    current_price, fib_price, cluster_density, step_velocity, psychological_level
                )
                
                if confluence_score >= 75:
                    # Determine direction based on market structure
                    direction = 'long' if current_price < recent_high else 'short'
                    
                    return {
                        'action': 'enter',
                        'direction': direction,
                        'confluence_score': confluence_score,
                        'fib_level': fib_name,
                        'entry_price': current_price
                    }
        
        return None
    
    def _update_positions(self, current_price: float, current_data: pd.DataFrame):
        """Update existing positions"""
        positions_to_close = []
        
        for trade in self.system.positions:
            # Update trailing stops
            self.system.update_trailing_stop(trade, current_price)
            
            # Check for scaling opportunities
            if len(current_data) >= 10:
                recent_prices = current_data['close'].tail(10).tolist()
                atr = current_data['atr'].iloc[-1]
                self.system.scale_position(trade, current_price, atr)
            
            # Check exit conditions
            if self.system.check_exit_conditions(trade, current_price):
                positions_to_close.append(trade)
        
        # Close positions that hit exit conditions
        for trade in positions_to_close:
            pnl = self.system.close_trade(trade, current_price)
    
    def _calculate_performance_metrics(self, results: Dict) -> Dict:
        """Calculate comprehensive performance metrics"""
        equity_curve = pd.DataFrame(results['equity_curve'])
        
        if equity_curve.empty:
            return {}
        
        # Basic metrics
        initial_capital = equity_curve['equity'].iloc[0]
        final_capital = equity_curve['equity'].iloc[-1]
        total_return = (final_capital - initial_capital) / initial_capital
        
        # Drawdown analysis
        equity_curve['peak'] = equity_curve['equity'].expanding().max()
        equity_curve['drawdown'] = (equity_curve['peak'] - equity_curve['equity']) / equity_curve['peak']
        max_drawdown = equity_curve['drawdown'].max()
        
        # Trade analysis
        trades = self.system.trades_history
        if trades:
            winning_trades = sum(1 for t in trades 
                               if (t.direction == 'long' and t.exit_price > t.entry_price) or
                                  (t.direction == 'short' and t.exit_price < t.entry_price))
            win_rate = winning_trades / len(trades)
            
            # Calculate average win/loss
            wins = []
            losses = []
            for t in trades:
                if t.direction == 'long':
                    pnl = (t.exit_price - t.entry_price) * t.position_size
                else:
                    pnl = (t.entry_price - t.exit_price) * t.position_size
                
                if pnl > 0:
                    wins.append(pnl)
                else:
                    losses.append(abs(pnl))
            
            avg_win = np.mean(wins) if wins else 0
            avg_loss = np.mean(losses) if losses else 0
            profit_factor = sum(wins) / sum(losses) if losses else float('inf')
            
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
        
        # Risk metrics
        daily_returns = equity_curve['equity'].pct_change().dropna()
        sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0
        
        return {
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': len(trades),
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'sharpe_ratio': sharpe_ratio,
            'final_capital': final_capital
        }
    
    def plot_results(self, results: Dict):
        """Plot backtest results"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Equity curve
        equity_df = pd.DataFrame(results['equity_curve'])
        axes[0, 0].plot(equity_df['timestamp'], equity_df['equity'])
        axes[0, 0].set_title('Equity Curve')
        axes[0, 0].set_ylabel('Capital ($)')
        
        # Drawdown
        axes[0, 1].fill_between(equity_df['timestamp'], equity_df['drawdown'], alpha=0.3, color='red')
        axes[0, 1].set_title('Drawdown')
        axes[0, 1].set_ylabel('Drawdown (%)')
        
        # Trade distribution
        if self.system.trades_history:
            pnls = []
            for t in self.system.trades_history:
                if t.direction == 'long':
                    pnl = (t.exit_price - t.entry_price) * t.position_size
                else:
                    pnl = (t.entry_price - t.exit_price) * t.position_size
                pnls.append(pnl)
            
            axes[1, 0].hist(pnls, bins=20, alpha=0.7)
            axes[1, 0].set_title('PnL Distribution')
            axes[1, 0].set_xlabel('PnL ($)')
        
        # Performance metrics table
        metrics = results['performance_metrics']
        metrics_text = f"""
        Total Return: {metrics.get('total_return', 0):.2%}
        Max Drawdown: {metrics.get('max_drawdown', 0):.2%}
        Win Rate: {metrics.get('win_rate', 0):.2%}
        Total Trades: {metrics.get('total_trades', 0)}
        Profit Factor: {metrics.get('profit_factor', 0):.2f}
        Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}
        """
        
        axes[1, 1].text(0.1, 0.5, metrics_text, fontsize=12, verticalalignment='center')
        axes[1, 1].set_title('Performance Metrics')
        axes[1, 1].axis('off')
        
        plt.tight_layout()
        plt.savefig('backtest_results.png', dpi=300, bbox_inches='tight')
        plt.show()

# Usage Example
if __name__ == "__main__":
    backtester = StepIndexBacktester(initial_capital=100000)
    
    start_date = datetime.now() - timedelta(days=90)
    end_date = datetime.now()
    
    results = backtester.run_backtest(start_date, end_date)
    backtester.plot_results(results)