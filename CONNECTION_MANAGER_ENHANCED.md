# Enhanced Connection Manager Documentation

## Overview

The `connection_manager.py` module has been enhanced with robust reconnection and monitoring logic as specified in Step 6 of the project plan. This implementation provides:

- **Thread-safe state machine** for connection management
- **Exponential backoff** with configurable retry limits
- **Priority fast-path** for TX drops mid-frame
- **Power monitoring** with 0W detection early warning
- **Structured log events** for comprehensive monitoring

## Key Features

### 1. Thread-Safe State Machine

The connection manager now uses a proper state machine with the following states:

```python
class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    TX_DROPPED = "tx_dropped"
```

All state transitions are thread-safe and emit structured events for monitoring.

### 2. Exponential Backoff with MAX_RETRIES

The reconnection logic implements exponential backoff with jitter:

- **Initial backoff**: 100ms
- **Maximum backoff**: 10 seconds
- **Maximum retries**: 10 attempts
- **Jitter**: ±10% to prevent thundering herd

```python
# Configuration constants
MAX_RETRIES = 10
INITIAL_BACKOFF_MS = 100
MAX_BACKOFF_MS = 10000
```

### 3. Priority Fast-Path for TX Drops

When a transmission is dropped mid-frame, the system uses a fast-path reconnection:

- **Detection**: `mark_tx_drop()` sets TX_DROPPED state
- **Fast path**: Skips backoff delay for immediate reconnection
- **Timeout**: 0.5 seconds for fast-path attempts

```python
# Detect TX drop and trigger fast reconnection
conn_mgr.mark_tx_drop()
conn_mgr.safe_reconnect(fast_path=True)
```

### 4. Power Monitoring with 0W Detection

The `PowerMonitor` class provides early warning for connection issues:

- **Polling interval**: 1 second
- **Zero power threshold**: 0.1W
- **Warning threshold**: 1 consecutive zero reading
- **Critical threshold**: 3 consecutive zero readings

```python
# Power monitoring events
LogEvent.POWER_WARNING    # Single zero reading
LogEvent.POWER_CRITICAL   # Multiple zero readings
```

### 5. Structured Log Events

All significant events are logged with structured data:

```python
class LogEvent:
    RECONNECT_START = "EVENT_RECONNECT_START"
    RECONNECT_OK = "EVENT_RECONNECT_OK"
    RECONNECT_FAILED = "EVENT_RECONNECT_FAILED"
    POWER_WARNING = "EVENT_POWER_WARNING"
    POWER_CRITICAL = "EVENT_POWER_CRITICAL"
    TX_DROP_DETECTED = "EVENT_TX_DROP_DETECTED"
    FAST_PATH_ACTIVE = "EVENT_FAST_PATH_ACTIVE"
    STATE_CHANGE = "EVENT_STATE_CHANGE"
    CONNECTION_STABLE = "EVENT_CONNECTION_STABLE"
    MAX_RETRIES_EXCEEDED = "EVENT_MAX_RETRIES_EXCEEDED"
```

Each event includes:
- Event type and timestamp
- Current state and reconnect count
- Relevant context data

## Usage Examples

### Basic Usage

```python
from connection_manager import ConnectionManager

# Create connection manager
conn_mgr = ConnectionManager()

# Start monitoring
conn_mgr.start_monitoring()
conn_mgr.start_power_polling()

# Update data activity
conn_mgr.update_last_data_time()

# Get status
status = conn_mgr.get_connection_status()
```

### Handling TX Drops

```python
# When TX drop is detected
conn_mgr.mark_tx_drop()

# System automatically triggers fast-path reconnection
# Manual trigger if needed:
conn_mgr.safe_reconnect(fast_path=True)
```

### Power Monitoring

```python
# Update power reading
warning = conn_mgr.power_monitor.update_power(watts)

if warning == LogEvent.POWER_CRITICAL:
    # Handle critical power condition
    pass
```

### Graceful Shutdown

```python
# Stop all monitoring threads
conn_mgr.stop_monitoring()
```

## Integration Points

### Main Application

The enhanced connection manager integrates with the main application:

```python
# In main.py
conn_manager = ConnectionManager()
conn_manager.start_monitoring()
conn_manager.start_power_polling()

# Monitor in UI thread
status = conn_manager.get_connection_status()
ui.update_status(status)
```

### CAT Emulator

The CAT emulator should call update methods:

```python
# In cat_emulator.py
conn_manager.update_last_data_time()  # On data received
conn_manager.mark_tx_drop()          # On TX drop detection
```

### Power Interface

Real power monitoring integration:

```python
# Replace simulated power reading
def _power_polling_loop(self):
    while not self.shutdown_event.is_set():
        actual_power = read_power_from_hardware()  # Replace simulation
        warning = self.power_monitor.update_power(actual_power)
        # ... rest of logic
```

## Configuration

Key configuration constants can be adjusted:

```python
# Connection timeouts
CONNECTION_TIMEOUT = 3.0        # Seconds before connection timeout
FAST_PATH_TIMEOUT = 0.5         # Fast-path timeout

# Power monitoring
POWER_POLL_INTERVAL = 1.0       # Power polling interval
ZERO_POWER_THRESHOLD = 0.1      # Watts threshold for zero power

# Backoff parameters
MAX_RETRIES = 10                # Maximum reconnection attempts
INITIAL_BACKOFF_MS = 100        # Initial backoff delay
MAX_BACKOFF_MS = 10000          # Maximum backoff delay
```

## Event Monitoring

Structured events can be monitored for system health:

```python
# Custom event handler
def handle_connection_event(event_type, event_data):
    if event_type == LogEvent.POWER_CRITICAL:
        # Alert operators
        send_alert(f"Power critical: {event_data['power_watts']}W")
    elif event_type == LogEvent.MAX_RETRIES_EXCEEDED:
        # Restart service
        restart_connection_service()
```

## Testing

Run the test suite to verify functionality:

```bash
python3 test_connection_manager.py
```

Run the demo to see the system in action:

```bash
python3 demo_connection_manager.py
```

## Performance Considerations

- **Thread safety**: All operations are thread-safe with minimal locking
- **Memory usage**: Power history is limited to 10 entries
- **CPU usage**: Monitoring threads sleep appropriately
- **Network impact**: Exponential backoff prevents connection storms

## Future Enhancements

Potential improvements:

1. **Adaptive backoff**: Adjust backoff based on success rate
2. **Health scoring**: Score connection health over time
3. **Predictive failure**: Use power trends to predict failures
4. **Recovery strategies**: Different strategies for different failure types
5. **Metrics collection**: Detailed metrics for analysis

## Conclusion

The enhanced connection manager provides robust, production-ready connection handling with comprehensive monitoring and intelligent reconnection strategies. The thread-safe design ensures reliable operation in multi-threaded environments, while structured logging provides excellent observability for operations teams.
