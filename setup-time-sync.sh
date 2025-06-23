#!/bin/bash

# Automatic Time Sync Setup Script for Linux Mint
# This script configures your system for regular, automatic time synchronization
# Created for truSDX radio operations where accurate time is critical

echo "================================================"
echo "   Automatic Time Sync Setup Script"
echo "   For Linux Mint Systems"
echo "================================================"
echo

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "This script should NOT be run as root."
   echo "Please run it as a regular user - it will ask for sudo when needed."
   exit 1
fi

# Function to check service status
check_service_status() {
    local service="$1"
    if systemctl is-active --quiet "$service"; then
        echo "✓ $service is running"
        return 0
    else
        echo "✗ $service is not running"
        return 1
    fi
}

echo "Step 1: Installing time synchronization utilities..."
echo "--------------------------------------------------"

# Update package list and install ntpdate for manual sync
sudo apt update
sudo apt install -y ntpdate

echo
echo "Step 2: Configuring systemd-timesyncd for automatic sync..."
echo "--------------------------------------------------------"

# Configure systemd-timesyncd with multiple reliable NTP servers
echo "Creating optimized timesyncd configuration..."

# Backup original config if it exists
if [ -f /etc/systemd/timesyncd.conf ]; then
    sudo cp /etc/systemd/timesyncd.conf /etc/systemd/timesyncd.conf.backup.$(date +%Y%m%d_%H%M%S)
fi

# Create optimized timesyncd configuration
sudo tee /etc/systemd/timesyncd.conf > /dev/null << 'EOF'
[Time]
# Primary NTP servers - multiple reliable sources
NTP=0.pool.ntp.org 1.pool.ntp.org 2.pool.ntp.org 3.pool.ntp.org
# Fallback NTP servers - high-quality time sources
FallbackNTP=time.nist.gov time.google.com pool.ntp.org
# Use these servers if no others are available
#RootDistanceMaxSec=5
# Poll interval range (min 32 seconds, max 2048 seconds)
PollIntervalMinSec=32
PollIntervalMaxSec=2048
EOF

echo "Enabling and starting systemd-timesyncd service..."
sudo timedatectl set-ntp true
sudo systemctl enable systemd-timesyncd
sudo systemctl restart systemd-timesyncd

echo
echo "Step 3: Performing immediate time synchronization..."
echo "--------------------------------------------------"

# Force immediate sync using ntpdate
echo "Forcing immediate time synchronization..."
sudo ntpdate -s time.nist.gov

# Restart timesyncd to ensure it picks up the new config
sudo systemctl restart systemd-timesyncd

# Wait a moment for sync
sleep 3

echo
echo "Step 4: Setting up time sync status checker..."
echo "---------------------------------------------"

# Create a script to check and report time sync status
sudo tee /usr/local/bin/check-time-sync.sh > /dev/null << 'EOF'
#!/bin/bash
# Time sync status checker for systemd-timesyncd

echo "=== Time Synchronization Status ==="
echo "Current date/time: $(date)"
echo

echo "System time sync status:"
timedatectl status
echo

echo "systemd-timesyncd service status:"
systemctl status systemd-timesyncd --no-pager -l
echo

echo "timesyncd detailed status:"
timedatectl timesync-status 2>/dev/null || echo "Detailed sync info not available"
echo

echo "Recent timesyncd logs:"
journalctl -u systemd-timesyncd --no-pager -n 10 --since "1 hour ago"
EOF

sudo chmod +x /usr/local/bin/check-time-sync.sh

# Create desktop shortcut for time sync checker
cat > /home/milton/Desktop/check-time-sync.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Check Time Sync Status
Comment=Check the current time synchronization status
Exec=gnome-terminal -- /usr/local/bin/check-time-sync.sh
Icon=preferences-system-time
Terminal=true
Categories=System;
StartupNotify=true
EOF

chmod +x /home/milton/Desktop/check-time-sync.desktop

echo
echo "Step 5: Configuring system timezone and RTC..."
echo "---------------------------------------------"

# Make sure timezone is set correctly
echo "Current timezone settings:"
timedatectl status
echo
echo "If timezone is incorrect, you can change it with:"
echo "sudo timedatectl set-timezone America/New_York"  # Adjust as needed
echo "(Replace with your correct timezone)"
echo

# Set RTC to UTC (recommended)
echo "Setting hardware clock to UTC..."
sudo timedatectl set-local-rtc 0

echo
echo "Step 6: Final verification and status..."
echo "--------------------------------------"

# Check final status
echo "Checking service status..."
check_service_status "systemd-timesyncd"

echo
echo "Current time synchronization status:"
timedatectl status

echo
echo "================================================"
echo "   SETUP COMPLETE!"
echo "================================================"
echo
echo "Your system is now configured for automatic time synchronization."
echo
echo "Key features configured:"
echo "• systemd-timesyncd service running and enabled at boot"
echo "• Multiple reliable NTP servers configured"
echo "• Hardware clock set to UTC"
echo "• Immediate synchronization performed"
echo "• Desktop shortcut created to check sync status"
echo
echo "The system will now automatically:"
echo "• Sync time at boot"
echo "• Continuously maintain accurate time"
echo "• Adjust for network delays and clock drift"
echo "• Use multiple NTP sources for reliability"
echo
echo "To check time sync status anytime:"
echo "• Double-click 'Check Time Sync Status' on desktop"
echo "• Or run: /usr/local/bin/check-time-sync.sh"
echo "• Or run: timedatectl status"
echo
echo "For truSDX operations, your system time should now be"
echo "accurate within milliseconds of international time standards."
echo
echo "Script completed successfully!"
echo "================================================"

