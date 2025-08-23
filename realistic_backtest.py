import pandas as pd
import numpy as np

# Realistic 1-month backtest with fixed position sizing
np.random.seed(42)

# Generate 30 days of Step Index data
periods = 30 * 24 * 12  # 5-minute intervals
data = []
price = 8500.0

for i in range(periods):
    if np.random.random() < 0.3:  # 30% step probability
        step = np.random.choice([-0.1, 0.1])
        price += step
    data.append(price)

# Strategy backtest
initial_capital = 100000
capital = initial_capital
trades = []
daily_pnl = []

for i in range(50, len(data)):
    current_price = data[i]
    recent_prices = data[i-10:i]
    
    # Step velocity detection
    step_count = 0
    for j in range(len(recent_prices)-1):
        if abs(recent_prices[j+1] - recent_prices[j]) >= 0.1:
            step_count += 1
    
    if step_count >= 3:
        # Confluence scoring
        psychological = abs(current_price - round(current_price)) < 0.01
        confluence_score = 50 + step_count*5 + (15 if psychological else 0)
        
        if confluence_score >= 75:
            # Fixed risk amount (2% of INITIAL capital)
            risk_amount = initial_capital * 0.02  # $2000 fixed
            
            # Win probability
            win_prob = min(0.8, confluence_score / 100)
            
            if np.random.random() < win_prob:
                # Win: 2:1 to 4:1 R:R
                profit = risk_amount * np.random.uniform(2.0, 4.0)
                outcome = 'WIN'
            else:
                # Loss
                profit = -risk_amount
                outcome = 'LOSS'
            
            capital += profit
            
            trades.append({
                'day': i // (24*12) + 1,
                'profit': profit,
                'outcome': outcome,
                'confluence': confluence_score,
                'capital': capital
            })

# Calculate daily PnL
for day in range(1, 31):
    day_trades = [t for t in trades if t['day'] == day]
    day_pnl = sum(t['profit'] for t in day_trades)
    daily_pnl.append(day_pnl)

# Results
total_trades = len(trades)
winning_trades = sum(1 for t in trades if t['outcome'] == 'WIN')
total_profit = capital - initial_capital
win_rate = winning_trades / total_trades if total_trades > 0 else 0

print("REALISTIC 1-MONTH STEP INDEX BACKTEST")
print("="*40)
print(f"Initial Capital: ${initial_capital:,}")
print(f"Final Capital: ${capital:,.2f}")
print(f"Total Profit: ${total_profit:,.2f}")
print(f"Return: {(total_profit/initial_capital)*100:.1f}%")
print(f"Total Trades: {total_trades}")
print(f"Win Rate: {win_rate:.1%}")

if trades:
    wins = [t['profit'] for t in trades if t['outcome'] == 'WIN']
    losses = [abs(t['profit']) for t in trades if t['outcome'] == 'LOSS']
    
    print(f"\nTRADE ANALYSIS:")
    print(f"Average Win: ${np.mean(wins):,.2f}")
    print(f"Average Loss: ${np.mean(losses):,.2f}")
    print(f"Profit Factor: {sum(wins)/sum(losses):.2f}")
    
    # Best/worst days
    profitable_days = sum(1 for pnl in daily_pnl if pnl > 0)
    print(f"\nDAILY PERFORMANCE:")
    print(f"Profitable Days: {profitable_days}/30 ({profitable_days/30:.1%})")
    print(f"Best Day: ${max(daily_pnl):,.2f}")
    print(f"Worst Day: ${min(daily_pnl):,.2f}")
    print(f"Average Daily P&L: ${np.mean(daily_pnl):,.2f}")
    
    # Projections
    monthly_return = (total_profit/initial_capital) * 100
    print(f"\nPROJECTIONS:")
    print(f"Monthly Return: {monthly_return:.1f}%")
    print(f"Quarterly Projection: {monthly_return*3:.1f}%")
    print(f"Annual Projection: {monthly_return*12:.1f}%")
    
    # Account growth scenarios
    print(f"\nACCOUNT GROWTH SCENARIOS:")
    for account_size in [1000, 5000, 10000, 50000]:
        monthly_profit = account_size * (monthly_return/100)
        print(f"${account_size:,} account → ${monthly_profit:,.0f}/month profit")

else:
    print("No trades executed")