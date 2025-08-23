import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from typing import Dict, List, Optional
import sqlite3
import json

class StepIndexDataManager:
    def __init__(self, db_path: str = "step_index_data.db"):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database for storing market data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_data (
                timestamp DATETIME PRIMARY KEY,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                step_count INTEGER,
                atr REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS psychological_levels (
                level REAL PRIMARY KEY,
                level_type TEXT,
                strength INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def generate_step_index_data(self, start_price: float = 8500.0, periods: int = 1000) -> pd.DataFrame:
        """Generate synthetic Step Index data for backtesting"""
        np.random.seed(42)
        
        data = []
        current_price = start_price
        timestamp = datetime.now() - timedelta(hours=periods)
        
        for i in range(periods):
            # Step Index moves in 0.1 increments
            step_change = np.random.choice([-0.1, 0, 0.1], p=[0.3, 0.4, 0.3])
            
            # Add volatility clustering
            if i > 0 and abs(data[-1]['close'] - data[-1]['open']) > 0.5:
                step_change *= 1.5
                
            current_price += step_change
            current_price = round(current_price, 1)  # Ensure step precision
            
            # Generate OHLC
            volatility = np.random.uniform(0.1, 0.8)
            high = current_price + volatility
            low = current_price - volatility
            open_price = current_price + np.random.uniform(-0.2, 0.2)
            
            # Count steps in this period
            step_count = int(abs(step_change) / 0.1) if step_change != 0 else 0
            
            data.append({
                'timestamp': timestamp + timedelta(hours=i),
                'open': round(open_price, 1),
                'high': round(high, 1),
                'low': round(low, 1),
                'close': current_price,
                'volume': np.random.randint(1000, 10000),
                'step_count': step_count
            })
            
        df = pd.DataFrame(data)
        df['atr'] = self.calculate_atr(df)
        return df
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        tr = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def identify_swing_points(self, df: pd.DataFrame, lookback: int = 5) -> Dict[str, List]:
        """Identify swing highs and lows"""
        swing_highs = []
        swing_lows = []
        
        for i in range(lookback, len(df) - lookback):
            # Check for swing high
            is_swing_high = all(df.iloc[i]['high'] >= df.iloc[j]['high'] 
                              for j in range(i - lookback, i + lookback + 1) if j != i)
            
            # Check for swing low
            is_swing_low = all(df.iloc[i]['low'] <= df.iloc[j]['low'] 
                             for j in range(i - lookback, i + lookback + 1) if j != i)
            
            if is_swing_high:
                swing_highs.append({
                    'timestamp': df.iloc[i]['timestamp'],
                    'price': df.iloc[i]['high'],
                    'index': i
                })
                
            if is_swing_low:
                swing_lows.append({
                    'timestamp': df.iloc[i]['timestamp'],
                    'price': df.iloc[i]['low'],
                    'index': i
                })
        
        return {'highs': swing_highs, 'lows': swing_lows}
    
    def detect_market_structure(self, df: pd.DataFrame) -> Dict:
        """Detect market structure changes"""
        swing_points = self.identify_swing_points(df)
        
        structure_breaks = []
        liquidity_sweeps = []
        
        # Analyze structure breaks
        highs = swing_points['highs']
        lows = swing_points['lows']
        
        for i in range(1, len(highs)):
            if highs[i]['price'] > highs[i-1]['price']:
                structure_breaks.append({
                    'type': 'bullish_bos',
                    'timestamp': highs[i]['timestamp'],
                    'price': highs[i]['price'],
                    'previous_high': highs[i-1]['price']
                })
        
        for i in range(1, len(lows)):
            if lows[i]['price'] < lows[i-1]['price']:
                structure_breaks.append({
                    'type': 'bearish_bos',
                    'timestamp': lows[i]['timestamp'],
                    'price': lows[i]['price'],
                    'previous_low': lows[i-1]['price']
                })
        
        return {
            'structure_breaks': structure_breaks,
            'liquidity_sweeps': liquidity_sweeps,
            'swing_points': swing_points
        }
    
    def get_psychological_levels(self, price_range: tuple) -> List[Dict]:
        """Generate psychological levels for given price range"""
        levels = []
        start_price, end_price = price_range
        
        # Whole numbers
        for price in range(int(start_price), int(end_price) + 1):
            levels.append({
                'level': float(price),
                'type': 'whole',
                'strength': 3
            })
            
        # Half levels
        for price in np.arange(start_price, end_price, 0.5):
            if price != int(price):  # Not a whole number
                levels.append({
                    'level': round(price, 1),
                    'type': 'half',
                    'strength': 2
                })
                
        # Quarter levels
        for price in np.arange(start_price, end_price, 0.25):
            if price not in [l['level'] for l in levels]:
                levels.append({
                    'level': round(price, 2),
                    'type': 'quarter',
                    'strength': 1
                })
        
        return sorted(levels, key=lambda x: x['level'])
    
    def save_data(self, df: pd.DataFrame):
        """Save market data to database"""
        conn = sqlite3.connect(self.db_path)
        df.to_sql('market_data', conn, if_exists='append', index=False)
        conn.close()
    
    def load_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Load market data from database"""
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT * FROM market_data 
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp
        '''
        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
        return df
    
    def get_real_time_data(self) -> Dict:
        """Simulate real-time data feed"""
        # In production, this would connect to actual data provider
        current_time = datetime.now()
        base_price = 8500.0
        
        # Simulate current market data
        step_change = np.random.choice([-0.1, 0, 0.1], p=[0.3, 0.4, 0.3])
        current_price = base_price + step_change
        
        return {
            'timestamp': current_time,
            'price': round(current_price, 1),
            'bid': round(current_price - 0.05, 2),
            'ask': round(current_price + 0.05, 2),
            'volume': np.random.randint(100, 1000)
        }
    
    def calculate_volatility_regime(self, df: pd.DataFrame) -> str:
        """Determine current volatility regime"""
        if df.empty or len(df) < 20:
            return 'normal'
            
        recent_atr = df['atr'].iloc[-1]
        atr_mean = df['atr'].mean()
        atr_std = df['atr'].std()
        
        if recent_atr > atr_mean + 2 * atr_std:
            return 'extreme'
        elif recent_atr > atr_mean + 1.5 * atr_std:
            return 'high'
        elif recent_atr < atr_mean - 0.5 * atr_std:
            return 'low'
        else:
            return 'normal'

# Usage Example
if __name__ == "__main__":
    data_manager = StepIndexDataManager()
    
    # Generate sample data
    df = data_manager.generate_step_index_data(periods=500)
    print(f"Generated {len(df)} data points")
    
    # Analyze market structure
    structure = data_manager.detect_market_structure(df)
    print(f"Found {len(structure['structure_breaks'])} structure breaks")
    
    # Get psychological levels
    price_range = (df['close'].min(), df['close'].max())
    levels = data_manager.get_psychological_levels(price_range)
    print(f"Identified {len(levels)} psychological levels")
    
    # Check volatility regime
    regime = data_manager.calculate_volatility_regime(df)
    print(f"Current volatility regime: {regime}")