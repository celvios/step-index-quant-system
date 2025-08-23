import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from step_index_quant_system import StepIndexQuantSystem
from data_manager import StepIndexDataManager
import warnings
warnings.filterwarnings('ignore')

class MonthlyBacktester:
    def __init__(self):
        self.system = StepIndexQuantSystem(100000)
        self.data_manager = StepIndexDataManager()
        self.results = {
            'trades': [],
            'daily_pnl': [],
            'signals_generated': [],
            'signals_taken': [],
            'false_signals': [],
            'market_conditions': []
        }
    
    def generate_realistic_data(self, days=30):
        """Generate realistic Step Index data for 1 month"""
        np.random.seed(42)  # For reproducible results
        
        # Generate 30 days of 5-minute data
        periods = days * 24 * 12  # 5-min intervals
        timestamps = pd.date_range(start='2024-01-01', periods=periods, freq='5T')
        
        data = []
        current_price = 8500.0
        
        for i, ts in enumerate(timestamps):
            # Market regime simulation
            hour = ts.hour
            
            # Higher volatility during London/NY sessions
            if 8 <= hour <= 16:  # London/NY overlap
                volatility_mult = 1.5
                trend_strength = 0.7
            elif 0 <= hour <= 6:  # Asian session
                volatility_mult = 0.8
                trend_strength = 0.3
            else:
                volatility_mult = 1.0
                trend_strength = 0.5
            
            # Step movement probability
            step_prob = 0.3 * volatility_mult
            
            # Generate step movement
            if np.random.random() < step_prob:
                # Trending bias
                if np.random.random() < trend_strength:
                    direction = 1 if i % 100 < 60 else -1  # Trend periods
                else:
                    direction = np.random.choice([-1, 1])
                
                step_change = direction * 0.1
            else:
                step_change = 0
            
            current_price += step_change
            current_price = round(current_price, 1)
            
            # Generate OHLC with realistic spread
            spread = np.random.uniform(0.02, 0.08)
            high = current_price + spread/2
            low = current_price - spread/2
            open_price = current_price + np.random.uniform(-0.05, 0.05)
            
            data.append({
                'timestamp': ts,
                'open': round(open_price, 1),
                'high': round(high, 1),
                'low': round(low, 1),
                'close': current_price,
                'volume': np.random.randint(100, 1000),
                'hour': hour
            })
        
        df = pd.DataFrame(data)
        df['atr'] = self._calculate_atr(df)
        return df
    
    def _calculate_atr(self, df, period=14):
        """Calculate ATR"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        tr = np.maximum(high_low, np.maximum(high_close, low_close))
        return tr.rolling(window=period).mean().fillna(0.1)
    
    def run_month_test(self):
        """Run comprehensive 1-month backtest"""
        print("Starting 1-Month Step Index Backtest...")
        print("=" * 50)
        
        # Generate data
        df = self.generate_realistic_data(30)
        print(f"Generated {len(df)} data points (30 days)")
        
        # Run backtest
        for i in range(50, len(df)):
            current_data = df.iloc[:i+1]
            self._process_timeframe(current_data, i)
            
            if i % 1000 == 0:
                progress = (i / len(df)) * 100
                print(f"Progress: {progress:.1f}% - Trades: {len(self.results['trades'])}")
        
        # Analyze results
        return self._analyze_results(df)
    
    def _process_timeframe(self, data, index):
        """Process each timeframe for signals"""
        current_price = data.iloc[-1]['close']
        recent_prices = data['close'].tail(10).tolist()
        atr = data['atr'].iloc[-1]
        hour = data.iloc[-1]['hour']
        
        # Market condition analysis
        volatility_regime = 'high' if atr > 0.15 else 'low' if atr < 0.05 else 'normal'
        
        self.results['market_conditions'].append({
            'timestamp': data.iloc[-1]['timestamp'],
            'price': current_price,
            'atr': atr,
            'volatility_regime': volatility_regime,
            'hour': hour
        })
        
        # Generate signal
        signal = self._generate_signal(data, index)
        
        if signal:
            self.results['signals_generated'].append(signal)
            
            # Check if signal meets criteria
            if signal['confluence_score'] >= 75:
                self.results['signals_taken'].append(signal)
                
                # Execute trade
                trade = self._execute_trade(signal, current_price, atr)
                if trade:
                    self.results['trades'].append(trade)
            else:
                self.results['false_signals'].append(signal)
    
    def _generate_signal(self, data, index):
        """Generate trading signal"""
        if len(data) < 20:
            return None
        
        current_price = data.iloc[-1]['close']
        recent_prices = data['close'].tail(10).tolist()
        
        # Step velocity detection
        step_count = 0
        direction = None
        
        for i in range(len(recent_prices) - 1):
            diff = recent_prices[i+1] - recent_prices[i]
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
            # Calculate confluence
            cluster_density = self._cluster_density(current_price)
            psychological = self._is_psychological_level(current_price)
            
            confluence_score = 40  # Base
            if step_count >= 3:
                confluence_score += 30
            if cluster_density > 0.4:
                confluence_score += 20
            if psychological:
                confluence_score += 10
            
            return {
                'timestamp': data.iloc[-1]['timestamp'],
                'price': current_price,
                'direction': direction,
                'step_count': step_count,
                'confluence_score': confluence_score,
                'cluster_density': cluster_density,
                'psychological': psychological,
                'hour': data.iloc[-1]['hour'],
                'atr': data['atr'].iloc[-1]
            }
        
        return None
    
    def _cluster_density(self, price):
        """Calculate cluster density"""
        return np.random.uniform(0.2, 0.8)  # Simplified
    
    def _is_psychological_level(self, price):
        """Check psychological level"""
        return abs(price - round(price)) < 0.01 or abs(price - round(price*2)/2) < 0.01
    
    def _execute_trade(self, signal, entry_price, atr):
        """Execute trade and simulate outcome"""
        # Position sizing
        risk_amount = self.system.capital * 0.02
        
        # Simulate trade outcome
        success_prob = min(0.8, signal['confluence_score'] / 100)
        
        if np.random.random() < success_prob:
            # Winning trade
            profit = risk_amount * np.random.uniform(1.5, 4.0)  # 1.5:1 to 4:1 RR
            outcome = 'win'
        else:
            # Losing trade
            profit = -risk_amount
            outcome = 'loss'
        
        self.system.capital += profit
        
        return {
            'timestamp': signal['timestamp'],
            'entry_price': entry_price,
            'direction': signal['direction'],
            'confluence_score': signal['confluence_score'],
            'risk_amount': risk_amount,
            'profit': profit,
            'outcome': outcome,
            'hour': signal['hour'],
            'atr': atr
        }
    
    def _analyze_results(self, df):
        """Analyze backtest results"""
        results = {}
        
        # Basic metrics
        total_trades = len(self.results['trades'])
        winning_trades = sum(1 for t in self.results['trades'] if t['outcome'] == 'win')
        
        results['total_trades'] = total_trades
        results['win_rate'] = winning_trades / total_trades if total_trades > 0 else 0
        results['total_return'] = (self.system.capital - 100000) / 100000
        
        # Signal analysis
        results['signals_generated'] = len(self.results['signals_generated'])
        results['signals_taken'] = len(self.results['signals_taken'])
        results['signal_conversion'] = results['signals_taken'] / results['signals_generated'] if results['signals_generated'] > 0 else 0
        
        # Performance by conditions
        results['performance_by_hour'] = self._analyze_by_hour()
        results['performance_by_volatility'] = self._analyze_by_volatility()
        results['performance_by_confluence'] = self._analyze_by_confluence()
        
        return results
    
    def _analyze_by_hour(self):
        """Analyze performance by hour"""
        hourly_performance = {}
        
        for trade in self.results['trades']:
            hour = trade['hour']
            if hour not in hourly_performance:
                hourly_performance[hour] = {'trades': 0, 'wins': 0, 'profit': 0}
            
            hourly_performance[hour]['trades'] += 1
            if trade['outcome'] == 'win':
                hourly_performance[hour]['wins'] += 1
            hourly_performance[hour]['profit'] += trade['profit']
        
        # Calculate win rates
        for hour in hourly_performance:
            data = hourly_performance[hour]
            data['win_rate'] = data['wins'] / data['trades'] if data['trades'] > 0 else 0
        
        return hourly_performance
    
    def _analyze_by_volatility(self):
        """Analyze performance by volatility regime"""
        vol_performance = {'low': [], 'normal': [], 'high': []}
        
        for trade in self.results['trades']:
            atr = trade['atr']
            if atr < 0.05:
                regime = 'low'
            elif atr > 0.15:
                regime = 'high'
            else:
                regime = 'normal'
            
            vol_performance[regime].append(trade['profit'])
        
        # Calculate metrics
        for regime in vol_performance:
            profits = vol_performance[regime]
            if profits:
                vol_performance[regime] = {
                    'trades': len(profits),
                    'win_rate': sum(1 for p in profits if p > 0) / len(profits),
                    'avg_profit': np.mean(profits),
                    'total_profit': sum(profits)
                }
            else:
                vol_performance[regime] = {'trades': 0, 'win_rate': 0, 'avg_profit': 0, 'total_profit': 0}
        
        return vol_performance
    
    def _analyze_by_confluence(self):
        """Analyze performance by confluence score"""
        confluence_ranges = {
            '75-80': [],
            '80-85': [],
            '85-90': [],
            '90+': []
        }
        
        for trade in self.results['trades']:
            score = trade['confluence_score']
            if 75 <= score < 80:
                confluence_ranges['75-80'].append(trade['profit'])
            elif 80 <= score < 85:
                confluence_ranges['80-85'].append(trade['profit'])
            elif 85 <= score < 90:
                confluence_ranges['85-90'].append(trade['profit'])
            else:
                confluence_ranges['90+'].append(trade['profit'])
        
        # Calculate metrics
        for range_name in confluence_ranges:
            profits = confluence_ranges[range_name]
            if profits:
                confluence_ranges[range_name] = {
                    'trades': len(profits),
                    'win_rate': sum(1 for p in profits if p > 0) / len(profits),
                    'avg_profit': np.mean(profits)
                }
            else:
                confluence_ranges[range_name] = {'trades': 0, 'win_rate': 0, 'avg_profit': 0}
        
        return confluence_ranges
    
    def generate_report(self, results):
        """Generate comprehensive report"""
        print("\n" + "="*60)
        print("1-MONTH STEP INDEX BACKTEST RESULTS")
        print("="*60)
        
        print(f"\nPERFORMANCE SUMMARY:")
        print(f"Initial Capital: $100,000")
        print(f"Final Capital: ${self.system.capital:,.2f}")
        print(f"Total Return: {results['total_return']:.2%}")
        print(f"Total Trades: {results['total_trades']}")
        print(f"Win Rate: {results['win_rate']:.2%}")
        
        print(f"\nSIGNAL ANALYSIS:")
        print(f"Signals Generated: {results['signals_generated']}")
        print(f"Signals Taken: {results['signals_taken']}")
        print(f"Signal Conversion: {results['signal_conversion']:.2%}")
        
        print(f"\nPERFORMANCE BY HOUR:")
        best_hours = []
        worst_hours = []
        
        for hour, data in results['performance_by_hour'].items():
            if data['trades'] >= 3:  # Minimum sample size
                if data['win_rate'] >= 0.7:
                    best_hours.append((hour, data['win_rate'], data['trades']))
                elif data['win_rate'] <= 0.4:
                    worst_hours.append((hour, data['win_rate'], data['trades']))
        
        print("Best Hours (70%+ win rate):")
        for hour, wr, trades in sorted(best_hours, key=lambda x: x[1], reverse=True):
            print(f"  {hour:02d}:00 - Win Rate: {wr:.1%} ({trades} trades)")
        
        print("Worst Hours (40%- win rate):")
        for hour, wr, trades in sorted(worst_hours, key=lambda x: x[1]):
            print(f"  {hour:02d}:00 - Win Rate: {wr:.1%} ({trades} trades)")
        
        print(f"\nPERFORMANCE BY VOLATILITY:")
        for regime, data in results['performance_by_volatility'].items():
            print(f"{regime.upper()} Volatility: {data['win_rate']:.1%} win rate, "
                  f"${data['avg_profit']:.2f} avg profit ({data['trades']} trades)")
        
        print(f"\nPERFORMANCE BY CONFLUENCE SCORE:")
        for range_name, data in results['performance_by_confluence'].items():
            print(f"Score {range_name}: {data['win_rate']:.1%} win rate, "
                  f"${data['avg_profit']:.2f} avg profit ({data['trades']} trades)")
        
        # ML Improvement Areas
        print(f"\nML IMPROVEMENT OPPORTUNITIES:")
        print("="*40)
        
        # Time-based patterns
        hour_variance = np.var([data['win_rate'] for data in results['performance_by_hour'].values()])
        if hour_variance > 0.05:
            print("[+] TIME-BASED ML: High variance in hourly performance")
            print("    -> ML can optimize trading hours and session-specific parameters")
        
        # Volatility adaptation
        vol_data = results['performance_by_volatility']
        vol_diff = max(vol_data[r]['win_rate'] for r in vol_data) - min(vol_data[r]['win_rate'] for r in vol_data)
        if vol_diff > 0.2:
            print("[+] VOLATILITY ML: Performance varies significantly by volatility")
            print("    -> ML can adapt confluence thresholds based on market regime")
        
        # Confluence optimization
        conf_data = results['performance_by_confluence']
        if conf_data['90+']['win_rate'] - conf_data['75-80']['win_rate'] > 0.15:
            print("[+] CONFLUENCE ML: Strong correlation between score and success")
            print("    -> ML can dynamically adjust minimum confluence requirements")
        
        # Signal filtering
        false_signal_rate = len(self.results['false_signals']) / len(self.results['signals_generated'])
        if false_signal_rate > 0.3:
            print("[+] SIGNAL FILTERING ML: High false signal rate")
            print("    -> ML can improve signal quality and reduce noise")
        
        return results

def main():
    """Run the monthly backtest"""
    backtester = MonthlyBacktester()
    results = backtester.run_month_test()
    backtester.generate_report(results)
    
    # Save detailed results
    import json
    with open('month_backtest_results.json', 'w') as f:
        json.dump({k: v for k, v in results.items() if isinstance(v, (int, float, str, dict))}, f, indent=2)
    
    print(f"\nDetailed results saved to 'month_backtest_results.json'")

if __name__ == "__main__":
    main()