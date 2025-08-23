#!/usr/bin/env python3
"""
Deriv Setup and Configuration Script
Helps you get started with Deriv API integration
"""

import asyncio
import json
from deriv_connector import DerivConnector

class DerivSetup:
    def __init__(self):
        self.app_id = "1089"  # Default Deriv app ID
        self.api_token = None
        
    def get_credentials(self):
        """Get Deriv API credentials from user"""
        print("=== Deriv API Setup ===")
        print()
        print("To use this system with Deriv, you need:")
        print("1. A Deriv account (demo or real)")
        print("2. An API token")
        print()
        print("Steps to get your API token:")
        print("1. Go to https://app.deriv.com")
        print("2. Login to your account")
        print("3. Go to Settings > API Token")
        print("4. Create a new token with 'Trade' permissions")
        print("5. Copy the token")
        print()
        
        # Get API token
        self.api_token = input("Enter your Deriv API token: ").strip()
        
        if not self.api_token:
            print("Error: API token is required")
            return False
        
        # Ask about account type
        account_type = input("Use demo account? (y/n): ").strip().lower()
        self.is_demo = account_type in ['y', 'yes', '']
        
        return True
    
    async def test_connection(self):
        """Test connection to Deriv API"""
        print("\nTesting connection to Deriv API...")
        
        try:
            connector = DerivConnector(
                app_id=self.app_id,
                api_token=self.api_token,
                is_demo=self.is_demo
            )
            
            await connector.connect()
            
            # Wait for authorization
            await asyncio.sleep(2)
            
            if connector.balance > 0:
                print(f"✓ Connection successful!")
                print(f"✓ Account balance: ${connector.balance}")
                print(f"✓ Account type: {'Demo' if self.is_demo else 'Real'}")
                
                # Test Step Index subscription
                await connector.subscribe_ticks('STEP_10')
                await asyncio.sleep(2)
                
                print("✓ Step Index data subscription successful")
                
            else:
                print("⚠ Connected but no balance information received")
            
            await connector.disconnect()
            return True
            
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    def save_config(self):
        """Save configuration to file"""
        config = {
            'app_id': self.app_id,
            'api_token': self.api_token,
            'is_demo': self.is_demo
        }
        
        try:
            with open('deriv_config.json', 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"\n✓ Configuration saved to deriv_config.json")
            return True
            
        except Exception as e:
            print(f"✗ Failed to save config: {e}")
            return False
    
    def load_config(self):
        """Load configuration from file"""
        try:
            with open('deriv_config.json', 'r') as f:
                config = json.load(f)
            
            self.app_id = config.get('app_id', self.app_id)
            self.api_token = config.get('api_token')
            self.is_demo = config.get('is_demo', True)
            
            print("✓ Configuration loaded from deriv_config.json")
            return True
            
        except FileNotFoundError:
            print("No existing configuration found")
            return False
        except Exception as e:
            print(f"✗ Failed to load config: {e}")
            return False
    
    def show_next_steps(self):
        """Show next steps to user"""
        print("\n=== Setup Complete! ===")
        print()
        print("Next steps:")
        print("1. Run the trading system:")
        print("   python deriv_integration.py")
        print()
        print("2. Or run a backtest first:")
        print("   python backtester.py")
        print()
        print("3. Monitor your trades in Deriv app:")
        print("   https://app.deriv.com")
        print()
        print("⚠ Important:")
        print("- Start with demo account to test")
        print("- Use small amounts when going live")
        print("- Monitor your trades closely")
        print("- This system is for educational purposes")

async def main():
    setup = DerivSetup()
    
    print("Deriv Step Index Trading System Setup")
    print("====================================")
    
    # Try to load existing config
    if setup.load_config() and setup.api_token:
        print(f"Found existing configuration")
        print(f"API Token: {setup.api_token[:10]}...")
        print(f"Account Type: {'Demo' if setup.is_demo else 'Real'}")
        
        use_existing = input("\nUse existing configuration? (y/n): ").strip().lower()
        
        if use_existing not in ['y', 'yes', '']:
            if not setup.get_credentials():
                return
    else:
        if not setup.get_credentials():
            return
    
    # Test connection
    if await setup.test_connection():
        # Save configuration
        setup.save_config()
        
        # Show next steps
        setup.show_next_steps()
    else:
        print("\n✗ Setup failed. Please check your credentials and try again.")

if __name__ == "__main__":
    asyncio.run(main())