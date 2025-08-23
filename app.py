import streamlit as st
import asyncio
import json
import time
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from deriv_integration import DerivStepIndexSystem
from real_analytics import RealAnalytics
import threading

# Page config
st.set_page_config(
    page_title="Step Index Pro Bot",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .status-running {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 0.5rem;
        border-radius: 5px;
        color: white;
        text-align: center;
    }
    .status-stopped {
        background: linear-gradient(135deg, #fc466b 0%, #3f5efb 100%);
        padding: 0.5rem;
        border-radius: 5px;
        color: white;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'trading_system' not in st.session_state:
    st.session_state.trading_system = None
if 'analytics' not in st.session_state:
    st.session_state.analytics = RealAnalytics()

async def authenticate_user(deriv_id, server, activation_code):
    """Authenticate with real Deriv API"""
    valid_codes = ["STEPINDEX2024", "PREMIUM001", "TRADER123"]
    
    if activation_code not in valid_codes:
        return False, "Invalid activation code"
    
    try:
        # Test Deriv connection
        from deriv_connector import DerivConnector
        
        # Map server selection to websocket URL
        server_urls = {
            "Demo (ws.binaryws.com)": "wss://ws.binaryws.com/websockets/v3",
            "Real (ws.binaryws.com)": "wss://ws.binaryws.com/websockets/v3",
            "EU (ws.derivws.com)": "wss://ws.derivws.com/websockets/v3",
            "UK (ws.derivws.com)": "wss://ws.derivws.com/websockets/v3",
            "Australia (ws.derivws.com)": "wss://ws.derivws.com/websockets/v3",
            "Singapore (ws.derivws.com)": "wss://ws.derivws.com/websockets/v3",
            "Japan (ws.derivws.com)": "wss://ws.derivws.com/websockets/v3"
        }
        
        # Use proper app_id for authentication
        app_id = "1089" if "Demo" in server else "16929"
        
        connector = DerivConnector(
            app_id=app_id,
            api_token=deriv_id,
            is_demo="Demo" in server
        )
        
        # Test connection
        await connector.connect()
        await asyncio.sleep(2)  # Wait for auth
        
        if connector.is_connected and hasattr(connector, 'account_info') and connector.account_info:
            balance = connector.balance
            loginid = connector.account_info.get('loginid', 'Unknown')
            
            # Store balance in session state
            import streamlit as st
            st.session_state.deriv_balance = balance
            
            await connector.disconnect()
            return True, f"Connected! Account: {loginid}, Balance: ${balance:.2f}"
        else:
            await connector.disconnect()
            return False, "Authentication failed - invalid API token"
            
    except Exception as e:
        return False, f"Connection error: {str(e)}"

def login_page():
    """Login page UI"""
    st.markdown('<h1 class="main-header">🚀 Step Index Pro Bot</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Authentication Required")
        
        with st.form("login_form"):
            deriv_id = st.text_input("Deriv API Token", type="password", help="Your Deriv API token")
            server = st.selectbox("Server", [
                "Demo (ws.binaryws.com)",
                "Real (ws.binaryws.com)", 
                "EU (ws.derivws.com)",
                "UK (ws.derivws.com)",
                "Australia (ws.derivws.com)",
                "Singapore (ws.derivws.com)",
                "Japan (ws.derivws.com)"
            ], help="Choose your Deriv server")
            activation_code = st.text_input("Activation Code", type="password", help="Your premium activation code")
            
            submitted = st.form_submit_button("🚀 Launch Bot", use_container_width=True)
            
            if submitted:
                with st.spinner("🔄 Connecting to Deriv..."):
                    success, message = asyncio.run(authenticate_user(deriv_id, server, activation_code))
                    
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.deriv_id = deriv_id
                        st.session_state.server = server
                        st.success(f"✅ {message}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
        
        st.markdown("---")
        st.info("💡 **Demo Activation Codes**: STEPINDEX2024, PREMIUM001, TRADER123")
        
        # Features preview
        st.markdown("### 🌟 Features")
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("""
            - 🎯 Advanced Step Index Strategy
            - 📊 Real-time Analytics
            - 🔄 Auto Trading Bot
            - 💰 Profit Tracking
            """)
        
        with col_b:
            st.markdown("""
            - 🛡️ Risk Management
            - 📈 Performance Metrics
            - 🚨 Smart Alerts
            - 📱 Mobile Friendly
            """)

def dashboard_page():
    """Main dashboard UI"""
    st.markdown('<h1 class="main-header">📊 Step Index Pro Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar controls
    with st.sidebar:
        st.markdown("### 🎛️ Bot Controls")
        
        # Bot status with balance check
        current_balance = st.session_state.get('deriv_balance', 0)
        
        # Auto-stop bot if balance is 0
        if current_balance <= 0 and st.session_state.bot_running:
            st.session_state.bot_running = False
            st.error("🚨 Bot stopped - Insufficient balance!")
        
        if st.session_state.bot_running:
            st.markdown('<div class="status-running">🟪 LIVE TRADING</div>', unsafe_allow_html=True)
            if st.button("⏹️ Stop Bot", use_container_width=True):
                st.session_state.bot_running = False
                st.success("Bot stopped!")
                st.rerun()
        else:
            st.markdown('<div class="status-stopped">🔴 BOT STOPPED</div>', unsafe_allow_html=True)
            
            # Disable start button if balance is 0
            if current_balance <= 0:
                st.button("▶️ Insufficient Balance", use_container_width=True, disabled=True)
                st.error("💰 Add funds to your Deriv account to start trading")
            else:
                if st.button("▶️ Start Live Trading", use_container_width=True):
                    st.session_state.bot_running = True
                    st.success("Starting live trading with Deriv!")
                    st.rerun()
        
        st.markdown("---")
        
        # Settings
        st.markdown("### ⚙️ Settings")
        risk_mode = st.selectbox("Risk Mode", ["Conservative (2%)", "Moderate (5%)", "Aggressive (15%)"])
        risk_per_trade = {"Conservative (2%)": 2, "Moderate (5%)": 5, "Aggressive (15%)": 15}[risk_mode]
        min_confluence = st.slider("Min Confluence Score", 70, 90, 75)
        max_daily_trades = st.slider("Max Daily Trades", 10, 100, 50)
        
        # Store risk setting
        st.session_state.risk_per_trade = risk_per_trade
        
        st.markdown("---")
        
        # Account info
        st.markdown("### 👤 Account")
        st.write(f"**Server**: {st.session_state.server}")
        st.write(f"**Token**: {st.session_state.deriv_id[:10]}...")
        
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.rerun()
    
    # Main dashboard content
    # Get real-time data from Deriv
    if 'deriv_connector' not in st.session_state:
        st.session_state.deriv_connector = None
    
    # Initialize Deriv connection if bot is running
    if st.session_state.bot_running and st.session_state.deriv_connector is None:
        try:
            from deriv_connector import DerivConnector
            st.session_state.deriv_connector = DerivConnector(
                app_id="1089",
                api_token=st.session_state.deriv_id,
                is_demo="Demo" in st.session_state.server
            )
            # Connect in background
            asyncio.run(st.session_state.deriv_connector.connect())
            # Store the balance once connected
            if st.session_state.deriv_connector.balance > 0:
                st.session_state.deriv_balance = st.session_state.deriv_connector.balance
        except Exception as e:
            st.error(f"Connection error: {e}")
    
    # Get real analytics data
    analytics = st.session_state.analytics
    performance_metrics = analytics.get_performance_metrics()
    
    # Get real balance from session or connector
    current_balance = 1000  # Default
    
    # Check if we have stored balance from login
    if 'deriv_balance' in st.session_state:
        current_balance = st.session_state.deriv_balance
    
    # Update from live connector if running
    if st.session_state.deriv_connector and st.session_state.bot_running:
        try:
            if hasattr(st.session_state.deriv_connector, 'balance') and st.session_state.deriv_connector.balance > 0:
                current_balance = st.session_state.deriv_connector.balance
                st.session_state.deriv_balance = current_balance
        except:
            pass
    
    # Update analytics with current balance
    if current_balance != 1000:  # Only update if we have real balance
        analytics.update_balance(current_balance)
    
    # Real metrics from analytics
    daily_pnl = analytics.get_daily_pnl()
    total_trades = performance_metrics['total_trades']
    win_rate = performance_metrics['win_rate']
    
    # Top metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>💰 Balance</h3>
            <h2>${current_balance:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📈 Daily P&L</h3>
            <h2>${daily_pnl:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>🎯 Win Rate</h3>
            <h2>{win_rate:.1%}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📊 Trades</h3>
            <h2>{total_trades}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Charts section
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.markdown("### 📈 Balance History")
        
        # Get real balance history
        timestamps, balance_data = analytics.get_balance_history_chart_data()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=balance_data,
            mode='lines+markers',
            name='Balance',
            line=dict(color='#1f77b4', width=3),
            fill='tonexty'
        ))
        
        fig.update_layout(
            title="Account Balance Growth",
            xaxis_title="Date",
            yaxis_title="Balance ($)",
            height=400,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col_right:
        st.markdown("### 🎯 Performance Metrics")
        
        # Real performance metrics
        metrics_data = {
            'Metric': ['Total Return', 'Max Drawdown', 'Sharpe Ratio', 'Profit Factor', 'Avg Win', 'Avg Loss'],
            'Value': [
                f"{performance_metrics['total_return']:.1%}",
                f"{performance_metrics['max_drawdown']:.1%}",
                f"{performance_metrics['sharpe_ratio']:.2f}",
                f"{performance_metrics['profit_factor']:.2f}",
                f"${performance_metrics['avg_win']:.2f}",
                f"${performance_metrics['avg_loss']:.2f}"
            ]
        }
        
        df_metrics = pd.DataFrame(metrics_data)
        st.dataframe(df_metrics, hide_index=True, use_container_width=True)
        
        st.markdown("### 🚨 Live Alerts")
        
        if st.session_state.bot_running:
            if st.session_state.deriv_connector:
                balance_display = st.session_state.get('deriv_balance', 0)
                st.success("🟪 Connected to Deriv API")
                st.info(f"🌍 Server: {st.session_state.server}")
                st.info(f"💰 Live Balance: ${balance_display:,.2f}")
                st.info("🔍 Monitoring Step Index patterns...")
            else:
                st.warning("🔄 Connecting to Deriv...")
        else:
            st.info("🔴 Bot stopped - No active trading")
    
    # Recent trades table
    st.markdown("### 📋 Recent Trades")
    
    # Show real trades from analytics
    recent_trades = analytics.get_recent_trades(10)
    
    if recent_trades:
        df_trades = pd.DataFrame(recent_trades)
        st.dataframe(df_trades, hide_index=True, use_container_width=True)
    elif st.session_state.bot_running:
        st.info("🔍 Waiting for trading signals...")
    else:
        st.info("Start the bot to begin live trading with Deriv!")
    
    # AI Suggestions
    st.markdown("### 🤖 AI Suggestions")
    
    col_sug1, col_sug2 = st.columns(2)
    
    with col_sug1:
        # Dynamic suggestions based on real performance
        if performance_metrics['win_rate'] > 0.7:
            st.success(f"""
            **🎯 Excellent Performance**
            
            Win rate: {performance_metrics['win_rate']:.1%}! Your strategy is working well. Current profit factor: {performance_metrics['profit_factor']:.2f}
            """)
        elif performance_metrics['win_rate'] > 0.5:
            st.info(f"""
            **📈 Good Performance**
            
            Win rate: {performance_metrics['win_rate']:.1%}. Consider optimizing confluence thresholds for better results.
            """)
        else:
            st.warning(f"""
            **⚠️ Performance Alert**
            
            Win rate: {performance_metrics['win_rate']:.1%}. Review strategy parameters and market conditions.
            """)
    
    with col_sug2:
        # Risk-based suggestions
        if performance_metrics['max_drawdown'] > 0.15:
            st.error(f"""
            **🚨 High Drawdown Alert**
            
            Max drawdown: {performance_metrics['max_drawdown']:.1%}. Consider reducing position sizes.
            """)
        elif daily_pnl < 0:
            st.warning(f"""
            **📉 Daily Loss Alert**
            
            Today's P&L: ${daily_pnl:.2f}. Monitor closely and consider stopping if losses continue.
            """)
        else:
            st.info(f"""
            **✅ Risk Management**
            
            Daily P&L: ${daily_pnl:.2f}. Risk levels within acceptable limits.
            """)
    
    # Performance analytics
    with st.expander("📊 Advanced Analytics"):
        col_an1, col_an2 = st.columns(2)
        
        with col_an1:
            # Real hourly performance
            hourly_perf = analytics.get_hourly_performance()
            
            if hourly_perf:
                hours = list(hourly_perf.keys())
                win_rates = [hourly_perf[h]['win_rate'] * 100 for h in hours]
                
                fig_hourly = px.bar(
                    x=hours,
                    y=win_rates,
                    title="Win Rate by Hour (Real Data)",
                    labels={'x': 'Hour (GMT)', 'y': 'Win Rate (%)'}
                )
                st.plotly_chart(fig_hourly, use_container_width=True)
            else:
                st.info("No hourly data yet - start trading to see patterns")
        
        with col_an2:
            # Real confluence score performance
            conf_perf = analytics.get_confluence_performance()
            
            if any(conf_perf[r]['trades'] > 0 for r in conf_perf):
                ranges = list(conf_perf.keys())
                trade_counts = [conf_perf[r]['trades'] for r in ranges]
                
                fig_conf = px.pie(
                    values=trade_counts,
                    names=ranges,
                    title="Trades by Confluence Score (Real Data)"
                )
                st.plotly_chart(fig_conf, use_container_width=True)
            else:
                st.info("No confluence data yet - start trading to see distribution")

def main():
    """Main app logic"""
    if not st.session_state.authenticated:
        login_page()
    else:
        dashboard_page()
        
        # Auto-refresh for live updates
        if st.session_state.bot_running:
            time.sleep(10)  # Refresh every 10 seconds
            st.rerun()

if __name__ == "__main__":
    main()