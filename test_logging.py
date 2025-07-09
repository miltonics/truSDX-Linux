#!/usr/bin/env python3
"""
Test script to demonstrate the new logging functionality.
"""

import sys
import os
import time
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from logging_cfg import configure_logging, log, debug, info, warning, reconnect, error, critical, exception

def test_logging_functionality():
    """Test all logging features."""
    
    print("=== Testing truSDX-AI Logging System ===\n")
    
    # Test 1: Basic configuration
    print("1. Testing basic logging configuration...")
    configure_logging(verbose=True)
    
    # Test 2: Test all log levels
    print("\n2. Testing all log levels...")
    debug("This is a debug message")
    info("This is an info message")
    warning("This is a warning message")
    reconnect("Radio reconnection detected")
    error("This is an error message")
    critical("This is a critical message")
    
    # Test 3: Test backward compatibility
    print("\n3. Testing backward compatibility...")
    log("Legacy log message", "INFO")
    log("Legacy debug message", "DEBUG")
    log("Legacy warning message", "WARNING")
    log("Legacy reconnect message", "RECONNECT")
    log("Legacy error message", "ERROR")
    log("Legacy critical message", "CRITICAL")
    log("Legacy event message", "EVENT")
    
    # Test 4: Test with extra context
    print("\n4. Testing with extra context...")
    info("Message with context", frequency=14074000, mode="FT8", signal_level=-12)
    error("Connection failed", host="192.168.1.100", port=4532, retry_count=3)
    
    # Test 5: Test exception logging
    print("\n5. Testing exception logging...")
    try:
        raise ValueError("Test exception for logging")
    except ValueError as e:
        exception("Caught test exception")
    
    # Test 6: Test custom log file
    print("\n6. Testing custom log file...")
    custom_log = Path("/tmp/trusdx_test.log")
    configure_logging(verbose=True, log_file=str(custom_log))
    info("Message written to custom log file")
    
    if custom_log.exists():
        print(f"Custom log file created: {custom_log}")
        print("Sample log entries:")
        with open(custom_log, 'r') as f:
            lines = f.readlines()
            for line in lines[-3:]:  # Show last 3 lines
                print(f"  {line.strip()}")
    
    # Test 7: Test syslog (if available)
    print("\n7. Testing syslog integration...")
    try:
        configure_logging(verbose=True, enable_syslog=True)
        info("Message sent to syslog")
        print("Syslog handler configured successfully")
    except Exception as e:
        print(f"Syslog not available: {e}")
    
    print("\n=== Logging Test Complete ===")

if __name__ == "__main__":
    test_logging_functionality()
