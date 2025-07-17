#!/usr/bin/env python3
"""Test script to identify correct TX/PTT commands for truSDX radio"""

import serial
import serial.tools.list_ports
import time
import sys

def find_serial_device(name):
    """Find serial device by name"""
    result = [port.device for port in serial.tools.list_ports.comports() if name in port.description]
    return result[0] if len(result) else ""

def test_command(ser, cmd, description):
    """Test a command and show response"""
    print(f"\n[TEST] {description}")
    print(f"Sending: {cmd}")
    
    # Clear any pending data
    if ser.in_waiting > 0:
        ser.read(ser.in_waiting)
    
    # Send command
    ser.write(cmd)
    ser.flush()
    
    # Wait for response
    time.sleep(0.5)
    
    # Read response
    response = b''
    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting)
    
    if response:
        print(f"Response: {response}")
        if b'?' in response:
            print("  ❌ Command rejected!")
        else:
            print("  ✅ Command accepted")
    else:
        print("  ⚠️  No response")
    
    return response

def main():
    print("=== truSDX TX/PTT Command Tester ===\n")
    
    # Find and open serial port
    device = find_serial_device("USB Serial")
    if not device:
        print("❌ truSDX device not found!")
        sys.exit(1)
    
    print(f"Found device: {device}")
    
    try:
        ser = serial.Serial(device, 115200, timeout=1)
        time.sleep(2)  # Wait for device to stabilize
        
        print("\nTesting TX/PTT commands...")
        
        # Test various TX command formats
        test_command(ser, b";TX;", "Query TX status (TX)")
        test_command(ser, b";TX1;", "Enter TX mode (TX1)")
        test_command(ser, b";TX0;", "Exit TX mode (TX0)")
        test_command(ser, b";RX;", "Set RX mode (RX)")
        
        # Test alternative PTT commands that some radios use
        test_command(ser, b";PS1;", "Power on (PS1)")
        test_command(ser, b";PS0;", "Power off (PS0)")
        
        # Test PC (power control)
        test_command(ser, b";PC;", "Query power (PC)")
        test_command(ser, b";PC100;", "Set power 100W (PC100)")
        
        # Test mode
        test_command(ser, b";MD;", "Query mode (MD)")
        test_command(ser, b";MD2;", "Set USB mode (MD2)")
        
        # Test audio mute
        test_command(ser, b";UA;", "Query audio state (UA)")
        test_command(ser, b";UA1;", "Unmute audio (UA1)")
        test_command(ser, b";UA2;", "Mute audio (UA2)")
        
        # Test frequency
        test_command(ser, b";FA;", "Query VFO A frequency (FA)")
        
        # Try alternative TX commands used by some transceivers
        print("\n\nTesting alternative TX command formats...")
        test_command(ser, b";TX;1;", "Alternative TX on (TX;1)")
        test_command(ser, b";TX;0;", "Alternative TX off (TX;0)")
        test_command(ser, b";TX 1;", "Space format TX on")
        test_command(ser, b";TX 0;", "Space format TX off")
        
        # Close serial port
        ser.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
