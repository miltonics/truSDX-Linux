# Time Synchronization Monitor

This monitoring solution checks system time synchronization every 10 minutes and logs any issues.

## Components

1. **check_time_sync.sh** - Main monitoring script that:
   - Checks if system clock is synchronized using `timedatectl`
   - If not synchronized, calls `chronyc makestep` to force synchronization
   - Monitors clock drift and logs if drift exceeds 0.5 seconds
   - Logs to both syslog (with tag 'truSDX') and `/var/log/trusdx/time_sync.log`

2. **check-time-sync.service** - Systemd service unit that runs the script

3. **check-time-sync.timer** - Systemd timer that triggers the service every 10 minutes

## Installation

Run the installation script:
```bash
./install_time_sync_monitor.sh
```

Or manually:
```bash
# Create log directory
sudo mkdir -p /var/log/trusdx
sudo chmod 755 /var/log/trusdx

# Install script
sudo cp check_time_sync.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/check_time_sync.sh

# Install systemd units
sudo cp check-time-sync.service /etc/systemd/system/
sudo cp check-time-sync.timer /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable check-time-sync.timer
sudo systemctl start check-time-sync.timer
```

## Usage

### Check timer status
```bash
sudo systemctl status check-time-sync.timer
```

### View recent runs
```bash
sudo systemctl list-timers check-time-sync.timer
```

### Manually trigger a check
```bash
sudo systemctl start check-time-sync.service
```

### View logs
```bash
# System journal
journalctl -t truSDX

# Log file
tail -f /var/log/trusdx/time_sync.log
```

### Stop monitoring
```bash
sudo systemctl stop check-time-sync.timer
sudo systemctl disable check-time-sync.timer
```

## Log Format

Logs appear in two places:
1. **Syslog/Journal**: Tagged with 'truSDX'
2. **File**: `/var/log/trusdx/time_sync.log` with timestamps

Example log entries:
- `2024-01-10 14:30:00 - Clock unsynced – calling chronyc makestep`
- `2024-01-10 14:30:00 - Clock drift >0.5s: 0.7s`
