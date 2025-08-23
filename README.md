# Step Index Institutional Quant System

A comprehensive institutional-grade quantitative trading system specifically designed for Step Index markets, implementing advanced market structure analysis, risk management, and execution capabilities.

## 🚀 Features

### Core Strategy Implementation
- **Market Structure Logic**: HTF (4H/Daily) liquidity sweep detection and Break of Structure (BOS) analysis
- **Fibonacci POI**: Dynamic Point of Interest calculation with volatility-based adjustments
- **Entry Execution**: Multi-timeframe confluence scoring with 75+ minimum threshold
- **Exit Strategy**: Dynamic trailing stops with psychological level targeting
- **Position Scaling**: Momentum-based pyramid scaling with volatility explosion detection

### Institutional Components
- **Risk Management**: VaR calculation, position sizing, circuit breakers, and exposure limits
- **Execution Engine**: Smart order routing with TWAP, VWAP, Iceberg, and Sniper strategies
- **Data Management**: Real-time market data processing and historical analysis
- **Backtesting**: Comprehensive performance analysis with multiple metrics
- **Monitoring**: Real-time risk monitoring and automated alerts

## 📁 System Architecture

```
step_index_quant_system.py    # Core trading logic and strategy implementation
data_manager.py               # Market data management and analysis
risk_manager.py              # Institutional risk management system
execution_engine.py          # Order execution and smart routing
backtester.py               # Backtesting and performance analysis
main_system.py              # Main orchestration system
```

## 🛠️ Installation

1. **Clone or download the system files**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 🎯 Quick Start

### Basic Usage
```python
from main_system import StepIndexInstitutionalSystem

# Configure system
config = {
    'initial_capital': 100000,
    'max_portfolio_risk': 0.02,
    'max_single_trade_risk': 0.005,
    'sandbox': True
}

# Initialize and start system
system = StepIndexInstitutionalSystem(config)
await system.start()
```

### Backtesting
```python
from backtester import StepIndexBacktester
from datetime import datetime, timedelta

# Initialize backtester
backtester = StepIndexBacktester(initial_capital=100000)

# Run backtest
start_date = datetime.now() - timedelta(days=90)
end_date = datetime.now()
results = backtester.run_backtest(start_date, end_date)

# Plot results
backtester.plot_results(results)
```

### Risk Analysis
```python
from risk_manager import InstitutionalRiskManager

# Initialize risk manager
risk_manager = InstitutionalRiskManager()

# Calculate position size
position_info = risk_manager.calculate_position_size(
    entry_price=8525.0,
    stop_loss=8500.0,
    account_balance=100000,
    confluence_score=85,
    volatility=1.2
)
```

## 📊 Strategy Details

### Market Structure Analysis
- **Liquidity Sweep Detection**: Break of prior structure ≥ 0.3 steps with immediate rejection
- **BOS Confirmation**: 3+ consecutive steps in direction with proper close
- **Fibonacci Levels**: Dynamic 0.60-0.80 retracement zones with volatility adjustment

### Entry Criteria
| Entry Type | Price Level | Requirements |
|------------|-------------|--------------|
| Primary | 0.618 Fib | Cluster density >40% |
| Secondary | 0.786 Fib | Step velocity ≥3 |
| Reactive | 0.50 Fib | Engulfing/pinbar + liquidity sweep |

### Confluence Scoring
| Factor | Weight | Validation |
|--------|--------|------------|
| Fib Alignment | 40% | Within 0.05 steps |
| Cluster Density | 30% | >60% at level |
| Step Velocity | 20% | ≥3 consecutive steps |
| Psychological Level | 10% | Whole/.5/.25 step |

**Minimum Score**: 75/100 for execution

### Risk Management
- **Position Sizing**: Dynamic based on confluence score (2-10% risk)
- **Circuit Breakers**: 8% daily drawdown, 15% peak-to-trough
- **VaR Monitoring**: 95% and 99% confidence levels
- **Correlation Limits**: Maximum 70% position correlation

### Position Scaling Strategy
| Confluence Score | Risk | Position Size | TP Multiplier | R:R Target |
|------------------|------|---------------|---------------|------------|
| 90-100 | 10% | Full | 1.0x | 1:4 |
| 80-89 | 7% | 70% | 1.2x | 1:5 |
| 75-79 | 5% | 50% | 1.5x | 1:6 |

## 🔧 Configuration Options

### System Configuration
```python
config = {
    'initial_capital': 100000,           # Starting capital
    'max_portfolio_risk': 0.02,          # 2% max portfolio risk
    'max_single_trade_risk': 0.005,      # 0.5% max single trade risk
    'analysis_interval_minutes': 5,       # Analysis frequency
    'sandbox': True,                     # Use sandbox mode
    'api_key': 'your_api_key',          # Broker API key
    'secret_key': 'your_secret_key'     # Broker secret key
}
```

### Risk Parameters
```python
risk_config = {
    'daily_var_limit': 0.05,            # 5% daily VaR limit
    'correlation_limit': 0.7,           # 70% max correlation
    'concentration_limit': 0.3,         # 30% max single position
    'volatility_filter': 0.3            # Minimum ATR for entries
}
```

## 📈 Performance Metrics

The system tracks comprehensive performance metrics:

- **Return Metrics**: Total return, annualized return, monthly returns
- **Risk Metrics**: Maximum drawdown, VaR, Expected Shortfall, Sharpe ratio
- **Trade Metrics**: Win rate, profit factor, average win/loss
- **Execution Metrics**: Fill rate, slippage, commission costs

## 🚨 Risk Controls

### Automated Circuit Breakers
- **Daily Drawdown**: 8% → Stop trading
- **Peak-to-Trough**: 15% → 24hr cooldown
- **Volatility Filter**: ATR < 0.3σ → No entries

### Position Limits
- **Single Position**: Maximum 10% of account value
- **Portfolio Risk**: Maximum 2% total risk exposure
- **Correlation**: Maximum 70% between positions

## 📝 Logging and Monitoring

The system provides comprehensive logging:
- **Trade Execution**: All entries, exits, and modifications
- **Risk Events**: Limit breaches, violations, warnings
- **System Events**: Startup, shutdown, errors
- **Performance**: Daily PnL, drawdown, metrics

## 🔄 Live Trading vs Backtesting

### Backtesting Mode
- Uses synthetic Step Index data
- Historical performance analysis
- Strategy optimization
- Risk parameter testing

### Live Trading Mode
- Real-time market data integration
- Actual order execution
- Live risk monitoring
- Real-time performance tracking

## 🛡️ Safety Features

- **Graceful Shutdown**: Proper position closing on system stop
- **Error Recovery**: Automatic reconnection and error handling
- **Data Validation**: Input validation and sanity checks
- **Backup Systems**: Multiple data sources and failover mechanisms

## 📞 Support and Customization

This system is designed for institutional use and can be customized for specific requirements:

- Custom risk parameters
- Additional Step Index variants (10, 25, 50, 75, 100)
- Integration with specific brokers
- Custom reporting and analytics
- Portfolio management features

## ⚠️ Disclaimer

This system is for educational and research purposes. Always test thoroughly in a sandbox environment before live trading. Past performance does not guarantee future results. Trading involves substantial risk of loss.

## 📄 License

Proprietary institutional trading system. All rights reserved.