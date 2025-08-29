# Client Setup Guide - Step Index Trading System

## Quick Setup for Testing

### Prerequisites
- Windows 10/11 or Linux
- Python 3.8+ installed
- Deriv demo account with API token

### 1. Download & Install
```bash
# Download the system
git clone https://github.com/celvios/step-index-quant-system.git
cd step-index-quant-system

# Install dependencies
pip install -r requirements.txt
```

### 2. Get Your Deriv API Token
1. Go to [Deriv.com](https://deriv.com) → Login
2. Settings → API Token → Create New Token
3. Copy the token (starts with letters/numbers)

### 3. Run Demo Test
```bash
# Test the system (demo mode only)
python final_live_strategy.py
```

When prompted:
- Enter your API token
- Select "1" for Conservative mode
- System will start trading with demo money

### 4. Monitor Performance
- Check `stepbot.log` for trade logs
- Check `trading_data.json` for performance data
- Press Ctrl+C to stop anytime

## Demo Limitations
- **Demo accounts only** - No real money risk
- **Conservative mode only** - 2-5% position sizing
- **7-day trial** - System stops after 7 days
- **No multi-account** - Single account testing only

## What You'll See
- Real-time Step Index price monitoring
- Trade signals when 3+ consecutive steps detected
- Automatic trade execution on Deriv demo account
- Performance tracking and analytics

## Support
- Check logs in `stepbot.log` for any issues
- Ensure stable internet connection
- Verify Deriv demo account has sufficient balance

## Next Steps
After successful demo testing, contact us for:
- Full system access (all risk modes)
- Multi-account management
- Production deployment assistance
- Custom configuration options