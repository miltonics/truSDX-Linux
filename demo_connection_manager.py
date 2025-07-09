#!/usr/bin/env python3
"""
Demo script for the enhanced connection manager.
Shows how to use the new robust reconnection and monitoring logic.
"""

import sys
import os
import time
import threading
import signal

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from connection_manager import ConnectionManager, ConnectionState, LogEvent
from logging_cfg import configure_logging

def demo_connection_manager():
    """Demonstrate the enhanced connection manager features."""
    
    print("=== Enhanced Connection Manager Demo ===\n")
    
    # Configure logging
    configure_logging(verbose=True)
    
    # Create connection manager
    conn_mgr = ConnectionManager()
    
    print("1. Starting connection manager...")
    
    # Start monitoring threads
    conn_mgr.start_monitoring()
    conn_mgr.start_power_polling()
    
    print("2. Connection manager started with monitoring and power polling")
    print("   - State machine running")
    print("   - Power monitoring active")
    print("   - Exponential backoff configured")
    print("   - Structured event logging enabled")
    
    # Simulate connection events
    print("\n3. Simulating connection events...")
    
    # Change to connected state
    conn_mgr._change_state(ConnectionState.CONNECTED, "Initial connection")
    print("   Connection established")
    
    # Simulate some data activity
    time.sleep(1)
    conn_mgr.update_last_data_time()
    print("   Data activity detected")
    
    # Simulate TX drop
    time.sleep(1)
    print("   Simulating TX drop...")
    conn_mgr.mark_tx_drop()
    
    # Trigger fast-path reconnection
    print("   Triggering fast-path reconnection...")
    threading.Thread(target=conn_mgr.safe_reconnect, args=(True,), daemon=True).start()
    
    time.sleep(1)
    
    # Simulate power warning
    print("   Simulating power warning...")
    conn_mgr.power_monitor.update_power(0.0)
    
    # Show status
    print("\n4. Current connection status:")
    status = conn_mgr.get_connection_status()
    for key, value in status.items():
        if key == 'power_status':
            print(f"   {key}: {value['current_power']}W (zero_count: {value['zero_power_count']})")
        else:
            print(f"   {key}: {value}")
    
    print("\n5. Demo running... (Press Ctrl+C to stop)")
    
    # Set up signal handler for graceful shutdown
    def signal_handler(signum, frame):
        print("\nShutting down connection manager...")
        conn_mgr.stop_monitoring()
        print("Demo completed.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Keep demo running
        while True:
            time.sleep(1)
            
            # Show periodic status updates
            if int(time.time()) % 5 == 0:
                print(f"Status: {conn_mgr.state.value} | Reconnect count: {conn_mgr.reconnect_count} | Power: {conn_mgr.power_monitor.current_power:.1f}W")
            
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    demo_connection_manager()
