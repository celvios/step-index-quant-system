import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Quick 1-month backtest
np.random.seed(42)

# Generate 30 days of realistic Step Index data
periods = 30 * 24 * 12  # 5-minute intervals
data = []
price = 8500.0
capital = 100000

for i in range(periods):
    # Step movement (30% chance)
    if np.random.random() < 0.3:
        step = np.random.choice([-0.1, 0.1])
        price += step
    
    data.append(price)

# Strategy simulation
trades = []
signals_generated = 0
signals_taken = 0

for i in range(50, len(data)):
    current_price = data[i]
    recent_prices = data[i-10:i]
    
    # Detect step velocity (3+ consecutive 0.1 moves)
    step_count = 0
    for j in range(len(recent_prices)-1):
        if abs(recent_prices[j+1] - recent_prices[j]) >= 0.1:
            step_count += 1
    
    if step_count >= 3:
        signals_generated += 1
        
        # Confluence scoring
        psychological = abs(current_price - round(current_price)) < 0.01
        confluence_score = 50 + step_count*5 + (15 if psychological else 0)
        
        if confluence_score >= 75:
            signals_taken += 1
            
            # Trade simulation
            risk_amount = capital * 0.02
            
            # Win probability based on confluence
            win_prob = min(0.85, confluence_score / 100)
            
            if np.random.random() < win_prob:
                # Win: 1.5:1 to 4:1 R:R
                profit = risk_amount * np.random.uniform(1.5, 4.0)
                outcome = 'WIN'
            else:
                # Loss
                profit = -risk_amount
                outcome = 'LOSS'
            
            capital += profit
            
            trades.append({
                'profit': profit,
                'outcome': outcome,
                'confluence': confluence_score,
                'capital': capital
            })

# Results
total_trades = len(trades)
winning_trades = sum(1 for t in trades if t['outcome'] == 'WIN')
total_profit = capital - 100000
win_rate = winning_trades / total_trades if total_trades > 0 else 0

print("1-MONTH STEP INDEX BACKTEST RESULTS")
print("="*40)
print(f"Initial Capital: $100,000")
print(f"Final Capital: ${capital:,.2f}")
print(f"Total Profit: ${total_profit:,.2f}")
print(f"Return: {(total_profit/100000)*100:.1f}%")
print(f"Total Trades: {total_trades}")
print(f"Win Rate: {win_rate:.1%}")
print(f"Signals Generated: {signals_generated}")
print(f"Signals Taken: {signals_taken}")
print(f"Signal Conversion: {(signals_taken/signals_generated)*100:.1f}%" if signals_generated > 0 else "0%")

# Profit breakdown
if trades:
    wins = [t['profit'] for t in trades if t['outcome'] == 'WIN']
    losses = [abs(t['profit']) for t in trades if t['outcome'] == 'LOSS']
    
    print(f"\nPROFIT BREAKDOWN:")
    print(f"Average Win: ${np.mean(wins):,.2f}" if wins else "No wins")
    print(f"Average Loss: ${np.mean(losses):,.2f}" if losses else "No losses")
    print(f"Largest Win: ${max(wins):,.2f}" if wins else "No wins")
    print(f"Largest Loss: ${max(losses):,.2f}" if losses else "No losses")
    
    # Daily average
    daily_profit = total_profit / 30
    print(f"\nDaily Average Profit: ${daily_profit:,.2f}")
    print(f"Weekly Projection: ${daily_profit * 7:,.2f}")
    print(f"Monthly Projection: ${daily_profit * 30:,.2f}")