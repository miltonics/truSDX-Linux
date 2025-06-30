# truSDX Serial Bridge Installation

This document explains how to install the persistent CAT port implementation for truSDX.

## Files Created

1. `create_serial_bridge.sh` - Creates a socat PTY pair linked to `/tmp/trusdx_cat`
2. `stop_serial_bridge.sh` - Stops the socat bridge process
3. `99-trusdx-cat.rules` - udev rule for device permissions (optional)

## Automatic Setup

The driver (`trusdx-rxtx-AI.py`) now automatically:
- Checks for `/tmp/trusdx_cat` existence
- Creates the serial bridge if it doesn't exist
- Uses the persistent port for CAT communication

## Manual Setup (if needed)

### 1. Create Serial Bridge
```bash
chmod +x create_serial_bridge.sh
./create_serial_bridge.sh
```

### 2. Install udev Rule (Optional)
```bash
sudo cp 99-trusdx-cat.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### 3. Verify Bridge
```bash
ls -la /tmp/trusdx_cat*
```

### 4. Stop Bridge (when needed)
```bash
./stop_serial_bridge.sh
```

## WSJT-X/JS8Call Configuration

Configure your program to use:
- **Radio**: Kenwood TS-480
- **CAT Port**: `/tmp/trusdx_cat`
- **Baud Rate**: 115200
- **Data Bits**: 8, Stop Bits: 1, Parity: None
- **PTT Method**: CAT or RTS/DTR

## Troubleshooting

### Bridge Not Created
```bash
# Check if socat is installed
which socat

# Install if missing (Ubuntu/Debian)
sudo apt install socat
```

### Permission Issues
```bash
# Check bridge permissions
ls -la /tmp/trusdx_cat*

# Fix manually if needed
chmod 777 /tmp/trusdx_cat
```

### Multiple Processes
```bash
# Check for existing socat processes
ps aux | grep socat

# Kill if needed
./stop_serial_bridge.sh
```

The driver will automatically handle bridge creation and management in most cases.
