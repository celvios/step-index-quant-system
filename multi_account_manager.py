#!/usr/bin/env python3
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List
from deriv_connector import StepIndexDerivTrader
from real_analytics import RealAnalytics

class MultiAccountManager:
    def __init__(self, accounts_config_file="accounts.json"):
        self.accounts_config_file = accounts_config_file
        self.accounts = {}
        self.traders = {}
        self.analytics = {}
        self.running = False
        
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        self.load_accounts_config()
    
    def load_accounts_config(self):
        """Load accounts configuration"""
        try:
            with open(self.accounts_config_file, 'r') as f:
                config = json.load(f)
                self.accounts = config.get('accounts', {})
                self.logger.info(f"Loaded {len(self.accounts)} accounts")
        except FileNotFoundError:
            self.logger.warning(f"Config file {self.accounts_config_file} not found. Creating template.")
            self.create_template_config()
    
    def create_template_config(self):
        """Create template accounts configuration"""
        template = {
            "accounts": {
                "account1": {
                    "api_token": "YOUR_API_TOKEN_1",
                    "risk_mode": "conservative",
                    "is_demo": True,
                    "max_balance": 10000,
                    "enabled": True
                },
                "account2": {
                    "api_token": "YOUR_API_TOKEN_2", 
                    "risk_mode": "moderate",
                    "is_demo": True,
                    "max_balance": 25000,
                    "enabled": False
                },
                "account3": {
                    "api_token": "YOUR_API_TOKEN_3",
                    "risk_mode": "aggressive", 
                    "is_demo": True,
                    "max_balance": 50000,
                    "enabled": False
                }
            }
        }
        
        with open(self.accounts_config_file, 'w') as f:
            json.dump(template, f, indent=2)
        
        print(f"Created template config: {self.accounts_config_file}")
        print("Please update with your actual API tokens and settings")
    
    async def initialize_accounts(self):
        """Initialize all enabled accounts"""
        for account_name, config in self.accounts.items():
            if not config.get('enabled', False):
                continue
            
            try:
                # Create trader
                trader = StepIndexDerivTrader("1089", config['api_token'], config['is_demo'])
                await trader.connect()
                await asyncio.sleep(2)
                
                if trader.connector.is_connected:
                    balance = trader.connector.balance
                    self.logger.info(f"{account_name}: Connected - Balance: ${balance}")
                    
                    self.traders[account_name] = trader
                    self.analytics[account_name] = RealAnalytics(f"{account_name}_analytics.json")
                else:
                    self.logger.error(f"{account_name}: Connection failed")
                    
            except Exception as e:
                self.logger.error(f"{account_name}: Initialization error - {e}")
    
    async def start_multi_account_trading(self):
        """Start trading on all accounts"""
        await self.initialize_accounts()
        
        if not self.traders:
            self.logger.error("No accounts connected")
            return
        
        self.logger.info(f"Starting trading on {len(self.traders)} accounts")
        self.running = True
        
        # Create trading tasks for each account
        tasks = []
        for account_name in self.traders.keys():
            task = asyncio.create_task(self._account_trading_loop(account_name))
            tasks.append(task)
        
        # Run all accounts concurrently
        await asyncio.gather(*tasks)
    
    async def _account_trading_loop(self, account_name):
        """Trading loop for individual account"""
        trader = self.traders[account_name]
        config = self.accounts[account_name]
        analytics = self.analytics[account_name]
        
        price_history = []
        consecutive_wins = 0
        
        self.logger.info(f"{account_name}: Starting trading loop")
        
        while self.running:
            try:
                price = await trader.get_current_price('STEP_10')
                
                if price:
                    price_history.append(price)
                    
                    if len(price_history) > 15:
                        price_history = price_history[-15:]
                    
                    if len(price_history) >= 5:
                        signal = self._analyze_signal(price_history)
                        
                        if signal:
                            await self._execute_account_trade(account_name, signal, consecutive_wins)
                
                await asyncio.sleep(5)  # 5-second intervals
                
            except Exception as e:
                self.logger.error(f"{account_name}: Trading error - {e}")
                await asyncio.sleep(10)
    
    def _analyze_signal(self, prices):
        """Proven signal analysis"""
        if len(prices) < 5:
            return None
        
        current_price = prices[-1]
        
        # Count consecutive steps
        step_count = 0
        direction = None
        
        for i in range(len(prices) - 1):
            diff = prices[i+1] - prices[i]
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
        
        # Mean reversion after 3+ steps
        if step_count >= 3:
            trade_direction = 'SHORT' if direction == 'up' else 'LONG'
            
            return {
                'price': current_price,
                'direction': trade_direction,
                'step_count': step_count,
                'confidence': min(95, 60 + step_count * 8)
            }
        
        return None
    
    def _calculate_position_size(self, account_name, signal, consecutive_wins):
        """Calculate position size per account"""
        config = self.accounts[account_name]
        trader = self.traders[account_name]
        balance = trader.connector.balance
        
        # Risk modes
        risk_configs = {
            "conservative": {"base_risk": 0.02, "max_risk": 0.05},
            "moderate": {"base_risk": 0.10, "max_risk": 0.25},
            "aggressive": {"base_risk": 0.15, "max_risk": 0.50}
        }
        
        risk_config = risk_configs[config['risk_mode']]
        base_risk = risk_config["base_risk"]
        
        # Scale with wins
        if consecutive_wins >= 3:
            risk = min(risk_config["max_risk"], base_risk * 2.5)
        elif consecutive_wins >= 1:
            risk = base_risk * 1.5
        else:
            risk = base_risk
        
        stake = balance * risk
        return max(5.0, min(stake, balance * risk_config["max_risk"]))
    
    async def _execute_account_trade(self, account_name, signal, consecutive_wins):
        """Execute trade for specific account"""
        try:
            trader = self.traders[account_name]
            analytics = self.analytics[account_name]
            balance = trader.connector.balance
            
            if balance <= 10:
                self.logger.warning(f"{account_name}: Balance too low")
                return
            
            stake = self._calculate_position_size(account_name, signal, consecutive_wins)
            
            # Place real trade
            contract_id = await trader.place_step_trade(
                symbol='STEP_10',
                direction=signal['direction'],
                stake=stake,
                duration_ticks=5
            )
            
            if contract_id:
                analytics.add_trade({
                    'timestamp': datetime.now(),
                    'account': account_name,
                    'symbol': 'STEP_10',
                    'direction': signal['direction'],
                    'stake': stake,
                    'confidence': signal['confidence'],
                    'outcome': 'PENDING',
                    'contract_id': contract_id
                })
                
                self.logger.info(f"{account_name}: TRADE {signal['direction']} ${stake:.0f} Conf:{signal['confidence']}%")
            
        except Exception as e:
            self.logger.error(f"{account_name}: Trade execution error - {e}")
    
    async def get_portfolio_summary(self):
        """Get summary of all accounts"""
        summary = {}
        total_balance = 0
        
        for account_name, trader in self.traders.items():
            balance = trader.connector.balance
            total_balance += balance
            
            analytics = self.analytics[account_name]
            trades = analytics.get_trade_history()
            
            summary[account_name] = {
                'balance': balance,
                'total_trades': len(trades),
                'risk_mode': self.accounts[account_name]['risk_mode'],
                'status': 'Active' if self.running else 'Stopped'
            }
        
        summary['total_portfolio'] = total_balance
        return summary
    
    async def stop_all_accounts(self):
        """Stop trading on all accounts"""
        self.running = False
        
        for account_name, trader in self.traders.items():
            try:
                await trader.connector.disconnect()
                self.logger.info(f"{account_name}: Disconnected")
            except Exception as e:
                self.logger.error(f"{account_name}: Disconnect error - {e}")

async def main():
    print("MULTI-ACCOUNT STEP INDEX TRADING SYSTEM")
    print("Manages multiple Deriv accounts simultaneously")
    
    manager = MultiAccountManager()
    
    try:
        await manager.start_multi_account_trading()
    except KeyboardInterrupt:
        print("\nStopping all accounts...")
        await manager.stop_all_accounts()

if __name__ == "__main__":
    asyncio.run(main())