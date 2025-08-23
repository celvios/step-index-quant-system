#!/bin/bash
# VPS Deployment Script for Step Index Bot

echo "Setting up Step Index Bot on VPS..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3 python3-pip screen htop curl

# Install Python packages
pip3 install pandas numpy websockets plotly psutil asyncio

# Create bot directory
mkdir -p ~/stepbot
cd ~/stepbot

# Upload bot files (you'll need to scp these)
echo "Upload your bot files to ~/stepbot/"
echo "Required files:"
echo "- app.py"
echo "- deriv_connector.py" 
echo "- real_analytics.py"
echo "- headless_bot.py"
echo "- requirements_app.txt"

# Set permissions
chmod +x headless_bot.py

# Create systemd service for auto-restart
sudo tee /etc/systemd/system/stepbot.service > /dev/null <<EOF
[Unit]
Description=Step Index Trading Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/stepbot
ExecStart=/usr/bin/python3 /home/$USER/stepbot/headless_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable stepbot

echo "Setup complete!"
echo ""
echo "To start bot:"
echo "1. Upload your files to ~/stepbot/"
echo "2. sudo systemctl start stepbot"
echo "3. sudo systemctl status stepbot"
echo ""
echo "To run with screen (manual):"
echo "screen -S stepbot"
echo "cd ~/stepbot && python3 headless_bot.py"