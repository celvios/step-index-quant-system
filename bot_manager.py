#!/usr/bin/env python3
"""
Step Index Bot Manager - Handle running instances
"""
import os
import sys
import json
import psutil
import asyncio
from datetime import datetime
from real_analytics import RealAnalytics

class BotManager:
    def __init__(self):
        self.pid_file = "stepbot.pid"
        self.analytics = RealAnalytics()
    
    def is_bot_running(self):
        """Check if bot is already running"""
        if not os.path.exists(self.pid_file):
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process exists
            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                # Check if it's our bot process
                if 'python' in proc.name().lower() and any('bot' in arg for arg in proc.cmdline()):
                    return pid
            
            # PID file exists but process doesn't, clean up
            os.remove(self.pid_file)
            return False
            
        except (ValueError, psutil.NoSuchProcess, PermissionError):
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
            return False
    
    def save_pid(self):
        """Save current process PID"""
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))
    
    def stop_bot(self, pid):
        """Stop running bot"""
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            proc.wait(timeout=10)
            
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
            
            print("✅ Bot stopped successfully")
            return True
            
        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
            print("❌ Failed to stop bot")
            return False
    
    def show_metrics(self):
        """Show current trading metrics"""
        metrics = self.analytics.get_performance_metrics()
        
        if metrics['total_trades'] == 0:
            print("📊 No trades yet")
            return
        
        print("\n" + "="*40)
        print("📊 CURRENT TRADING METRICS")
        print("="*40)
        
        # Get current balance
        balance = 10000  # Default
        if self.analytics.balance_history:
            balance = self.analytics.balance_history[-1]['balance']
        
        print(f"💰 Current Balance: ${balance:,.2f}")
        print(f"📈 Total Return: {metrics['total_return']:.2%}")
        print(f"🎯 Win Rate: {metrics['win_rate']:.1%}")
        print(f"📊 Total Trades: {metrics['total_trades']}")
        print(f"💵 Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"📉 Max Drawdown: {metrics['max_drawdown']:.1%}")
        
        # Today's performance
        daily_pnl = self.analytics.get_daily_pnl()
        print(f"📅 Today's P&L: ${daily_pnl:,.2f}")
        
        # Recent trades
        recent_trades = self.analytics.get_recent_trades(5)
        if recent_trades:
            print(f"\n🔄 Last 5 Trades:")
            for trade in recent_trades[-5:]:
                status_icon = "✅" if "+" in trade['P&L'] else "❌"
                print(f"  {status_icon} {trade['Time']} {trade['Direction']} {trade['P&L']} (Score: {trade['Score']})")
    
    def show_status_menu(self, pid):
        """Show status menu for running bot"""
        print("="*50)
        print("🤖 STEP INDEX BOT IS RUNNING")
        print("="*50)
        print(f"Process ID: {pid}")
        print(f"Started: {self.get_start_time(pid)}")
        print()
        print("Options:")
        print("1. Show trading metrics")
        print("2. Stop bot")
        print("3. Exit (leave bot running)")
        print()
        
        while True:
            choice = input("Select option (1-3): ").strip()
            
            if choice == '1':
                self.show_metrics()
                input("\nPress Enter to continue...")
                continue
            elif choice == '2':
                confirm = input("Stop bot? (y/n): ").strip().lower()
                if confirm == 'y':
                    return self.stop_bot(pid)
                continue
            elif choice == '3':
                print("Bot continues running in background")
                return False
            else:
                print("Invalid choice. Try again.")
    
    def get_start_time(self, pid):
        """Get process start time"""
        try:
            proc = psutil.Process(pid)
            start_time = datetime.fromtimestamp(proc.create_time())
            return start_time.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return "Unknown"

def main():
    """Main bot manager"""
    manager = BotManager()
    
    # Check if bot is already running
    running_pid = manager.is_bot_running()
    
    if running_pid:
        # Bot is running, show status menu
        should_exit = manager.show_status_menu(running_pid)
        if should_exit:
            sys.exit(0)
    else:
        # No bot running, start new one
        print("🚀 Starting new Step Index bot...")
        
        # Import and run the launcher
        from start_bot import main as start_main
        
        # Save PID before starting
        manager.save_pid()
        
        try:
            asyncio.run(start_main())
        except KeyboardInterrupt:
            print("\n⏹️ Bot stopped")
        finally:
            # Clean up PID file
            if os.path.exists(manager.pid_file):
                os.remove(manager.pid_file)

if __name__ == "__main__":
    main()