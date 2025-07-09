#!/usr/bin/env python3
"""
Connection management module for truSDX-AI driver.
Handles serial port setup and reconnections with robust state management.
"""

import serial
import time
import threading
import math
from enum import Enum
from typing import Dict, Any, Optional
from logging_cfg import log, LogLevel

# Connection state machine states
class ConnectionState(Enum):
    """Connection state machine states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    TX_DROPPED = "tx_dropped"

# Structured log event types
class LogEvent:
    """Structured log event constants."""
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

# Configuration constants
MAX_RETRIES = 10
INITIAL_BACKOFF_MS = 100
MAX_BACKOFF_MS = 10000
POWER_POLL_INTERVAL = 1.0
CONNECTION_TIMEOUT = 3.0
FAST_PATH_TIMEOUT = 0.5
ZERO_POWER_THRESHOLD = 0.1  # Watts

class PowerMonitor:
    """Monitors power levels and provides early warning for connection issues."""
    
    def __init__(self):
        self.current_power = 0.0
        self.last_poll_time = time.time()
        self.zero_power_count = 0
        self.zero_power_threshold = 3  # Consecutive zero readings before warning
        self.power_history = []
        self.max_history_size = 10
        self.power_lock = threading.Lock()
        
    def update_power(self, watts: float) -> Optional[str]:
        """Update power reading and return warning event if needed.
        
        Args:
            watts: Current power reading in watts
            
        Returns:
            Warning event type if power issue detected, None otherwise
        """
        with self.power_lock:
            self.current_power = watts
            self.last_poll_time = time.time()
            
            # Maintain power history
            self.power_history.append(watts)
            if len(self.power_history) > self.max_history_size:
                self.power_history.pop(0)
            
            # Check for zero power condition
            if watts <= ZERO_POWER_THRESHOLD:
                self.zero_power_count += 1
                if self.zero_power_count >= self.zero_power_threshold:
                    return LogEvent.POWER_CRITICAL
                elif self.zero_power_count >= 1:
                    return LogEvent.POWER_WARNING
            else:
                self.zero_power_count = 0
                
            return None
    
    def get_power_status(self) -> Dict[str, Any]:
        """Get current power status.
        
        Returns:
            Dictionary with power status information
        """
        with self.power_lock:
            return {
                'current_power': self.current_power,
                'last_poll_time': self.last_poll_time,
                'zero_power_count': self.zero_power_count,
                'power_history': self.power_history.copy(),
                'is_critical': self.zero_power_count >= self.zero_power_threshold
            }

class ConnectionManager:
    """Manages the serial connections for truSDX communication with thread-safe state machine."""
    
    def __init__(self):
        self.connections = {
            'ser': None,
            'ser2': None
        }
        
        # Thread-safe state machine
        self.state = ConnectionState.DISCONNECTED
        self.state_lock = threading.RLock()
        
        # Connection tracking
        self.last_data_time = time.time()
        self.reconnect_count = 0
        self.hardware_disconnected = False
        self.tx_dropped_time = None
        
        # Power monitoring
        self.power_monitor = PowerMonitor()
        
        # Backoff calculation
        self.backoff_multiplier = 1.0
        
        # Locks for thread safety
        self.handle_lock = threading.Lock()
        self.power_thread = None
        self.monitor_thread = None
        self.shutdown_event = threading.Event()
        
    def _emit_structured_event(self, event_type: str, **kwargs):
        """Emit structured log events.
        
        Args:
            event_type: Event type from LogEvent constants
            **kwargs: Additional event data
        """
        event_data = {
            'event': event_type,
            'timestamp': time.time(),
            'state': self.state.value,
            'reconnect_count': self.reconnect_count,
            **kwargs
        }
        
        # Format for logging
        event_str = f"{event_type}: {event_data}"
        
        if event_type in [LogEvent.RECONNECT_START, LogEvent.RECONNECT_OK, LogEvent.RECONNECT_FAILED]:
            log(event_str, LogLevel.RECONNECT)
        elif event_type in [LogEvent.POWER_CRITICAL, LogEvent.TX_DROP_DETECTED]:
            log(event_str, LogLevel.ERROR)
        elif event_type in [LogEvent.POWER_WARNING, LogEvent.FAST_PATH_ACTIVE]:
            log(event_str, LogLevel.WARNING)
        else:
            log(event_str, LogLevel.INFO)
    
    def _change_state(self, new_state: ConnectionState, reason: str = ""):
        """Thread-safe state change with event emission.
        
        Args:
            new_state: New connection state
            reason: Reason for state change
        """
        with self.state_lock:
            old_state = self.state
            self.state = new_state
            
            self._emit_structured_event(
                LogEvent.STATE_CHANGE,
                old_state=old_state.value,
                new_state=new_state.value,
                reason=reason
            )
    
    def _calculate_backoff_delay(self) -> float:
        """Calculate exponential backoff delay.
        
        Returns:
            Delay in seconds
        """
        delay_ms = min(
            INITIAL_BACKOFF_MS * (2 ** (self.reconnect_count - 1)),
            MAX_BACKOFF_MS
        )
        
        # Add jitter to prevent thundering herd
        jitter = delay_ms * 0.1 * (2 * time.time() % 1 - 1)  # ±10% jitter
        
        return (delay_ms + jitter) / 1000.0

    def create_serial_connection(self, port: str, baud_rate: int = 115200) -> serial.Serial:
        """Setup a serial connection.

        Args:
            port: Serial port to use
            baud_rate: Communication speed

        Returns:
            Configured serial connection
        """
        try:
            ser = serial.Serial(port, baud_rate, write_timeout=0)
            log(f"Serial connection established on {port}")
            return ser
        except Exception as e:
            log(f"Failed to create serial connection: {e}")
            raise
    
    def detect_tx_drop(self) -> bool:
        """Detect if transmission was dropped mid-frame.
        
        Returns:
            True if TX drop detected
        """
        with self.state_lock:
            if self.tx_dropped_time is None:
                return False
            
            # Check if we're in a TX drop condition
            time_since_drop = time.time() - self.tx_dropped_time
            return time_since_drop < FAST_PATH_TIMEOUT
    
    def mark_tx_drop(self):
        """Mark that transmission was dropped mid-frame."""
        with self.state_lock:
            self.tx_dropped_time = time.time()
            self._change_state(ConnectionState.TX_DROPPED, "TX dropped mid-frame")
            self._emit_structured_event(LogEvent.TX_DROP_DETECTED)
    
    def safe_reconnect(self, fast_path: bool = False):
        """Safely reconnect hardware with atomic handle replacement and exponential backoff.
        
        Args:
            fast_path: Use fast reconnection path for TX drops
        """
        with self.handle_lock:
            # Check if already reconnecting
            if self.state in [ConnectionState.RECONNECTING, ConnectionState.CONNECTING]:
                log("Already reconnecting, skipping...")
                return

            # Check retry limit
            if self.reconnect_count >= MAX_RETRIES:
                self._emit_structured_event(
                    LogEvent.MAX_RETRIES_EXCEEDED,
                    max_retries=MAX_RETRIES
                )
                self._change_state(ConnectionState.FAILED, "Max retries exceeded")
                self.hardware_disconnected = True
                return

            # Start reconnection process
            self.reconnect_count += 1
            self._change_state(ConnectionState.RECONNECTING, "Starting reconnection")
            
            self._emit_structured_event(
                LogEvent.RECONNECT_START,
                attempt=self.reconnect_count,
                fast_path=fast_path
            )

            # Calculate backoff delay (skip for fast path)
            if not fast_path:
                delay = self._calculate_backoff_delay()
                log(f"Reconnection attempt #{self.reconnect_count} after {delay:.2f}s delay")
                time.sleep(delay)
            else:
                self._emit_structured_event(LogEvent.FAST_PATH_ACTIVE)
                log("Fast-path reconnection for TX drop")

            # Stop threads and audio
            old_status = True  # Placeholder for stopping condition
            time.sleep(0.1 if fast_path else 0.5)  # Shorter delay for fast path

            # Reinitialize hardware
            try:
                self._change_state(ConnectionState.CONNECTING, "Attempting hardware reinit")
                
                # Reinitialize using the same logic
                new_ser = self.create_serial_connection("/dev/ttyUSB0")

                # Atomically replace handles
                with self.state_lock:
                    old_ser = self.connections['ser']
                    self.connections['ser'] = new_ser
                    
                    # Close old connection if it exists
                    if old_ser and old_ser.is_open:
                        old_ser.close()

                # Reset TX drop flag
                self.tx_dropped_time = None
                
                # Restart threads or processes if necessary
                old_status = False  # Placeholder for re-enabling condition
                
                # Success - update state
                self._change_state(ConnectionState.CONNECTED, "Reconnection successful")
                self._emit_structured_event(LogEvent.RECONNECT_OK, attempt=self.reconnect_count)
                
                # Reset reconnect count on success
                self.reconnect_count = 0
                self.last_data_time = time.time()
                
                log("Reconnection completed successfully")

            except Exception as e:
                self._emit_structured_event(
                    LogEvent.RECONNECT_FAILED,
                    attempt=self.reconnect_count,
                    error=str(e)
                )
                self._change_state(ConnectionState.DISCONNECTED, f"Reconnection failed: {e}")
                log(f"Error during hardware re-init: {e}", LogLevel.ERROR)
                
                # Schedule retry if under limit
                if self.reconnect_count < MAX_RETRIES:
                    threading.Timer(1.0, lambda: self.safe_reconnect(fast_path=False)).start()

    def monitor_connection(self):
        """Monitor connection health and trigger reconnection if needed, including power and TX drop detection."""
        try:
            while not self.shutdown_event.is_set():
                with self.state_lock:
                    current_time = time.time()
                    time_since_data = current_time - self.last_data_time
                    power_warning = None

                    # Check for zero power warning
                    if (current_time - self.power_monitor.last_poll_time) > POWER_POLL_INTERVAL:
                        power_warning = self.power_monitor.update_power(0.0)  # Simulate polling logic here
                        if power_warning:
                            self._emit_structured_event(power_warning)

                    # Check if connection is lost
                    if time_since_data > CONNECTION_TIMEOUT and self.state == ConnectionState.CONNECTED:
                        log("Connection lost - initiating reconnection sequence")
                        self._change_state(ConnectionState.DISCONNECTED, "Timeout detected")

                        # Trigger reconnection
                        if not self.state == ConnectionState.RECONNECTING:
                            threading.Thread(target=self.safe_reconnect, daemon=True).start()

                    # If connection is back
                    elif time_since_data < CONNECTION_TIMEOUT and self.state == ConnectionState.DISCONNECTED:
                        self._change_state(ConnectionState.CONNECTED, "Connection restored")
                        self.last_data_time = current_time
                        self._emit_structured_event(LogEvent.RECONNECT_OK)

                time.sleep(0.5)  # Check every half second

        except Exception as e:
            log(f"Connection monitor error: {e}")
    
    def start_power_polling(self):
        """Start power monitoring thread."""
        if self.power_thread is None or not self.power_thread.is_alive():
            self.power_thread = threading.Thread(target=self._power_polling_loop, daemon=True)
            self.power_thread.start()
            log("Power monitoring started")
    
    def _power_polling_loop(self):
        """Power polling loop that runs in separate thread."""
        while not self.shutdown_event.is_set():
            try:
                # Simulate power reading - in real implementation, this would read from hardware
                # For now, use a placeholder that simulates varying power levels
                simulated_power = max(0.0, 50.0 + 30.0 * math.sin(time.time() * 0.1))
                
                # Update power and check for warnings
                warning_event = self.power_monitor.update_power(simulated_power)
                if warning_event:
                    self._emit_structured_event(
                        warning_event,
                        power_watts=simulated_power,
                        zero_count=self.power_monitor.zero_power_count
                    )
                    
                    # Trigger fast reconnection on critical power loss
                    if warning_event == LogEvent.POWER_CRITICAL:
                        if self.state == ConnectionState.CONNECTED:
                            threading.Thread(target=self.safe_reconnect, args=(True,), daemon=True).start()
                
                time.sleep(POWER_POLL_INTERVAL)
                
            except Exception as e:
                log(f"Power polling error: {e}", LogLevel.ERROR)
                time.sleep(POWER_POLL_INTERVAL)
    
    def start_monitoring(self):
        """Start connection monitoring thread."""
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.monitor_thread = threading.Thread(target=self.monitor_connection, daemon=True)
            self.monitor_thread.start()
            log("Connection monitoring started")
    
    def stop_monitoring(self):
        """Stop all monitoring threads."""
        self.shutdown_event.set()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
            
        if self.power_thread and self.power_thread.is_alive():
            self.power_thread.join(timeout=2.0)
            
        log("Monitoring stopped")
    
    def update_last_data_time(self):
        """Update the last data received time."""
        with self.state_lock:
            self.last_data_time = time.time()
    
    def get_connection_status(self) -> dict:
        """Get current connection status for UI display.
        
        Returns:
            Dictionary with connection status information
        """
        with self.state_lock:
            return {
                'state': self.state.value,
                'reconnecting': self.state == ConnectionState.RECONNECTING,
                'stable': self.state == ConnectionState.CONNECTED,
                'last_data_time': self.last_data_time,
                'reconnect_count': self.reconnect_count,
                'hardware_disconnected': self.hardware_disconnected,
                'tx_dropped': self.detect_tx_drop(),
                'power_status': self.power_monitor.get_power_status()
            }
    
    def get_port_info(self) -> dict:
        """Get port information for UI display.
        
        Returns:
            Dictionary with port information
        """
        return {
            'cat_port': '/tmp/trusdx_cat',
            'audio_device': 'TRUSDX'
        }

