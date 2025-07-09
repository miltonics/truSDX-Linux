#!/usr/bin/env python3
"""
Test script for the enhanced connection manager functionality.
Verifies state machine, power monitoring, and reconnection logic.
"""

import sys
import os
import time
import threading

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from connection_manager import ConnectionManager, ConnectionState, LogEvent
from logging_cfg import configure_logging

def test_state_machine():
    """Test the connection state machine."""
    print("Testing state machine...")
    
    conn_mgr = ConnectionManager()
    
    # Test initial state
    assert conn_mgr.state == ConnectionState.DISCONNECTED
    print("✓ Initial state is DISCONNECTED")
    
    # Test state change
    conn_mgr._change_state(ConnectionState.CONNECTED, "Test connection")
    assert conn_mgr.state == ConnectionState.CONNECTED
    print("✓ State change to CONNECTED works")
    
    # Test TX drop detection
    conn_mgr.mark_tx_drop()
    assert conn_mgr.state == ConnectionState.TX_DROPPED
    assert conn_mgr.detect_tx_drop() == True
    print("✓ TX drop detection works")
    
    print("State machine tests passed!\n")

def test_power_monitoring():
    """Test power monitoring functionality."""
    print("Testing power monitoring...")
    
    conn_mgr = ConnectionManager()
    
    # Test normal power
    warning = conn_mgr.power_monitor.update_power(50.0)
    assert warning is None
    print("✓ Normal power reading works")
    
    # Test zero power warning
    warning = conn_mgr.power_monitor.update_power(0.0)
    assert warning == LogEvent.POWER_WARNING
    print("✓ Zero power warning triggered")
    
    # Test critical power (multiple zero readings)
    for i in range(3):
        warning = conn_mgr.power_monitor.update_power(0.0)
    assert warning == LogEvent.POWER_CRITICAL
    print("✓ Critical power warning triggered")
    
    # Test power recovery
    warning = conn_mgr.power_monitor.update_power(50.0)
    assert warning is None
    print("✓ Power recovery works")
    
    print("Power monitoring tests passed!\n")

def test_backoff_calculation():
    """Test exponential backoff calculation."""
    print("Testing backoff calculation...")
    
    conn_mgr = ConnectionManager()
    
    # Test increasing backoff
    delays = []
    for i in range(5):
        conn_mgr.reconnect_count = i + 1
        delay = conn_mgr._calculate_backoff_delay()
        delays.append(delay)
        print(f"  Attempt {i+1}: {delay:.3f}s")
    
    # Verify exponential increase (with some tolerance for jitter)
    for i in range(1, len(delays)):
        assert delays[i] > delays[i-1] * 1.5, f"Backoff should increase exponentially"
    
    print("✓ Exponential backoff calculation works")
    print("Backoff calculation tests passed!\n")

def test_connection_status():
    """Test connection status reporting."""
    print("Testing connection status...")
    
    conn_mgr = ConnectionManager()
    
    # Test initial status
    status = conn_mgr.get_connection_status()
    assert status['state'] == ConnectionState.DISCONNECTED.value
    assert status['reconnecting'] == False
    assert status['stable'] == False
    print("✓ Initial connection status correct")
    
    # Test connected status
    conn_mgr._change_state(ConnectionState.CONNECTED, "Test")
    status = conn_mgr.get_connection_status()
    assert status['state'] == ConnectionState.CONNECTED.value
    assert status['stable'] == True
    print("✓ Connected status correct")
    
    # Test power status inclusion
    assert 'power_status' in status
    assert 'current_power' in status['power_status']
    print("✓ Power status included in connection status")
    
    print("Connection status tests passed!\n")

def test_structured_events():
    """Test structured event emission."""
    print("Testing structured events...")
    
    conn_mgr = ConnectionManager()
    
    # Test event emission (this will log to console)
    conn_mgr._emit_structured_event(
        LogEvent.RECONNECT_START,
        attempt=1,
        fast_path=False
    )
    print("✓ Structured event emission works")
    
    conn_mgr._emit_structured_event(
        LogEvent.POWER_WARNING,
        power_watts=0.0,
        zero_count=1
    )
    print("✓ Power warning event emission works")
    
    print("Structured event tests passed!\n")

def main():
    """Run all tests."""
    print("=== Connection Manager Enhanced Tests ===\n")
    
    # Configure logging for tests
    configure_logging(verbose=True)
    
    try:
        test_state_machine()
        test_power_monitoring()
        test_backoff_calculation()
        test_connection_status()
        test_structured_events()
        
        print("🎉 All tests passed! Connection manager is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
