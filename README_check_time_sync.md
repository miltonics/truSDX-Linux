# Time Synchronization Monitor (check_time_sync.sh)

A comprehensive time synchronization monitoring script for WSJT-X and other applications that require precise timing.

## Features

- **Dual Backend Support**: Uses both `timedatectl` and `chronyc tracking` to read time synchronization status
- **Colorized Output**: Beautiful table-based display with color-coded status indicators
- **Threshold Monitoring**: Warns when time offset exceeds 0.5 seconds
- **Multiple Modes**: Supports both one-time checks and continuous monitoring
- **Exit Code Integration**: Returns appropriate exit codes for launcher wrapper scripts
- **Graceful Fallback**: Works even when chronyc is not available

## Usage

```bash
./check_time_sync.sh [OPTIONS]
```

### Options

- `--once`: Run once and exit (useful for scripts)
- `--watch`: Run continuously with 5-second updates (default)
- `-h, --help`: Show help message

### Exit Codes

- `0`: Time is synchronized
- `1`: Time is not synchronized
- `2`: Error accessing time services

## Output Information

### System Status Section
- **NTP Service**: Shows if NTP service is active/inactive
- **Sync Status**: Color-coded synchronization status (SYNCED/NOT SYNCED)

### Chrony Tracking Section (when available)
- **Reference ID**: Current NTP server reference
- **Stratum**: Time server stratum level
- **System Time**: Current system time offset
- **Last Offset**: Most recent time offset (with warning if > 0.5s)
- **RMS Offset**: Root mean square of time offsets
- **Leap Status**: Leap second status (Normal/Insert/Delete)

## Color Coding

- **Green**: Good status (synchronized, normal leap status)
- **Red**: Critical status (not synchronized, errors)
- **Yellow**: Warning status (high offset, leap second events)
- **Cyan**: Information status (normal display elements)

## Integration with WSJT-X

This script is designed to work with WSJT-X launcher wrappers. The exit codes allow launchers to:

- Check time sync before starting WSJT-X
- Abort launch if time is not synchronized
- Display appropriate error messages to users

Example launcher integration:
```bash
#!/bin/bash
if ! ./check_time_sync.sh --once; then
    echo "ERROR: Time not synchronized. WSJT-X requires accurate time."
    exit 1
fi
exec wsjt-x
```

## Requirements

- `timedatectl` (systemd-based systems)
- `chronyc` (optional, for detailed tracking info)
- Bash 4.0 or later
- Terminal with color support

## Installation

1. Make the script executable:
   ```bash
   chmod +x check_time_sync.sh
   ```

2. Optionally install chrony for enhanced features:
   ```bash
   sudo apt install chrony  # Debian/Ubuntu
   sudo yum install chrony  # Red Hat/CentOS
   ```

## Examples

### One-time Check
```bash
./check_time_sync.sh --once
```

### Continuous Monitoring
```bash
./check_time_sync.sh --watch
```

### Script Integration
```bash
if ./check_time_sync.sh --once; then
    echo "Time is synchronized"
else
    echo "Time synchronization problem detected"
fi
```

## Troubleshooting

### Common Issues

1. **"Cannot access timedatectl"**: Ensure systemd is running
2. **"chronyc tracking information not available"**: Install chrony or use NTP
3. **Offset warnings**: Check NTP server connectivity and system clock

### Debug Mode

For debugging, you can run individual commands:
```bash
timedatectl status
chronyc tracking
```

## Contributing

This script is designed to be easily extensible. Key areas for enhancement:

- Additional time service backends (ntpq, etc.)
- Configurable thresholds
- Log file output
- Email notifications
- Graphical status display

## License

This script is provided as-is for use with WSJT-X and similar applications requiring precise timing.
