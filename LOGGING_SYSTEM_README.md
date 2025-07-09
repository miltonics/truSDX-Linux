# truSDX-AI Extended Logging System

This document describes the enhanced logging system implemented for truSDX-AI.

## Features

- **Python logging module**: Uses standard Python logging instead of ad-hoc functions
- **JSON formatted logs**: Structured logging with JSON format for easy parsing
- **Rotating log files**: Automatic log rotation (10MB max, 5 backups)
- **Multiple log levels**: DEBUG, INFO, WARNING, RECONNECT, ERROR, CRITICAL
- **Console output**: Colored console output with configurable verbosity
- **Syslog integration**: Optional syslog handler for systemd integration
- **Default log location**: `~/.cache/trusdx/logs/trusdx.log`
- **Custom log file**: `--logfile /path/to/custom.log` CLI option

## Usage

### Command Line Options

```bash
# Basic usage with verbose output
python src/main.py --verbose

# Custom log file
python src/main.py --logfile /var/log/trusdx.log

# Enable syslog for systemd integration
python src/main.py --syslog

# Combined options
python src/main.py --verbose --logfile /tmp/debug.log --syslog
```

### Code Usage

#### New Logging Functions

```python
from logging_cfg import debug, info, warning, reconnect, error, critical, exception

# Basic logging
debug("Debug message")
info("Info message")
warning("Warning message")
reconnect("Radio reconnection detected")
error("Error message")
critical("Critical message")

# Exception logging with traceback
try:
    risky_operation()
except Exception as e:
    exception("Operation failed")

# Structured logging with context
info("Connection established", 
     host="192.168.1.100", 
     port=4532, 
     frequency=14074000)
```

#### Backward Compatibility

The old `log()` function is still supported:

```python
from logging_cfg import log

log("Message", "INFO")
log("Debug message", "DEBUG")
log("Warning message", "WARNING")
log("Reconnect message", "RECONNECT")
log("Error message", "ERROR")
log("Critical message", "CRITICAL")
```

### Configuration

```python
from logging_cfg import configure_logging

# Basic configuration
configure_logging(verbose=True)

# Custom log file
configure_logging(verbose=True, log_file="/var/log/trusdx.log")

# Enable syslog
configure_logging(verbose=True, enable_syslog=True)

# Full configuration
configure_logging(
    verbose=True,
    log_file="/var/log/trusdx.log",
    enable_syslog=True
)
```

## Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General information messages
- **WARNING**: Warning messages for potential issues
- **RECONNECT**: Special level for radio reconnection events
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical errors that may cause system failure

## Log Format

### Console Output
```
[2025-01-27 12:34:56] INFO: Audio device initialized
[2025-01-27 12:34:57] RECONNECT: Radio reconnection detected
[2025-01-27 12:34:58] ERROR: Connection failed
```

### JSON Log File
```json
{
  "timestamp": "2025-01-27T12:34:56.123456Z",
  "level": "INFO",
  "message": "Connection established",
  "module": "connection_manager",
  "function": "connect",
  "line": 123,
  "process": 12345,
  "thread": 67890,
  "host": "192.168.1.100",
  "port": 4532,
  "frequency": 14074000
}
```

## File Structure

### Default Log Directory
```
~/.cache/trusdx/logs/
├── trusdx.log          # Current log file
├── trusdx.log.1        # Previous log file
├── trusdx.log.2        # Older log file
└── ...                 # Up to 5 backup files
```

### Log Rotation
- **Maximum file size**: 10MB
- **Backup files**: 5 (trusdx.log.1 through trusdx.log.5)
- **Automatic rotation**: When current log exceeds 10MB

## Syslog Integration

When enabled with `--syslog`, messages are sent to the system log:

```bash
# View trusdx logs in syslog
journalctl -f | grep trusdx

# Or with systemd journal
journalctl -u your-trusdx-service -f
```

## Migration from Old System

The old logging system has been completely replaced but maintains backward compatibility:

### Old Usage (still works)
```python
from logging_cfg import log, LogLevel

log("Message", LogLevel.INFO)
log("Debug message", LogLevel.DEBUG)
```

### New Usage (recommended)
```python
from logging_cfg import info, debug

info("Message")
debug("Debug message")
```

## Testing

Run the test script to verify logging functionality:

```bash
python test_logging.py
```

This will demonstrate:
- All log levels
- JSON formatting
- File rotation
- Syslog integration
- Backward compatibility
- Structured logging with context
