#!/usr/bin/env python3
"""
Step Index Pro Bot - Terminal Launcher
"""
import asyncio
import os
import sys
from headless_bot import HeadlessStepBot

def get_config():
    """Get bot configuration from user"""
    print("=" * 50)
    print("🚀 STEP INDEX PRO BOT")
    print("=" * 50)
    
    # API Token
    api_token = input("Enter Deriv API Token: ").strip()
    if not api_token:
        print("❌ API token required!")
        sys.exit(1)
    
    # Account type
    account_type = input("Account type (demo/real) [demo]: ").strip().lower()
    is_demo = account_type != 'real'
    
    # Risk mode
    print("\nRisk Modes:")
    print("1. Conservative (2%)")
    print("2. Moderate (5%)")  
    print("3. Aggressive (15%)")
    
    risk_choice = input("Select risk mode (1-3) [1]: ").strip()
    risk_modes = {'1': 2, '2': 5, '3': 15}
    risk_mode = risk_modes.get(risk_choice, 2)
    
    # Confluence threshold
    confluence = input("Min confluence score (70-90) [75]: ").strip()
    try:
        confluence = int(confluence) if confluence else 75
        confluence = max(70, min(90, confluence))
    except:
        confluence = 75
    
    return {
        'api_token': api_token,
        'is_demo': is_demo,
        'risk_mode': risk_mode,
        'confluence': confluence
    }

async def main():
    """Main launcher"""
    try:
        # Get configuration
        config = get_config()
        
        print(f"\n✅ Configuration:")
        print(f"Account: {'Demo' if config['is_demo'] else 'Real'}")
        print(f"Risk Mode: {config['risk_mode']}%")
        print(f"Min Confluence: {config['confluence']}")
        print(f"API Token: {config['api_token'][:10]}...")
        
        confirm = input("\nStart bot? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Bot cancelled.")
            return
        
        # Initialize and start bot
        bot = HeadlessStepBot(
            api_token=config['api_token'],
            risk_mode=config['risk_mode'],
            is_demo=config['is_demo'],
            min_confluence=config['confluence']
        )
        
        print("\n🚀 Starting bot...")
        await bot.start()
        
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())