#!/usr/bin/env python3
"""Test script to diagnose PTT and mode query issues with truSDX"""

import serial
import time
import sys

def test_cat_connection(port='/tmp/trusdx_cat'):
    """Test basic CAT connection and mode queries"""
    try:
        # Open serial connection
        print(f"Opening CAT port: {port}")
        ser = serial.Serial(
            port=port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2,  # 2 second timeout
            write_timeout=1,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False
        )
        
        time.sleep(0.5)  # Let connection stabilize
        
        # Clear any pending data
        if ser.in_waiting > 0:
            old_data = ser.read(ser.in_waiting)
            print(f"Cleared {len(old_data)} bytes of old data")
        
        # Test 1: ID query
        print("\n=== Test 1: ID Query ===")
        ser.write(b'ID;')
        ser.flush()
        time.sleep(0.1)
        
        response = ser.read(100)
        print(f"Sent: ID;")
        print(f"Received: {response}")
        
        # Test 2: Mode query (MD)
        print("\n=== Test 2: Mode Query (MD) ===")
        ser.write(b'MD;')
        ser.flush()
        time.sleep(0.1)
        
        response = ser.read(100)
        print(f"Sent: MD;")
        print(f"Received: {response}")
        
        # Test 3: Multiple rapid mode queries (simulate Hamlib behavior)
        print("\n=== Test 3: Rapid Mode Queries ===")
        for i in range(3):
            ser.write(b'MD;')
            ser.flush()
            time.sleep(0.05)  # 50ms between queries
            
            response = ser.read(100)
            print(f"Query {i+1} - Sent: MD; Received: {response}")
        
        # Test 4: PTT sequence
        print("\n=== Test 4: PTT Test Sequence ===")
        
        # Query initial TX status
        ser.write(b'TX;')
        ser.flush()
        time.sleep(0.1)
        response = ser.read(100)
        print(f"Initial TX status - Sent: TX; Received: {response}")
        
        # Enter TX mode
        print("\nEntering TX mode...")
        ser.write(b'TX1;')
        ser.flush()
        time.sleep(0.5)  # Wait for TX to engage
        
        # Query mode during TX
        ser.write(b'MD;')
        ser.flush()
        time.sleep(0.1)
        response = ser.read(100)
        print(f"Mode during TX - Sent: MD; Received: {response}")
        
        # Exit TX mode
        print("\nExiting TX mode...")
        ser.write(b'TX0;')
        ser.flush()
        time.sleep(0.5)
        
        # Query mode after TX
        ser.write(b'MD;')
        ser.flush()
        time.sleep(0.1)
        response = ser.read(100)
        print(f"Mode after TX - Sent: MD; Received: {response}")
        
        # Test 5: IF command (comprehensive status)
        print("\n=== Test 5: IF Query ===")
        ser.write(b'IF;')
        ser.flush()
        time.sleep(0.1)
        
        response = ser.read(100)
        print(f"Sent: IF;")
        print(f"Received: {response}")
        print(f"Response length: {len(response)} bytes")
        
        ser.close()
        print("\n✅ All tests completed")
        
    except serial.SerialException as e:
        print(f"❌ Serial error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    # Check if trusdx-txrx-AI.py is running
    print("Make sure trusdx-txrx-AI.py is running before running this test!")
    print("Press Enter to continue or Ctrl+C to cancel...")
    input()
    
    # Run the test
    success = test_cat_connection()
    sys.exit(0 if success else 1)
