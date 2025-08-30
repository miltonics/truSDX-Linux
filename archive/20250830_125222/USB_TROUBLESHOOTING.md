# truSDX USB Connection Troubleshooting Guide

## Problem Description
The truSDX radio USB connection was experiencing disconnections causing:
- Initial connection and VU signal display
- USB disconnection (ch341 serial converter)
- Driver crashes with corrupted data
- Communication failures after reconnection attempts

## Root Causes Identified
1. **USB Power Management**: Linux was suspending the USB device after 2 seconds of inactivity
2. **USB-to-Serial Chip**: CH340/CH341 chips can be sensitive to power management
3. **Possible hardware issues**: Cable quality, USB port power delivery

## Solutions Implemented

### 1. USB Power Management Fix (Permanent)
Created udev rules to disable USB autosuspend for the truSDX device:
- File: `/etc/udev/rules.d/99-trusdx.rules`
- Disables autosuspend for CH340 chip (vendor:1a86, product:7523)
- Creates stable symlink at `/dev/trusdx`
- Sets proper permissions for dialout group

### 2. Monitoring Script
Created `trusdx-monitor.sh` that:
- Monitors USB connection status every 5 seconds
- Automatically restarts driver when USB reconnects
- Maintains USB power settings
- Logs all events to `logs/trusdx-monitor-*.log`

### 3. Manual USB Reset Commands
If the device gets stuck with corrupted data:

```bash
# Option 1: Unbind and rebind USB device
echo '3-2' | sudo tee /sys/bus/usb/drivers/usb/unbind
sleep 2
echo '3-2' | sudo tee /sys/bus/usb/drivers/usb/bind

# Option 2: Reset USB device (if usbreset is installed)
sudo apt install usbutils
sudo usbreset 1a86:7523

# Option 3: Power cycle the radio manually
```

## Usage Instructions

### Normal Operation
```bash
# Start the driver normally
./trusdx-txrx-AI.py

# Or use the monitor for automatic recovery
./trusdx-monitor.sh
```

### Using the Monitor Script
The monitor script provides automatic recovery from USB disconnections:

```bash
# Start monitor (runs driver automatically)
./trusdx-monitor.sh

# Monitor will:
# - Start driver if USB is connected
# - Restart driver if it crashes
# - Stop driver if USB disconnects
# - Restart driver when USB reconnects

# Stop monitor with Ctrl+C
```

### Check USB Status
```bash
# Check if device exists
ls -la /dev/ttyUSB* /dev/trusdx

# Check USB power settings
cat /sys/bus/usb/devices/3-2/power/autosuspend
cat /sys/bus/usb/devices/3-2/power/control

# Monitor USB events
journalctl -f | grep -E "USB|ttyUSB|ch341"

# Check what's using the device
sudo lsof /dev/ttyUSB0
```

## Troubleshooting Steps

### If driver won't connect:
1. Check USB device exists: `ls /dev/ttyUSB*`
2. Check permissions: `groups` (should include 'dialout')
3. Kill any stuck processes: `pkill -f trusdx`
4. Reset USB device (see commands above)
5. Check dmesg for errors: `dmesg | tail -50`

### If experiencing frequent disconnections:
1. Try a different USB cable (shorter, higher quality)
2. Connect directly to computer (no USB hub)
3. Try USB 2.0 port instead of USB 3.0
4. Check radio power supply stability
5. Ensure antenna SWR is acceptable
6. Check for RF interference on USB cable (add ferrite beads)

### If seeing corrupted data:
1. Reset the USB device using unbind/bind method
2. Power cycle the radio
3. Check serial port settings match radio:
   - Baud rate: 9600
   - Data bits: 8
   - Stop bits: 1
   - Parity: None
   - Flow control: None

## Prevention Tips
1. **Use quality USB cable**: Short, shielded cable with ferrite beads
2. **Stable power**: Ensure radio has adequate, clean power supply
3. **RF isolation**: Keep USB cable away from antenna and RF fields
4. **Use monitor script**: Provides automatic recovery from issues
5. **Regular monitoring**: Check logs periodically for warnings

## Log Files
- Driver logs: `logs/trusdx-*.log`
- Monitor logs: `logs/trusdx-monitor-*.log`
- System logs: `journalctl -u trusdx` (if running as service)

## Additional Resources
- CH340/CH341 Linux driver: Usually included in kernel
- PySerial documentation: https://pyserial.readthedocs.io/
- USB power management: https://www.kernel.org/doc/html/latest/driver-api/usb/power-management.html

## Emergency Recovery
If all else fails:
1. Unplug USB cable
2. Power cycle radio
3. Reboot computer
4. Reconnect USB cable
5. Run: `./trusdx-monitor.sh`

The monitor script should handle most recovery scenarios automatically.
