#!/bin/bash

# truSDX USB Connection Monitor
# Monitors USB connection and automatically restarts driver if disconnected

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRIVER_SCRIPT="$SCRIPT_DIR/trusdx-txrx-AI.py"
LOG_FILE="$SCRIPT_DIR/logs/trusdx-monitor-$(date +%Y%m%d_%H%M%S).log"
PID_FILE="/tmp/trusdx-driver.pid"
USB_DEVICE="/dev/ttyUSB0"
CHECK_INTERVAL=5  # seconds

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Ensure logs directory exists
mkdir -p "$SCRIPT_DIR/logs"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to check if USB device exists
check_usb_device() {
    if [ -e "$USB_DEVICE" ] || [ -e "/dev/trusdx" ]; then
        return 0
    else
        return 1
    fi
}

# Function to check if driver is running
is_driver_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    
    # Also check by process name
    if pgrep -f "trusdx-txrx-AI.py" > /dev/null; then
        return 0
    fi
    
    return 1
}

# Function to stop the driver
stop_driver() {
    log_message "Stopping truSDX driver..."
    
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        kill "$pid" 2>/dev/null
        sleep 2
        
        # Force kill if still running
        if ps -p "$pid" > /dev/null 2>&1; then
            kill -9 "$pid" 2>/dev/null
        fi
        rm -f "$PID_FILE"
    fi
    
    # Kill by name as fallback
    pkill -f "trusdx-txrx-AI.py" 2>/dev/null
    sleep 1
}

# Function to start the driver
start_driver() {
    log_message "Starting truSDX driver..."
    
    # Check if driver script exists
    if [ ! -f "$DRIVER_SCRIPT" ]; then
        log_message "ERROR: Driver script not found: $DRIVER_SCRIPT"
        return 1
    fi
    
    # Start the driver in background and save PID
    cd "$SCRIPT_DIR"
    python3 "$DRIVER_SCRIPT" >> "$LOG_FILE" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"
    
    sleep 3  # Give driver time to initialize
    
    if is_driver_running; then
        log_message "Driver started successfully (PID: $pid)"
        return 0
    else
        log_message "ERROR: Failed to start driver"
        return 1
    fi
}

# Function to check USB power settings
check_usb_power() {
    local usb_path="/sys/bus/usb/devices/3-2"
    
    if [ -d "$usb_path" ]; then
        local autosuspend=$(cat "$usb_path/power/autosuspend" 2>/dev/null)
        local control=$(cat "$usb_path/power/control" 2>/dev/null)
        
        if [ "$autosuspend" != "-1" ] || [ "$control" != "on" ]; then
            log_message "WARNING: USB power management not optimal (autosuspend=$autosuspend, control=$control)"
            log_message "Fixing USB power settings..."
            
            echo -1 | sudo tee "$usb_path/power/autosuspend" > /dev/null 2>&1
            echo on | sudo tee "$usb_path/power/control" > /dev/null 2>&1
            
            log_message "USB power settings corrected"
        fi
    fi
}

# Trap signals for clean shutdown
trap 'log_message "Monitor shutting down..."; stop_driver; exit 0' SIGINT SIGTERM

# Main monitoring loop
log_message "=== truSDX Monitor Started ==="
log_message "Monitoring USB device: $USB_DEVICE"
log_message "Check interval: $CHECK_INTERVAL seconds"

# Initial checks
check_usb_power

# Start driver if USB is connected and driver not running
if check_usb_device; then
    if ! is_driver_running; then
        start_driver
    else
        log_message "Driver already running"
    fi
else
    log_message "USB device not detected, waiting..."
fi

# Monitor loop
usb_was_connected=false
consecutive_failures=0

while true; do
    if check_usb_device; then
        # USB is connected
        if [ "$usb_was_connected" = false ]; then
            log_message "USB device detected"
            usb_was_connected=true
            consecutive_failures=0
            
            # Check USB power settings
            check_usb_power
        fi
        
        # Check if driver is running
        if ! is_driver_running; then
            log_message "Driver not running, attempting to start..."
            
            if start_driver; then
                consecutive_failures=0
            else
                consecutive_failures=$((consecutive_failures + 1))
                
                if [ $consecutive_failures -ge 3 ]; then
                    log_message "ERROR: Failed to start driver 3 times, waiting 30 seconds..."
                    sleep 30
                    consecutive_failures=0
                fi
            fi
        fi
    else
        # USB is not connected
        if [ "$usb_was_connected" = true ]; then
            log_message "WARNING: USB device disconnected!"
            usb_was_connected=false
            
            # Stop the driver since USB is gone
            if is_driver_running; then
                stop_driver
            fi
        fi
    fi
    
    sleep "$CHECK_INTERVAL"
done
