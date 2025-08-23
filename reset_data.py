#!/usr/bin/env python3
"""
Reset trading data and fix issues
"""
import os
import json

def reset_trading_data():
    """Reset all trading data files"""
    files_to_remove = [
        'trading_data.json',
        'stepbot.pid',
        'stepbot.log'
    ]
    
    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)
            print(f"Removed {file}")
    
    # Create fresh trading data with demo balance
    fresh_data = {
        'trades': [],
        'balance_history': [
            {
                'timestamp': '2024-01-01T00:00:00',
                'balance': 10000.0
            }
        ],
        'daily_stats': []
    }
    
    with open('trading_data.json', 'w') as f:
        json.dump(fresh_data, f, indent=2)
    
    print("✅ Reset complete!")
    print("💰 Balance set to $10,000")
    print("📊 All trades cleared")
    print("\nRestart the bot now.")

if __name__ == "__main__":
    reset_trading_data()