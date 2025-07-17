#!/bin/bash
#
# Installation script for time sync monitoring

set -e

echo "Installing time sync monitoring..."

# Create log directory
echo "Creating log directory..."
sudo mkdir -p /var/log/trusdx
sudo chmod 755 /var/log/trusdx

# Install the script
echo "Installing check_time_sync.sh..."
sudo cp check_time_sync.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/check_time_sync.sh

# Install systemd service and timer
echo "Installing systemd service and timer..."
sudo cp check-time-sync.service /etc/systemd/system/
sudo cp check-time-sync.timer /etc/systemd/system/

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable and start the timer
echo "Enabling and starting timer..."
sudo systemctl enable check-time-sync.timer
sudo systemctl start check-time-sync.timer

# Check status
echo ""
echo "Installation complete! Checking status..."
sudo systemctl status check-time-sync.timer --no-pager

echo ""
echo "Timer will run every 10 minutes. First run in 2 minutes after boot."
echo "Logs will be written to:"
echo "  - System journal (viewable with: journalctl -t truSDX)"
echo "  - /var/log/trusdx/time_sync.log"
